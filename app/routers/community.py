"""Community & Forums Router"""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from app.core.dependencies import CurrentUser, DB
from app.repositories import CommunityGroupRepo, PostRepo, CommentRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    GroupCreate, GroupResponse,
    PostCreate, PostResponse, PostUpdate,
    CommentCreate, CommentResponse,
)
from app.models.community import GroupMember, PostReaction, ContentReport

router = APIRouter(prefix="/community", tags=["community"])


# ─── Groups ───────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupResponse])
async def list_groups(current_user: CurrentUser, db: DB, repo: CommunityGroupRepo,
                       category: str = Query(default=None), search: str = Query(default=None),
                       limit: int = Query(default=20, le=50), offset: int = 0):
    groups = await repo.get_all(category=category, search=search, limit=limit, offset=offset)
    return [GroupResponse.model_validate(g) for g in groups]


@router.post("/groups", response_model=GroupResponse, status_code=201)
async def create_group(payload: GroupCreate, current_user: CurrentUser, db: DB, repo: CommunityGroupRepo):
    import re
    slug = re.sub(r'[^a-z0-9-]', '-', payload.name.lower().strip())[:80]
    if await repo.get_by_slug(slug):
        slug = f"{slug}-{str(current_user.id)[:6]}"
    group = await repo.create(created_by=current_user.id, slug=slug, **payload.model_dump())
    # Auto-join as admin
    db.add(GroupMember(group_id=group.id, user_id=current_user.id, role="admin", joined_at=date.today()))
    await db.flush()
    return GroupResponse.model_validate(group)


@router.post("/groups/{group_id}/join", response_model=MessageResponse)
async def join_group(group_id: UUID, current_user: CurrentUser, db: DB, repo: CommunityGroupRepo):
    group = await repo.get_or_404(group_id)
    if await repo.is_member(group_id, current_user.id):
        raise HTTPException(status_code=409, detail="Already a member.")
    db.add(GroupMember(group_id=group_id, user_id=current_user.id, role="member", joined_at=date.today()))
    group.member_count += 1
    await db.flush()
    return MessageResponse(message=f"Joined {group.name}. Ahlan wa sahlan!")


