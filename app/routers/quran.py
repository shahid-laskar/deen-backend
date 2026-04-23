"""Phase 3 + Lovable-Plan Quran Router — full Quran API."""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func, or_

from app.core.dependencies import CurrentUser, DB
from app.repositories import HifzRepo, DuaFavRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import (
    DuaFavoriteCreate, DuaFavoriteResponse,
    HifzProgressCreate, HifzProgressUpdate, HifzReviewSubmit,
    DuaResponse, PersonalDuaCreate, PersonalDuaUpdate, PersonalDuaResponse,
    HadithResponse,
    QuranReadingLogCreate, QuranReadingLogResponse, QuranStatsResponse,
    QuranBookmarkCreate, QuranBookmarkResponse,
    HifzProgressResponseV2,
)
from app.services.quran_service import (
    fetch_surah_list, fetch_surah, fetch_ayah, search_quran, sm2_next_review, fetch_tafsir,
    fetch_juz, fetch_page, fetch_word_by_word,
    RECITERS_LIST, TRANSLATIONS_LIST,
)

router = APIRouter(prefix="/quran", tags=["quran"])

# ─── Static metadata (Lovable Plan #1, #2) ────────────────────────────────────

@router.get("/recitations")
async def list_recitations():
    """List available reciters with id, name, style."""
    return RECITERS_LIST


@router.get("/translations")
async def list_translations():
    """List available translations with id, language, author."""
    return TRANSLATIONS_LIST


# ─── Verse of day ─────────────────────────────────────────────────────────────

@router.get("/verse-of-day")
async def get_verse_of_day():
    """Fetch a random ayah for the daily highlight."""
    import random
    s = random.randint(1, 114)
    try:
        surah_data = await fetch_surah(s)
        verses = surah_data.get("verses", [])
        if not verses: raise Exception("No verses")
        v = random.choice(verses)
        return v
    except Exception:
        return await fetch_ayah(1, 1)

TOTAL_QURAN_VERSES = 6236

# ─── Surah / text ─────────────────────────────────────────────────────────────

@router.get("/surahs")
async def list_surahs():
    try: return await fetch_surah_list()
    except Exception as e: raise HTTPException(503, f"Quran API unavailable: {e}")


@router.get("/surah/{n}")
async def get_surah(n: int, translation_id: int = Query(default=131), reciter_id: int = Query(default=7)):
    if not 1 <= n <= 114: raise HTTPException(422, "Surah 1-114.")
    try: return await fetch_surah(n, translation_id, reciter_id)
    except Exception as e: raise HTTPException(503, str(e))


@router.get("/ayah/{s}/{a}")
async def get_ayah(s: int, a: int):
    try: return await fetch_ayah(s, a)
    except Exception as e: raise HTTPException(503, str(e))


@router.get("/tafsir/{s}/{a}")
async def get_tafsir(s: int, a: int, tafsir_id: int = Query(default=169)):
    try: return await fetch_tafsir(s, a, tafsir_id)
    except Exception as e: raise HTTPException(503, str(e))


@router.get("/search")
async def search(q: str = Query(min_length=2), language: str = "en", page: int = Query(default=1, ge=1)):
    try: return await search_quran(q, language, size=50, page=page)
    except Exception as e: raise HTTPException(503, str(e))


# ─── Juz & Mushaf page (Lovable Plan #3) ─────────────────────────────────────

@router.get("/juz/{n}")
async def get_juz(n: int):
    """Browse Quran by Juz (1-30)."""
    if not 1 <= n <= 30: raise HTTPException(422, "Juz must be 1-30.")
    try: return await fetch_juz(n)
    except Exception as e: raise HTTPException(503, str(e))


@router.get("/page/{n}")
async def get_mushaf_page(n: int):
    """Browse Quran by Mushaf page (1-604)."""
    if not 1 <= n <= 604: raise HTTPException(422, "Page must be 1-604.")
    try: return await fetch_page(n)
    except Exception as e: raise HTTPException(503, str(e))


# ─── Word-by-word (Lovable Plan #8) ──────────────────────────────────────────

@router.get("/word-by-word/{s}/{a}")
async def get_word_by_word(s: int, a: int):
    """Word-level translation for tap-to-learn."""
    try: return await fetch_word_by_word(s, a)
    except Exception as e: raise HTTPException(503, str(e))


# ─── Server-side last-read sync (Lovable Plan #4) ────────────────────────────

