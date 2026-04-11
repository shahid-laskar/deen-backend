"""
Meal & Halal Diet Models
========================
MealPlan  — weekly/custom plan with calorie goals
MealEntry — individual logged meal (breakfast/suhoor/iftar/etc.)
FoodItem  — reusable food catalogue entry (user-created or global)
"""

import uuid
from datetime import date, time

from sqlalchemy import (
    Boolean, Date, Float, ForeignKey, Integer,
    String, Text, Time, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class FoodItem(Base, TimestampMixin):
    __tablename__ = "food_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )  # None = global/system item

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    arabic_name: Mapped[str | None] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(
        String(50), default="other"
    )  # protein, carb, dairy, fruit, veg, grain, beverage, other
    is_halal_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)

    # Nutrition per 100g / per serving
    serving_size_g: Mapped[float | None] = mapped_column(Float)
    calories_per_100g: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    fibre_g: Mapped[float | None] = mapped_column(Float)

    barcode: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    entries: Mapped[list["MealEntry"]] = relationship(back_populates="food_item")


class MealPlan(Base, TimestampMixin):
    __tablename__ = "meal_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Nutritional goals
    daily_calorie_goal: Mapped[int | None] = mapped_column(Integer)
    daily_protein_goal_g: Mapped[float | None] = mapped_column(Float)
    daily_carb_goal_g: Mapped[float | None] = mapped_column(Float)
    daily_fat_goal_g: Mapped[float | None] = mapped_column(Float)
    daily_water_goal_ml: Mapped[int | None] = mapped_column(Integer, default=2000)

    # Ramadan mode
    is_ramadan_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    entries: Mapped[list["MealEntry"]] = relationship(back_populates="plan")


class MealEntry(Base, TimestampMixin):
    __tablename__ = "meal_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="SET NULL"), nullable=True
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("food_items.id", ondelete="SET NULL"), nullable=True
    )

    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # breakfast, lunch, dinner, snack, suhoor, iftar, sehri
    meal_time: Mapped[time | None] = mapped_column(Time)

    # Can be free-text if no food_item_id
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity_g: Mapped[float | None] = mapped_column(Float)
    servings: Mapped[float] = mapped_column(Float, default=1.0)

    # Computed / entered nutrition
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)

    # Water tracking (standalone)
    is_water_entry: Mapped[bool] = mapped_column(Boolean, default=False)
    water_ml: Mapped[int | None] = mapped_column(Integer)

    # Halal flag
    is_halal: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped["MealPlan | None"] = relationship(back_populates="entries")
    food_item: Mapped["FoodItem | None"] = relationship(back_populates="entries")
