"""
V2 + V3 Pydantic Schemas
========================
Meal, Workout, Child, Recitation, Qibla, Community, Waqf, Cycle-sync
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Shared base ──────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─── Food / Meal ──────────────────────────────────────────────────────────────

class FoodItemCreate(BaseModel):
    name: str = Field(..., max_length=200)
    arabic_name: Optional[str] = None
    brand: Optional[str] = None
    category: str = "other"
    is_halal_certified: bool = False
    is_vegetarian: bool = False
    serving_size_g: Optional[float] = None
    calories_per_100g: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fibre_g: Optional[float] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None


class FoodItemResponse(OrmBase):
    id: uuid.UUID
    name: str
    arabic_name: Optional[str] = None
    brand: Optional[str] = None
    category: str
    is_halal_certified: bool
    is_vegetarian: bool
    serving_size_g: Optional[float] = None
    calories_per_100g: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fibre_g: Optional[float] = None
    barcode: Optional[str] = None
    created_at: datetime


class MealPlanCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    daily_calorie_goal: Optional[int] = None
    daily_protein_goal_g: Optional[float] = None
    daily_carb_goal_g: Optional[float] = None
    daily_fat_goal_g: Optional[float] = None
    daily_water_goal_ml: int = 2000
    is_ramadan_mode: bool = False


class MealPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    daily_calorie_goal: Optional[int] = None
    daily_water_goal_ml: Optional[int] = None
    is_active: Optional[bool] = None
    is_ramadan_mode: Optional[bool] = None


class MealPlanResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    is_ramadan_mode: bool
    daily_calorie_goal: Optional[int] = None
    daily_water_goal_ml: Optional[int] = None
    created_at: datetime


class MealEntryCreate(BaseModel):
    entry_date: date
    meal_type: str  # breakfast, lunch, dinner, snack, suhoor, iftar
    food_name: str = Field(..., max_length=200)
    quantity_g: Optional[float] = None
    servings: float = 1.0
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    is_water_entry: bool = False
    water_ml: Optional[int] = None
    is_halal: Optional[bool] = None
    plan_id: Optional[uuid.UUID] = None
    food_item_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class MealEntryUpdate(BaseModel):
    food_name: Optional[str] = None
    quantity_g: Optional[float] = None
    servings: Optional[float] = None
    calories: Optional[float] = None
    notes: Optional[str] = None


class MealEntryResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    entry_date: date
    meal_type: str
    food_name: str
    servings: float
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    is_water_entry: bool
    water_ml: Optional[int] = None
    is_halal: Optional[bool] = None
    notes: Optional[str] = None
    created_at: datetime


class DailyNutritionSummary(BaseModel):
    date: date
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: int


# ─── Workout ──────────────────────────────────────────────────────────────────

class ExerciseCreate(BaseModel):
    name: str = Field(..., max_length=200)
    arabic_name: Optional[str] = None
    description: Optional[str] = None
    category: str = "strength"
    muscle_groups: Optional[list[str]] = None
    equipment: Optional[str] = None
    is_wudu_safe: bool = True
    gender_suitable: str = "all"
    notes: Optional[str] = None
    video_url: Optional[str] = None


class ExerciseResponse(OrmBase):
    id: uuid.UUID
    name: str
    arabic_name: Optional[str] = None
    category: str
    muscle_groups: Optional[list[str]] = None
    equipment: Optional[str] = None
    is_wudu_safe: bool
    gender_suitable: str
    notes: Optional[str] = None


class WorkoutPlanCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    goal: Optional[str] = None
    days_per_week: int = Field(default=3, ge=1, le=7)
    duration_weeks: Optional[int] = None
    is_ramadan_mode: bool = False
    preferred_time_block: Optional[str] = None


class WorkoutPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    days_per_week: Optional[int] = None
    is_active: Optional[bool] = None
    is_ramadan_mode: Optional[bool] = None
    preferred_time_block: Optional[str] = None


class WorkoutPlanResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    goal: Optional[str] = None
    days_per_week: int
    duration_weeks: Optional[int] = None
    is_active: bool
    is_ramadan_mode: bool
    preferred_time_block: Optional[str] = None
    created_at: datetime


class WorkoutSessionCreate(BaseModel):
    session_date: date
    session_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    exercises_log: Optional[list[dict]] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    time_block: Optional[str] = None
    plan_id: Optional[uuid.UUID] = None


class WorkoutSessionUpdate(BaseModel):
    session_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    exercises_log: Optional[list[dict]] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    completed: Optional[bool] = None


class WorkoutSessionResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    session_date: date
    session_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    exercises_log: Optional[list[dict]] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    time_block: Optional[str] = None
    completed: bool
    created_at: datetime


# ─── Child ────────────────────────────────────────────────────────────────────

class ChildCreate(BaseModel):
    name: str = Field(..., max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    avatar_emoji: str = "🌟"
    notes: Optional[str] = None


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    avatar_emoji: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ChildResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    avatar_emoji: str
    notes: Optional[str] = None
    is_active: bool
    # Gamification
    xp_total: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[date] = None
    age_group: Optional[str] = None
    created_at: datetime


class MilestoneCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    category: str
    target_age_months: Optional[int] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    achieved: Optional[bool] = None
    achieved_date: Optional[date] = None
    celebration_note: Optional[str] = None


class MilestoneResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    title: str
    description: Optional[str] = None
    category: str
    target_age_months: Optional[int] = None
    achieved: bool
    achieved_date: Optional[date] = None
    celebration_note: Optional[str] = None
    created_at: datetime


class DuaTeachingCreate(BaseModel):
    dua_key: str = Field(..., max_length=100)
    dua_name: str = Field(..., max_length=200)
    status: str = "learning"
    notes: Optional[str] = None


class DuaTeachingUpdate(BaseModel):
    status: Optional[str] = None
    mastered_date: Optional[date] = None
    notes: Optional[str] = None


class DuaTeachingResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    dua_key: str
    dua_name: str
    status: str
    started_date: Optional[date] = None
    mastered_date: Optional[date] = None
    practice_count: int = 0
    last_practiced: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime


class LessonLogCreate(BaseModel):
    lesson_date: date
    subject: str
    topic: str = Field(..., max_length=300)
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class LessonLogResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    lesson_date: date
    subject: str
    topic: str
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    created_at: datetime


class ChildActivityLogCreate(BaseModel):
    activity_key: str = Field(..., max_length=100)
    activity_name: str = Field(..., max_length=200)
    activity_category: str  # quran, salah, dua, story, akhlaq, craft
    xp_earned: int = Field(default=10, ge=0)
    duration_minutes: Optional[int] = None
    completed: bool = True
    log_date: Optional[date] = None
    notes: Optional[str] = None
    logged_by: str = "parent"  # parent or child


class ChildActivityLogResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    activity_key: str
    activity_name: str
    activity_category: str
    xp_earned: int
    duration_minutes: Optional[int] = None
    completed: bool
    log_date: date
    notes: Optional[str] = None
    logged_by: str
    created_at: datetime


class ChildBadgeResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    badge_key: str
    badge_name: str
    badge_icon: str
    badge_category: str
    earned_date: date
    xp_awarded: int
    created_at: datetime


class ChildActivityResult(BaseModel):
    """Response from logging an activity — includes XP gain, level-up, new badges."""
    activity: ChildActivityLogResponse
    xp_gained: int
    new_total_xp: int
    new_level: int
    level_name: str
    leveled_up: bool
    new_badges: list[ChildBadgeResponse] = []


class ChildStoryProgressResponse(OrmBase):
    id: uuid.UUID
    child_id: uuid.UUID
    story_key: str
    started_date: Optional[date] = None
    completed_date: Optional[date] = None
    is_favorite: bool
    times_read: int
    xp_earned: int
    created_at: datetime


# ─── Recitation ───────────────────────────────────────────────────────────────

class RecitationSessionCreate(BaseModel):
    session_date: date
    surah_number: Optional[int] = Field(default=None, ge=1, le=114)
    surah_name: Optional[str] = None
    ayah_from: Optional[int] = None
    ayah_to: Optional[int] = None
    recited_text: Optional[str] = None
    audio_url: Optional[str] = None
    audio_duration_seconds: Optional[int] = None
    session_type: str = "practice"
    notes: Optional[str] = None


class RecitationSessionResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    session_date: date
    surah_number: Optional[int] = None
    surah_name: Optional[str] = None
    ayah_from: Optional[int] = None
    ayah_to: Optional[int] = None
    overall_score: Optional[float] = None
    fluency_score: Optional[float] = None
    tajweed_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    status: str
    session_type: str
    audio_duration_seconds: Optional[int] = None
    user_rating: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime


class RecitationFeedbackResponse(OrmBase):
    id: uuid.UUID
    session_id: uuid.UUID
    tajweed_errors: Optional[list[dict]] = None
    strengths: Optional[list[str]] = None
    improvement_areas: Optional[list[str]] = None
    next_steps: Optional[str] = None
    summary: Optional[str] = None
    detailed_feedback: Optional[str] = None
    transcription_confidence: Optional[float] = None
    created_at: datetime


class RecitationStats(BaseModel):
    total_sessions: int
    avg_score: float
    total_minutes: float


# ─── Community ────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = "general"
    icon: str = "🕌"
    is_private: bool = False
    rules: Optional[str] = None


class GroupResponse(OrmBase):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    category: str
    icon: str
    is_private: bool
    is_verified: bool
    member_count: int
    post_count: int
    created_at: datetime


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(default=None, max_length=300)
    post_type: str = "text"
    tags: Optional[list[str]] = None
    is_anonymous: bool = False
    group_id: Optional[uuid.UUID] = None


class PostUpdate(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[list[str]] = None


class PostResponse(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    group_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    content: str
    post_type: str
    tags: Optional[list[str]] = None
    is_anonymous: bool
    is_pinned: bool
    like_count: int
    comment_count: int
    created_at: datetime


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_anonymous: bool = False
    parent_id: Optional[uuid.UUID] = None


class CommentResponse(OrmBase):
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    is_anonymous: bool
    like_count: int
    parent_id: Optional[uuid.UUID] = None
    created_at: datetime


# ─── Waqf ─────────────────────────────────────────────────────────────────────

class WaqfProjectResponse(OrmBase):
    id: uuid.UUID
    title: str
    description: str
    category: str
    location: Optional[str] = None
    country: Optional[str] = None
    goal_amount: float
    raised_amount: float
    currency: str
    beneficiaries_count: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    is_verified: bool
    is_featured: bool
    is_completed: bool
    image_url: Optional[str] = None
    external_donation_url: Optional[str] = None
    tags: Optional[list[str]] = None
    created_at: datetime

    @property
    def progress_pct(self) -> float:
        if not self.goal_amount:
            return 0.0
        return min(100.0, round((self.raised_amount / self.goal_amount) * 100, 1))


class DonationCreate(BaseModel):
    project_id: uuid.UUID
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    is_anonymous: bool = False
    is_recurring: bool = False
    recurring_interval: Optional[str] = None
    niyyah: Optional[str] = None


class DonationResponse(OrmBase):
    id: uuid.UUID
    project_id: uuid.UUID
    amount: float
    currency: str
    donation_date: date
    is_anonymous: bool
    is_recurring: bool
    status: str
    niyyah: Optional[str] = None
    created_at: datetime
