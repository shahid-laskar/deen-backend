"""
Community & Waqf / Donation Models
====================================
Community:
  CommunityGroup  — topic-based group (e.g. "Quran study circle")
  GroupMember     — membership + role
  Post            — content post inside a group or global feed
  Comment         — threaded comment on a post
  PostReaction    — like / mashaaAllah / etc.
  Report          — content moderation report

Waqf:
  WaqfProject     — a charitable project listed for donations
  Donation        — a pledge/donation by a user
"""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean, Date, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base, TimestampMixin


# ─── Community ─────────────────────────────────────────────────────────────────

class CommunityGroup(Base, TimestampMixin):
    __tablename__ = "community_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="general")
    # general, quran, hadith, fiqh, lifestyle, sisters, brothers, youth, family
    icon: Mapped[str] = mapped_column(String(10), default="🕌")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # moderated group
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    rules: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    members: Mapped[list["GroupMember"]] = relationship(back_populates="group")
    posts: Mapped[list["Post"]] = relationship(back_populates="group")


class GroupMember(Base, TimestampMixin):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member")  # member, moderator, admin
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[date] = mapped_column(Date, nullable=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)

    group: Mapped["CommunityGroup"] = relationship(back_populates="members")


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_groups.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    post_type: Mapped[str] = mapped_column(
        String(20), default="text"
    )  # text, question, reflection, resource, announcement
    tags: Mapped[list | None] = mapped_column(JSON)

    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified_scholar: Mapped[bool] = mapped_column(Boolean, default=False)

    # Engagement counts (denormalised for performance)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    group: Mapped["CommunityGroup | None"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates="post")
    reactions: Mapped[list["PostReaction"]] = relationship(back_populates="post")


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    post: Mapped["Post"] = relationship(back_populates="comments")


class PostReaction(Base, TimestampMixin):
    __tablename__ = "post_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reaction_type: Mapped[str] = mapped_column(
        String(20), default="like"
    )  # like, mashaallah, jazakallah, ameen

    post: Mapped["Post"] = relationship(back_populates="reactions")


class ContentReport(Base, TimestampMixin):
    __tablename__ = "content_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    reason: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # spam, inappropriate, misinformation, harassment, off_topic
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, resolved, dismissed
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# ─── Waqf / Donations ──────────────────────────────────────────────────────────

class WaqfProject(Base, TimestampMixin):
    __tablename__ = "waqf_projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # masjid, school, water, food, healthcare, orphan, quran, infrastructure
    location: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))

    goal_amount: Mapped[float] = mapped_column(Float, nullable=False)
    raised_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    beneficiaries_count: Mapped[int | None] = mapped_column(Integer)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    image_url: Mapped[str | None] = mapped_column(String(500))
    external_donation_url: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[list | None] = mapped_column(JSON)

    donations: Mapped[list["Donation"]] = relationship(back_populates="project")


class Donation(Base, TimestampMixin):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("waqf_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    donation_date: Mapped[date] = mapped_column(Date, nullable=False)

    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_interval: Mapped[str | None] = mapped_column(String(20))  # monthly, quarterly, annual
    niyyah: Mapped[str | None] = mapped_column(Text)  # intention note

    # Payment
    status: Mapped[str] = mapped_column(String(20), default="pledged")  # pledged, confirmed, failed
    external_reference: Mapped[str | None] = mapped_column(String(200))

    project: Mapped["WaqfProject"] = relationship(back_populates="donations")
