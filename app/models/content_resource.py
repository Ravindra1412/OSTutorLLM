"""
app/models/content_resource.py

`content_resources` table (Part 3.10, Section 7). Metadata for files
faculty upload against a Topic (PDF notes, slide decks, images).
Actual bytes live on disk under `Config.UPLOAD_FOLDER` — only the
validated, generated filename and metadata are stored here, per the
standard "never trust the client-supplied path" file-upload pattern
(see content_management.py's `save_resource_file` for the validation).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class ContentResource(TimestampMixin, db.Model):
    __tablename__ = "content_resources"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)  # sanitized, disk-safe, collision-free
    file_type = db.Column(db.String(10), nullable=False)  # extension, lowercase
    file_size_bytes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    topic = db.relationship("Topic")
    uploaded_by = db.relationship("User")

    def __repr__(self) -> str:
        return f"<ContentResource id={self.id} topic_id={self.topic_id} file={self.original_filename}>"
