from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB
from app.repositories import AIConvRepo, CycleRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import AIConversationResponse, AIMessageRequest, AIMessageResponse
from app.services.ai_service import (
    build_referral_response, generate_ai_reply, is_fiqh_question,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _user_context(user, cycle_status=None):
    return {"gender": user.gender, "madhab": user.madhab, "timezone": user.timezone, "cycle_status": cycle_status}


@router.post("/chat", response_model=AIMessageResponse)
async def chat(payload: AIMessageRequest, current_user: CurrentUser, db: DB, ai_repo: AIConvRepo, cycle_repo: CycleRepo):
    all_convs = await ai_repo.get_all_for_user(current_user.id)
    messages_today = ai_repo.count_today_messages(all_convs)

    if messages_today >= settings.AI_DAILY_LIMIT_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit of {settings.AI_DAILY_LIMIT_PER_USER} messages reached. Resets at midnight.",
        )

    # Fiqh intent check — zero LLM cost
    if is_fiqh_question(payload.content):
        referral = build_referral_response(current_user.madhab)
        conv = await _get_or_create_conv(ai_repo, db, current_user.id, payload)
        await _append_exchange(conv, payload.content, referral["reply"], db)
        return AIMessageResponse(
            conversation_id=conv.id,
            reply=referral["reply"],
            was_referred=True,
            referral_links=referral["referral_links"],
            messages_used_today=messages_today + 1,
            messages_limit=settings.AI_DAILY_LIMIT_PER_USER,
        )

    conv = await _get_or_create_conv(ai_repo, db, current_user.id, payload)

    # Female cycle context
    cycle_status = None
    if current_user.gender == "female":
        open_cycle = await cycle_repo.get_open_cycle(current_user.id)
        if open_cycle:
            days_in = (date.today() - open_cycle.start_date).days + 1
            cycle_status = f"Currently in hayd (day {days_in}). Can pray: {open_cycle.can_pray}. Can fast: {open_cycle.can_fast}."

    history = list(conv.messages or [])
    reply = await generate_ai_reply(
        user_message=payload.content,
        conversation_history=history,
        user_context=_user_context(current_user, cycle_status),
    )

    await _append_exchange(conv, payload.content, reply, db)
    if not conv.title and len(payload.content) > 10:
        conv.title = payload.content[:60] + ("..." if len(payload.content) > 60 else "")
    await db.flush()

    return AIMessageResponse(
        conversation_id=conv.id,
        reply=reply,
        was_referred=False,
        messages_used_today=messages_today + 1,
        messages_limit=settings.AI_DAILY_LIMIT_PER_USER,
    )


async def _get_or_create_conv(ai_repo, db, user_id, payload):
    if payload.conversation_id:
        conv = await ai_repo.get_owned_or_404(payload.conversation_id, user_id)
        return conv
    return await ai_repo.create(
        user_id=user_id,
        context_module=payload.context_module,
        messages=[],
        message_count=0,
    )


async def _append_exchange(conv, user_msg, ai_reply, db):
    today = date.today().isoformat()
    ts = datetime.now(timezone.utc).isoformat()
    history = list(conv.messages or [])
    conv.messages = (history + [
        {"role": "user", "content": user_msg, "date": today, "timestamp": ts},
        {"role": "assistant", "content": ai_reply, "timestamp": ts},
    ])[-50:]
    conv.message_count += 1
    await db.flush()


@router.get("/conversations", response_model=list[AIConversationResponse])
async def list_conversations(current_user: CurrentUser, db: DB, ai_repo: AIConvRepo):
    convs = await ai_repo.get_active_for_user(current_user.id)
    return [AIConversationResponse.model_validate(c) for c in convs]


@router.get("/conversations/{conv_id}", response_model=AIConversationResponse)
async def get_conversation(conv_id: UUID, current_user: CurrentUser, db: DB, ai_repo: AIConvRepo):
    conv = await ai_repo.get_owned_or_404(conv_id, current_user.id)
    return AIConversationResponse.model_validate(conv)


@router.delete("/conversations/{conv_id}", response_model=MessageResponse)
async def delete_conversation(conv_id: UUID, current_user: CurrentUser, db: DB, ai_repo: AIConvRepo):
    conv = await ai_repo.get_owned_or_404(conv_id, current_user.id)
    await ai_repo.update(conv, is_active=False)
    return MessageResponse(message="Conversation archived.")


@router.get("/usage", response_model=dict)
async def get_ai_usage(current_user: CurrentUser, db: DB, ai_repo: AIConvRepo):
    convs = await ai_repo.get_all_for_user(current_user.id)
    used = ai_repo.count_today_messages(convs)
    return {
        "messages_used_today": used,
        "messages_limit": settings.AI_DAILY_LIMIT_PER_USER,
        "messages_remaining": max(0, settings.AI_DAILY_LIMIT_PER_USER - used),
    }
