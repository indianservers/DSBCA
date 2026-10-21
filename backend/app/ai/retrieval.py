import math
import re
from datetime import date
from sqlalchemy import select, or_, func, cast, literal
from pgvector.sqlalchemy import Vector
from fastapi import HTTPException
from app.ai.models import (
    KnowledgeDocument as D,
    DocumentVersion as V,
    KnowledgeChunk as C,
    KnowledgeEmbedding as E,
    DocumentPage,
)
from app.ai.access import document_access_clause
from app.ai.providers import embedding_provider
from app.core.config import settings

SYNONYMS = {
    "ct": "Corporate Tax",
    "tp": "Transfer Pricing",
    "dmtt": "Domestic Minimum Top-up Tax",
    "qfzp": "Qualifying Free Zone Person",
    "fta": "Federal Tax Authority",
    "ifrs": "International Financial Reporting Standards",
    "vat": "Value Added Tax",
    "pe": "Permanent Establishment",
}
AUTHORITY = {
    "Legislation": 1,
    "Cabinet Decision": 1,
    "Ministerial Decision": 1,
    "Official Tax Guidance": 2,
    "Public Clarification": 2,
    "IFRS Standard": 3,
    "Audit Standard": 3,
    "Professional Interpretation": 4,
    "Internal Technical Note": 5,
    "Demonstration Material": 6,
    "Other": 7,
}


def normalize(query):
    return (
        query
        + " "
        + " ".join(
            v
            for k, v in SYNONYMS.items()
            if re.search(r"\b" + re.escape(k) + r"\b", query, re.I)
        )
    )


def cosine(a, b):
    divisor = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / divisor if divisor else 0


def eligible(request, user_id):
    filters = [
        D.archived.is_(False),
        V.approval_status == "approved",
        D.subject == request.subject,
        D.jurisdiction == request.jurisdiction,
        document_access_clause(user_id),
    ]
    if not request.include_demo:
        filters.append(D.scope != "demo")
    if request.issuer:
        filters.append(D.issuer == request.issuer)
    if request.period_start:
        filters += [
            V.processing_status.in_(["ready", "superseded"]),
            V.effective_from.is_not(None),
            V.effective_from <= request.period_end,
            or_(V.effective_to.is_(None), V.effective_to >= request.period_start),
        ]
    else:
        filters += [
            V.processing_status == "ready",
            or_(V.effective_from.is_(None), V.effective_from <= date.today()),
            or_(V.effective_to.is_(None), V.effective_to >= date.today()),
        ]
    return filters


def evidence_card(db, chunk, version, document, score):
    page = db.scalar(
        select(DocumentPage).where(
            DocumentPage.version_id == version.id,
            DocumentPage.physical_page == chunk.page_start,
        )
    )
    meta = version.source_metadata
    return {
        "id": chunk.id,
        "version_id": version.id,
        "document_id": document.id,
        "title": meta.get("title", document.title),
        "version": version.version,
        "issuer": meta.get("issuer", document.issuer),
        "document_type": meta.get("document_type", document.document_type),
        "subject": document.subject,
        "physical_page": chunk.page_start,
        "page_end": chunk.page_end,
        "printed_label": page.printed_label if page else str(chunk.page_start),
        "heading": chunk.heading,
        "passage": chunk.text,
        "score": round(score, 5),
        "effective_from": (
            str(version.effective_from) if version.effective_from else None
        ),
        "effective_to": str(version.effective_to) if version.effective_to else None,
        "demo": document.scope == "demo",
        "source_path": "/ai/sources/" + chunk.id,
        "page_path": f"/ai/documents/{version.id}/pages/{chunk.page_start}",
        "status": version.processing_status,
    }


async def retrieve(db, request, user, config, embedder=None):
    if request.subject not in config["allowed_subjects"]:
        return []
    query = normalize(request.question)
    base = (
        select(C, V, D, E)
        .join(V, C.version_id == V.id)
        .join(D, V.document_id == D.id)
        .join(E, E.chunk_id == C.id)
        .where(*eligible(request, user.id))
    )
    if not db.scalar(select(func.count()).select_from(base.subquery())):
        return []
    embedder = embedder or embedding_provider(config["embedding_model"])
    base = base.where(E.model == embedder.model)
    vector = await embedder.embed_query(query)
    if len(vector) != 512 or not all(math.isfinite(x) for x in vector):
        raise ValueError("Invalid query embedding")
    top = config["retrieval_top_k"]
    if db.bind.dialect.name == "postgresql":
        rank = func.ts_rank_cd(
            func.to_tsvector("english", C.text),
            func.websearch_to_tsquery("english", query),
        )
        lexical = list(
            db.execute(
                base.where(
                    func.to_tsvector("english", C.text).op("@@")(
                        func.websearch_to_tsquery("english", query)
                    )
                )
                .order_by(rank.desc())
                .limit(top * 4)
            )
        )
    else:
        # SQLite is a test harness only. Production and local PostgreSQL use real FTS.
        tokens = set(re.findall(r"\w+", query.lower()))
        lexical = sorted(
            db.execute(base).all(),
            key=lambda row: len(tokens & set(re.findall(r"\w+", row[0].text.lower()))),
            reverse=True,
        )[: top * 4]
    if (
        db.bind.dialect.name == "postgresql"
        and settings().ai_vector_backend == "pgvector"
    ):
        distance = E.vector.op("<=>")(cast(literal(str(vector)), Vector(512)))
        semantic = list(db.execute(base.order_by(distance).limit(top * 4)))
    else:
        candidates = list(db.execute(base.limit(1001)))
        if len(candidates) > 1000:
            raise HTTPException(
                503,
                "Exact vector fallback limit reached. Activate pgvector before expanding this corpus.",
            )
        semantic = sorted(
            candidates, key=lambda row: cosine(vector, row[3].vector), reverse=True
        )[: top * 4]
    fused, rows = {}, {}
    for ranking in [lexical, semantic]:
        for rank, row in enumerate(ranking):
            key = row[0].id
            fused[key] = fused.get(key, 0) + 1 / (60 + rank + 1)
            rows[key] = row
    scored = []
    for key, rrf in fused.items():
        chunk, version, document, embedding = rows[key]
        similarity = cosine(vector, embedding.vector)
        if similarity < config["minimum_evidence_score"]:
            continue
        authority = AUTHORITY.get(
            version.source_metadata.get("document_type", document.document_type), 7
        )
        scored.append((rrf + 0.001 / authority, similarity, chunk, version, document))
    scored.sort(key=lambda x: x[0], reverse=True)
    output, seen, budget = [], set(), settings().ai_max_context_chars
    for _, similarity, chunk, version, document in scored[:top]:
        # Surrounding passages remain subject to the SAME version/access eligibility.
        around = list(
            db.scalars(
                select(C)
                .where(
                    C.version_id == version.id,
                    C.ordinal.between(max(0, chunk.ordinal - 1), chunk.ordinal + 1),
                )
                .order_by(C.ordinal)
            )
        )
        for passage in [chunk] + around:
            if (
                passage.id not in seen
                and len(passage.text) <= budget
                and len(output) < top * 2
            ):
                output.append(evidence_card(db, passage, version, document, similarity))
                budget -= len(passage.text)
                seen.add(passage.id)
    return output
