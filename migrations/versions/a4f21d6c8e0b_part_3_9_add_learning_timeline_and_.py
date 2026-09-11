"""Part 3.9: add learning_timeline and recommendations tables

Revision ID: a4f21d6c8e0b
Revises: 933c2df8f2dd
Create Date: 2026-09-04 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4f21d6c8e0b'
down_revision = '933c2df8f2dd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('learning_timeline',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=30), nullable=False),
    sa.Column('topic_name', sa.String(length=150), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('xp_earned', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint(
        "event_type IN ('lesson_completed','quiz_attempted','code_review_submitted',"
        "'tutor_session','achievement_earned')",
        name='ck_learning_timeline_event_type',
    ),
    sa.CheckConstraint('score IS NULL OR (score >= 0 AND score <= 100)', name='ck_learning_timeline_score_range'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('learning_timeline', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learning_timeline_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learning_timeline_event_type'), ['event_type'], unique=False)

    op.create_table('recommendations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('rec_type', sa.String(length=20), nullable=False),
    sa.Column('topic_name', sa.String(length=150), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('reason', sa.String(length=300), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('is_dismissed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint(
        "rec_type IN ('next_lesson','next_quiz','revision','practice','reading')",
        name='ck_recommendations_type',
    ),
    sa.CheckConstraint('priority BETWEEN 1 AND 3', name='ck_recommendations_priority_range'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recommendations_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recommendations_is_dismissed'), ['is_dismissed'], unique=False)


def downgrade():
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recommendations_is_dismissed'))
        batch_op.drop_index(batch_op.f('ix_recommendations_user_id'))
    op.drop_table('recommendations')

    with op.batch_alter_table('learning_timeline', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_learning_timeline_event_type'))
        batch_op.drop_index(batch_op.f('ix_learning_timeline_user_id'))
    op.drop_table('learning_timeline')
