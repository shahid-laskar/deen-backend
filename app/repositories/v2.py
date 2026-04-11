"""
V2 + V3 Repositories
=====================
Meal, Workout, Child, Recitation, Community, Waqf
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select, func, desc

from app.models.meal import FoodItem, MealPlan, MealEntry
from app.models.workout import Exercise, WorkoutPlan, WorkoutSession
from app.models.child import Child, ChildMilestone, DuaTeachingLog, IslamicLessonLog
from app.models.recitation import RecitationSession, RecitationFeedback
from app.models.community import (
    CommunityGroup, GroupMember, Post, Comment,
    PostReaction, ContentReport, WaqfProject, Donation,
)
from app.repositories.base import BaseRepository


# ─── Meal ─────────────────────────────────────────────────────────────────────

class FoodItemRepository(BaseRepository[FoodItem]):
    model = FoodItem

    async def search(self, user_id: UUID, query: str, limit: int = 20) -> list[FoodItem]:
        result = await self.db.execute(
            select(FoodItem)
            .where(
                FoodItem.name.ilike(f"%{query}%"),
                (FoodItem.user_id == user_id) | (FoodItem.user_id == None),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_global(self, limit: int = 100) -> list[FoodItem]:
        result = await self.db.execute(
            select(FoodItem).where(FoodItem.user_id == None).limit(limit)
        )
        return list(result.scalars().all())


class MealPlanRepository(BaseRepository[MealPlan]):
    model = MealPlan

    async def get_active_for_user(self, user_id: UUID) -> MealPlan | None:
        result = await self.db.execute(
            select(MealPlan).where(
                MealPlan.user_id == user_id,
                MealPlan.is_active == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_for_user(self, user_id: UUID) -> list[MealPlan]:
        result = await self.db.execute(
            select(MealPlan).where(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
        )
        return list(result.scalars().all())


class MealEntryRepository(BaseRepository[MealEntry]):
    model = MealEntry

    async def get_for_date(self, user_id: UUID, entry_date: date) -> list[MealEntry]:
        result = await self.db.execute(
            select(MealEntry).where(
                MealEntry.user_id == user_id,
                MealEntry.entry_date == entry_date,
            ).order_by(MealEntry.meal_time)
        )
        return list(result.scalars().all())

    async def get_daily_totals(self, user_id: UUID, entry_date: date) -> dict:
        result = await self.db.execute(
            select(
                func.sum(MealEntry.calories).label("calories"),
                func.sum(MealEntry.protein_g).label("protein_g"),
                func.sum(MealEntry.carbs_g).label("carbs_g"),
                func.sum(MealEntry.fat_g).label("fat_g"),
                func.sum(MealEntry.water_ml).label("water_ml"),
            ).where(
                MealEntry.user_id == user_id,
                MealEntry.entry_date == entry_date,
            )
        )
        row = result.one()
        return {
            "calories": float(row.calories or 0),
            "protein_g": float(row.protein_g or 0),
            "carbs_g": float(row.carbs_g or 0),
            "fat_g": float(row.fat_g or 0),
            "water_ml": int(row.water_ml or 0),
            "date": entry_date,
        }

    async def get_for_date_range(self, user_id: UUID, start: date, end: date) -> list[MealEntry]:
        result = await self.db.execute(
            select(MealEntry).where(
                MealEntry.user_id == user_id,
                MealEntry.entry_date >= start,
                MealEntry.entry_date <= end,
            ).order_by(MealEntry.entry_date.desc(), MealEntry.meal_time)
        )
        return list(result.scalars().all())


# ─── Workout ──────────────────────────────────────────────────────────────────

class ExerciseRepository(BaseRepository[Exercise]):
    model = Exercise

    async def search(self, user_id: UUID, query: str, limit: int = 20) -> list[Exercise]:
        result = await self.db.execute(
            select(Exercise).where(
                Exercise.name.ilike(f"%{query}%"),
                (Exercise.user_id == user_id) | (Exercise.user_id == None),
            ).limit(limit)
        )
        return list(result.scalars().all())


class WorkoutPlanRepository(BaseRepository[WorkoutPlan]):
    model = WorkoutPlan

    async def get_all_for_user(self, user_id: UUID) -> list[WorkoutPlan]:
        result = await self.db.execute(
            select(WorkoutPlan).where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active(self, user_id: UUID) -> WorkoutPlan | None:
        result = await self.db.execute(
            select(WorkoutPlan).where(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.is_active == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()


class WorkoutSessionRepository(BaseRepository[WorkoutSession]):
    model = WorkoutSession

    async def get_for_user(
        self, user_id: UUID, start: date | None = None, end: date | None = None
    ) -> list[WorkoutSession]:
        stmt = select(WorkoutSession).where(WorkoutSession.user_id == user_id)
        if start:
            stmt = stmt.where(WorkoutSession.session_date >= start)
        if end:
            stmt = stmt.where(WorkoutSession.session_date <= end)
        stmt = stmt.order_by(WorkoutSession.session_date.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_weekly_count(self, user_id: UUID) -> int:
        from datetime import timedelta
        week_start = date.today() - timedelta(days=date.today().weekday())
        result = await self.db.execute(
            select(func.count()).select_from(WorkoutSession).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.session_date >= week_start,
            )
        )
        return result.scalar_one()


# ─── Child ─────────────────────────────────────────────────────────────────────

class ChildRepository(BaseRepository[Child]):
    model = Child

    async def get_all_for_user(self, user_id: UUID) -> list[Child]:
        result = await self.db.execute(
            select(Child).where(
                Child.user_id == user_id,
                Child.is_active == True,
            ).order_by(Child.created_at)
        )
        return list(result.scalars().all())


class MilestoneRepository(BaseRepository[ChildMilestone]):
    model = ChildMilestone

    async def get_for_child(
        self, child_id: UUID, category: str | None = None
    ) -> list[ChildMilestone]:
        stmt = select(ChildMilestone).where(ChildMilestone.child_id == child_id)
        if category:
            stmt = stmt.where(ChildMilestone.category == category)
        stmt = stmt.order_by(ChildMilestone.achieved, ChildMilestone.target_age_months)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class DuaTeachingRepository(BaseRepository[DuaTeachingLog]):
    model = DuaTeachingLog

    async def get_for_child(self, child_id: UUID) -> list[DuaTeachingLog]:
        result = await self.db.execute(
            select(DuaTeachingLog).where(DuaTeachingLog.child_id == child_id)
            .order_by(DuaTeachingLog.status)
        )
        return list(result.scalars().all())


class LessonLogRepository(BaseRepository[IslamicLessonLog]):
    model = IslamicLessonLog

    async def get_for_child(
        self, child_id: UUID, subject: str | None = None, limit: int = 50
    ) -> list[IslamicLessonLog]:
        stmt = select(IslamicLessonLog).where(IslamicLessonLog.child_id == child_id)
        if subject:
            stmt = stmt.where(IslamicLessonLog.subject == subject)
        stmt = stmt.order_by(IslamicLessonLog.lesson_date.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# ─── Recitation ───────────────────────────────────────────────────────────────

class RecitationRepository(BaseRepository[RecitationSession]):
    model = RecitationSession

    async def get_for_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[RecitationSession]:
        result = await self.db.execute(
            select(RecitationSession)
            .where(RecitationSession.user_id == user_id)
            .order_by(RecitationSession.session_date.desc(), RecitationSession.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_stats(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(
                func.count().label("total"),
                func.avg(RecitationSession.overall_score).label("avg_score"),
                func.sum(RecitationSession.audio_duration_seconds).label("total_seconds"),
            ).where(
                RecitationSession.user_id == user_id,
                RecitationSession.status == "complete",
            )
        )
        row = result.one()
        return {
            "total_sessions": int(row.total or 0),
            "avg_score": round(float(row.avg_score or 0), 1),
            "total_minutes": round(int(row.total_seconds or 0) / 60, 1),
        }


class RecitationFeedbackRepository(BaseRepository[RecitationFeedback]):
    model = RecitationFeedback

    async def get_for_session(self, session_id: UUID) -> RecitationFeedback | None:
        result = await self.db.execute(
            select(RecitationFeedback).where(RecitationFeedback.session_id == session_id)
        )
        return result.scalar_one_or_none()


# ─── Community ────────────────────────────────────────────────────────────────

class CommunityGroupRepository(BaseRepository[CommunityGroup]):
    model = CommunityGroup

    async def get_all(
        self, category: str | None = None, search: str | None = None,
        limit: int = 30, offset: int = 0,
    ) -> list[CommunityGroup]:
        stmt = select(CommunityGroup).where(CommunityGroup.is_active == True)
        if category:
            stmt = stmt.where(CommunityGroup.category == category)
        if search:
            stmt = stmt.where(CommunityGroup.name.ilike(f"%{search}%"))
        stmt = stmt.order_by(CommunityGroup.member_count.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> CommunityGroup | None:
        result = await self.db.execute(
            select(CommunityGroup).where(CommunityGroup.slug == slug)
        )
        return result.scalar_one_or_none()

    async def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None


class PostRepository(BaseRepository[Post]):
    model = Post

    async def get_for_group(
        self, group_id: UUID, post_type: str | None = None,
        limit: int = 20, offset: int = 0,
    ) -> list[Post]:
        stmt = select(Post).where(
            Post.group_id == group_id,
            Post.is_active == True,
        )
        if post_type:
            stmt = stmt.where(Post.post_type == post_type)
        stmt = stmt.order_by(Post.is_pinned.desc(), Post.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_global_feed(
        self, limit: int = 30, offset: int = 0,
    ) -> list[Post]:
        result = await self.db.execute(
            select(Post).where(
                Post.group_id == None,
                Post.is_active == True,
            ).order_by(Post.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def user_reacted(self, post_id: UUID, user_id: UUID) -> PostReaction | None:
        result = await self.db.execute(
            select(PostReaction).where(
                PostReaction.post_id == post_id,
                PostReaction.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def get_for_post(
        self, post_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Comment]:
        result = await self.db.execute(
            select(Comment).where(
                Comment.post_id == post_id,
                Comment.is_active == True,
                Comment.parent_id == None,  # top-level only
            ).order_by(Comment.created_at.asc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())


# ─── Waqf ─────────────────────────────────────────────────────────────────────

class WaqfProjectRepository(BaseRepository[WaqfProject]):
    model = WaqfProject

    async def get_all(
        self, category: str | None = None, featured_only: bool = False,
        limit: int = 20, offset: int = 0,
    ) -> list[WaqfProject]:
        stmt = select(WaqfProject).where(WaqfProject.is_active == True)
        if category:
            stmt = stmt.where(WaqfProject.category == category)
        if featured_only:
            stmt = stmt.where(WaqfProject.is_featured == True)
        stmt = stmt.order_by(
            WaqfProject.is_featured.desc(),
            WaqfProject.is_verified.desc(),
            WaqfProject.created_at.desc(),
        ).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class DonationRepository(BaseRepository[Donation]):
    model = Donation

    async def get_for_user(self, user_id: UUID) -> list[Donation]:
        result = await self.db.execute(
            select(Donation).where(Donation.user_id == user_id)
            .order_by(Donation.donation_date.desc())
        )
        return list(result.scalars().all())

    async def get_user_total(self, user_id: UUID) -> float:
        result = await self.db.execute(
            select(func.sum(Donation.amount)).where(
                Donation.user_id == user_id,
                Donation.status == "confirmed",
            )
        )
        return float(result.scalar_one() or 0)
