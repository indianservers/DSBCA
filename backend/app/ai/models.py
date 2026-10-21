from datetime import datetime, date
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    JSON,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.models import Base, Record
from sqlalchemy.types import TypeDecorator
from app.core.config import settings


class VectorStorage(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and settings().ai_vector_backend == "pgvector":
            return dialect.type_descriptor(Vector(512))
        return dialect.type_descriptor(JSON())


class Organization(Record, Base):
    __tablename__ = "ai_organizations"
    name: Mapped[str] = mapped_column(String(180))


class OrganizationMember(Record, Base):
    __tablename__ = "ai_organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("ai_organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class Assistant(Record, Base):
    __tablename__ = "ai_assistants"
    name: Mapped[str] = mapped_column(String(100), unique=True)


class AssistantConfig(Record, Base):
    __tablename__ = "ai_assistant_config_versions"
    assistant_id: Mapped[str] = mapped_column(
        ForeignKey("ai_assistants.id"), index=True
    )
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    configuration: Mapped[dict] = mapped_column(JSON)


class KnowledgeDocument(Record, Base):
    __tablename__ = "knowledge_documents"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_organizations.id"), index=True
    )
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id"), index=True
    )
    scope: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(240))
    subject: Mapped[str] = mapped_column(String(80), index=True)
    issuer: Mapped[str] = mapped_column(String(180))
    jurisdiction: Mapped[str] = mapped_column(String(80), default="UAE")
    language: Mapped[str] = mapped_column(String(20), default="en")
    document_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    internal_notes: Mapped[str] = mapped_column(Text, default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class DocumentVersion(Record, Base):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version"),
        UniqueConstraint("document_id", "sha256"),
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(400), unique=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    source_metadata: Mapped[dict] = mapped_column(JSON)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True)
    applicable_periods: Mapped[str] = mapped_column(String(240), default="")
    processing_status: Mapped[str] = mapped_column(
        String(24), default="draft", index=True
    )
    approval_status: Mapped[str] = mapped_column(
        String(24), default="pending", index=True
    )
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(80))


class DocumentPage(Record, Base):
    __tablename__ = "knowledge_document_pages"
    __table_args__ = (UniqueConstraint("version_id", "physical_page"),)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id"), index=True
    )
    physical_page: Mapped[int] = mapped_column(Integer)
    printed_label: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    tables: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[str] = mapped_column(String(100), default="pdfplumber")
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    preview_key: Mapped[str] = mapped_column(String(400))


class KnowledgeChunk(Record, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("version_id", "ordinal"),)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    heading: Mapped[str] = mapped_column(String(400))
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer)
    structural_location: Mapped[str] = mapped_column(String(400))


class KnowledgeEmbedding(Record, Base):
    __tablename__ = "knowledge_embeddings"
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_chunks.id"), unique=True
    )
    model: Mapped[str] = mapped_column(String(100), index=True)
    vector: Mapped[list] = mapped_column(VectorStorage())


class ProcessingJob(Record, Base):
    __tablename__ = "knowledge_processing_jobs"
    version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint: Mapped[str] = mapped_column(String(24), default="intake")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    lease_token: Mapped[str | None] = mapped_column(String(80))
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)


class JobEvent(Record, Base):
    __tablename__ = "knowledge_processing_job_events"
    job_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_processing_jobs.id"), index=True
    )
    stage: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(400))


class Conversation(Record, Base):
    __tablename__ = "chat_conversations"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="New research")
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )


class ChatMessage(Record, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("conversation_id", "request_id", "role"),)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    subject: Mapped[str] = mapped_column(String(80))
    config_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_assistant_config_versions.id")
    )
    response_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class MessageEvidence(Record, Base):
    __tablename__ = "chat_message_evidence"
    __table_args__ = (UniqueConstraint("message_id", "chunk_id"),)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id"))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id")
    )
    snapshot: Mapped[dict] = mapped_column(JSON)


class AnswerFeedback(Record, Base):
    __tablename__ = "chat_answer_feedback"
    __table_args__ = (UniqueConstraint("user_id", "message_id"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE")
    )
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(1000), default="")


class UsageEvent(Record, Base):
    __tablename__ = "ai_usage_events"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    request_id: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(100), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(80), default="")
    estimated_cost: Mapped[float | None] = mapped_column(Float)
