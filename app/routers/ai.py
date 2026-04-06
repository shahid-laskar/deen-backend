from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB
from app.models.ai import AIConversation
from app.models.female import MenstrualCycle
from app.schemas.base import MessageResponse
from app.schemas.schemas import AIConversationResponse, AIMessageRequest, AIMessageResponse
from app.services.ai_service import (
    build_referral_response,
    count_today_messages,
    generate_ai_reply,
    is_fiqh_question,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_user_context(user, cycle_status: str | None = None) -> dict:
    return {
        "gender": user.gender,
        "madhab": user.madhab,
        "timezone": user.timezone,
        "cycle_status": cycle_status,
    }


@router.post("/chat", response_model=AIMessageResponse)
async def chat(payload: AIMessageRequest, current_user: CurrentUser, db: DB):
    """
    Send a message to the AI guide.
    - Fiqh questions are intercepted before the LLM call
    - Daily message limit enforced (free-tier sustainability)
    - Conversation history maintained per thread
    """
    # Load all user conversations to count today's usage
    conv_result = await db.execute(
        select(AIConversation).where(AIConversation.user_id == current_user.id)
    )
    all_conversations = conv_result.scalars().all()

    messages_today = count_today_messages(all_conversations)

    if messages_today >= settings.AI_DAILY_LIMIT_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You have reached your daily limit of {settings.AI_DAILY_LIMIT_PER_USER} "
                f"messages. JazakAllahu Khayran for using Deen Guide. "
                f"Your limit resets at midnight. This limit helps keep the service free for everyone."
            ),
        )

    # ─── Fiqh Intent Check (zero-cost, before LLM call) ──────────────────────
    if is_fiqh_question(payload.content):
        referral = build_referral_response(current_user.madhab)
        # Still store this exchange in conversation history
        await _save_exchange(
            db=db,
            user=current_user,
            conversation_id=payload.conversation_id,
            context_module=payload.context_module,
            user_message=payload.content,
            ai_reply=referral["reply"],
        )
        return AIMessageResponse(
            conversation_id=payload.conversation_id or UUID(int=0),
            reply=referral["reply"],
            was_referred=True,
            referral_links=referral["referral_links"],
            messages_used_today=messages_today + 1,
            messages_limit=settings.AI_DAILY_LIMIT_PER_USER,
        )

    # ─── Load / Create Conversation ───────────────────────────────────────────
    conversation = None
    if payload.conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == payload.conversation_id,
                AIConversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            user_id=current_user.id,
            context_module=payload.context_module,
            messages=[],
            message_count=0,
        )
        db.add(conversation)
        await db.flush()

    # ─── Fetch Female Context (cycle status for personalized guidance) ────────
    cycle_status = None
    if current_user.gender == "female":
        open_cycle_result = await db.execute(
            select(MenstrualCycle).where(
                MenstrualCycle.user_id == current_user.id,
                MenstrualCycle.end_date == None,
            )
        )
        open_cycle = open_cycle_result.scalar_one_or_none()
        if open_cycle:
            days_in = (date.today() - open_cycle.start_date).days + 1
            cycle_status = f"Currently in hayd (day {days_in}). Can pray: {open_cycle.can_pray}. Can fast: {open_cycle.can_fast}."

    # ─── Generate Reply ───────────────────────────────────────────────────────
    user_context = _get_user_context(current_user, cycle_status)
    history = list(conversation.messages or [])

    reply = await generate_ai_reply(
        user_message=payload.content,
        conversation_history=history,
        user_context=user_context,
    )

    # ─── Persist Exchange ─────────────────────────────────────────────────────
    today = date.today().isoformat()
    new_messages = history + [
        {"role": "user", "content": payload.content, "date": today,
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": reply,
         "timestamp": datetime.now(timezone.utc).isoformat()},
    ]
    # Keep only last 50 messages in history to prevent unbounded growth
    conversation.messages = new_messages[-50:]
    conversation.message_count += 1
    if not conversation.title and len(payload.content) > 10:
        conversation.title = payload.content[:60] + ("..." if len(payload.content) > 60 else "")

    await db.flush()
    await db.refresh(conversation)

    return AIMessageResponse(
        conversation_id=conversation.id,
        reply=reply,
        was_referred=False,
        messages_used_today=messages_today + 1,
        messages_limit=settings.AI_DAILY_LIMIT_PER_USER,
    )


async def _save_exchange(db, user, conversation_id, context_module, user_message, ai_reply):
    """Save a referral exchange to conversation history."""
    conversation = None
    if conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            user_id=user.id,
            context_module=context_module,
            messages=[],
            message_count=0,
        )
        db.add(conversation)
        await db.flush()

    today = date.today().isoformat()
    history = list(conversation.messages or [])
    conversation.messages = (history + [
        {"role": "user", "content": user_message, "date": today,
         "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": ai_reply,
         "timestamp": datetime.now(timezone.utc).isoformat()},
    ])[-50:]
    conversation.message_count += 1
    await db.flush()


@router.get("/conversations", response_model=list[AIConversationResponse])
async def list_conversations(current_user: CurrentUser, db: DB):
    """List user's AI conversation threads."""
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id, AIConversation.is_active == True)
        .order_by(AIConversation.updated_at.desc())
        .limit(20)
    )
    return [AIConversationResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/conversations/{conv_id}", response_model=AIConversationResponse)
async def get_conversation(conv_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conv_id, AIConversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return AIConversationResponse.model_validate(conv)


@router.delete("/conversations/{conv_id}", response_model=MessageResponse)
async def delete_conversation(conv_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conv_id, AIConversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conv.is_active = False
    return MessageResponse(message="Conversation archived.")


@router.get("/usage", response_model=dict)
async def get_ai_usage(current_user: CurrentUser, db: DB):
    """Get today's AI message usage for the user."""
    conv_result = await db.execute(
        select(AIConversation).where(AIConversation.user_id == current_user.id)
    )
    convs = conv_result.scalars().all()
    used = count_today_messages(convs)
    return {
        "messages_used_today": used,
        "messages_limit": settings.AI_DAILY_LIMIT_PER_USER,
        "messages_remaining": max(0, settings.AI_DAILY_LIMIT_PER_USER - used),
    }
