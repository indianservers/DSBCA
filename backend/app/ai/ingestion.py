import hashlib
import io
import math
import re
import secrets
import uuid
from datetime import timedelta
from sqlalchemy import select, func, or_, and_
from fastapi import HTTPException
from app.models import now
from app.ai.models import (
    DocumentVersion,
    DocumentPage,
    KnowledgeChunk,
    KnowledgeEmbedding,
    ProcessingJob,
    JobEvent,
    UsageEvent,
)
from app.ai.storage import storage
from app.ai.providers import embedding_provider
from app.ai.configuration import current_config
from app.core.config import settings


def validate_pdf(data):
    from pypdf import PdfReader

    cfg = settings()
    if len(data) > cfg.pdf_max_bytes or not data.startswith(b"%PDF-"):
        raise ValueError("INVALID_PDF_OR_SIZE")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("ENCRYPTED_PDF")
    if not 0 < len(reader.pages) <= cfg.pdf_max_pages:
        raise ValueError("PDF_PAGE_LIMIT")
    for page in reader.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if not all(math.isfinite(v) and 1 <= v <= 20000 for v in [width, height]):
            raise ValueError("PDF_PAGE_GEOMETRY_LIMIT")
    # Reject actions/attachments at every object level, including page annotations.
    # Inspect dictionaries only: never execute or decode embedded active content.
    from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject

    pending, seen = [reader.trailer["/Root"]], set()
    while pending:
        item = pending.pop()
        if isinstance(item, IndirectObject):
            item = item.get_object()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if len(seen) > 50000:
            raise ValueError("PDF_OBJECT_LIMIT")
        if isinstance(item, DictionaryObject):
            if any(
                key in item
                for key in [
                    "/OpenAction",
                    "/AA",
                    "/JS",
                    "/JavaScript",
                    "/EmbeddedFiles",
                    "/AF",
                ]
            ) or item.get("/S") in [
                "/JavaScript",
                "/Launch",
                "/SubmitForm",
                "/ImportData",
                "/GoToR",
            ]:
                raise ValueError("ACTIVE_PDF_REJECTED")
            pending.extend(item.values())
        elif isinstance(item, (ArrayObject, list)):
            pending.extend(item)
    return reader


def add_job(db, version):
    row = db.scalar(select(ProcessingJob).where(ProcessingJob.version_id == version.id))
    if row:
        return row
    row = ProcessingJob(version_id=version.id, idempotency_key="index:" + version.id)
    db.add(row)
    db.flush()
    db.add(
        JobEvent(
            job_id=row.id,
            stage="intake",
            message="Original private object registered; awaiting worker",
        )
    )
    return row


