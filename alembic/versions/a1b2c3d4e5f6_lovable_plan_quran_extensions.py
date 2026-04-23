"""lovable_plan_quran_extensions

Revision ID: a1b2c3d4e5f6
Revises: 5af12ab19050
Create Date: 2026-04-21 12:00:00.000000

Adds:
  - quran_last_read   (server-side last-read sync)
  - bookmark_folders  (bookmark organization)
  - khatam_plans      (khatam goal tracking)
  - quran_bookmarks.folder_id nullable FK
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'b6e9ec4c0396'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── bookmark_folders (must come before quran_bookmarks FK) ──
    op.create_table(
        'bookmark_folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(30), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bookmark_folders_user_id', 'bookmark_folders', ['user_id'])

    # ── Add folder_id to quran_bookmarks ──
    op.add_column('quran_bookmarks', sa.Column('folder_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_quran_bookmarks_folder_id',
        'quran_bookmarks', 'bookmark_folders',
        ['folder_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_quran_bookmarks_folder_id', 'quran_bookmarks', ['folder_id'])

    # ── quran_last_read ──
    op.create_table(
        'quran_last_read',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('surah_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('ayah_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('surah_name', sa.String(150), nullable=True),
        sa.Column('surah_arabic', sa.String(100), nullable=True),
        sa.Column('total_ayahs', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_quran_last_read_user_id', 'quran_last_read', ['user_id'])

    # ── khatam_plans ──
    op.create_table(
        'khatam_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('daily_verse_goal', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_khatam_plans_user_id', 'khatam_plans', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_khatam_plans_user_id', table_name='khatam_plans')
    op.drop_table('khatam_plans')

    op.drop_index('ix_quran_last_read_user_id', table_name='quran_last_read')
    op.drop_table('quran_last_read')

    op.drop_index('ix_quran_bookmarks_folder_id', table_name='quran_bookmarks')
    op.drop_constraint('fk_quran_bookmarks_folder_id', 'quran_bookmarks', type_='foreignkey')
    op.drop_column('quran_bookmarks', 'folder_id')

    op.drop_index('ix_bookmark_folders_user_id', table_name='bookmark_folders')
    op.drop_table('bookmark_folders')
