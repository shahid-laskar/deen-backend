"""
Health Router — Phase 9
=======================
POST /health/water
GET /health/water/today
"""
from datetime import date as DateType, datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB
from app.models.health import WaterLog

router = APIRouter(prefix="/health", tags=["health"])


class AddWaterForm(BaseModel):
    cups: int


@router.get("/water/today")
async def get_water_today(current_user: CurrentUser, db: DB):
    today = datetime.now(timezone.utc).date()
    result = await db.execute(select(WaterLog).where(WaterLog.user_id == current_user.id, WaterLog.date == today))
    log = result.scalar()
    if not log:
        log = WaterLog(user_id=current_user.id, date=today, cups=0, goal=8)
        db.add(log)
        await db.commit()
    return {"cups": log.cups, "goal": log.goal}


@router.post("/water")
async def add_water(form: AddWaterForm, current_user: CurrentUser, db: DB):
    today = datetime.now(timezone.utc).date()
    result = await db.execute(select(WaterLog).where(WaterLog.user_id == current_user.id, WaterLog.date == today))
    log = result.scalar()
    if not log:
        log = WaterLog(user_id=current_user.id, date=today, cups=0, goal=8)
        db.add(log)

    # Note: cups is the AMOUNT to add, not the absolute total. 
    # Or to make it simpler, we just use cups=1 
    if form.cups > 0:
        log.cups += form.cups
    elif form.cups == 0:
        log.cups = 0

    await db.commit()
    return {"cups": log.cups, "goal": log.goal}
