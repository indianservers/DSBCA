import asyncio
import json
import re
import time
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models import User, now
from app.ai.models import (
    ChatMessage,
    MessageEvidence,
    UsageEvent,
    KnowledgeChunk,
    DocumentVersion,
    KnowledgeDocument,
)
from app.ai.access import owned_conversation, document_access_clause
from app.ai.configuration import current_config
from app.ai.providers import chat_provider
from app.ai.retrieval import retrieve, eligible
from app.core.config import settings


def compact(value):
    return re.sub(r"\s+", " ", value).strip()


def complete_excerpt(quote, passage):
    quote, passage = compact(quote), compact(passage)
    if quote == passage:
        return True
    index = passage.find(quote)
    return (
        index >= 0
        and quote.endswith((".", "!", "?"))
        and (index == 0 or passage[:index].rstrip().endswith((".", "!", "?")))
    )


def validate_citations(answer, evidence):
    lookup = {e["id"]: e for e in evidence}
    used = {}
    for claim in answer.claims:
        if len(claim.evidence_ids) != len(claim.supporting_quotes):
            raise ValueError("CITATION_QUOTE_COUNT")
        if re.search(r"https?://|www\.", claim.text, re.I):
            raise ValueError("UNTRUSTED_MODEL_URL")
        supporting = []
        for id, quote in zip(claim.evidence_ids, claim.supporting_quotes):
            if (
                id not in lookup
                or len(compact(quote)) < 15
                or compact(quote) not in compact(lookup[id]["passage"])
            ):
                raise ValueError("INVALID_CITATION_OR_QUOTE")
            supporting.append(quote)
            used[id] = lookup[id]
        # Fail closed: a substring quote is not proof that a paraphrase preserves
        # negation, conditions or exceptions. Until an independently evaluated
        # entailment verifier exists, only exact source excerpts can be emitted.
        if not any(
            compact(claim.text) == compact(quote)
            and complete_excerpt(quote, lookup[id]["passage"])
            for id, quote in zip(claim.evidence_ids, supporting)
        ):
            raise ValueError("UNVERIFIED_PARAPHRASE")
        # Numerical details cannot be introduced solely by generative text.
        numbers = re.findall(r"\d+(?:[.,]\d+)*", claim.text)
        if any(number not in " ".join(supporting) for number in numbers):
            raise ValueError("UNSUPPORTED_NUMERICAL_CLAIM")
    return list(used.values())


def reserve(db, user, data):
    cfg = settings()
    conversation = owned_conversation(db, data.conversation_id, user)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    existing = db.scalar(
        select(ChatMessage).where(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.request_id == data.request_id,
            ChatMessage.role == "assistant",
        )
    )
    if existing:
        question = db.scalar(
            select(ChatMessage).where(
                ChatMessage.conversation_id == conversation.id,
                ChatMessage.request_id == data.request_id,
                ChatMessage.role == "user",
            )
        )
        if question.text != data.question:
            raise HTTPException(
                409, "Request ID was already used for a different question"
            )
        return existing, None, None
    since = now().replace(hour=0, minute=0, second=0, microsecond=0)
    requests = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.user_id == user.id,
            UsageEvent.kind == "chat",
            UsageEvent.created_at >= since,
        )
    )
    recent = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.user_id == user.id,
            UsageEvent.kind == "chat",
            UsageEvent.created_at >= now() - timedelta(minutes=1),
        )
    )
    consumed = db.scalar(
        select(
            func.coalesce(
                func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens), 0
            )
        ).where(UsageEvent.user_id == user.id, UsageEvent.created_at >= since)
    )
    config_id, config = current_config(db)
    reservation = (len(data.question) + cfg.ai_max_context_chars + 12000) // 3 + config[
        "max_output_tokens"
    ]
    if (
        requests >= cfg.ai_daily_requests
        or recent >= 10
        or consumed + reservation > cfg.ai_daily_tokens
    ):
        raise HTTPException(
            429,
            "AI consumption limit reached. Try later or contact your administrator.",
        )
    if config["rerank_enabled"]:
        raise HTTPException(503, "Optional reranking adapter is not configured")
    user_message = ChatMessage(
        conversation_id=conversation.id,
        request_id=data.request_id,
        role="user",
        text=data.question,
        status="completed",
        subject=data.subject,
    )
    assistant = ChatMessage(
        conversation_id=conversation.id,
        request_id=data.request_id,
        role="assistant",
        status="running",
        subject=data.subject,
        config_id=config_id,
        response_metadata={
            "mode": "approved_pdfs",
            "official_verification_performed": False,
            "research_period": [str(data.period_start), str(data.period_end)],
            "config_snapshot": config,
        },
    )
    db.add_all([user_message, assistant])
    conversation.updated_at = now()
    if conversation.title in ("New research", "New conversation"):
        conversation.title = data.question[:150]
    event = UsageEvent(
        user_id=user.id,
        kind="chat",
        request_id=data.request_id,
        model=config["chat_model"],
        input_tokens=reservation,
        outcome="reserved",
        subject=data.subject,
    )
    db.add(event)
    db.commit()
    return assistant, event, config


