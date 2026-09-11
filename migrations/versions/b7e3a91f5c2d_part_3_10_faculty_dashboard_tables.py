"""Part 3.10: Faculty Dashboard tables (assignments, submissions,
content resources/revisions) + Quiz publish/schedule columns

Revision ID: b7e3a91f5c2d
Revises: a4f21d6c8e0b
Create Date: 2026-09-05 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e3a91f5c2d'
down_revision = 'a4f21d6c8e0b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('due_at', sa.DateTime(), nullable=False),
    sa.Column('allow_late_submission', sa.Boolean(), nullable=False),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('max_score', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('max_score > 0', name='ck_assignments_max_score_positive'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignments_topic_id'), ['topic_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignments_is_published'), ['is_published'], unique=False)

    op.create_table('assignment_submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('submission_text', sa.Text(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=False),
    sa.Column('is_late', sa.Boolean(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('graded_at', sa.DateTime(), nullable=True),
    sa.Column('graded_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('score IS NULL OR (score >= 0)', name='ck_assignment_submission_score_nonnegative'),
    sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['graded_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('assignment_id', 'user_id', name='uq_assignment_submission_per_student')
    )
    with op.batch_alter_table('assignment_submissions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignment_submissions_assignment_id'), ['assignment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignment_submissions_user_id'), ['user_id'], unique=False)

    op.create_table('content_resources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('uploaded_by_user_id', sa.Integer(), nullable=True),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('stored_filename', sa.String(length=255), nullable=False),
    sa.Column('file_type', sa.String(length=10), nullable=False),
    sa.Column('file_size_bytes', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stored_filename')
    )
    with op.batch_alter_table('content_resources', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_content_resources_topic_id'), ['topic_id'], unique=False)

    op.create_table('content_revisions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('content_type', sa.String(length=10), nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=False),
    sa.Column('snapshot_json', sa.Text(), nullable=False),
    sa.Column('edited_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("content_type IN ('topic','lesson')", name='ck_content_revisions_type'),
    sa.ForeignKeyConstraint(['edited_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_revisions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_content_revisions_content_type'), ['content_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_content_revisions_content_id'), ['content_id'], unique=False)

    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('scheduled_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('faculty_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subjects_taught', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('faculty_profiles', schema=None) as batch_op:
        batch_op.drop_column('subjects_taught')

    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_column('scheduled_at')
        batch_op.drop_column('is_published')

    with op.batch_alter_table('content_revisions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_content_revisions_content_id'))
        batch_op.drop_index(batch_op.f('ix_content_revisions_content_type'))
    op.drop_table('content_revisions')

    with op.batch_alter_table('content_resources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_content_resources_topic_id'))
    op.drop_table('content_resources')

    with op.batch_alter_table('assignment_submissions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assignment_submissions_user_id'))
        batch_op.drop_index(batch_op.f('ix_assignment_submissions_assignment_id'))
    op.drop_table('assignment_submissions')

    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assignments_is_published'))
        batch_op.drop_index(batch_op.f('ix_assignments_topic_id'))
    op.drop_table('assignments')
