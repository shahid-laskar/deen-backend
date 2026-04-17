"""
AI Service
==========
- Lifestyle-only AI assistant (Gemini 2.0 Flash primary, Groq fallback)
- Intent classifier to detect and redirect fiqh/ruling questions
- Per-user daily message limits for free-tier sustainability
- Conversation history management
"""

import json
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

import httpx

from app.core.config import settings

# ─── Fiqh Intent Detection ────────────────────────────────────────────────────
# Keyword-based classifier. Fast, zero-cost, no LLM call needed.

FIQH_KEYWORDS = {
    "ruling", "fatwa", "is it haram", "is it halal", "is it permissible",
    "is it forbidden", "is it allowed", "is it a sin",
    "haram to", "halal to", "permissible to", "forbidden to",
    "impermissible", "makruh", "mustahabb", "wajib", "fard",
    "what is the ruling", "what does islam say about", "scholars say",
    "islamqa", "fatwa on", "divorce ruling", "nikah ruling",
    "zakat ruling", "inheritance ruling", "riba ruling", "interest ruling",
    "music ruling", "beard ruling", "hijab ruling",
}


def is_fiqh_question(text: str) -> bool:
    """
    Returns True if the message appears to be asking for an Islamic ruling.
    Uses keyword matching — fast and no LLM cost.
    """
    lower = text.lower()
    return any(kw in lower for kw in FIQH_KEYWORDS)


def build_referral_response(madhab: str) -> dict:
    """Build a structured referral response for fiqh questions."""
    madhab_resources = {
        "hanafi": {
            "name": "Hanafi",
            "sites": [
                {"label": "SeekersGuidance (Hanafi)", "url": "https://seekersguidance.org"},
                {"label": "Qibla (Hanafi fiqh)", "url": "https://qibla.com"},
                {"label": "Darul Iftaa (Mufti Taqi Usmani)", "url": "https://daruliftaa.com"},
            ],
        },
        "shafii": {
            "name": "Shafi'i",
            "sites": [
                {"label": "IslamQA (multi-madhab)", "url": "https://islamqa.info"},
                {"label": "Shafi'i Fiqh", "url": "https://www.shafii.com"},
            ],
        },
        "maliki": {
            "name": "Maliki",
            "sites": [
                {"label": "IslamQA", "url": "https://islamqa.info"},
                {"label": "Maliki Fiqh Resources", "url": "https://malikifiqh.com"},
            ],
        },
        "hanbali": {
            "name": "Hanbali",
            "sites": [
                {"label": "IslamQA (based on Hanbali)", "url": "https://islamqa.info"},
                {"label": "Permanent Committee Fatwas", "url": "https://alifta.gov.sa"},
            ],
        },
    }
    resources = madhab_resources.get(madhab, madhab_resources["hanafi"])
    return {
        "reply": (
            f"This question relates to an Islamic ruling (fiqh), which requires "
            f"a qualified scholar's guidance. As your {resources['name']} school "
            f"lifestyle companion, I'm not able to issue fatwas or rulings.\n\n"
            f"Please consult one of these trusted {resources['name']} resources:"
        ),
        "referral_links": resources["sites"],
        "was_referred": True,
    }


# ─── System Prompt ────────────────────────────────────────────────────────────

def build_system_prompt(user_context: dict) -> str:
    gender = user_context.get("gender", "")
    madhab = user_context.get("madhab", "hanafi")
    today = date.today().strftime("%A, %d %B %Y")

    female_context = ""
    if gender == "female":
        cycle_status = user_context.get("cycle_status", "")
        if cycle_status:
            female_context = f"\nUser's current cycle status: {cycle_status}"

    return f"""You are Deen Guide, an Islamic lifestyle and wellness companion.

Today is {today}.
User's madhab preference: {madhab.title()}{female_context}

YOUR ROLE:
- Help with daily habits, productivity, and goal-setting grounded in Islamic values
- Support Quran memorisation planning, revision scheduling, and motivation
- Offer wellness advice (sleep, nutrition mindset, exercise mindset) from an Islamic lens
- Provide emotional support and positive reinforcement
- Suggest morning/evening routines, time-blocking around prayer times
- Help with journaling prompts and self-reflection questions

STRICT BOUNDARIES — NEVER:
- Issue Islamic rulings, fatwas, or legal opinions on any topic
- Declare anything haram, halal, permissible, or forbidden
- Override or reinterpret scholarly positions
- Give medical diagnoses or prescriptions
- Replace professional mental health therapy

When fiqh/ruling questions arise: acknowledge the question warmly, explain you're a lifestyle companion not a scholar, and direct to qualified sources.

TONE: Warm, encouraging, non-judgmental. Use occasional Islamic phrases naturally (Alhamdulillah, InshaaAllah, MashaaAllah). Keep responses concise and actionable.

FORMAT: Use clear paragraphs. Use bullet points only for lists of 3+ items. No unnecessary headers."""


# ─── AI API Calls ─────────────────────────────────────────────────────────────

async def call_gemini(messages: list[dict], system_prompt: str, max_tokens: Optional[int] = None) -> str:
    """Call Gemini 2.0 Flash API."""
    # Convert to Gemini format
    gemini_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_messages.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": gemini_messages,
        "generationConfig": {
            "temperature": settings.AI_TEMPERATURE,
            "maxOutputTokens": max_tokens or settings.AI_MAX_TOKENS,
        },
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_gemini(system_prompt: str, user_message: str, max_tokens: int = 1000) -> str:
    """Internal helper for simple system/user prompt calls (e.g. from recitation service)."""
    messages = [{"role": "user", "content": user_message}]
    return await call_gemini(messages, system_prompt, max_tokens=max_tokens)


async def call_groq(messages: list[dict], system_prompt: str) -> str:
    """Call Groq API (llama-3.3-70b) as fallback."""
    groq_messages = [{"role": "system", "content": system_prompt}] + messages

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": groq_messages,
                "temperature": settings.AI_TEMPERATURE,
                "max_tokens": settings.AI_MAX_TOKENS,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def generate_ai_reply(
    user_message: str,
    conversation_history: list[dict],
    user_context: dict,
) -> str:
    """
    Generate a reply using Gemini (primary) with Groq fallback.
    conversation_history: list of {role, content} dicts.
    """
    system_prompt = build_system_prompt(user_context)

    # Build messages: history + new user message
    messages = conversation_history[-10:]  # last 10 messages for context
    messages = messages + [{"role": "user", "content": user_message}]

    # Try Gemini first
    if settings.GEMINI_API_KEY:
        try:
            return await call_gemini(messages, system_prompt)
        except Exception:
            pass  # fallthrough to Groq

    # Groq fallback
    if settings.GROQ_API_KEY:
        return await call_groq(messages, system_prompt)

    return (
        "I'm having trouble connecting right now. "
        "Please try again in a moment. JazakAllahu Khayran for your patience."
    )


# ─── Daily Usage Tracking ─────────────────────────────────────────────────────

def count_today_messages(conversations: list) -> int:
    """Count messages sent by this user today across all conversations."""
    today = date.today().isoformat()
    count = 0
    for conv in conversations:
        for msg in conv.messages or []:
            if msg.get("role") == "user" and msg.get("date", "") == today:
                count += 1
    return count