def public_message(db, message, user):
    evidence = []
    for stored in db.scalars(
        select(MessageEvidence).where(MessageEvidence.message_id == message.id)
    ):
        if db.scalar(
            select(KnowledgeDocument.id)
            .join(DocumentVersion)
            .where(
                DocumentVersion.id == stored.version_id, document_access_clause(user.id)
            )
        ):
            evidence.append(stored.snapshot)
    meta = {
        k: v for k, v in message.response_metadata.items() if k != "config_snapshot"
    }
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "request_id": message.request_id,
        "role": message.role,
        "text": message.text,
        "status": message.status,
        "subject": message.subject,
        "created_at": message.created_at.isoformat(),
        "citations": evidence,
        "metadata": meta,
    }


async def answer_question(
    db, user, data, assistant, event, config, model=None, embedder=None
):
    try:
        async with asyncio.timeout(settings().ai_total_request_timeout):
            return await _answer_question(
                db, user, data, assistant, event, config, model, embedder
            )
    except TimeoutError:
        db.rollback()
        db.refresh(assistant)
        assistant.status = "failed"
        assistant.text = "The research request exceeded its time budget. Your question is preserved; please retry later."
        assistant.response_metadata = {
            **assistant.response_metadata,
            "error_code": "request_timeout",
        }
        event.outcome = "request_timeout"
        db.commit()
        return public_message(db, assistant, user)


