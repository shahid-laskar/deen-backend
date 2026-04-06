from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB
from app.models.quran import HifzProgress, DuaFavorite
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    DuaFavoriteCreate,
    DuaFavoriteResponse,
    HifzProgressCreate,
    HifzProgressResponse,
    HifzProgressUpdate,
    HifzReviewSubmit,
)
from app.services.quran_service import (
    fetch_surah_list,
    fetch_surah,
    fetch_ayah,
    search_quran,
    sm2_next_review,
    get_duas_by_category,
    get_dua_by_key,
)

router = APIRouter(prefix="/quran", tags=["quran"])


# ─── Quran Content ────────────────────────────────────────────────────────────

@router.get("/surahs")
async def list_surahs():
    """List all 114 surahs with metadata."""
    try:
        return await fetch_surah_list()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quran API unavailable: {e}")


@router.get("/surah/{surah_number}")
async def get_surah(
    surah_number: int,
    translation_id: int = Query(default=131, description="Quran.com translation ID"),
):
    """Get a full surah with translation."""
    if not 1 <= surah_number <= 114:
        raise HTTPException(status_code=422, detail="Surah number must be between 1 and 114.")
    try:
        return await fetch_surah(surah_number, translation_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quran API unavailable: {e}")


@router.get("/ayah/{surah_number}/{ayah_number}")
async def get_ayah(surah_number: int, ayah_number: int):
    """Get a single ayah with translation and audio."""
    try:
        return await fetch_ayah(surah_number, ayah_number)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quran API unavailable: {e}")


@router.get("/search")
async def search(q: str = Query(min_length=2), language: str = Query(default="en")):
    """Search the Quran by keyword."""
    try:
        return await search_quran(q, language)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ─── Hifz Tracker ────────────────────────────────────────────────────────────

@router.get("/hifz", response_model=list[HifzProgressResponse])
async def list_hifz(current_user: CurrentUser, db: DB):
    """List all Hifz progress entries for the user."""
    result = await db.execute(
        select(HifzProgress)
        .where(HifzProgress.user_id == current_user.id)
        .order_by(HifzProgress.surah_number, HifzProgress.ayah_from)
    )
    return [HifzProgressResponse.model_validate(h) for h in result.scalars().all()]


@router.get("/hifz/due-today", response_model=list[HifzProgressResponse])
async def hifz_due_today(current_user: CurrentUser, db: DB):
    """Get all Hifz entries due for review today or overdue."""
    today = date.today()
    result = await db.execute(
        select(HifzProgress).where(
            HifzProgress.user_id == current_user.id,
            HifzProgress.next_review <= today,
            HifzProgress.status.in_(["in_progress", "memorised", "needs_review"]),
        ).order_by(HifzProgress.next_review)
    )
    return [HifzProgressResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/hifz", response_model=HifzProgressResponse, status_code=201)
async def add_hifz_entry(payload: HifzProgressCreate, current_user: CurrentUser, db: DB):
    """Add a new surah/ayah range to the Hifz tracker."""
    # Check duplicate
    result = await db.execute(
        select(HifzProgress).where(
            HifzProgress.user_id == current_user.id,
            HifzProgress.surah_number == payload.surah_number,
            HifzProgress.ayah_from == payload.ayah_from,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This ayah range is already in your Hifz tracker.")

    entry = HifzProgress(
        user_id=current_user.id,
        **payload.model_dump(),
        status="in_progress",
        next_review=date.today(),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return HifzProgressResponse.model_validate(entry)


@router.post("/hifz/{entry_id}/review", response_model=HifzProgressResponse)
async def submit_hifz_review(
    entry_id: UUID,
    payload: HifzReviewSubmit,
    current_user: CurrentUser,
    db: DB,
):
    """Submit a review rating (0–5) for a Hifz entry. Updates SM-2 schedule."""
    if not 0 <= payload.quality <= 5:
        raise HTTPException(status_code=422, detail="Quality must be between 0 and 5.")

    result = await db.execute(
        select(HifzProgress).where(
            HifzProgress.id == entry_id,
            HifzProgress.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Hifz entry not found.")

    new_ef, new_interval, next_review = sm2_next_review(
        quality=payload.quality,
        ease_factor=entry.ease_factor,
        interval_days=entry.interval_days,
        review_count=entry.review_count,
    )

    entry.ease_factor = new_ef
    entry.interval_days = new_interval
    entry.next_review = next_review
    entry.last_reviewed = date.today()
    entry.review_count += 1
    entry.status = "memorised" if payload.quality >= 4 else (
        "needs_review" if payload.quality <= 1 else "in_progress"
    )

    await db.flush()
    await db.refresh(entry)
    return HifzProgressResponse.model_validate(entry)


@router.patch("/hifz/{entry_id}", response_model=HifzProgressResponse)
async def update_hifz_entry(
    entry_id: UUID,
    payload: HifzProgressUpdate,
    current_user: CurrentUser,
    db: DB,
):
    result = await db.execute(
        select(HifzProgress).where(
            HifzProgress.id == entry_id,
            HifzProgress.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)

    await db.flush()
    await db.refresh(entry)
    return HifzProgressResponse.model_validate(entry)


@router.delete("/hifz/{entry_id}", response_model=MessageResponse)
async def delete_hifz_entry(entry_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(HifzProgress).where(
            HifzProgress.id == entry_id,
            HifzProgress.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found.")
    await db.delete(entry)
    return MessageResponse(message="Hifz entry deleted.")


# ─── Dua Library ─────────────────────────────────────────────────────────────

@router.get("/duas")
async def list_duas(category: Optional[str] = Query(default=None)):
    """List all duas, optionally filtered by category."""
    return get_duas_by_category(category)


@router.get("/duas/{key}")
async def get_dua(key: str):
    """Get a specific dua by key."""
    dua = get_dua_by_key(key)
    if not dua:
        raise HTTPException(status_code=404, detail="Dua not found.")
    return dua


@router.get("/duas/favorites", response_model=list[DuaFavoriteResponse])
async def list_dua_favorites(current_user: CurrentUser, db: DB):
    """Get user's saved dua favorites."""
    result = await db.execute(
        select(DuaFavorite).where(DuaFavorite.user_id == current_user.id)
    )
    return [DuaFavoriteResponse.model_validate(f) for f in result.scalars().all()]


@router.post("/duas/favorites", response_model=DuaFavoriteResponse, status_code=201)
async def add_dua_favorite(payload: DuaFavoriteCreate, current_user: CurrentUser, db: DB):
    """Save a dua to favorites."""
    # Validate dua exists
    if not get_dua_by_key(payload.dua_key):
        raise HTTPException(status_code=404, detail="Dua key not found in library.")

    result = await db.execute(
        select(DuaFavorite).where(
            DuaFavorite.user_id == current_user.id,
            DuaFavorite.dua_key == payload.dua_key,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in favorites.")

    fav = DuaFavorite(user_id=current_user.id, **payload.model_dump())
    db.add(fav)
    await db.flush()
    await db.refresh(fav)
    return DuaFavoriteResponse.model_validate(fav)


@router.delete("/duas/favorites/{fav_id}", response_model=MessageResponse)
async def remove_dua_favorite(fav_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(DuaFavorite).where(
            DuaFavorite.id == fav_id,
            DuaFavorite.user_id == current_user.id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found.")
    await db.delete(fav)
    return MessageResponse(message="Removed from favorites.")
