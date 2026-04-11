"""Meal & Halal Diet Planner Router"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.repositories import MealEntryRepo, MealPlanRepo, FoodItemRepo
from app.schemas.base import MessageResponse
from app.schemas.v2schemas import (
    FoodItemCreate, FoodItemResponse,
    MealEntryCreate, MealEntryResponse, MealEntryUpdate,
    MealPlanCreate, MealPlanResponse, MealPlanUpdate,
    DailyNutritionSummary,
)

router = APIRouter(prefix="/meal", tags=["meal"])


@router.get("/plans", response_model=list[MealPlanResponse])
async def list_plans(current_user: CurrentUser, db: DB, repo: MealPlanRepo):
    plans = await repo.get_all_for_user(current_user.id)
    return [MealPlanResponse.model_validate(p) for p in plans]


@router.post("/plans", response_model=MealPlanResponse, status_code=201)
async def create_plan(payload: MealPlanCreate, current_user: CurrentUser, db: DB, repo: MealPlanRepo):
    plan = await repo.create(user_id=current_user.id, **payload.model_dump())
    return MealPlanResponse.model_validate(plan)


@router.get("/plans/active", response_model=MealPlanResponse | None)
async def get_active_plan(current_user: CurrentUser, db: DB, repo: MealPlanRepo):
    plan = await repo.get_active_for_user(current_user.id)
    return MealPlanResponse.model_validate(plan) if plan else None


@router.patch("/plans/{plan_id}", response_model=MealPlanResponse)
async def update_plan(plan_id: UUID, payload: MealPlanUpdate, current_user: CurrentUser, db: DB, repo: MealPlanRepo):
    plan = await repo.get_owned_or_404(plan_id, current_user.id)
    plan = await repo.update(plan, **payload.model_dump(exclude_none=True))
    return MealPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}", response_model=MessageResponse)
async def delete_plan(plan_id: UUID, current_user: CurrentUser, db: DB, repo: MealPlanRepo):
    plan = await repo.get_owned_or_404(plan_id, current_user.id)
    await repo.delete(plan)
    return MessageResponse(message="Meal plan deleted.")


@router.get("/log", response_model=list[MealEntryResponse])
async def list_entries(current_user: CurrentUser, db: DB, repo: MealEntryRepo,
                        entry_date: date = Query(default=None)):
    target = entry_date or date.today()
    entries = await repo.get_for_date(current_user.id, target)
    return [MealEntryResponse.model_validate(e) for e in entries]


@router.post("/log", response_model=MealEntryResponse, status_code=201)
async def log_meal(payload: MealEntryCreate, current_user: CurrentUser, db: DB, repo: MealEntryRepo):
    entry = await repo.create(user_id=current_user.id, **payload.model_dump())
    return MealEntryResponse.model_validate(entry)


@router.patch("/log/{entry_id}", response_model=MealEntryResponse)
async def update_entry(entry_id: UUID, payload: MealEntryUpdate, current_user: CurrentUser, db: DB, repo: MealEntryRepo):
    entry = await repo.get_owned_or_404(entry_id, current_user.id)
    entry = await repo.update(entry, **payload.model_dump(exclude_none=True))
    return MealEntryResponse.model_validate(entry)


@router.delete("/log/{entry_id}", response_model=MessageResponse)
async def delete_entry(entry_id: UUID, current_user: CurrentUser, db: DB, repo: MealEntryRepo):
    entry = await repo.get_owned_or_404(entry_id, current_user.id)
    await repo.delete(entry)
    return MessageResponse(message="Meal entry deleted.")


@router.get("/summary/today", response_model=DailyNutritionSummary)
async def today_summary(current_user: CurrentUser, db: DB, repo: MealEntryRepo):
    totals = await repo.get_daily_totals(current_user.id, date.today())
    return DailyNutritionSummary(**totals)


@router.get("/foods/search", response_model=list[FoodItemResponse])
async def search_foods(q: str = Query(min_length=2), current_user: CurrentUser = ...,
                        db: DB = ..., repo: FoodItemRepo = ...):
    items = await repo.search(current_user.id, q)
    return [FoodItemResponse.model_validate(i) for i in items]


@router.post("/foods", response_model=FoodItemResponse, status_code=201)
async def create_food(payload: FoodItemCreate, current_user: CurrentUser, db: DB, repo: FoodItemRepo):
    item = await repo.create(user_id=current_user.id, **payload.model_dump())
    return FoodItemResponse.model_validate(item)
