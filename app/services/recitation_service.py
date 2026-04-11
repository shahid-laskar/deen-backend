"""
Recitation AI Service
=====================
1. Transcribes uploaded audio via AssemblyAI (free tier: 100 hours/month)
   Falls back to basic word-count heuristic if no key set.
2. Sends transcribed text to Gemini for tajweed / pronunciation feedback.
3. Returns structured RecitationFeedback.

AssemblyAI free tier: https://www.assemblyai.com/
"""

import asyncio
import os
from typing import Any

import httpx

from app.core.config import settings


ASSEMBLYAI_URL = "https://api.assemblyai.com/v2"
ASSEMBLYAI_KEY = getattr(settings, "ASSEMBLYAI_API_KEY", "")


# ─── Transcription ─────────────────────────────────────────────────────────────

async def transcribe_audio(audio_url: str) -> dict:
    """
    Submit audio for transcription via AssemblyAI.
    Returns {"transcript": str, "confidence": float, "words": list}.
    Falls back gracefully if no API key.
    """
    if not ASSEMBLYAI_KEY:
        return {
            "transcript": "",
            "confidence": 0.0,
            "words": [],
            "error": "AssemblyAI key not configured. Set ASSEMBLYAI_API_KEY in .env.",
        }

    headers = {"authorization": ASSEMBLYAI_KEY, "content-type": "application/json"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit job
        resp = await client.post(
            f"{ASSEMBLYAI_URL}/transcript",
            headers=headers,
            json={
                "audio_url": audio_url,
                "language_code": "ar",   # Arabic
                "punctuate": False,
                "format_text": False,
            },
        )
        resp.raise_for_status()
        job_id = resp.json()["id"]

        # Poll until complete (max 2 minutes)
        for _ in range(24):
            await asyncio.sleep(5)
            poll = await client.get(f"{ASSEMBLYAI_URL}/transcript/{job_id}", headers=headers)
            poll.raise_for_status()
            result = poll.json()
            if result["status"] == "completed":
                return {
                    "transcript": result.get("text", ""),
                    "confidence": result.get("confidence", 0.0),
                    "words": result.get("words", []),
                }
            if result["status"] == "error":
                return {"transcript": "", "confidence": 0.0, "words": [], "error": result.get("error")}

    return {"transcript": "", "confidence": 0.0, "words": [], "error": "Transcription timed out."}


# ─── Tajweed Feedback ──────────────────────────────────────────────────────────

TAJWEED_SYSTEM_PROMPT = """
You are an expert Quran recitation teacher specialising in Tajweed (rules of Quranic recitation).

A student has recited a portion of the Quran. You will receive:
- The Arabic text they were supposed to recite
- The transcribed text of what they actually said (auto-transcribed, may have errors)
- The surah and ayah range

Your task is to provide structured, encouraging feedback focusing on:
1. Tajweed rules: Ghunna, Madd, Qalqalah, Idgham, Iqlab, Ikhfaa
2. Makharij (pronunciation of Arabic letters)
3. Waqf (pausing) and Ibtida (beginning)

RULES:
- Be kind, encouraging, and constructive — this is a student of the Quran
- Always start with what they did well
- Specific rule violations only, not vague criticism
- Give phonetic examples in brackets
- End with a motivational Islamic quote about learning Quran

Return ONLY valid JSON (no preamble) with this exact structure:
{
  "overall_score": <0-100 integer>,
  "fluency_score": <0-100>,
  "tajweed_score": <0-100>,
  "pronunciation_score": <0-100>,
  "strengths": ["strength 1", "strength 2"],
  "tajweed_errors": [
    {"rule": "rule name", "description": "what went wrong", "correction": "how to fix"}
  ],
  "improvement_areas": ["area 1", "area 2"],
  "summary": "2-3 sentence summary",
  "detailed_feedback": "paragraph of detailed feedback",
  "next_steps": "what to practice next"
}
"""


async def generate_tajweed_feedback(
    surah_name: str | None,
    ayah_from: int | None,
    ayah_to: int | None,
    expected_text: str,
    transcribed_text: str,
    transcription_confidence: float,
) -> dict:
    """
    Use Gemini to generate structured tajweed feedback.
    Falls back to a basic feedback dict if AI is unavailable.
    """
    if not settings.GEMINI_API_KEY:
        return _default_feedback(transcription_confidence)

    user_message = f"""
Surah: {surah_name or 'Unknown'}
Ayahs: {ayah_from} to {ayah_to}

Expected text (correct):
{expected_text}

Transcribed recitation (what the student said):
{transcribed_text}

Transcription confidence: {transcription_confidence:.0%}

Please provide tajweed feedback.
"""

    try:
        import json as _json
        from app.services.ai_service import _call_gemini
        raw = await _call_gemini(TAJWEED_SYSTEM_PROMPT, user_message, max_tokens=1500)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw)
    except Exception:
        return _default_feedback(transcription_confidence)


def _default_feedback(confidence: float) -> dict:
    return {
        "overall_score": 70,
        "fluency_score": 70,
        "tajweed_score": 70,
        "pronunciation_score": 70,
        "strengths": ["Completed the recitation — JazakAllahu Khayran for your effort"],
        "tajweed_errors": [],
        "improvement_areas": ["Continue practising regularly"],
        "summary": "Assessment unavailable. AI feedback requires a valid Gemini API key.",
        "detailed_feedback": "Please configure GEMINI_API_KEY to receive detailed tajweed analysis.",
        "next_steps": "Listen to a reciter (e.g. Sheikh Mishary Rashid) for the passage you practised.",
    }


# ─── Scoring ────────────────────────────────────────────────────────────────────

def compute_basic_score(
    expected_text: str,
    transcribed_text: str,
    confidence: float,
) -> dict:
    """
    Simple word-overlap score when transcription confidence is low.
    Used as a floor / sanity check before AI analysis.
    """
    if not expected_text or not transcribed_text:
        return {"overlap_score": 0.0, "word_count_expected": 0, "word_count_got": 0}

    expected_words = set(expected_text.split())
    got_words = set(transcribed_text.split())
    if not expected_words:
        return {"overlap_score": 0.0, "word_count_expected": 0, "word_count_got": len(got_words)}

    overlap = len(expected_words & got_words) / len(expected_words)
    return {
        "overlap_score": round(overlap * 100, 1),
        "word_count_expected": len(expected_words),
        "word_count_got": len(got_words),
        "confidence_adjusted_score": round(overlap * confidence * 100, 1),
    }
