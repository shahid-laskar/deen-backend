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
