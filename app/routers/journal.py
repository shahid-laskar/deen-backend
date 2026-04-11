from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import JournalRepo
from app.schemas.base import MessageResponse
from app.schemas.schemas import JournalEntryCreate, JournalEntryResponse, JournalEntryUpdate

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("", response_model=list[JournalEntryResponse])
async def list_entries(
    current_user: CurrentUser, db: DB, journal_repo: JournalRepo,
    start_date: date = Query(default=None), end_date: date = Query(default=None),
    mood: str = Query(default=None), limit: int = Query(default=20, le=100), offset: int = 0,
):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    entries = await journal_repo.get_for_user(current_user.id, start=start, end=end, mood=mood, limit=limit, offset=offset)
    return [JournalEntryResponse.model_validate(e) for e in entries]


@router.post("", response_model=JournalEntryResponse, status_code=201)
async def create_entry(payload: JournalEntryCreate, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.create(user_id=current_user.id, **payload.model_dump())
    return JournalEntryResponse.model_validate(entry)


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(entry_id: UUID, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    return JournalEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(entry_id: UUID, payload: JournalEntryUpdate, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    entry = await journal_repo.update(entry, **payload.model_dump(exclude_none=True))
    return JournalEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", response_model=MessageResponse)
async def delete_entry(entry_id: UUID, current_user: CurrentUser, db: DB, journal_repo: JournalRepo):
    entry = await journal_repo.get_owned_or_404(entry_id, current_user.id)
    await journal_repo.delete(entry)
    return MessageResponse(message="Journal entry deleted.")
