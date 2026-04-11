"""Child Upbringing Router"""
from uuid import UUID
from fastapi import APIRouter, Query
from app.core.dependencies import CurrentUser, DB
from app.repositories import ChildRepo, MilestoneRepo, DuaTeachingRepo, LessonLogRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    ChildCreate, ChildResponse, ChildUpdate,
    MilestoneCreate, MilestoneResponse, MilestoneUpdate,
    DuaTeachingCreate, DuaTeachingResponse, DuaTeachingUpdate,
    LessonLogCreate, LessonLogResponse,
)

router = APIRouter(prefix="/children", tags=["children"])


@router.get("", response_model=list[ChildResponse])
async def list_children(current_user: CurrentUser, db: DB, repo: ChildRepo):
    children = await repo.get_all_for_user(current_user.id)
    return [ChildResponse.model_validate(c) for c in children]


@router.post("", response_model=ChildResponse, status_code=201)
async def create_child(payload: ChildCreate, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.create(user_id=current_user.id, **payload.model_dump())
    return ChildResponse.model_validate(child)


@router.patch("/{child_id}", response_model=ChildResponse)
async def update_child(child_id: UUID, payload: ChildUpdate, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.get_owned_or_404(child_id, current_user.id)
    child = await repo.update(child, **payload.model_dump(exclude_none=True))
    return ChildResponse.model_validate(child)


@router.delete("/{child_id}", response_model=MessageResponse)
async def delete_child(child_id: UUID, current_user: CurrentUser, db: DB, repo: ChildRepo):
    child = await repo.get_owned_or_404(child_id, current_user.id)
    await repo.delete(child)
    return MessageResponse(message="Child profile deleted.")


@router.get("/{child_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(child_id: UUID, current_user: CurrentUser, db: DB, repo: MilestoneRepo,
                           category: str = Query(default=None)):
    milestones = await repo.get_for_child(child_id, category=category)
    return [MilestoneResponse.model_validate(m) for m in milestones]


@router.post("/{child_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def create_milestone(child_id: UUID, payload: MilestoneCreate, current_user: CurrentUser,
                            db: DB, repo: MilestoneRepo):
    milestone = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())
    return MilestoneResponse.model_validate(milestone)


@router.patch("/{child_id}/milestones/{ms_id}", response_model=MilestoneResponse)
async def update_milestone(child_id: UUID, ms_id: UUID, payload: MilestoneUpdate,
                            current_user: CurrentUser, db: DB, repo: MilestoneRepo):
    ms = await repo.get_owned_or_404(ms_id, current_user.id)
    ms = await repo.update(ms, **payload.model_dump(exclude_none=True))
    return MilestoneResponse.model_validate(ms)


@router.get("/{child_id}/duas", response_model=list[DuaTeachingResponse])
async def list_dua_progress(child_id: UUID, current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    logs = await repo.get_for_child(child_id)
    return [DuaTeachingResponse.model_validate(l) for l in logs]


@router.post("/{child_id}/duas", response_model=DuaTeachingResponse, status_code=201)
async def log_dua(child_id: UUID, payload: DuaTeachingCreate, current_user: CurrentUser,
                   db: DB, repo: DuaTeachingRepo):
    log = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())
    return DuaTeachingResponse.model_validate(log)


@router.patch("/{child_id}/duas/{log_id}", response_model=DuaTeachingResponse)
async def update_dua(child_id: UUID, log_id: UUID, payload: DuaTeachingUpdate,
                      current_user: CurrentUser, db: DB, repo: DuaTeachingRepo):
    log = await repo.get_owned_or_404(log_id, current_user.id)
    log = await repo.update(log, **payload.model_dump(exclude_none=True))
    return DuaTeachingResponse.model_validate(log)


@router.get("/{child_id}/lessons", response_model=list[LessonLogResponse])
async def list_lessons(child_id: UUID, current_user: CurrentUser, db: DB, repo: LessonLogRepo,
                        subject: str = Query(default=None)):
    logs = await repo.get_for_child(child_id, subject=subject)
    return [LessonLogResponse.model_validate(l) for l in logs]


@router.post("/{child_id}/lessons", response_model=LessonLogResponse, status_code=201)
async def log_lesson(child_id: UUID, payload: LessonLogCreate, current_user: CurrentUser,
                      db: DB, repo: LessonLogRepo):
    log = await repo.create(child_id=child_id, user_id=current_user.id, **payload.model_dump())
    return LessonLogResponse.model_validate(log)