def claim_job(db):
    cfg = settings()
    if db.bind.dialect.name == "postgresql":
        db.execute(
            __import__("sqlalchemy").text("SELECT pg_advisory_xact_lock(749301)")
        )
    active = db.scalar(
        select(func.count())
        .select_from(ProcessingJob)
        .where(ProcessingJob.status == "running", ProcessingJob.lease_until > now())
    )
    if active >= cfg.indexing_max_concurrency:
        db.rollback()
        return None
    row = db.scalar(
        select(ProcessingJob)
        .where(
            or_(
                ProcessingJob.status == "queued",
                and_(
                    ProcessingJob.status == "running", ProcessingJob.lease_until < now()
                ),
            )
        )
        .order_by(ProcessingJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not row:
        db.rollback()
        return None
    if row.attempts >= cfg.indexing_max_attempts:
        row.status, row.error_code = "failed", "RETRY_LIMIT"
        row.lease_until, row.lease_token = None, None
        version = db.get(DocumentVersion, row.version_id)
        version.processing_status, version.failure_code = "failed", "RETRY_LIMIT"
        db.add(JobEvent(job_id=row.id, stage=row.checkpoint, message="RETRY_LIMIT"))
        db.commit()
        return None
    if row.status == "running":
        row.attempts += 1
    row.status, row.lease_token = "running", secrets.token_hex(24)
    row.lease_until = now() + timedelta(seconds=cfg.indexing_lease_seconds)
    db.get(DocumentVersion, row.version_id).processing_status = "processing"
    db.commit()
    return row.id, row.lease_token


def chunk_pages(pages):
    groups, current = [], []
    heading = "Document introduction"
    for page in pages:
        for line in page.text.splitlines():
            line = line.strip()
            if not line:
                continue
            boundary = re.match(
                r"^(Article\s+\d+|Section\s+\d+|\d+\.\s+[A-Z]|[A-Z][A-Z /-]{8,})", line
            )
            if boundary and current:
                groups.append((heading, current))
                current = []
            if boundary:
                heading = line[:400]
            current.append((page.physical_page, line))
    if current:
        groups.append((heading, current))
    chunks = []
    for title, lines in groups:
        text = "\n".join(line for _, line in lines)
        if len(text) > 12000:
            raise ValueError("OVERSIZED_SECTION_REQUIRES_REVIEW")
        if len(text.strip()) >= 30:
            chunks.append(
                {
                    "text": text,
                    "heading": title,
                    "page_start": min(p for p, _ in lines),
                    "page_end": max(p for p, _ in lines),
                    "token_count": math.ceil(len(text) / 3),
                    "structural_location": title,
                }
            )
    if not chunks:
        raise ValueError("NO_RELIABLE_CHUNKS")
    return chunks


def extract_page(data, index):
    import pdfplumber
    import pypdfium2 as pdfium

    reader = validate_pdf(data)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page = pdf.pages[index]
        text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
        tables = page.extract_tables() or []
    if len(re.sub(r"\s", "", text)) < 35:
        raise ValueError("OCR_REQUIRED_PAGE_" + str(index + 1))
    # Preserve tables as structured cells alongside the original page text.
    raster = pdfium.PdfDocument(data)
    rendered = raster[index]
    image = rendered.render(
        scale=min(
            1.4,
            1100 / max(rendered.get_width(), 1),
            1600 / max(rendered.get_height(), 1),
        )
    ).to_pil()
    out = io.BytesIO()
    image.save(out, format="PNG")
    image.close()
    rendered.close()
    raster.close()
    return (
        text,
        tables,
        str(reader.page_labels[index]),
        out.getvalue(),
        len(reader.pages),
    )


async def run_step(db, job_id, lease, embedder=None, store=None):
    job = db.get(ProcessingJob, job_id)
    if not job or job.status != "running" or job.lease_token != lease:
        raise ValueError("STALE_LEASE")
    version = db.get(DocumentVersion, job.version_id)
    try:
        store = store or storage()
        if job.checkpoint in ("intake", "pages"):
            try:
                data = store.get(version.storage_key, settings().pdf_max_bytes)
            except Exception:
                data = store.get(
                    version.storage_key.replace("originals/", "intake/", 1),
                    settings().pdf_max_bytes,
                )
                if hashlib.sha256(data).hexdigest() != version.sha256:
                    raise ValueError("CONTENT_HASH_MISMATCH")
                store.put(version.storage_key, data, "application/pdf")
            if (
                hashlib.sha256(data).hexdigest() != version.sha256
                or len(data) != version.byte_size
            ):
                raise ValueError("CONTENT_HASH_MISMATCH")
            reader = validate_pdf(data)
            version.page_count = len(reader.pages)
            count = db.scalar(
                select(func.count())
                .select_from(DocumentPage)
                .where(DocumentPage.version_id == version.id)
            )
            if count < version.page_count:
                text, tables, label, preview, total = extract_page(data, count)
                key = f"previews/{version.id}/{count + 1}.png"
                try:
                    store.put(key, preview, "image/png")
                except Exception:
                    if store.get(key, 4000000) != preview:
                        raise ValueError("PREVIEW_STORAGE_FAILED")
                db.add(
                    DocumentPage(
                        version_id=version.id,
                        physical_page=count + 1,
                        printed_label=label,
                        text=text,
                        tables=tables,
                        preview_key=key,
                        provenance="pdfplumber+pdfium; no OCR",
                        uncertain=False,
                    )
                )
                job.progress = int((count + 1) / total * 55)
            job.checkpoint = "chunks" if count + 1 >= version.page_count else "pages"
        elif job.checkpoint == "chunks":
            pages = list(
                db.scalars(
                    select(DocumentPage)
                    .where(DocumentPage.version_id == version.id)
                    .order_by(DocumentPage.physical_page)
                )
            )
            existing = db.scalar(
                select(func.count())
                .select_from(KnowledgeChunk)
                .where(KnowledgeChunk.version_id == version.id)
            )
            if not existing:
                for i, values in enumerate(chunk_pages(pages)):
                    stable_id = str(
                        uuid.uuid5(uuid.NAMESPACE_URL, version.id + ":" + str(i))
                    )
                    db.add(
                        KnowledgeChunk(
                            id=stable_id, version_id=version.id, ordinal=i, **values
                        )
                    )
            job.checkpoint, job.progress = "embeddings", 60
        elif job.checkpoint == "embeddings":
            _, config = current_config(db)
            metadata = dict(version.source_metadata or {})
            pinned = metadata.get("_embedding_model")
            embedder = embedder or embedding_provider(
                pinned or config["embedding_model"]
            )
            if pinned and pinned != embedder.model:
                raise ValueError("EMBEDDING_MODEL_CHANGED_REPLACE_VERSION")
            metadata["_embedding_model"] = embedder.model
            version.source_metadata = metadata
            done = select(KnowledgeEmbedding.chunk_id)
            chunks = list(
                db.scalars(
                    select(KnowledgeChunk)
                    .where(
                        KnowledgeChunk.version_id == version.id,
                        KnowledgeChunk.id.not_in(done),
                    )
                    .order_by(KnowledgeChunk.ordinal)
                    .limit(settings().ai_embedding_batch_size)
                )
            )
            if chunks:
                from app.ai.models import KnowledgeDocument

                from app.models import User

                owner_id = db.get(KnowledgeDocument, version.document_id).owner_id
                db.scalar(select(User).where(User.id == owner_id).with_for_update())
                spent = db.scalar(
                    select(
                        func.coalesce(
                            func.sum(
                                UsageEvent.input_tokens + UsageEvent.output_tokens
                            ),
                            0,
                        )
                    ).where(
                        UsageEvent.user_id == owner_id,
                        UsageEvent.created_at
                        >= now().replace(hour=0, minute=0, second=0, microsecond=0),
                    )
                )
                if (
                    spent + sum(c.token_count for c in chunks)
                    > settings().ai_daily_tokens
                ):
                    raise ValueError("DAILY_EMBEDDING_QUOTA")
                usage = UsageEvent(
                    user_id=owner_id,
                    kind="embedding",
                    request_id=job.id,
                    model=embedder.model,
                    input_tokens=sum(c.token_count for c in chunks),
                    outcome="reserved",
                )
                db.add(usage)
                # Reserve atomically under the same per-user lock as chat. Failed calls retain
                # their conservative reservation until the daily window resets.
                db.commit()
                vectors = await embedder.embed_documents([c.text for c in chunks])
                if len(vectors) != len(chunks) or any(
                    len(v) != 512 or any(not math.isfinite(x) for x in v)
                    for v in vectors
                ):
                    raise ValueError("INVALID_EMBEDDING_RESPONSE")
                for chunk, vector in zip(chunks, vectors):
                    db.add(
                        KnowledgeEmbedding(
                            chunk_id=chunk.id, vector=vector, model=embedder.model
                        )
                    )
                usage.input_tokens = getattr(
                    embedder, "last_usage_tokens", sum(c.token_count for c in chunks)
                )
                usage.outcome = "indexed"
                job.progress = 85
            else:
                job.checkpoint = "validate"
        elif job.checkpoint == "validate":
            pages = db.scalar(
                select(func.count())
                .select_from(DocumentPage)
                .where(
                    DocumentPage.version_id == version.id,
                    DocumentPage.uncertain.is_(False),
                )
            )
            chunks = db.scalar(
                select(func.count())
                .select_from(KnowledgeChunk)
                .where(KnowledgeChunk.version_id == version.id)
            )
            embedded = db.scalar(
                select(func.count())
                .select_from(KnowledgeEmbedding)
                .join(KnowledgeChunk)
                .where(KnowledgeChunk.version_id == version.id)
            )
            if pages != version.page_count or not chunks or embedded != chunks:
                raise ValueError("INCOMPLETE_INDEX")
            version.processing_status, version.failure_code = "ready", None
            job.status, job.progress, job.checkpoint = "succeeded", 100, "complete"
        db.flush()
        # A row lock fences stale worker commits after a lease has expired/reassigned.
        db.refresh(job, ["lease_token", "lease_until"])
        if (
            job.lease_token != lease
            or job.lease_until.replace(tzinfo=__import__("datetime").timezone.utc)
            < now()
        ):
            raise ValueError("STALE_LEASE")
        if job.status != "succeeded":
            job.status = "queued"
        job.lease_until, job.lease_token = None, None
        db.add(
            JobEvent(
                job_id=job.id,
                stage=job.checkpoint,
                message=f"Checkpoint saved; {job.progress}% complete",
            )
        )
        db.commit()
        return {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "checkpoint": job.checkpoint,
        }
    except Exception as exc:
        db.rollback()
        job = db.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
        )
        if job.lease_token != lease:
            return {"job_id": job.id, "status": "stale"}
        code = (
            str(exc)
            if isinstance(exc, ValueError)
            else "PROVIDER_OR_STORAGE_UNAVAILABLE"
        )
        if not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
            code = "PROCESSING_VALIDATION_FAILED"
        if isinstance(exc, HTTPException):
            code = "PROVIDER_NOT_CONFIGURED"
        # Never persist provider exception payloads, prompts, credentials, or passages in ordinary logs.
        job.status, job.error_code = "failed", code[:100]
        job.attempts += 1
        job.lease_token, job.lease_until = None, None
        version = db.get(DocumentVersion, job.version_id)
        version.processing_status, version.failure_code = "failed", job.error_code
        db.add(JobEvent(job_id=job.id, stage=job.checkpoint, message=job.error_code))
        db.commit()
        return {"job_id": job.id, "status": "failed", "error_code": job.error_code}
