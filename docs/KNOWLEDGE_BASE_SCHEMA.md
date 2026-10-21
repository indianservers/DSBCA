# Knowledge base schema

Migration `backend/alembic/versions/0003_ai_research.py` adds only Phase 2 tables and indexes. Phase 1 tables/data are retained. Migration execution uses the direct PostgreSQL URL and TLS. The local test database is disposable; production is never used by tests.

| Table | Purpose |
|---|---|
| ai_organizations, ai_organization_members | Explicit organization membership |
| ai_assistants, ai_assistant_config_versions | Immutable assistant configuration history |
| knowledge_documents | Source metadata, owner and access scope |
| knowledge_document_versions | Hash, private object reference, applicability and separate processing/approval |
| knowledge_document_pages | Physical page, printed label, extracted text, structured tables and preview reference |
| knowledge_chunks | Stable UUID5 passage ID, structural heading and page range |
| knowledge_embeddings | Chunk vector, dimension/model and processing timestamps |
| knowledge_processing_jobs, knowledge_processing_job_events | Durable progress, lease, retry and sanitized event history |
| chat_conversations, chat_messages | Owner history, idempotent request pair and response/config metadata |
| chat_message_evidence | Version-specific immutable citation snapshot |
| chat_answer_feedback | One owner rating per message |
| ai_usage_events | Tokens, latency, outcome and optional configured-price estimates |

Foreign keys enforce identity/version relationships. Unique constraints protect document/version hashes, job idempotency, chunk order, page number, request role and feedback. Existing admin audit records capture mutations without document content or prompts.

## Retrieval indexes

Production `AI_VECTOR_BACKEND=pgvector` creates `vector(512)`, an HNSW cosine index and PostgreSQL GIN full-text index. The explicit migration enables the vector extension. Exact development mode stores the same 512 numeric values as JSON and evaluates cosine similarity over a bounded accessible candidate set, alongside real PostgreSQL FTS. Do not change backend modes against an already migrated database: provision/migrate the intended branch with the correct mode.

## Immutability and history

Replacing a PDF creates a new version and object key. Approved source metadata cannot be edited in place. Older PDFs, chunks and evidence remain available to authorized owners of historical answers after supersession. Access revocation takes precedence over historical links. Model identity is pinned in version metadata on first embedding; changing models midway fails rather than mixing vector spaces. A model migration requires new document versions and full reindexing.

Organization membership currently uses explicit provisioned records; an organization membership administration UI is outside this phase. Client scope uses existing company ownership. An admin role does not grant blanket access to another account's private/client/organization documents.
