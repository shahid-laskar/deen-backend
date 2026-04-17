"""Phase 10 — Admin, GDPR & Notification Endpoints"""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.core.dependencies import CurrentUser, DB, AdminUser
from app.schemas.base import MessageResponse

router = APIRouter(prefix="/admin", tags=["admin"])
gdpr_router = APIRouter(prefix="/user", tags=["user"])
notif_router = APIRouter(prefix="/notifications", tags=["notifications"])


# ─── Admin - Moderation ────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(admin_user: AdminUser, db: DB,
                       status: str = "pending", limit: int = 50, offset: int = 0):
    from sqlalchemy import select
    from app.models.community import ContentReport
    q = select(ContentReport).where(ContentReport.status == status).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.patch("/reports/{report_id}")
async def update_report(report_id: UUID, action: str, admin_user: AdminUser, db: DB):
    from sqlalchemy import select
    from app.models.community import ContentReport
    result = await db.execute(select(ContentReport).where(ContentReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = "resolved" if action in ("approve", "remove", "warn") else "dismissed"
    report.reviewed_by = admin_user.id
    await db.flush()
    return {"action": action, "report_id": str(report_id)}


@router.get("/users")
async def list_users(admin_user: AdminUser, db: DB,
                     search: str = None, role: str = None, is_verified: bool = None,
                     limit: int = 50, offset: int = 0):
    from sqlalchemy import select, or_
    from app.models.user import User
    q = select(User)
    if search:
        q = q.where(or_(User.email.ilike(f"%{search}%")))
    if role:
        q = q.where(User.role == role)
    if is_verified is not None:
        q = q.where(User.is_verified == is_verified)
        
    q = q.offset(offset).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(q)
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "is_active": u.is_active,
             "role": u.role, "is_verified": u.is_verified,
             "created_at": str(u.created_at)} for u in users]


@router.post("/users/{user_id}/verify-scholar")
async def verify_scholar(user_id: UUID, admin_user: AdminUser, db: DB):
    """Verify a user as a scholar and update their role."""
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    user.role = "scholar"
    await db.flush()
    return {"message": f"User {user.email} verified as scholar", "role": user.role}


# ─── Admin - 2FA (TOTP) ───────────────────────────────────────────────────────

@router.post("/totp/setup")
async def setup_totp(admin_user: AdminUser, db: DB):
    """Generate a new TOTP secret for the admin."""
    import pyotp
    if admin_user.totp_enabled:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    if not admin_user.totp_secret:
        admin_user.totp_secret = pyotp.random_base32()
        await db.flush()
    
    totp = pyotp.TOTP(admin_user.totp_secret)
    provisioning_uri = totp.provisioning_uri(name=admin_user.email, issuer_name="Deen App")
    return {"secret": admin_user.totp_secret, "uri": provisioning_uri}


class TOTPVerify(BaseModel):
    code: str

@router.post("/totp/enable")
async def enable_totp(payload: TOTPVerify, admin_user: AdminUser, db: DB):
    """Verify TOTP code and enable 2FA for the admin."""
    import pyotp
    if not admin_user.totp_secret:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="TOTP not set up")
    
    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(payload.code):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    admin_user.totp_enabled = True
    await db.flush()
    return {"message": "2FA successfully enabled"}


@router.get("/stats")
async def admin_stats(admin_user: AdminUser, db: DB):
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


@gdpr_router.post("/data-export")
async def request_data_export(current_user: CurrentUser, db: DB):
    """GDPR core: Collect all user data and return as JSON."""
    from app.models.user import User
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from datetime import datetime, timezone
    
    # Reload user with all key relationships
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.prayer_logs),
            selectinload(User.habits),
            selectinload(User.journal_entries),
            selectinload(User.hifz_progress),
            selectinload(User.tasks),
            selectinload(User.fasting_logs)
        )
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()

    data = {
        "user_info": {
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            "profile": {
                "display_name": user.profile.display_name if user.profile else None,
                "bio": user.profile.bio if user.profile else None,
            }
        },
        "prayer_logs": [
            {"date": str(log.date), "prayer_name": log.prayer_name, "is_prayed": log.is_prayed}
            for log in user.prayer_logs
        ],
        "habits": [
            {"title": h.title, "frequency": h.frequency, "streak": h.streak}
            for h in user.habits
        ],
        "journal_entries": [
            {"date": entry.entry_date.isoformat(), "sentiment": entry.sentiment_score}
            for entry in user.journal_entries
        ],
        "hifz_progress": [
            {"surah": p.surah_number, "ayah": p.ayah_number, "status": p.status}
            for p in user.hifz_progress
        ],
        "tasks": [
            {"title": t.title, "is_completed": t.is_completed}
            for t in user.tasks
        ],
        "fasting_logs": [
            {"date": str(log.date), "type": log.fast_type}
            for log in user.fasting_logs
        ],
        "export_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": "Privacy-first, Deen App Core."
        }
    }
    
    return {"message": "Data export prepared", "data": data}


@gdpr_router.delete("/account")
async def delete_account(current_user: CurrentUser, db: DB):
    """Permanent account deletion — GDPR Article 17 (Right to Erasure)."""
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user:
        # Instead of 30 days, we honor the request immediately if not specified otherwise
        await db.delete(user)
        await db.flush()
    return {"message": "Account and all associated records permanently deleted. Ma'as-salama."}


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
