"""
Journal Router
"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB
from app.models.journal import JournalEntry
from app.schemas.base import MessageResponse
from app.schemas.schemas import JournalEntryCreate, JournalEntryResponse, JournalEntryUpdate

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("", response_model=list[JournalEntryResponse])
async def list_entries(
    current_user: CurrentUser,
    db: DB,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    mood: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    query = (
        select(JournalEntry)
        .where(
            JournalEntry.user_id == current_user.id,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date <= end,
        )
        .order_by(JournalEntry.entry_date.desc())
        .limit(limit)
        .offset(offset)
    )
    if mood:
        query = query.where(JournalEntry.mood == mood)
    result = await db.execute(query)
    return [JournalEntryResponse.model_validate(e) for e in result.scalars().all()]


@router.post("", response_model=JournalEntryResponse, status_code=201)
async def create_entry(payload: JournalEntryCreate, current_user: CurrentUser, db: DB):
    entry = JournalEntry(user_id=current_user.id, **payload.model_dump())
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return JournalEntryResponse.model_validate(entry)


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(entry_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return JournalEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(entry_id: UUID, payload: JournalEntryUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)
    await db.flush()
    await db.refresh(entry)
    return JournalEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", response_model=MessageResponse)
async def delete_entry(entry_id: UUID, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
    await db.delete(entry)
    return MessageResponse(message="Journal entry deleted.")