@router.get("/last-read")
async def get_last_read(current_user: CurrentUser, db: DB):
    from app.models.quran import QuranLastRead
    result = await db.execute(select(QuranLastRead).where(QuranLastRead.user_id == current_user.id))
    row = result.scalar_one_or_none()
    if not row:
        return {"surah_number": 1, "ayah_number": 1, "surah_name": "Al-Fatihah"}
    return {
        "surah_number": row.surah_number, "ayah_number": row.ayah_number,
        "surah_name": row.surah_name, "surah_arabic": row.surah_arabic,
        "total_ayahs": row.total_ayahs,
    }


@router.post("/last-read")
async def save_last_read(
    surah_number: int = Query(...),
    ayah_number: int = Query(default=1),
    surah_name: Optional[str] = Query(default=None),
    surah_arabic: Optional[str] = Query(default=None),
    total_ayahs: Optional[int] = Query(default=None),
    current_user: CurrentUser = None,
    db: DB = None,
):
    from app.models.quran import QuranLastRead
    result = await db.execute(select(QuranLastRead).where(QuranLastRead.user_id == current_user.id))
    row = result.scalar_one_or_none()
    if row:
        row.surah_number = surah_number; row.ayah_number = ayah_number
        if surah_name: row.surah_name = surah_name
        if surah_arabic: row.surah_arabic = surah_arabic
        if total_ayahs: row.total_ayahs = total_ayahs
    else:
        row = QuranLastRead(
            user_id=current_user.id,
            surah_number=surah_number, ayah_number=ayah_number,
            surah_name=surah_name, surah_arabic=surah_arabic, total_ayahs=total_ayahs,
        )
        db.add(row)
    await db.flush()
    return {"saved": True}


# ─── Reading logs & stats ─────────────────────────────────────────────────────

@router.post("/reading-log", response_model=QuranReadingLogResponse, status_code=201)
async def log_reading(payload: QuranReadingLogCreate, current_user: CurrentUser, db: DB):
    from app.models.quran import QuranReadingLog
    log = QuranReadingLog(user_id=current_user.id, log_date=payload.log_date or date.today(),
                          **{k:v for k,v in payload.model_dump(exclude={"log_date"}).items()})
    db.add(log); await db.flush(); await db.refresh(log)
    return QuranReadingLogResponse.model_validate(log)


