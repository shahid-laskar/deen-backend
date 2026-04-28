"""phase4_5_6_child_upbringing

Revision ID: d7e8f9a0b1c2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-27 12:00:00.000000

Adds child story progress, dua teaching log updates, and child quran progress.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd7e8f9a0b1c2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # ── child_story_progress ──
    if 'child_story_progress' not in tables:
        op.create_table(
            'child_story_progress',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('story_key', sa.String(100), nullable=False),
            sa.Column('started_date', sa.Date(), nullable=True),
            sa.Column('completed_date', sa.Date(), nullable=True),
            sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('times_read', sa.Integer(), server_default='0', nullable=False),
            sa.Column('xp_earned', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # ── child_quran_progress ──
    if 'child_quran_progress' not in tables:
        op.create_table(
            'child_quran_progress',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('surah_number', sa.Integer(), nullable=False),
            sa.Column('surah_name', sa.String(100), nullable=False),
            sa.Column('status', sa.String(20), server_default='not_started', nullable=False),
            sa.Column('ayahs_memorized', sa.Integer(), server_default='0', nullable=False),
            sa.Column('total_ayahs', sa.Integer(), nullable=False),
            sa.Column('started_date', sa.Date(), nullable=True),
            sa.Column('memorized_date', sa.Date(), nullable=True),
            sa.Column('last_reviewed', sa.Date(), nullable=True),
            sa.Column('quality_rating', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # ── dua_teaching_logs updates ──
    # Check if columns exist (for local dev environments where we did it manually)
    columns = [c['name'] for c in inspector.get_columns('dua_teaching_logs')]
    
    if 'practice_count' not in columns:
        op.add_column('dua_teaching_logs', sa.Column('practice_count', sa.Integer(), server_default='0', nullable=False))
    if 'last_practiced' not in columns:
        op.add_column('dua_teaching_logs', sa.Column('last_practiced', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('dua_teaching_logs', 'last_practiced')
    op.drop_column('dua_teaching_logs', 'practice_count')
    op.drop_table('child_quran_progress')
    op.drop_table('child_story_progress')
