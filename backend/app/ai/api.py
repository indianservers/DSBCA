import asyncio
import hashlib
import secrets
import uuid
from datetime import timedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import select, func
from pydantic import ValidationError
import jwt
from app.core.database import db_session
from app.core.config import settings
from app.core.security import current_user, administrator, roles, bearer, expired
from app.models import User, AuthSession, AuditLog, now
from app.ai import models as m
from app.ai import schemas as s
from app.ai.access import (
    accessible_document,
    document_access_clause,
    validate_scope,
    owned_conversation,
    owns_evidence,
)
from app.ai.configuration import current_config
from app.ai.storage import storage, S3PrivateStorage
from app.ai.ingestion import validate_pdf, add_job, claim_job, run_step
from app.ai.chat import reserve, answer_question, public_message, sse

router = APIRouter(tags=["Phase 2 research"])


def audit(db, user, action, id):
    db.add(AuditLog(actor_id=user.id, action="ai_" + action, resource_id=id))


def row_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def page_result(rows, total, page, size):
    return {"items": rows, "total": total, "page": page, "page_size": size}


def document_result(db, doc):
    versions = list(
        db.scalars(
            select(m.DocumentVersion)
            .where(m.DocumentVersion.document_id == doc.id)
            .order_by(m.DocumentVersion.created_at.desc())
        )
    )
    return {**row_dict(doc), "versions": [row_dict(v) for v in versions]}


def create_version(db, metadata, user, sha256, size, document=None):
    validate_scope(db, metadata, user)
    since = now().replace(hour=0, minute=0, second=0, microsecond=0)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    uploads = db.scalar(
        select(func.count())
        .select_from(m.DocumentVersion)
        .join(m.KnowledgeDocument)
        .where(
            m.KnowledgeDocument.owner_id == user.id,
            m.DocumentVersion.created_at >= since,
        )
    )
    if uploads >= settings().pdf_daily_uploads:
        raise HTTPException(429, "Daily PDF processing quota reached")
    if size > settings().pdf_max_bytes:
        raise HTTPException(413, "PDF exceeds configured size limit")
    if document is None:
        duplicate = db.scalar(
            select(m.DocumentVersion.id)
            .join(m.KnowledgeDocument)
            .where(
                m.DocumentVersion.sha256 == sha256,
                m.KnowledgeDocument.owner_id == user.id,
            )
        )
        if duplicate:
            raise HTTPException(409, "This PDF is already registered for this account")
        fields = metadata.model_dump(
            exclude={
                "version",
                "publication_date",
                "effective_from",
                "effective_to",
                "applicable_periods",
            }
        )
        document = m.KnowledgeDocument(owner_id=user.id, **fields)
        db.add(document)
        db.flush()
    else:
        if document.archived:
            raise HTTPException(409, "Archived documents cannot be replaced")
        if (
            document.scope != metadata.scope
            or document.organization_id != metadata.organization_id
            or document.company_id != metadata.company_id
        ):
            raise HTTPException(
                422, "Replacement must retain the document access scope"
            )
    vid = str(uuid.uuid4())
    version = m.DocumentVersion(
        id=vid,
        document_id=document.id,
        version=metadata.version,
        sha256=sha256,
        byte_size=size,
        storage_key=f"originals/{vid}/{sha256}.pdf",
        source_metadata=metadata.model_dump(mode="json"),
        publication_date=metadata.publication_date,
        effective_from=metadata.effective_from,
        effective_to=metadata.effective_to,
        applicable_periods=metadata.applicable_periods,
    )
    db.add(version)
    db.flush()
    audit(db, user, "upload_version", version.id)
    return document, version


def parse_metadata(raw):
    try:
        return s.DocumentInput.model_validate_json(raw)
    except (ValidationError, ValueError):
        raise HTTPException(
            422, "Invalid document metadata. Check subject, scope, type and date range."
        )


@router.get("/ai/capabilities")
def capabilities(user=Depends(current_user)):
    cfg = settings()
    return {
        "mode": "approved_pdfs",
        "openai_configured": bool(cfg.openai_api_key),
        "storage_configured": cfg.pdf_storage_backend != "disabled",
        "official_verification_enabled": False,
        "embedding_dimensions": 512,
        "vector_backend": cfg.ai_vector_backend,
        "streaming_policy": "status events followed by validated answer deltas; no unvalidated claims streamed",
    }


