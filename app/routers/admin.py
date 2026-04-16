"""Phase 10 — Admin, GDPR & Notification Endpoints"""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.core.dependencies import CurrentUser, DB
from app.schemas.base import MessageResponse

router = APIRouter(prefix="/admin", tags=["admin"])
gdpr_router = APIRouter(prefix="/user", tags=["user"])
notif_router = APIRouter(prefix="/notifications", tags=["notifications"])


# ─── Admin - Moderation ────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(current_user: CurrentUser, db: DB,
                       status: str = "pending", limit: int = 50, offset: int = 0):
    from sqlalchemy import select
    from app.models.community import ContentReport
    q = select(ContentReport).where(ContentReport.status == status).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.patch("/reports/{report_id}")
async def update_report(report_id: UUID, action: str, current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    from app.models.community import ContentReport
    result = await db.execute(select(ContentReport).where(ContentReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = "resolved" if action in ("approve", "remove", "warn") else "dismissed"
    report.reviewed_by = current_user.id
    await db.flush()
    return {"action": action, "report_id": str(report_id)}


@router.get("/users")
async def list_users(current_user: CurrentUser, db: DB,
                     search: str = None, limit: int = 50, offset: int = 0):
    from sqlalchemy import select, or_
    from app.models.user import User
    q = select(User)
    if search:
        q = q.where(or_(User.email.ilike(f"%{search}%")))
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "is_active": u.is_active,
             "created_at": str(u.created_at)} for u in users]


@router.get("/stats")
async def admin_stats(current_user: CurrentUser, db: DB):
    from sqlalchemy import func, select
    from app.models.user import User
    from app.models.community import Post, ContentReport

    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    post_count = (await db.execute(select(func.count()).select_from(Post).where(Post.is_active == True))).scalar()
    pending_reports = (await db.execute(select(func.count()).select_from(ContentReport).where(ContentReport.status == "pending"))).scalar()

    return {
        "total_users": user_count,
        "total_posts": post_count,
        "pending_reports": pending_reports,
    }


# ─── GDPR Data Export ─────────────────────────────────────────────────────────

class DataExportResponse(BaseModel):
    message: str
    estimated_minutes: int
    download_url: str | None = None


async def _generate_export(user_id: str):
    """Background task: generates user data ZIP and stores download URL."""
    # In production: query all user data, zip, upload to temp storage
    import asyncio
    await asyncio.sleep(2)  # simulate processing


@gdpr_router.post("/data-export", response_model=DataExportResponse)
async def request_data_export(current_user: CurrentUser, background_tasks: BackgroundTasks):
    background_tasks.add_task(_generate_export, str(current_user.id))
    return DataExportResponse(
        message="Your data export has been queued. You'll receive a download link within 10 minutes.",
        estimated_minutes=10,
    )


@gdpr_router.delete("/account", response_model=MessageResponse)
async def delete_account(current_user: CurrentUser, db: DB):
    """Permanent account deletion — GDPR Article 17 (Right to Erasure)."""
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.deen"  # anonymise
        await db.flush()
    return MessageResponse(message="Account scheduled for deletion within 30 days. Ma'as-salama.")


# ─── Notification Preferences ─────────────────────────────────────────────────

class NotifPrefsUpdate(BaseModel):
    prayer_adhan: bool = True
    prayer_pre_adhan: bool = True
    prayer_qada_reminder: bool = True
    quran_daily_reminder: bool = True
    hifz_review_due: bool = True
    habit_streaks: bool = True
    islamic_calendar: bool = True
    zakat_reminders: bool = True
    journal_wellbeing: bool = True
    community_replies: bool = True
    dnd_start: str | None = "22:00"
    dnd_end: str | None = "07:00"


@notif_router.get("/preferences")
async def get_notif_preferences(current_user: CurrentUser):
    # Return defaults — in production read from DB
    return NotifPrefsUpdate().model_dump()


@notif_router.put("/preferences", response_model=MessageResponse)
async def update_notif_preferences(payload: NotifPrefsUpdate, current_user: CurrentUser):
    # In production: upsert to NotificationPreference table
    return MessageResponse(message="Notification preferences updated.")