@router.post("/groups/{group_id}/leave", response_model=MessageResponse)
async def leave_group(group_id: UUID, current_user: CurrentUser, db: DB, repo: CommunityGroupRepo):
    from sqlalchemy import select, delete
    from app.models.community import GroupMember as GM
    result = await db.execute(select(GM).where(GM.group_id == group_id, GM.user_id == current_user.id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this group.")
    await db.delete(member)
    group = await repo.get_or_404(group_id)
    group.member_count = max(0, group.member_count - 1)
    await db.flush()
    return MessageResponse(message="Left group.")


# ─── Posts ────────────────────────────────────────────────────────────────────

@router.get("/feed", response_model=list[PostResponse])
async def global_feed(current_user: CurrentUser, db: DB, repo: PostRepo,
                       limit: int = Query(default=20, le=50), offset: int = 0):
    posts = await repo.get_global_feed(limit=limit, offset=offset)
    return [PostResponse.model_validate(p) for p in posts]


@router.get("/groups/{group_id}/posts", response_model=list[PostResponse])
async def group_posts(group_id: UUID, current_user: CurrentUser, db: DB, repo: PostRepo,
                       post_type: str = Query(default=None), limit: int = 20, offset: int = 0):
    posts = await repo.get_for_group(group_id, post_type=post_type, limit=limit, offset=offset)
    return [PostResponse.model_validate(p) for p in posts]


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(payload: PostCreate, current_user: CurrentUser, db: DB, repo: PostRepo,
                       group_repo: CommunityGroupRepo = ...):
    if payload.group_id and not await group_repo.is_member(payload.group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Join the group first.")
    post = await repo.create(user_id=current_user.id, **payload.model_dump())
    if payload.group_id:
        from sqlalchemy import select
        grp = await group_repo.get_or_404(payload.group_id)
        grp.post_count += 1
        await db.flush()
    return PostResponse.model_validate(post)


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(post_id: UUID, payload: PostUpdate, current_user: CurrentUser,
                       db: DB, repo: PostRepo):
    post = await repo.get_owned_or_404(post_id, current_user.id)
    post = await repo.update(post, **payload.model_dump(exclude_none=True))
    return PostResponse.model_validate(post)


@router.delete("/posts/{post_id}", response_model=MessageResponse)
async def delete_post(post_id: UUID, current_user: CurrentUser, db: DB, repo: PostRepo):
    post = await repo.get_owned_or_404(post_id, current_user.id)
    await repo.update(post, is_active=False)
    return MessageResponse(message="Post removed.")


@router.post("/posts/{post_id}/react", response_model=MessageResponse)
async def react_to_post(post_id: UUID, reaction_type: str = "like",
                         current_user: CurrentUser = ..., db: DB = ..., repo: PostRepo = ...):
    post = await repo.get_or_404(post_id)
    existing = await repo.user_reacted(post_id, current_user.id)
    if existing:
        if existing.reaction_type == reaction_type:
            await db.delete(existing)
            post.like_count = max(0, post.like_count - 1)
        else:
            existing.reaction_type = reaction_type
    else:
        db.add(PostReaction(post_id=post_id, user_id=current_user.id, reaction_type=reaction_type))
        post.like_count += 1
    await db.flush()
    return MessageResponse(message="Reaction saved.")


@router.post("/posts/{post_id}/report", response_model=MessageResponse)
async def report_post(post_id: UUID, reason: str, current_user: CurrentUser, db: DB):
    db.add(ContentReport(reporter_user_id=current_user.id, post_id=post_id, reason=reason))
    await db.flush()
    return MessageResponse(message="Report submitted. JazakAllahu Khayran.")


# ─── Comments ─────────────────────────────────────────────────────────────────

@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(post_id: UUID, current_user: CurrentUser, db: DB, repo: CommentRepo,
                          limit: int = 50, offset: int = 0):
    comments = await repo.get_for_post(post_id, limit=limit, offset=offset)
    return [CommentResponse.model_validate(c) for c in comments]


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(post_id: UUID, payload: CommentCreate, current_user: CurrentUser,
                          db: DB, repo: CommentRepo, post_repo: PostRepo = ...):
    post = await post_repo.get_or_404(post_id)
    comment = await repo.create(post_id=post_id, user_id=current_user.id, **payload.model_dump())
    post.comment_count += 1
    await db.flush()
    return CommentResponse.model_validate(comment)


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(comment_id: UUID, current_user: CurrentUser, db: DB, repo: CommentRepo):
    comment = await repo.get_owned_or_404(comment_id, current_user.id)
    await repo.update(comment, is_active=False)
    return MessageResponse(message="Comment removed.")


# ─── Scholar Q&A ───────────────────────────────────────────────────────────────

from app.models.community import QAQuestion, QAAnswer, ScholarProfile
from pydantic import BaseModel as PydanticBaseModel

class QAQuestionCreate(PydanticBaseModel):
    text: str
    category: str
    madhab_relevance: str | None = None
    is_anonymous: bool = False

class QAAnswerCreate(PydanticBaseModel):
    content: str
    citations: list[str] | None = None
    madhab_note: str | None = None



@router.get("/qa/questions")
async def list_qa_questions(current_user: CurrentUser, db: DB,
                             category: str = Query(default=None),
                             status: str = Query(default=None),
                             limit: int = 20, offset: int = 0):
    from sqlalchemy import select
    q = select(QAQuestion)
    if category:
        q = q.where(QAQuestion.category == category)
    if status:
        q = q.where(QAQuestion.status == status)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/qa/questions", status_code=201)
async def submit_qa_question(payload: QAQuestionCreate, current_user: CurrentUser, db: DB):
    question = QAQuestion(user_id=current_user.id, **payload.model_dump())
    db.add(question)
    await db.flush()
    return {"id": str(question.id), "status": "pending", "message": "Question submitted to scholars."}


@router.get("/qa/questions/{question_id}/answers")
async def get_answers(question_id: UUID, current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    q = select(QAAnswer).where(QAAnswer.question_id == question_id, QAAnswer.is_published == True)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/qa/questions/{question_id}/answers", status_code=201)
async def submit_qa_answer(question_id: UUID, payload: QAAnswerCreate, current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    # Verify scholar profile exists
    sp_result = await db.execute(select(ScholarProfile).where(ScholarProfile.user_id == current_user.id))
    scholar = sp_result.scalar_one_or_none()
    if not scholar or not scholar.is_verified:
        raise HTTPException(status_code=403, detail="Only verified scholars can answer.")
    answer = QAAnswer(question_id=question_id, scholar_id=scholar.id, **payload.model_dump())
    db.add(answer)
    await db.flush()
    return {"id": str(answer.id), "message": "Answer submitted for admin review."}


# ─── Accountability Circles ────────────────────────────────────────────────────

from app.models.community import AccountabilityCircle, CircleMember, CircleGoal, CircleCheckIn
from datetime import date as date_type

class CircleCreate(PydanticBaseModel):
    name: str
    description: str | None = None
    check_in_day: int = 0

class CircleGoalCreate(PydanticBaseModel):
    title: str
    description: str | None = None

class CircleCheckInCreate(PydanticBaseModel):
    goal_id: UUID
    status: str  # success, failed, warning
    note: str | None = None


@router.get("/circles")
async def list_circles(current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    q = select(AccountabilityCircle).join(CircleMember, CircleMember.circle_id == AccountabilityCircle.id).where(CircleMember.user_id == current_user.id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/circles", status_code=201)
async def create_circle(payload: CircleCreate, current_user: CurrentUser, db: DB):
    circle = AccountabilityCircle(**payload.model_dump())
    db.add(circle)
    await db.flush()
    member = CircleMember(circle_id=circle.id, user_id=current_user.id, role="admin")
    db.add(member)
    await db.flush()
    return {"id": str(circle.id), "name": circle.name}


@router.post("/circles/{circle_id}/join", response_model=MessageResponse)
async def join_circle(circle_id: UUID, current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    existing = await db.execute(select(CircleMember).where(CircleMember.circle_id == circle_id, CircleMember.user_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already a member.")
    db.add(CircleMember(circle_id=circle_id, user_id=current_user.id, role="member"))
    await db.flush()
    return MessageResponse(message="Joined circle!")


@router.post("/circles/{circle_id}/goals", status_code=201)
async def create_circle_goal(circle_id: UUID, payload: CircleGoalCreate, current_user: CurrentUser, db: DB):
    goal = CircleGoal(circle_id=circle_id, **payload.model_dump())
    db.add(goal)
    await db.flush()
    return {"id": str(goal.id), "title": goal.title}


@router.post("/circles/checkins", status_code=201)
async def submit_circle_checkin(payload: CircleCheckInCreate, current_user: CurrentUser, db: DB):
    checkin = CircleCheckIn(user_id=current_user.id, date=date_type.today(), **payload.model_dump())
    db.add(checkin)
    await db.flush()
    return {"id": str(checkin.id), "status": checkin.status}


# ─── Halaqah ──────────────────────────────────────────────────────────────────

from app.models.community import Halaqah, HalaqahSession, HalaqahNote

class HalaqahCreate(PydanticBaseModel):
    name: str
    h_type: str = "open_discussion"
    curriculum: str | None = None
    max_members: int = 20

class HalaqahSessionCreate(PydanticBaseModel):
    topic: str
    session_date: str  # ISO date


@router.get("/halaqahs")
async def list_halaqahs(current_user: CurrentUser, db: DB):
    from sqlalchemy import select
    q = select(Halaqah).where(Halaqah.moderator_id == current_user.id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/halaqahs", status_code=201)
async def create_halaqah(payload: HalaqahCreate, current_user: CurrentUser, db: DB):
    halaqah = Halaqah(moderator_id=current_user.id, **payload.model_dump())
    db.add(halaqah)
    await db.flush()
    return {"id": str(halaqah.id), "name": halaqah.name}


@router.post("/halaqahs/{halaqah_id}/sessions", status_code=201)
async def create_halaqah_session(halaqah_id: UUID, payload: HalaqahSessionCreate, current_user: CurrentUser, db: DB):
    from datetime import date as date_cls
    session = HalaqahSession(
        halaqah_id=halaqah_id,
        topic=payload.topic,
        session_date=date_cls.fromisoformat(payload.session_date)
    )
    db.add(session)
    await db.flush()
    return {"id": str(session.id), "topic": session.topic}