@router.get("/admin/ai/documents")
def documents(
    q: str = Query("", max_length=120),
    subject: str | None = None,
    status: str | None = None,
    approval: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(administrator),
    db=Depends(db_session),
):
    query = select(m.KnowledgeDocument).where(document_access_clause(user.id))
    if q:
        query = query.where(m.KnowledgeDocument.title.ilike("%" + q + "%"))
    if subject:
        query = query.where(m.KnowledgeDocument.subject == subject)
    if status or approval:
        versions = select(m.DocumentVersion.document_id)
        if status:
            versions = versions.where(m.DocumentVersion.processing_status == status)
        if approval:
            versions = versions.where(m.DocumentVersion.approval_status == approval)
        query = query.where(m.KnowledgeDocument.id.in_(versions))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = list(
        db.scalars(
            query.order_by(m.KnowledgeDocument.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return page_result([document_result(db, d) for d in rows], total, page, page_size)


@router.get("/admin/ai/organizations")
def organizations(user=Depends(administrator), db=Depends(db_session)):
    rows = list(
        db.scalars(
            select(m.Organization)
            .join(m.OrganizationMember)
            .where(m.OrganizationMember.user_id == user.id)
        )
    )
    return page_result([{"id": r.id, "name": r.name} for r in rows], len(rows), 1, 100)


@router.post("/admin/ai/documents", status_code=201)
async def upload_document(
    metadata: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(administrator),
    db=Depends(db_session),
):
    parsed = parse_metadata(metadata)
    if file.content_type != "application/pdf" or not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are accepted")
    data = await file.read(3000001)
    await file.close()
    if len(data) > 3000000:
        raise HTTPException(
            413, "Use authorized direct upload for PDFs larger than 3 MB"
        )
    try:
        validate_pdf(data)
    except Exception:
        raise HTTPException(422, "Invalid, encrypted, active or oversized PDF")
    store = storage()
    doc, version = create_version(
        db, parsed, user, hashlib.sha256(data).hexdigest(), len(data)
    )
    store.put(version.storage_key, data, "application/pdf")
    job = add_job(db, version)
    return {
        "document_id": doc.id,
        "version_id": version.id,
        "job_id": job.id,
        "sha256": version.sha256,
        "status": job.status,
    }


@router.post("/admin/ai/uploads", status_code=201)
def direct_upload(
    data: s.DirectUpload,
    document_id: str | None = None,
    user=Depends(administrator),
    db=Depends(db_session),
):
    store = storage()
    if not isinstance(store, S3PrivateStorage):
        raise HTTPException(503, "Direct uploads require private S3-compatible storage")
    doc, version = create_version(
        db,
        data.metadata,
        user,
        data.sha256,
        data.byte_size,
        accessible_document(db, document_id, user) if document_id else None,
    )
    return {
        "document_id": doc.id,
        "version_id": version.id,
        "upload": store.presign_upload(
            version.storage_key.replace("originals/", "intake/", 1),
            data.byte_size,
            data.sha256,
        ),
    }


@router.post("/admin/ai/uploads/{version_id}/complete")
def complete_upload(
    version_id: str, user=Depends(administrator), db=Depends(db_session)
):
    version = db.get(m.DocumentVersion, version_id)
    if not version:
        raise HTTPException(404)
    accessible_document(db, version.document_id, user)
    # Hash/type verification is performed by the durable worker, not trusted from client metadata.
    job = add_job(db, version)
    return {"job_id": job.id, "status": job.status}


@router.get("/admin/ai/documents/{id}")
def document_detail(id: str, user=Depends(administrator), db=Depends(db_session)):
    return document_result(db, accessible_document(db, id, user))


@router.patch("/admin/ai/documents/{id}")
def document_edit(
    id: str, data: s.DocumentInput, user=Depends(administrator), db=Depends(db_session)
):
    doc = accessible_document(db, id, user)
    approved = db.scalar(
        select(m.DocumentVersion.id).where(
            m.DocumentVersion.document_id == id,
            m.DocumentVersion.approval_status == "approved",
        )
    )
    if approved:
        raise HTTPException(
            409,
            "Approved metadata is immutable. Upload a new version to change source metadata.",
        )
    validate_scope(db, data, user)
    versions = list(
        db.scalars(select(m.DocumentVersion).where(m.DocumentVersion.document_id == id))
    )
    if any(v.processing_status == "processing" for v in versions):
        raise HTTPException(409, "Wait for current processing before editing metadata")
    values = data.model_dump()
    for key in [
        "title",
        "subject",
        "issuer",
        "jurisdiction",
        "language",
        "document_type",
        "description",
        "keywords",
        "internal_notes",
    ]:
        setattr(doc, key, values[key])
    # Access scope never changes in-place; it is part of the source security boundary.
    if (data.scope, data.organization_id, data.company_id) != (
        doc.scope,
        doc.organization_id,
        doc.company_id,
    ):
        raise HTTPException(422, "Access scope cannot be changed in place")
    for version in versions:
        pinned = (version.source_metadata or {}).get("_embedding_model")
        version.source_metadata = {
            **data.model_dump(mode="json"),
            **({"_embedding_model": pinned} if pinned else {}),
        }
        version.effective_from, version.effective_to = (
            data.effective_from,
            data.effective_to,
        )
        version.publication_date, version.applicable_periods = (
            data.publication_date,
            data.applicable_periods,
        )
    audit(db, user, "edit_metadata", id)
    return document_result(db, doc)


@router.post("/admin/ai/documents/{id}/replace", status_code=201)
async def replace(
    id: str,
    metadata: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(administrator),
    db=Depends(db_session),
):
    doc = accessible_document(db, id, user)
    parsed = parse_metadata(metadata)
    if file.content_type != "application/pdf" or not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(415)
    data = await file.read(3000001)
    await file.close()
    if len(data) > 3000000:
        raise HTTPException(413, "Use direct version upload for large replacements")
    try:
        validate_pdf(data)
    except Exception:
        raise HTTPException(422, "Invalid PDF")
    _, version = create_version(
        db, parsed, user, hashlib.sha256(data).hexdigest(), len(data), doc
    )
    storage().put(version.storage_key, data, "application/pdf")
    return {
        "document_id": doc.id,
        "version_id": version.id,
        "job_id": add_job(db, version).id,
    }


@router.post("/admin/ai/documents/{id}/{action}")
def document_action(
    id: str,
    action: str,
    version_id: str | None = None,
    user=Depends(administrator),
    db=Depends(db_session),
):
    doc = accessible_document(db, id, user)
    if action == "archive":
        doc.archived = True
        audit(db, user, action, id)
        return {"archived": True}
    version = db.scalar(
        select(m.DocumentVersion)
        .where(
            m.DocumentVersion.document_id == id,
            *([m.DocumentVersion.id == version_id] if version_id else []),
        )
        .order_by(m.DocumentVersion.created_at.desc())
        .with_for_update()
        .limit(1)
    )
    if not version:
        raise HTTPException(404)
    if action == "approve":
        if doc.archived or version.processing_status != "ready":
            raise HTTPException(
                409, "Only completely processed, non-archived sources can be approved"
            )
        version.approval_status, version.approved_by, version.approved_at = (
            "approved",
            user.id,
            now(),
        )
    elif action == "reject":
        version.approval_status = "rejected"
    elif action == "supersede":
        if version.processing_status != "ready":
            raise HTTPException(409)
        version.processing_status = "superseded"
    elif action == "retry":
        job = db.scalar(
            select(m.ProcessingJob)
            .where(m.ProcessingJob.version_id == version.id)
            .with_for_update()
        )
        if (
            not job
            or job.status != "failed"
            or job.attempts >= settings().indexing_max_attempts
        ):
            raise HTTPException(
                409, "Job cannot be retried; inspect attempts and processing log"
            )
        job.status, job.error_code = "queued", None
        version.processing_status, version.failure_code = "draft", None
        db.add(
            m.JobEvent(
                job_id=job.id,
                stage=job.checkpoint,
                message="Administrator requested retry from saved checkpoint",
            )
        )
    else:
        raise HTTPException(404)
    audit(db, user, action, version.id)
    return row_dict(version)


@router.get("/admin/ai/processing-jobs")
def jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(administrator),
    db=Depends(db_session),
):
    query = (
        select(m.ProcessingJob)
        .join(m.DocumentVersion)
        .join(m.KnowledgeDocument)
        .where(document_access_clause(user.id))
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = list(
        db.scalars(
            query.order_by(m.ProcessingJob.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return page_result(
        [
            {
                **{k: v for k, v in row_dict(job).items() if k != "lease_token"},
                "events": [
                    row_dict(e)
                    for e in db.scalars(
                        select(m.JobEvent)
                        .where(m.JobEvent.job_id == job.id)
                        .order_by(m.JobEvent.created_at.desc())
                        .limit(20)
                    )
                ],
            }
            for job in rows
        ],
        total,
        page,
        page_size,
    )


@router.get("/admin/ai/settings")
def get_settings(user=Depends(administrator), db=Depends(db_session)):
    id, config = current_config(db)
    return {
        "version_id": id,
        "configuration": config,
        "providers": {
            "openai_configured": bool(settings().openai_api_key),
            "storage_backend": settings().pdf_storage_backend,
            "official_verification_enabled": False,
        },
        "history": [
            {"id": r.id, "created_at": r.created_at}
            for r in db.scalars(
                select(m.AssistantConfig)
                .order_by(m.AssistantConfig.created_at.desc())
                .limit(20)
            )
        ],
    }


@router.patch("/admin/ai/settings")
def save_settings(
    data: s.ConfigInput, user=Depends(administrator), db=Depends(db_session)
):
    if "super_admin" not in roles(db, user.id):
        raise HTTPException(403, "Super administrator required for AI configuration")
    if data.rerank_enabled:
        raise HTTPException(422, "No optional reranker adapter is configured")
    assistant = db.scalar(select(m.Assistant).where(m.Assistant.name == "DSBCA"))
    if not assistant:
        assistant = m.Assistant(name="DSBCA")
        db.add(assistant)
        db.flush()
    row = m.AssistantConfig(
        assistant_id=assistant.id, author_id=user.id, configuration=data.model_dump()
    )
    db.add(row)
    db.flush()
    audit(db, user, "configuration_version", row.id)
    return {"version_id": row.id, "configuration": row.configuration}


@router.get("/admin/ai/analytics")
def analytics(user=Depends(administrator), db=Depends(db_session)):
    # Aggregates only. No prompts, client source text, identity or conversation logs.
    counts = {
        "conversations": db.scalar(
            select(func.count())
            .select_from(m.Conversation)
            .where(m.Conversation.deleted_at.is_(None))
        ),
        "questions": db.scalar(
            select(func.count())
            .select_from(m.UsageEvent)
            .where(m.UsageEvent.kind == "chat")
        ),
        "indexing_failures": db.scalar(
            select(func.count())
            .select_from(m.ProcessingJob)
            .where(m.ProcessingJob.status == "failed")
        ),
        "indexed_versions": db.scalar(
            select(func.count())
            .select_from(m.DocumentVersion)
            .where(m.DocumentVersion.processing_status == "ready")
        ),
        "total_versions": db.scalar(
            select(func.count()).select_from(m.DocumentVersion)
        ),
        "feedback_positive": db.scalar(
            select(func.count())
            .select_from(m.AnswerFeedback)
            .where(m.AnswerFeedback.rating == 1)
        ),
        "feedback_negative": db.scalar(
            select(func.count())
            .select_from(m.AnswerFeedback)
            .where(m.AnswerFeedback.rating == -1)
        ),
    }
    for outcome in [
        "insufficient_evidence",
        "citation_validation_failed",
        "provider_unavailable",
    ]:
        counts[outcome] = db.scalar(
            select(func.count())
            .select_from(m.UsageEvent)
            .where(m.UsageEvent.outcome == outcome)
        )
    counts["input_tokens"] = db.scalar(
        select(func.coalesce(func.sum(m.UsageEvent.input_tokens), 0))
    )
    counts["output_tokens"] = db.scalar(
        select(func.coalesce(func.sum(m.UsageEvent.output_tokens), 0))
    )
    counts["average_latency_ms"] = db.scalar(
        select(func.avg(m.UsageEvent.latency_ms)).where(m.UsageEvent.kind == "chat")
    )
    counts["estimated_cost"] = db.scalar(select(func.sum(m.UsageEvent.estimated_cost)))
    counts["cost_note"] = (
        "Only configured pricing and recorded usage; null means unavailable, not zero cost."
    )
    counts["questions_per_subject"] = dict(
        db.execute(
            select(m.UsageEvent.subject, func.count())
            .where(m.UsageEvent.kind == "chat")
            .group_by(m.UsageEvent.subject)
        ).all()
    )
    return counts


@router.get("/ai/conversations")
def conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(current_user),
    db=Depends(db_session),
):
    query = select(m.Conversation).where(
        m.Conversation.owner_id == user.id, m.Conversation.deleted_at.is_(None)
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(m.Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return page_result(
        [
            {
                **row_dict(r),
                "message_count": db.scalar(
                    select(func.count())
                    .select_from(m.ChatMessage)
                    .where(m.ChatMessage.conversation_id == r.id)
                ),
            }
            for r in rows
        ],
        total,
        page,
        page_size,
    )


@router.post("/ai/conversations", status_code=201)
def new_conversation(
    data: s.ConversationInput, user=Depends(current_user), db=Depends(db_session)
):
    row = m.Conversation(owner_id=user.id, title=data.title)
    db.add(row)
    db.flush()
    return row_dict(row)


@router.get("/ai/conversations/{id}")
def get_conversation(id: str, user=Depends(current_user), db=Depends(db_session)):
    return row_dict(owned_conversation(db, id, user))


@router.delete("/ai/conversations/{id}", status_code=204)
def delete_conversation(id: str, user=Depends(current_user), db=Depends(db_session)):
    row = owned_conversation(db, id, user)
    row.deleted_at = now()
    # Messages/evidence are hidden immediately, retained until the configured purge job.


@router.get("/ai/conversations/{id}/messages")
def messages(
    id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user=Depends(current_user),
    db=Depends(db_session),
):
    owned_conversation(db, id, user)
    query = select(m.ChatMessage).where(m.ChatMessage.conversation_id == id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = list(
        db.scalars(
            query.order_by(m.ChatMessage.created_at.desc(), m.ChatMessage.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    rows.reverse()
    return page_result(
        [public_message(db, r, user) for r in rows], total, page, page_size
    )


@router.post("/ai/chat")
async def chat(data: s.ChatInput, user=Depends(current_user), db=Depends(db_session)):
    message, event, config = reserve(db, user, data)
    if event is None:
        return public_message(db, message, user)
    return await answer_question(db, user, data, message, event, config)


@router.post("/ai/chat/stream")
async def stream_chat(
    data: s.ChatInput,
    request: Request,
    user=Depends(current_user),
    db=Depends(db_session),
):
    message, event, config = reserve(db, user, data)

    async def events():
        yield sse("accepted", {"message_id": message.id, "request_id": data.request_id})
        if event is None:
            yield sse("done", public_message(db, message, user))
            return
        yield sse("status", {"stage": "retrieving_approved_evidence"})
        task = asyncio.create_task(
            answer_question(db, user, data, message, event, config)
        )
        try:
            while not task.done():
                done, _ = await asyncio.wait({task}, timeout=8)
                if await request.is_disconnected():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    return
                if not done:
                    yield ": keepalive\n\n"
            result = await task
            yield sse("citations", {"citations": result["citations"]})
            for index in range(0, len(result["text"]), 96):
                yield sse(
                    "answer_delta",
                    {"text": result["text"][index : index + 96], "validated": True},
                )
                await asyncio.sleep(0)
            yield sse("done", result)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/ai/messages/{id}/cancel")
def cancel(id: str, user=Depends(current_user), db=Depends(db_session)):
    message = db.get(m.ChatMessage, id)
    if not message:
        raise HTTPException(404)
    owned_conversation(db, message.conversation_id, user)
    if message.status in ("pending", "running"):
        message.status = "cancelled"
    return {"status": message.status}


@router.post("/ai/feedback")
def feedback(data: s.FeedbackInput, user=Depends(current_user), db=Depends(db_session)):
    message = db.get(m.ChatMessage, data.message_id)
    if not message:
        raise HTTPException(404)
    owned_conversation(db, message.conversation_id, user)
    if message.role != "assistant":
        raise HTTPException(422)
    config = message.response_metadata.get("config_snapshot", {})
    if not config.get("feedback_enabled", True):
        raise HTTPException(409, "Feedback disabled for this answer configuration")
    row = db.scalar(
        select(m.AnswerFeedback).where(
            m.AnswerFeedback.user_id == user.id,
            m.AnswerFeedback.message_id == message.id,
        )
    )
    if not row:
        row = m.AnswerFeedback(user_id=user.id, **data.model_dump())
        db.add(row)
    else:
        row.rating, row.comment = data.rating, data.comment
    return {"saved": True}


def source_access(db, version, user, chunk_id=None):
    doc = accessible_document(db, version.document_id, user)
    normal = (
        version.approval_status == "approved"
        and version.processing_status == "ready"
        and not doc.archived
    )
    historical = (
        owns_evidence(db, user.id, chunk_id)
        if chunk_id
        else db.scalar(
            select(m.MessageEvidence.id)
            .join(m.ChatMessage)
            .join(m.Conversation)
            .where(
                m.MessageEvidence.version_id == version.id,
                m.Conversation.owner_id == user.id,
                m.Conversation.deleted_at.is_(None),
            )
        )
        is not None
    )
    admin = bool(set(roles(db, user.id)) & {"admin", "super_admin"})
    if not (normal or historical or admin):
        raise HTTPException(404, "Source is not accessible")
    return doc


@router.get("/ai/sources/{source_id}")
def source(source_id: str, user=Depends(current_user), db=Depends(db_session)):
    from app.ai.retrieval import evidence_card

    chunk = db.get(m.KnowledgeChunk, source_id)
    if not chunk:
        raise HTTPException(404)
    version = db.get(m.DocumentVersion, chunk.version_id)
    doc = source_access(db, version, user, chunk.id)
    return evidence_card(db, chunk, version, doc, 0)


@router.get("/ai/documents/{version_id}/pages/{page}")
def document_page(
    version_id: str, page: int, user=Depends(current_user), db=Depends(db_session)
):
    version = db.get(m.DocumentVersion, version_id)
    if not version:
        raise HTTPException(404)
    source_access(db, version, user)
    row = db.scalar(
        select(m.DocumentPage).where(
            m.DocumentPage.version_id == version_id,
            m.DocumentPage.physical_page == page,
        )
    )
    if not row:
        raise HTTPException(404)
    return {
        "physical_page": page,
        "printed_label": row.printed_label,
        "text": row.text,
        "tables": row.tables,
        "provenance": row.provenance,
        "uncertain": row.uncertain,
        "page_count": version.page_count,
        "preview_path": f"/ai/documents/{version_id}/pages/{page}/preview",
    }


@router.get("/ai/documents/{version_id}/pages/{page}/preview")
def page_preview(
    version_id: str, page: int, user=Depends(current_user), db=Depends(db_session)
):
    document_page(version_id, page, user, db)
    row = db.scalar(
        select(m.DocumentPage).where(
            m.DocumentPage.version_id == version_id,
            m.DocumentPage.physical_page == page,
        )
    )
    return Response(
        storage().get(row.preview_key, 4000000),
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/ai/documents/{version_id}/download")
def download(
    version_id: str,
    token=Depends(bearer),
    user=Depends(current_user),
    db=Depends(db_session),
):
    version = db.get(m.DocumentVersion, version_id)
    if not version:
        raise HTTPException(404)
    source_access(db, version, user)
    store = storage()
    if isinstance(store, S3PrivateStorage):
        return {"url": store.download_url(version.storage_key), "expires_in": 60}
    payload = jwt.decode(
        token.credentials, settings().jwt_secret_key, algorithms=["HS256"]
    )
    ticket = jwt.encode(
        {
            "type": "pdf_ticket",
            "sub": user.id,
            "sid": payload["sid"],
            "version_id": version_id,
            "exp": now() + timedelta(seconds=60),
        },
        settings().jwt_secret_key,
        algorithm="HS256",
    )
    return {"path": f"/ai/files/{version_id}?ticket={ticket}", "expires_in": 60}


@router.get("/ai/files/{version_id}")
def private_file(
    version_id: str, request: Request, ticket: str, db=Depends(db_session)
):
    # Parsed ticket remains local; redact the URL query before the ASGI access log sees the response.
    request.scope["query_string"] = b""
    try:
        payload = jwt.decode(
            ticket,
            settings().jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sid", "sub", "type", "version_id"]},
        )
        session = db.get(AuthSession, payload["sid"])
        user = db.get(User, payload["sub"])
        if (
            payload["type"] != "pdf_ticket"
            or payload["version_id"] != version_id
            or not session
            or session.revoked
            or expired(session.expires_at)
            or session.user_id != user.id
            or user.status != "active"
        ):
            raise ValueError()
    except Exception:
        raise HTTPException(401, "PDF access ticket is invalid or expired")
    version = db.get(m.DocumentVersion, version_id)
    if not version:
        raise HTTPException(404)
    source_access(db, version, user)
    data = storage().get(version.storage_key, settings().pdf_max_bytes)
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": 'inline; filename="source.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/internal/ai/jobs/tick")
async def job_tick(request: Request, db=Depends(db_session)):
    secrets_configured = [
        value
        for value in [settings().indexing_worker_secret, settings().cron_secret]
        if value
    ]
    if not any(
        secrets.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + value
        )
        for value in secrets_configured
    ):
        raise HTTPException(401, "Worker authorization required")
    claimed = claim_job(db)
    return await run_step(db, *claimed) if claimed else {"status": "idle"}
