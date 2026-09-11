"""Part 3.13: AI Learning Mentor tables (study_plans, mentor_interactions)

Revision ID: c9f4d82a1e6b
Revises: b7e3a91f5c2d
Create Date: 2026-09-08 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c9f4d82a1e6b'
down_revision = 'b7e3a91f5c2d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('study_plans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('period_type', sa.String(length=10), nullable=False),
    sa.Column('plan_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("period_type IN ('daily','weekly','monthly')", name='ck_study_plan_period_type'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'period_type', name='uq_study_plan_per_user_period')
    )
    with op.batch_alter_table('study_plans', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_study_plans_user_id'), ['user_id'], unique=False)

    op.create_table('mentor_interactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=10), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('intent', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("role IN ('student','faculty')", name='ck_mentor_interaction_role'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('mentor_interactions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mentor_interactions_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('mentor_interactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mentor_interactions_user_id'))
    op.drop_table('mentor_interactions')

    with op.batch_alter_table('study_plans', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_study_plans_user_id'))
    op.drop_table('study_plans')
