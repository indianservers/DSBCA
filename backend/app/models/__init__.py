import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    String,
    ForeignKey,
    UniqueConstraint,
    JSON,
    Text,
    DateTime,
    Date,
    Integer,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="active")


class UserProfile(Record, Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(120))


class Role(Record, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(32), unique=True)


class UserRole(Record, Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))


class AuthSession(Record, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class PasswordResetToken(Record, Base):
    __tablename__ = "password_reset_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Company(Record, Base):
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    __tablename__ = "companies"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    trn: Mapped[str | None] = mapped_column(String(32))


class CompanyPerson(Record, Base):
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    __tablename__ = "company_people"
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32))


class CompanyDocument(Record, Base):
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    __tablename__ = "company_documents"
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    person_id: Mapped[str | None] = mapped_column(
        ForeignKey("company_people.id", ondelete="SET NULL")
    )
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(180))
    expires_on: Mapped[date] = mapped_column(Date, index=True)
    storage_key: Mapped[str | None] = mapped_column(String(400))


class CompanyReminder(Record, Base):
    __tablename__ = "company_reminders"
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("company_documents.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(180))
    due_on: Mapped[date] = mapped_column(Date, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class ReminderPreference(Record, Base):
    schedule: Mapped[list] = mapped_column(JSON, default=lambda: [30, 7, 0])
    channels: Mapped[list] = mapped_column(JSON, default=lambda: ["in_app"])
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __tablename__ = "reminder_preferences"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    days_before: Mapped[int] = mapped_column(Integer, default=30)


class SubjectCategory(Record, Base):
    __tablename__ = "subject_categories"
    name: Mapped[str] = mapped_column(String(100), unique=True)


class VideoCategory(Record, Base):
    __tablename__ = "video_categories"
    subject_id: Mapped[str] = mapped_column(ForeignKey("subject_categories.id"))
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Content:
    metadata_extra: Mapped[dict] = mapped_column(JSON, default=dict)
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("subject_categories.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Video(Record, Content, Base):
    __tablename__ = "videos"
    video_category_id: Mapped[str | None] = mapped_column(
        ForeignKey("video_categories.id")
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    media_url: Mapped[str | None] = mapped_column(Text)


class Publication(Record, Content, Base):
    __tablename__ = "publications"
    download_url: Mapped[str | None] = mapped_column(Text)


class PublicationChapter(Record, Base):
    asset_id: Mapped[str | None] = mapped_column(String(36))
    body: Mapped[str] = mapped_column(Text, default="")
    __tablename__ = "publication_chapters"
    __table_args__ = (UniqueConstraint("publication_id", "position"),)
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    position: Mapped[int] = mapped_column(Integer)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    download_url: Mapped[str | None] = mapped_column(Text)


class Article(Record, Content, Base):
    __tablename__ = "articles"
    reading_minutes: Mapped[int] = mapped_column(Integer, default=4)


class ArticleBookmark(Record, Base):
    __tablename__ = "article_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "article_id"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    article_id: Mapped[str] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE")
    )


class RegulatoryUpdate(Record, Content, Base):
    __tablename__ = "regulatory_updates"
    source_url: Mapped[str | None] = mapped_column(Text)


class Webinar(Record, Content, Base):
    __tablename__ = "webinars"
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    join_url: Mapped[str | None] = mapped_column(Text)


class Notification(Record, Base):
    __tablename__ = "notifications"
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    deep_link: Mapped[str] = mapped_column(String(240), default="/updates")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    demo: Mapped[bool] = mapped_column(Boolean, default=False)


class NotificationRecipient(Record, Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (UniqueConstraint("notification_id", "user_id"),)
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Record, Base):
    email: Mapped[bool] = mapped_column(Boolean, default=False)
    push: Mapped[bool] = mapped_column(Boolean, default=False)
    __tablename__ = "notification_preferences"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    categories: Mapped[list] = mapped_column(JSON, default=list)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)


class AppSetting(Record, Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict] = mapped_column(JSON)


class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(100))


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer, default=1)


class RegulatoryUpdateRead(Record, Base):
    __tablename__ = "regulatory_update_reads"
    __table_args__ = (UniqueConstraint("user_id", "update_id"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    update_id: Mapped[str] = mapped_column(
        ForeignKey("regulatory_updates.id", ondelete="CASCADE"), index=True
    )
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# Register Phase 2 metadata after Phase 1 base classes exist; no startup DDL.
from app.ai import models as ai_models  # noqa: E402,F401

from app.professional import models as professional_models  # noqa: E402,F401