@router.get("/reading-log", response_model=list[QuranReadingLogResponse])
async def get_reading_logs(current_user: CurrentUser, db: DB, days: int = Query(default=30, ge=1, le=365)):
    from app.models.quran import QuranReadingLog
    start = date.today() - timedelta(days=days)
    result = await db.execute(select(QuranReadingLog).where(
        QuranReadingLog.user_id == current_user.id, QuranReadingLog.log_date >= start
    ).order_by(QuranReadingLog.log_date.desc()))
    return [QuranReadingLogResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/stats", response_model=QuranStatsResponse)
async def get_stats(current_user: CurrentUser, db: DB):
    from app.models.quran import QuranReadingLog
    month_start = date.today().replace(day=1)
    total = (await db.execute(select(
        func.sum(QuranReadingLog.verses_read), func.sum(QuranReadingLog.minutes_read),
        func.sum(QuranReadingLog.minutes_listened)
    ).where(QuranReadingLog.user_id == current_user.id))).one()
    month = (await db.execute(select(
        func.sum(QuranReadingLog.verses_read), func.sum(QuranReadingLog.minutes_read), func.count()
    ).where(QuranReadingLog.user_id == current_user.id, QuranReadingLog.log_date >= month_start))).one()
    tv, tmr, tml = int(total[0] or 0), int(total[1] or 0), int(total[2] or 0)
    mv, mmr, sessions = int(month[0] or 0), int(month[1] or 0), int(month[2] or 0)
    days_e = (date.today() - month_start).days + 1
    avg = round(mmr / days_e, 1) if days_e > 0 else 0.0
    pct = round((tv / TOTAL_QURAN_VERSES) * 100, 2)
    proj = None
    if avg > 0 and tv < TOTAL_QURAN_VERSES:
        vpm = tv / max(tmr, 1)
        proj = int((TOTAL_QURAN_VERSES - tv) / max(vpm * avg, 0.01))
    return QuranStatsResponse(
        total_verses_read=tv, total_minutes_read=tmr, total_minutes_listened=tml,
        verses_this_month=mv, minutes_this_month=mmr, sessions_this_month=sessions,
        avg_daily_minutes=avg, projected_khatam_days=proj, khatam_progress_pct=min(pct, 100.0)
    )


# ─── Bookmarks ────────────────────────────────────────────────────────────────

@router.get("/bookmarks", response_model=list[QuranBookmarkResponse])
async def list_bookmarks(current_user: CurrentUser, db: DB, folder_id: Optional[UUID] = None):
    from app.models.quran import QuranBookmark
    q = select(QuranBookmark).where(QuranBookmark.user_id == current_user.id)
    if folder_id: q = q.where(QuranBookmark.folder_id == folder_id)
    result = await db.execute(q.order_by(QuranBookmark.surah_number, QuranBookmark.ayah_number))
    return [QuranBookmarkResponse.model_validate(b) for b in result.scalars().all()]


@router.post("/bookmarks", response_model=QuranBookmarkResponse, status_code=201)
async def add_bookmark(payload: QuranBookmarkCreate, current_user: CurrentUser, db: DB):
    from app.models.quran import QuranBookmark
    bm = QuranBookmark(user_id=current_user.id, **payload.model_dump())
    db.add(bm); await db.flush(); await db.refresh(bm)
    return QuranBookmarkResponse.model_validate(bm)


@router.delete("/bookmarks/{bookmark_id}", response_model=MessageResponse)
async def delete_bookmark(bookmark_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.quran import QuranBookmark
    result = await db.execute(select(QuranBookmark).where(
        QuranBookmark.id == bookmark_id, QuranBookmark.user_id == current_user.id
    ))
    bm = result.scalar_one_or_none()
    if not bm: raise HTTPException(404, "Bookmark not found.")
    await db.delete(bm)
    return MessageResponse(message="Bookmark removed.")


# ─── Bookmark folders (Lovable Plan #5) ──────────────────────────────────────

@router.get("/bookmarks/folders")
async def list_bookmark_folders(current_user: CurrentUser, db: DB):
    from app.models.quran import BookmarkFolder
    result = await db.execute(
        select(BookmarkFolder).where(BookmarkFolder.user_id == current_user.id)
        .order_by(BookmarkFolder.sort_order, BookmarkFolder.created_at)
    )
    folders = result.scalars().all()
    return [{"id": str(f.id), "name": f.name, "color": f.color, "sort_order": f.sort_order} for f in folders]


@router.post("/bookmarks/folders", status_code=201)
async def create_bookmark_folder(
    name: str = Query(...), color: Optional[str] = Query(default=None),
    current_user: CurrentUser = None, db: DB = None,
):
    from app.models.quran import BookmarkFolder
    folder = BookmarkFolder(user_id=current_user.id, name=name, color=color)
    db.add(folder); await db.flush(); await db.refresh(folder)
    return {"id": str(folder.id), "name": folder.name, "color": folder.color}


@router.delete("/bookmarks/folders/{folder_id}", response_model=MessageResponse)
async def delete_bookmark_folder(folder_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.quran import BookmarkFolder
    result = await db.execute(select(BookmarkFolder).where(
        BookmarkFolder.id == folder_id, BookmarkFolder.user_id == current_user.id
    ))
    folder = result.scalar_one_or_none()
    if not folder: raise HTTPException(404, "Folder not found.")
    await db.delete(folder)
    return MessageResponse(message="Folder deleted.")


# ─── Hifz (Leitner + SM-2) ────────────────────────────────────────────────────

@router.get("/hifz", response_model=list[HifzProgressResponseV2])
async def list_hifz(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    return [HifzProgressResponseV2.model_validate(h) for h in await hifz_repo.get_all_for_user(current_user.id)]


@router.get("/hifz/due", response_model=list[HifzProgressResponseV2])
async def hifz_due(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    return [HifzProgressResponseV2.model_validate(h) for h in await hifz_repo.get_due_today(current_user.id)]


@router.get("/hifz/due-today", response_model=list[HifzProgressResponseV2])
async def hifz_due_today(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    return [HifzProgressResponseV2.model_validate(h) for h in await hifz_repo.get_due_today(current_user.id)]


@router.get("/hifz/stats")
async def hifz_stats(current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    """Hifz-specific aggregates (Lovable Plan #6)."""
    from app.models.quran import HifzProgress
    all_entries = await hifz_repo.get_all_for_user(current_user.id)
    due_today = await hifz_repo.get_due_today(current_user.id)
    total_verses = sum(h.ayah_to - h.ayah_from + 1 for h in all_entries)
    memorised = [h for h in all_entries if h.status == "memorised"]
    memorised_verses = sum(h.ayah_to - h.ayah_from + 1 for h in memorised)
    by_surah: dict = {}
    for h in all_entries:
        key = h.surah_number
        if key not in by_surah:
            by_surah[key] = {"surah_number": key, "surah_name": h.surah_name, "verses": 0, "status": h.status}
        by_surah[key]["verses"] += h.ayah_to - h.ayah_from + 1
    logs_result = await db.execute(
        select(HifzProgress.last_reviewed)
        .where(HifzProgress.user_id == current_user.id, HifzProgress.last_reviewed != None)
        .distinct().order_by(HifzProgress.last_reviewed.desc())
    )
    review_days = [r[0] for r in logs_result.all()]
    streak = 0
    today = date.today()
    for i, d in enumerate(review_days):
        if d == today - timedelta(days=i): streak += 1
        else: break
    return {
        "total_entries": len(all_entries), "total_verses_tracked": total_verses,
        "memorised_count": len(memorised), "memorised_verses": memorised_verses,
        "due_today_count": len(due_today), "review_streak_days": streak,
        "leitner_distribution": {
            str(box): sum(1 for h in all_entries if (h.leitner_box or 1) == box)
            for box in range(1, 6)
        },
        "by_surah": list(by_surah.values()),
    }


@router.post("/hifz", response_model=HifzProgressResponseV2, status_code=201)
async def add_hifz(payload: HifzProgressCreate, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    if await hifz_repo.get_by_surah_ayah(current_user.id, payload.surah_number, payload.ayah_from):
        raise HTTPException(409, "This ayah range is already in your Hifz tracker.")
    entry = await hifz_repo.create(
        user_id=current_user.id, **payload.model_dump(),
        status="in_progress", next_review=date.today(), leitner_box=1
    )
    return HifzProgressResponseV2.model_validate(entry)


@router.post("/hifz/{entry_id}/review", response_model=HifzProgressResponseV2)
async def review_hifz(entry_id: UUID, payload: HifzReviewSubmit, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    if not 0 <= payload.quality <= 5: raise HTTPException(422, "Quality 0-5.")
    entry = await hifz_repo.get_owned_or_404(entry_id, current_user.id)
    new_ef, new_interval, next_review = sm2_next_review(payload.quality, entry.ease_factor, entry.interval_days, entry.review_count)
    box = entry.leitner_box or 1
    if payload.quality >= 4:    new_box, new_status = min(5, box+1), ("memorised" if box+1 >= 5 else "in_progress")
    elif payload.quality <= 1:  new_box, new_status = 1, "needs_review"
    else:                       new_box, new_status = box, "in_progress"
    entry = await hifz_repo.update(
        entry, ease_factor=new_ef, interval_days=new_interval, next_review=next_review,
        last_reviewed=date.today(), review_count=entry.review_count+1,
        status=new_status, leitner_box=new_box
    )
    return HifzProgressResponseV2.model_validate(entry)


@router.patch("/hifz/{entry_id}", response_model=HifzProgressResponseV2)
async def update_hifz(entry_id: UUID, payload: HifzProgressUpdate, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    entry = await hifz_repo.get_owned_or_404(entry_id, current_user.id)
    return HifzProgressResponseV2.model_validate(await hifz_repo.update(entry, **payload.model_dump(exclude_none=True)))


@router.delete("/hifz/{entry_id}", response_model=MessageResponse)
async def delete_hifz(entry_id: UUID, current_user: CurrentUser, db: DB, hifz_repo: HifzRepo):
    await hifz_repo.delete(await hifz_repo.get_owned_or_404(entry_id, current_user.id))
    return MessageResponse(message="Hifz entry deleted.")


# ─── Khatam plans (Lovable Plan #7) ──────────────────────────────────────────

@router.get("/khatam-plans")
async def list_khatam_plans(current_user: CurrentUser, db: DB):
    from app.models.quran import KhatamPlan
    result = await db.execute(
        select(KhatamPlan).where(KhatamPlan.user_id == current_user.id)
        .order_by(KhatamPlan.is_active.desc(), KhatamPlan.created_at.desc())
    )
    plans = result.scalars().all()
    today = date.today()
    return [{
        "id": str(p.id), "name": p.name,
        "target_date": p.target_date.isoformat() if p.target_date else None,
        "daily_verse_goal": p.daily_verse_goal, "is_active": p.is_active,
        "start_date": p.start_date.isoformat(),
        "days_left": max(0, (p.target_date - today).days) if p.target_date else None,
    } for p in plans]


@router.post("/khatam-plans", status_code=201)
async def create_khatam_plan(
    daily_verse_goal: int = Query(default=20, ge=1),
    target_date: Optional[date] = Query(default=None),
    name: Optional[str] = Query(default=None),
    current_user: CurrentUser = None, db: DB = None,
):
    from app.models.quran import KhatamPlan
    result = await db.execute(
        select(KhatamPlan).where(KhatamPlan.user_id == current_user.id, KhatamPlan.is_active == True)
    )
    for old in result.scalars().all(): old.is_active = False
    plan = KhatamPlan(
        user_id=current_user.id, name=name or "Khatam Plan",
        daily_verse_goal=daily_verse_goal, target_date=target_date,
        start_date=date.today(), is_active=True,
    )
    db.add(plan); await db.flush(); await db.refresh(plan)
    return {"id": str(plan.id), "name": plan.name, "daily_verse_goal": plan.daily_verse_goal}


@router.delete("/khatam-plans/{plan_id}", response_model=MessageResponse)
async def delete_khatam_plan(plan_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.quran import KhatamPlan
    result = await db.execute(select(KhatamPlan).where(
        KhatamPlan.id == plan_id, KhatamPlan.user_id == current_user.id
    ))
    plan = result.scalar_one_or_none()
    if not plan: raise HTTPException(404, "Plan not found.")
    await db.delete(plan)
    return MessageResponse(message="Plan deleted.")


# ─── Duas ─────────────────────────────────────────────────────────────────────

@router.get("/duas/categories")
async def dua_categories(db: DB):
    from app.models.quran import Dua
    result = await db.execute(select(Dua.category, func.count().label("count")).group_by(Dua.category).order_by(Dua.category))
    return [{"category": r.category, "count": r.count} for r in result.all()]


@router.get("/duas/of-the-day", response_model=DuaResponse)
async def dua_of_day(db: DB):
    from app.models.quran import Dua
    result = await db.execute(select(Dua).order_by(Dua.dua_order))
    duas = result.scalars().all()
    if not duas: raise HTTPException(404, "No duas seeded.")
    return DuaResponse.model_validate(duas[date.today().timetuple().tm_yday % len(duas)])


@router.get("/duas/personal", response_model=list[PersonalDuaResponse])
async def list_personal_duas(current_user: CurrentUser, db: DB):
    from app.models.quran import PersonalDua
    result = await db.execute(select(PersonalDua).where(PersonalDua.user_id == current_user.id).order_by(PersonalDua.date_started.desc()))
    return [PersonalDuaResponse.model_validate(d) for d in result.scalars().all()]


@router.post("/duas/personal", response_model=PersonalDuaResponse, status_code=201)
async def create_personal_dua(payload: PersonalDuaCreate, current_user: CurrentUser, db: DB):
    from app.models.quran import PersonalDua
    pd = PersonalDua(user_id=current_user.id, title=payload.title, text=payload.text, date_started=payload.date_started or date.today())
    db.add(pd); await db.flush(); await db.refresh(pd)
    return PersonalDuaResponse.model_validate(pd)


@router.patch("/duas/personal/{dua_id}", response_model=PersonalDuaResponse)
async def update_personal_dua(dua_id: UUID, payload: PersonalDuaUpdate, current_user: CurrentUser, db: DB):
    from app.models.quran import PersonalDua
    result = await db.execute(select(PersonalDua).where(PersonalDua.id == dua_id, PersonalDua.user_id == current_user.id))
    pd = result.scalar_one_or_none()
    if not pd: raise HTTPException(404, "Personal dua not found.")
    for f, v in payload.model_dump(exclude_none=True).items(): setattr(pd, f, v)
    if payload.is_answered and not pd.answered_date: pd.answered_date = date.today()
    await db.flush(); await db.refresh(pd)
    return PersonalDuaResponse.model_validate(pd)


@router.delete("/duas/personal/{dua_id}", response_model=MessageResponse)
async def delete_personal_dua(dua_id: UUID, current_user: CurrentUser, db: DB):
    from app.models.quran import PersonalDua
    result = await db.execute(select(PersonalDua).where(PersonalDua.id == dua_id, PersonalDua.user_id == current_user.id))
    pd = result.scalar_one_or_none()
    if not pd: raise HTTPException(404, "Personal dua not found.")
    await db.delete(pd)
    return MessageResponse(message="Personal dua deleted.")


@router.get("/duas/favorites", response_model=list[DuaFavoriteResponse])
async def list_favorites(current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    return [DuaFavoriteResponse.model_validate(f) for f in await dua_fav_repo.get_all_for_user(current_user.id)]


@router.post("/duas/favorites", response_model=DuaFavoriteResponse, status_code=201)
async def add_favorite(payload: DuaFavoriteCreate, current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    if await dua_fav_repo.key_exists(current_user.id, payload.dua_key): raise HTTPException(409, "Already in favorites.")
    return DuaFavoriteResponse.model_validate(await dua_fav_repo.create(user_id=current_user.id, **payload.model_dump()))


@router.delete("/duas/favorites/{fav_id}", response_model=MessageResponse)
async def remove_favorite(fav_id: UUID, current_user: CurrentUser, db: DB, dua_fav_repo: DuaFavRepo):
    await dua_fav_repo.delete(await dua_fav_repo.get_owned_or_404(fav_id, current_user.id))
    return MessageResponse(message="Removed from favorites.")


@router.get("/duas", response_model=list[DuaResponse])
async def list_duas(db: DB, category: Optional[str] = None, limit: int = Query(default=50, le=200), offset: int = 0):
    from app.models.quran import Dua
    q = select(Dua).order_by(Dua.category, Dua.dua_order)
    if category: q = q.where(Dua.category == category)
    result = await db.execute(q.limit(limit).offset(offset))
    return [DuaResponse.model_validate(d) for d in result.scalars().all()]


@router.get("/duas/{key}", response_model=DuaResponse)
async def get_dua(key: str, db: DB):
    from app.models.quran import Dua
    result = await db.execute(select(Dua).where(Dua.key == key))
    dua = result.scalar_one_or_none()
    if not dua: raise HTTPException(404, f"Dua '{key}' not found.")
    return DuaResponse.model_validate(dua)


@router.post("/duas/seed", response_model=MessageResponse)
async def seed_duas_endpoint(db: DB, current_user: CurrentUser):
    from app.services.dua_seed import seed_duas
    count = await seed_duas(db); await db.commit()
    return MessageResponse(message=f"Seeded {count} new duas.")


# ─── Hadith ───────────────────────────────────────────────────────────────────

@router.get("/hadith/of-the-day", response_model=HadithResponse)
async def hadith_of_day(db: DB):
    from app.models.quran import Hadith
    result = await db.execute(select(Hadith))
    hadiths = result.scalars().all()
    if not hadiths: raise HTTPException(404, "No hadiths seeded.")
    return HadithResponse.model_validate(hadiths[date.today().timetuple().tm_yday % len(hadiths)])


@router.get("/hadith/search", response_model=list[HadithResponse])
async def search_hadith_endpoint(db: DB, q: str = Query(min_length=2), collection: Optional[str] = None):
    from app.models.quran import Hadith
    query = select(Hadith).where(or_(Hadith.english_text.ilike(f"%{q}%"), Hadith.topics.ilike(f"%{q}%"))).limit(20)
    if collection: query = query.where(Hadith.collection == collection)
    return [HadithResponse.model_validate(h) for h in (await db.execute(query)).scalars().all()]


@router.get("/hadith", response_model=list[HadithResponse])
async def list_hadith(db: DB, collection: Optional[str] = None, grade: Optional[str] = None, limit: int = Query(default=20, le=100)):
    from app.models.quran import Hadith
    q = select(Hadith)
    if collection: q = q.where(Hadith.collection == collection)
    if grade: q = q.where(Hadith.grade == grade)
    return [HadithResponse.model_validate(h) for h in (await db.execute(q.limit(limit))).scalars().all()]


@router.get("/hadith/{hadith_id}", response_model=HadithResponse)
async def get_hadith(hadith_id: UUID, db: DB):
    from app.models.quran import Hadith
    result = await db.execute(select(Hadith).where(Hadith.id == hadith_id))
    h = result.scalar_one_or_none()
    if not h: raise HTTPException(404, "Hadith not found.")
    return HadithResponse.model_validate(h)


@router.post("/hadith/seed", response_model=MessageResponse)
async def seed_hadiths_endpoint(db: DB, current_user: CurrentUser):
    from app.services.hadith_seed import seed_hadiths
    count = await seed_hadiths(db); await db.commit()
    return MessageResponse(message=f"Seeded {count} new hadiths.")
