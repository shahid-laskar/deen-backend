from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DB
from app.repositories import HifzRepo, DuaFavRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    DuaFavoriteCreate, DuaFavoriteResponse,
    HifzProgressCreate, HifzProgressResponse,
    HifzProgressUpdate, HifzReviewSubmit,
)
from app.services.quran_service import (
    fetch_surah_list, fetch_surah, fetch_ayah, search_quran,
    sm2_next_review, get_duas_by_category, get_dua_by_key,
)

router = APIRouter(prefix="/quran", tags=["quran"])


@router.get("/surahs")
async def list_surahs():
    try:
        return await fetch_surah_list()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quran API unavailable: {e}")


@router.get("/surah/{surah_number}")
async def get_surah(surah_number: int, translation_id: int = Query(default=131)):
    if not 1 <= surah_number <= 114:
        raise HTTPException(status_code=422, detail="Surah number must be between 1 and 114.")
    try:
        return await fetch_surah(surah_number, translation_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quran API unavailable: {e}")


@router.get("/ayah/{surah_number}/{ayah_number}")
async def get_ayah(surah_number: int, ayah_number: int):
    try:
        return await fetch_ayah(surah_number, ayah_number)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/search")
async def search(q: str = Query(min_length=2), language: str = Query(default="en")):
    try:
        return await search_quran(q, language)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ─── Hifz ─────────────────────────────────────────────────────────────────────

@router.get("/hifz", response_model=list[HifzProgressResponse])
async def list_hifz(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    entries = await hifz_repo.get_all_for_user(current_user.id)
    return [HifzProgressResponse.model_validate(h) for h in entries]


@router.get("/hifz/due-today", response_model=list[HifzProgressResponse])
async def hifz_due_today(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    entries = await hifz_repo.get_due_today(current_user.id)
    return [HifzProgressResponse.model_validate(h) for h in entries]


@router.post("/hifz", response_model=HifzProgressResponse, status_code=201)
async def add_hifz_entry(payload: HifzProgressCreate, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    existing = await hifz_repo.get_by_surah_ayah(current_user.id, payload.surah_number, payload.ayah_from)
    if existing:
        raise HTTPException(status_code=409, detail="This ayah range is already in your Hifz tracker.")
    entry = await hifz_repo.create(
        user_id=current_user.id,
        **payload.model_dump(),
        status="in_progress",
        next_review=date.today(),
    )
    return HifzProgressResponse.model_validate(entry)


@router.post("/hifz/{entry_id}/review", response_model=HifzProgressResponse)
async def submit_hifz_review(entry_id: UUID, payload: HifzReviewSubmit, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    if not 0 <= payload.quality <= 5:
        raise HTTPException(status_code=422, detail="Quality must be between 0 and 5.")
    entry = await hifz_repo.get_owned_or_404(entry_id, current_user.id)
    new_ef, new_interval, next_review = sm2_next_review(
        quality=payload.quality,
        ease_factor=entry.ease_factor,
        interval_days=entry.interval_days,
        review_count=entry.review_count,
    )
    new_status = "memorised" if payload.quality >= 4 else ("needs_review" if payload.quality <= 1 else "in_progress")
    entry = await hifz_repo.update(
        entry,
        ease_factor=new_ef,
        interval_days=new_interval,
        next_review=next_review,
        last_reviewed=date.today(),
        review_count=entry.review_count + 1,
        status=new_status,
    )
    return HifzProgressResponse.model_validate(entry)


@router.patch("/hifz/{entry_id}", response_model=HifzProgressResponse)
async def update_hifz_entry(entry_id: UUID, payload: HifzProgressUpdate, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    entry = await hifz_repo.get_owned_or_404(entry_id, current_user.id)
    entry = await hifz_repo.update(entry, **payload.model_dump(exclude_none=True))
    return HifzProgressResponse.model_validate(entry)


@router.delete("/hifz/{entry_id}", response_model=MessageResponse)
async def delete_hifz_entry(entry_id: UUID, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    entry = await hifz_repo.get_owned_or_404(entry_id, current_user.id)
    await hifz_repo.delete(entry)
    return MessageResponse(message="Hifz entry deleted.")


# ─── Duas ──────────────────────────────────────────────────────────────────────

@router.get("/duas")
async def list_duas(category: Optional[str] = Query(default=None)):
    return get_duas_by_category(category)


@router.get("/duas/{key}")
async def get_dua(key: str):
    dua = get_dua_by_key(key)
    if not dua:
        raise HTTPException(status_code=404, detail="Dua not found.")
    return dua


@router.get("/duas/favorites", response_model=list[DuaFavoriteResponse])
async def list_dua_favorites(current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    favs = await dua_fav_repo.get_all_for_user(current_user.id)
    return [DuaFavoriteResponse.model_validate(f) for f in favs]


@router.post("/duas/favorites", response_model=DuaFavoriteResponse, status_code=201)
async def add_dua_favorite(payload: DuaFavoriteCreate, current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    if not get_dua_by_key(payload.dua_key):
        raise HTTPException(status_code=404, detail="Dua key not found in library.")
    if await dua_fav_repo.key_exists(current_user.id, payload.dua_key):
        raise HTTPException(status_code=409, detail="Already in favorites.")
    fav = await dua_fav_repo.create(user_id=current_user.id, **payload.model_dump())
    return DuaFavoriteResponse.model_validate(fav)


@router.delete("/duas/favorites/{fav_id}", response_model=MessageResponse)
async def remove_dua_favorite(fav_id: UUID, current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    fav = await dua_fav_repo.get_owned_or_404(fav_id, current_user.id)
    await dua_fav_repo.delete(fav)
    return MessageResponse(message="Removed from favorites.")