async def _answer_question(
    db, user, data, assistant, event, config, model=None, embedder=None
):
    started = time.monotonic()
    try:
        from app.professional.tools import application_answer

        try:
            application = await application_answer(db, user, data, config)
        except HTTPException as exc:
            application = (
                "The requested application tool could not run: " + str(exc.detail),
                {"kind": "limitation", "status_code": exc.status_code},
            )
        if application:
            assistant.text, application_result = application
            assistant.status = (
                "completed"
                if application_result["kind"] != "limitation"
                else "clarification"
            )
            assistant.response_metadata = {
                **assistant.response_metadata,
                "application_result": application_result,
            }
            event.outcome, event.model = (
                "application_tool",
                "deterministic-application-tools",
            )
            event.input_tokens, event.output_tokens = 0, 0
            event.latency_ms = int((time.monotonic() - started) * 1000)
            db.commit()
            return public_message(db, assistant, user)
        if (
            re.search(r"\b(?:FY\s*)?(?:19|20)\d{2}\b", data.question, re.I)
            and not data.period_start
        ):
            assistant.text = "Please provide the start and end dates of the tax or financial period. A year label alone does not establish your fiscal period."
            assistant.status = "clarification"
            citations = []
        else:
            evidence = await retrieve(db, data, user, config, embedder)
            if not evidence:
                assistant.text = "I could not find sufficient approved, accessible PDF evidence for this question and period. This does not establish that no rule exists. Please add an approved source or clarify the subject, jurisdiction and relevant period."
                assistant.status, citations = "insufficient_evidence", []
            else:
                history = list(
                    db.scalars(
                        select(ChatMessage)
                        .where(
                            ChatMessage.conversation_id == data.conversation_id,
                            ChatMessage.id != assistant.id,
                            ChatMessage.status == "completed",
                        )
                        .order_by(ChatMessage.created_at.desc())
                        .limit(config["history_window"])
                    )
                )
                history_data = [
                    {"role": h.role, "text": h.text[:2000]} for h in reversed(history)
                ]
                history_data = history_data[-6:]
                db.commit()  # Release connection before waiting for the model.
                answer, usage = await (model or chat_provider()).generate_answer(
                    data.question, evidence, history_data, config
                )
                db.refresh(assistant)
                if assistant.status == "cancelled":
                    event.outcome = "cancelled"
                    db.commit()
                    return public_message(db, assistant, user)
                citations = validate_citations(answer, evidence)
                from app.ai.models import DocumentPage

                for citation in citations:
                    quotes = [
                        quote
                        for claim in answer.claims
                        for id, quote in zip(
                            claim.evidence_ids, claim.supporting_quotes
                        )
                        if id == citation["id"]
                    ]
                    pages = list(
                        db.scalars(
                            select(DocumentPage)
                            .where(
                                DocumentPage.version_id == citation["version_id"],
                                DocumentPage.physical_page.between(
                                    citation["physical_page"], citation["page_end"]
                                ),
                            )
                            .order_by(DocumentPage.physical_page)
                        )
                    )
                    matched = [
                        page
                        for page in pages
                        if any(compact(quote) in compact(page.text) for quote in quotes)
                    ]
                    if not matched:
                        matched = pages  # A quoted passage may cross a physical page boundary.
                    if not matched:
                        raise ValueError("CITATION_PAGE_MISSING")
                    citation["physical_page"] = matched[0].physical_page
                    citation["printed_label"] = matched[0].printed_label
                    citation["matched_pages"] = [page.physical_page for page in matched]
                    citation["supporting_quotes"] = quotes
                    citation["page_path"] = (
                        f"/ai/documents/{citation['version_id']}/pages/{matched[0].physical_page}"
                    )
                # Recheck current approval/access/applicability before exposing generated claims.
                for citation in citations:
                    valid = db.scalar(
                        select(KnowledgeChunk.id)
                        .join(DocumentVersion)
                        .join(KnowledgeDocument)
                        .where(
                            KnowledgeChunk.id == citation["id"],
                            *eligible(data, user.id),
                        )
                    )
                    if not valid:
                        raise ValueError("SOURCE_ACCESS_CHANGED")
                labels = {c["id"]: i + 1 for i, c in enumerate(citations)}
                parts = []
                if any(c["demo"] for c in citations):
                    parts.append("**DEMONSTRATION ONLY — NOT UAE LAW**")
                for claim in answer.claims:
                    parts.append(
                        "**Source excerpt (not a professional conclusion)**\n"
                        + claim.text
                        + " "
                        + " ".join(f"[{labels[id]}]" for id in claim.evidence_ids)
                    )
                if answer.missing_information:
                    parts.append(
                        "**Additional information**\n"
                        + "Further entity facts or approved source material are needed."
                    )
                limitations = [
                    "Based on approved uploaded PDFs. Independent official-source verification has not been performed."
                ]
                if any(c["effective_from"] is None for c in citations):
                    limitations.append(
                        "Some source applicability dates have not been established."
                    )
                parts.append(
                    "**Evidence limitations**\n"
                    + "\n".join("- " + x for x in limitations)
                )
                assistant.text = "\n\n".join(parts)
                assistant.status = (
                    "completed" if answer.claims else "insufficient_evidence"
                )
                event.input_tokens, event.output_tokens = (
                    usage.get("input_tokens", event.input_tokens),
                    usage.get("output_tokens", 0),
                )
                if (
                    config.get("input_cost_per_million") is not None
                    and config.get("output_cost_per_million") is not None
                ):
                    event.estimated_cost = (
                        event.input_tokens * config["input_cost_per_million"]
                        + event.output_tokens * config["output_cost_per_million"]
                    ) / 1000000
        for citation in citations:
            db.add(
                MessageEvidence(
                    message_id=assistant.id,
                    chunk_id=citation["id"],
                    version_id=citation["version_id"],
                    snapshot=citation,
                )
            )
        event.outcome, event.latency_ms = (
            assistant.status,
            int((time.monotonic() - started) * 1000),
        )
        if (
            assistant.status in ("insufficient_evidence", "clarification")
            and not citations
        ):
            event.input_tokens, event.output_tokens = 0, 0
        db.commit()
        return public_message(db, assistant, user)
    except asyncio.CancelledError:
        db.rollback()
        db.refresh(assistant)
        if assistant.status == "running":
            assistant.status = "cancelled"
            event.outcome = "cancelled"
            db.commit()
        raise
    except Exception as exc:
        db.rollback()
        db.refresh(assistant)
        if assistant.status == "cancelled":
            event.outcome = "cancelled"
            db.commit()
            return public_message(db, assistant, user)
        assistant.status = "failed"
        code = (
            "citation_validation_failed"
            if isinstance(exc, ValueError)
            else "provider_unavailable"
        )
        assistant.text = (
            "The answer could not be verified. Your question is preserved. Please retry after checking the source and provider configuration."
            if code == "citation_validation_failed"
            else "The AI provider is unavailable or unconfigured. Your question is preserved; please retry later."
        )
        assistant.response_metadata = {
            **assistant.response_metadata,
            "error_code": code,
        }
        event.outcome, event.latency_ms = code, int((time.monotonic() - started) * 1000)
        db.commit()
        return public_message(db, assistant, user)


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
