"""Family Accounts Router"""
from uuid import UUID
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from app.core.dependencies import CurrentUser, DB
from app.schemas.base import MessageResponse
from app.models.family import FamilyPlan, FamilyMember

router = APIRouter(prefix="/family", tags=["family"])

class FamilyMemberResponse(BaseModel):
    user_id: UUID
    role: str
    account_type: str

class FamilyPlanResponse(BaseModel):
    id: UUID
    plan_type: str
    member_count: int
    members: List[FamilyMemberResponse] = []

class InviteMemberInput(BaseModel):
    user_id: UUID
    role: str = "member"
    account_type: str = "adult"

@router.get("/", response_model=FamilyPlanResponse)
async def get_family_plan(current_user: CurrentUser, db: DB):
    # Mock lookup
    raise HTTPException(status_code=404, detail="No active family plan found.")

@router.post("/", response_model=FamilyPlanResponse)
async def create_family_plan(plan_type: str, current_user: CurrentUser, db: DB):
    plan = FamilyPlan(admin_user_id=current_user.id, plan_type=plan_type, member_count=1)
    db.add(plan)
    # Add self as admin
    member = FamilyMember(family_id=plan.id, user_id=current_user.id, role="admin", account_type="adult")
    db.add(member)
    await db.flush()
    return FamilyPlanResponse(id=plan.id, plan_type=plan.plan_type, member_count=1)

@router.post("/members", response_model=MessageResponse)
async def invite_member(payload: InviteMemberInput, current_user: CurrentUser, db: DB):
    # Logic to invite member
    return MessageResponse(message="Member successfully invited.")
