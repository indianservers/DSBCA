"""Phase 3 tables reuse existing content, company, document and notification records."""

from datetime import date, datetime
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base, Record


class RuleVersion(Record, Base):
    __tablename__ = "professional_rule_versions"
    __table_args__ = (UniqueConstraint("code", "version"),)
    code: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(30), default="calculator")
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    validation_cases: Mapped[list] = mapped_column(JSON, default=list)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class CalculatorRun(Record, Base):
    __tablename__ = "calculator_runs"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    calculator: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    inputs: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    rule_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class ContentBookmark(Record, Base):
    __tablename__ = "content_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "kind", "resource_id"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[str] = mapped_column(String(36))


class LearningProgress(Record, Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("user_id", "kind", "resource_id"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[str] = mapped_column(String(36))
    position: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class LearningPath(Record, Base):
    __tablename__ = "learning_paths"
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="draft")


class LearningPathItem(Record, Base):
    __tablename__ = "learning_path_items"
    __table_args__ = (UniqueConstraint("path_id", "position"),)
    path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    resource_id: Mapped[str] = mapped_column(String(36))
    position: Mapped[int] = mapped_column(Integer)


class LearningEnrollment(Record, Base):
    __tablename__ = "learning_enrollments"
    __table_args__ = (UniqueConstraint("path_id", "user_id"),)
    path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class ComplianceObligation(Record, Base):
    __tablename__ = "company_compliance_obligations"
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="awaiting_confirmation")
    origin: Mapped[str] = mapped_column(String(30), default="manual")
    rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("professional_rule_versions.id")
    )
    basis: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComplianceHistory(Record, Base):
    __tablename__ = "company_compliance_status_history"
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(40))
    snapshot: Mapped[dict] = mapped_column(JSON)


class NotificationJob(Record, Base):
    __tablename__ = "notification_jobs"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    source_kind: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(36), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))


class NotificationDelivery(Record, Base):
    __tablename__ = "notification_deliveries"
    job_id: Mapped[str] = mapped_column(
        ForeignKey("notification_jobs.id", ondelete="CASCADE"), index=True
    )
    attempt: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(30))
    provider_id: Mapped[str | None] = mapped_column(String(200))


class DeviceToken(Record, Base):
    __tablename__ = "notification_device_tokens"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UpdateSubscription(Record, Base):
    __tablename__ = "regulatory_update_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "subject"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(100))


class UpdateVersion(Record, Base):
    __tablename__ = "regulatory_update_versions"
    update_id: Mapped[str] = mapped_column(
        ForeignKey("regulatory_updates.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    snapshot: Mapped[dict] = mapped_column(JSON)


class WebinarRegistration(Record, Base):
    __tablename__ = "webinar_registrations"
    __table_args__ = (UniqueConstraint("webinar_id", "user_id"),)
    webinar_id: Mapped[str] = mapped_column(
        ForeignKey("webinars.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="registered")
    attended: Mapped[bool] = mapped_column(Boolean, default=False)


class MediaAsset(Record, Base):
    __tablename__ = "professional_media_assets"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(400), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))


class AIToolLog(Record, Base):
    __tablename__ = "ai_tool_execution_logs"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    tool: Mapped[str] = mapped_column(String(80))
    request_id: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(30))
    result_reference: Mapped[str | None] = mapped_column(String(180))
