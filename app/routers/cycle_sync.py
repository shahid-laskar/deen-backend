"""Cycle-Sync Ibadah Recommendations (extends female module)"""
from fastapi import APIRouter
from app.core.dependencies import FemaleUser, DB
from app.repositories import CycleRepo
from app.services.cycle_sync_service import get_ibadah_recommendations, get_phase_from_cycle

router = APIRouter(prefix="/female/ibadah", tags=["female"])


@router.get("/recommendations")
async def get_recommendations(current_user: FemaleUser, db: DB, cycle_repo: CycleRepo):
    open_cycle = await cycle_repo.get_open_cycle(current_user.id)
    phase = get_phase_from_cycle(open_cycle)
    recs = get_ibadah_recommendations(phase)
    return {
        "current_phase": phase,
        "cycle_day": (
            ((__import__('datetime').date.today() - open_cycle.start_date).days + 1)
            if open_cycle else None
        ),
        "recommendations": {
            "permitted": recs.permitted,
            "not_permitted": recs.not_permitted,
            "recommended_now": recs.recommended_now,
            "dhikr_suggestions": recs.dhikr_suggestions,
            "quran_engagement": recs.quran_engagement,
            "wellness_tips": recs.wellness_tips,
            "motivational_reminder": recs.motivational_reminder,
        },
    }
