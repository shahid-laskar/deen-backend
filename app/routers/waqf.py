"""Waqf / Donation Router"""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Query
from app.core.dependencies import CurrentUser, DB
from app.repositories import WaqfProjectRepo, DonationRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    WaqfProjectResponse, DonationCreate, DonationResponse,
)

router = APIRouter(prefix="/waqf", tags=["waqf"])


@router.get("/projects", response_model=list[WaqfProjectResponse])
async def list_projects(current_user: CurrentUser, db: DB, repo: WaqfProjectRepo,
                         category: str = Query(default=None),
                         featured: bool = Query(default=False),
                         limit: int = Query(default=20, le=50),
                         offset: int = 0):
    projects = await repo.get_all(category=category, featured_only=featured, limit=limit, offset=offset)
    return [WaqfProjectResponse.model_validate(p) for p in projects]


@router.get("/projects/{project_id}", response_model=WaqfProjectResponse)
async def get_project(project_id: UUID, current_user: CurrentUser, db: DB, repo: WaqfProjectRepo):
    project = await repo.get_or_404(project_id)
    return WaqfProjectResponse.model_validate(project)


@router.post("/donate", response_model=DonationResponse, status_code=201)
async def donate(payload: DonationCreate, current_user: CurrentUser, db: DB,
                  repo: DonationRepo, project_repo: WaqfProjectRepo = ...):
    project = await project_repo.get_or_404(payload.project_id)
    donation = await repo.create(
        user_id=current_user.id,
        donation_date=date.today(),
        **payload.model_dump(),
    )
    # Update raised amount on pledge
    project.raised_amount += payload.amount
    await db.flush()
    return DonationResponse.model_validate(donation)


@router.get("/my-donations", response_model=list[DonationResponse])
async def my_donations(current_user: CurrentUser, db: DB, repo: DonationRepo):
    donations = await repo.get_for_user(current_user.id)
    return [DonationResponse.model_validate(d) for d in donations]


@router.get("/my-total")
async def my_total(current_user: CurrentUser, db: DB, repo: DonationRepo):
    total = await repo.get_user_total(current_user.id)
    return {"total_donated_usd": total, "currency": "USD"}
