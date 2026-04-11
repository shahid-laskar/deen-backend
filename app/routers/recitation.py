"""Quran Recitation Router"""
from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.core.dependencies import CurrentUser, DB
from app.repositories import RecitationRepo, RecitationFbRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    RecitationSessionCreate, RecitationSessionResponse,
    RecitationFeedbackResponse, RecitationStats,
)
from app.services.recitation_service import (
    transcribe_audio, generate_tajweed_feedback, compute_basic_score,
)
import asyncio

router = APIRouter(prefix="/recitation", tags=["recitation"])


@router.get("", response_model=list[RecitationSessionResponse])
async def list_sessions(current_user: CurrentUser, db: DB, repo: RecitationRepo):
    sessions = await repo.get_for_user(current_user.id)
    return [RecitationSessionResponse.model_validate(s) for s in sessions]


@router.post("", response_model=RecitationSessionResponse, status_code=201)
async def create_session(payload: RecitationSessionCreate, current_user: CurrentUser,
                          db: DB, repo: RecitationRepo):
    session = await repo.create(user_id=current_user.id, **payload.model_dump())
    return RecitationSessionResponse.model_validate(session)


@router.post("/{session_id}/analyse", response_model=RecitationSessionResponse)
async def analyse_session(session_id: UUID, current_user: CurrentUser, db: DB,
                           repo: RecitationRepo, fb_repo: RecitationFbRepo):
    """
    Trigger AI analysis of a recitation session.
    Requires audio_url to be set on the session.
    """
    session = await repo.get_owned_or_404(session_id, current_user.id)
    if not session.audio_url:
        raise HTTPException(status_code=422, detail="No audio URL set on this session.")
    if session.status == "complete":
        raise HTTPException(status_code=409, detail="Session already analysed.")

    await repo.update(session, status="processing")

    # Transcribe
    transcription = await transcribe_audio(session.audio_url)
    transcript = transcription.get("transcript", "")
    confidence = transcription.get("confidence", 0.0)

    # Generate feedback
    feedback_data = await generate_tajweed_feedback(
        surah_name=session.surah_name,
        ayah_from=session.ayah_from,
        ayah_to=session.ayah_to,
        expected_text=session.recited_text or "",
        transcribed_text=transcript,
        transcription_confidence=confidence,
    )

    # Save feedback
    existing_fb = await fb_repo.get_for_session(session_id)
    if not existing_fb:
        await fb_repo.create(
            session_id=session_id,
            user_id=current_user.id,
            tajweed_errors=feedback_data.get("tajweed_errors"),
            strengths=feedback_data.get("strengths"),
            improvement_areas=feedback_data.get("improvement_areas"),
            next_steps=feedback_data.get("next_steps"),
            summary=feedback_data.get("summary"),
            detailed_feedback=feedback_data.get("detailed_feedback"),
            ai_model_used="gemini-2.0-flash",
            transcription_confidence=confidence,
        )

    # Update session scores
    session = await repo.update(
        session,
        status="complete",
        recited_text=transcript if transcript else session.recited_text,
        overall_score=feedback_data.get("overall_score"),
        fluency_score=feedback_data.get("fluency_score"),
        tajweed_score=feedback_data.get("tajweed_score"),
        pronunciation_score=feedback_data.get("pronunciation_score"),
    )
    return RecitationSessionResponse.model_validate(session)


@router.get("/{session_id}/feedback", response_model=RecitationFeedbackResponse)
async def get_feedback(session_id: UUID, current_user: CurrentUser, db: DB,
                        repo: RecitationRepo, fb_repo: RecitationFbRepo):
    await repo.get_owned_or_404(session_id, current_user.id)
    fb = await fb_repo.get_for_session(session_id)
    if not fb:
        raise HTTPException(status_code=404, detail="No feedback available. Run /analyse first.")
    return RecitationFeedbackResponse.model_validate(fb)


@router.get("/stats", response_model=RecitationStats)
async def get_stats(current_user: CurrentUser, db: DB, repo: RecitationRepo):
    stats = await repo.get_stats(current_user.id)
    return RecitationStats(**stats)


@router.delete("/{session_id}", response_model=MessageResponse)
async def delete_session(session_id: UUID, current_user: CurrentUser, db: DB, repo: RecitationRepo):
    session = await repo.get_owned_or_404(session_id, current_user.id)
    await repo.delete(session)
    return MessageResponse(message="Session deleted.")
