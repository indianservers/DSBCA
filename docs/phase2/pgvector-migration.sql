BEGIN;

-- Running upgrade 0002 -> 0003

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ai_assistants (
    name VARCHAR(100) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE ai_organizations (
    name VARCHAR(180) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE ai_assistant_config_versions (
    assistant_id VARCHAR(36) NOT NULL, 
    author_id VARCHAR(36) NOT NULL, 
    configuration JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(assistant_id) REFERENCES ai_assistants (id), 
    FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE INDEX ix_ai_assistant_config_versions_assistant_id ON ai_assistant_config_versions (assistant_id);

CREATE TABLE ai_organization_members (
    organization_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(organization_id) REFERENCES ai_organizations (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (organization_id, user_id)
);

CREATE INDEX ix_ai_organization_members_organization_id ON ai_organization_members (organization_id);

CREATE INDEX ix_ai_organization_members_user_id ON ai_organization_members (user_id);

CREATE TABLE ai_usage_events (
    user_id VARCHAR(36) NOT NULL, 
    kind VARCHAR(40) NOT NULL, 
    request_id VARCHAR(80) NOT NULL, 
    model VARCHAR(100) NOT NULL, 
    input_tokens INTEGER NOT NULL, 
    output_tokens INTEGER NOT NULL, 
    latency_ms INTEGER NOT NULL, 
    outcome VARCHAR(80) NOT NULL, 
    subject VARCHAR(80) NOT NULL, 
    estimated_cost FLOAT, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_ai_usage_events_kind ON ai_usage_events (kind);

CREATE INDEX ix_ai_usage_events_user_id ON ai_usage_events (user_id);

CREATE TABLE chat_conversations (
    owner_id VARCHAR(36) NOT NULL, 
    title VARCHAR(160) NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_chat_conversations_deleted_at ON chat_conversations (deleted_at);

CREATE INDEX ix_chat_conversations_owner_id ON chat_conversations (owner_id);

CREATE TABLE chat_messages (
    conversation_id VARCHAR(36) NOT NULL, 
    request_id VARCHAR(80) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    text TEXT NOT NULL, 
    status VARCHAR(24) NOT NULL, 
    subject VARCHAR(80) NOT NULL, 
    config_id VARCHAR(36), 
    response_metadata JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(config_id) REFERENCES ai_assistant_config_versions (id), 
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE, 
    UNIQUE (conversation_id, request_id, role)
);

CREATE INDEX ix_chat_messages_conversation_id ON chat_messages (conversation_id);

CREATE INDEX ix_chat_messages_request_id ON chat_messages (request_id);

CREATE TABLE knowledge_documents (
    owner_id VARCHAR(36) NOT NULL, 
    organization_id VARCHAR(36), 
    company_id VARCHAR(36), 
    scope VARCHAR(20) NOT NULL, 
    title VARCHAR(240) NOT NULL, 
    subject VARCHAR(80) NOT NULL, 
    issuer VARCHAR(180) NOT NULL, 
    jurisdiction VARCHAR(80) NOT NULL, 
    language VARCHAR(20) NOT NULL, 
    document_type VARCHAR(80) NOT NULL, 
    description TEXT NOT NULL, 
    keywords JSON NOT NULL, 
    internal_notes TEXT NOT NULL, 
    archived BOOLEAN NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(organization_id) REFERENCES ai_organizations (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_knowledge_documents_archived ON knowledge_documents (archived);

CREATE INDEX ix_knowledge_documents_company_id ON knowledge_documents (company_id);

CREATE INDEX ix_knowledge_documents_organization_id ON knowledge_documents (organization_id);

CREATE INDEX ix_knowledge_documents_owner_id ON knowledge_documents (owner_id);

CREATE INDEX ix_knowledge_documents_scope ON knowledge_documents (scope);

CREATE INDEX ix_knowledge_documents_subject ON knowledge_documents (subject);

CREATE TABLE chat_answer_feedback (
    user_id VARCHAR(36) NOT NULL, 
    message_id VARCHAR(36) NOT NULL, 
    rating INTEGER NOT NULL, 
    comment VARCHAR(1000) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(message_id) REFERENCES chat_messages (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (user_id, message_id)
);

CREATE INDEX ix_chat_answer_feedback_user_id ON chat_answer_feedback (user_id);

CREATE TABLE knowledge_document_versions (
    document_id VARCHAR(36) NOT NULL, 
    version VARCHAR(80) NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    storage_key VARCHAR(400) NOT NULL, 
    byte_size INTEGER NOT NULL, 
    source_metadata JSON NOT NULL, 
    publication_date DATE, 
    effective_from DATE, 
    effective_to DATE, 
    applicable_periods VARCHAR(240) NOT NULL, 
    processing_status VARCHAR(24) NOT NULL, 
    approval_status VARCHAR(24) NOT NULL, 
    approved_by VARCHAR(36), 
    approved_at TIMESTAMP WITH TIME ZONE, 
    page_count INTEGER NOT NULL, 
    failure_code VARCHAR(80), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(approved_by) REFERENCES users (id), 
    FOREIGN KEY(document_id) REFERENCES knowledge_documents (id), 
    UNIQUE (document_id, sha256), 
    UNIQUE (document_id, version), 
    UNIQUE (storage_key)
);

CREATE INDEX ix_knowledge_document_versions_approval_status ON knowledge_document_versions (approval_status);

CREATE INDEX ix_knowledge_document_versions_document_id ON knowledge_document_versions (document_id);

CREATE INDEX ix_knowledge_document_versions_effective_from ON knowledge_document_versions (effective_from);

CREATE INDEX ix_knowledge_document_versions_effective_to ON knowledge_document_versions (effective_to);

CREATE INDEX ix_knowledge_document_versions_processing_status ON knowledge_document_versions (processing_status);

CREATE INDEX ix_knowledge_document_versions_sha256 ON knowledge_document_versions (sha256);

CREATE TABLE knowledge_chunks (
    version_id VARCHAR(36) NOT NULL, 
    ordinal INTEGER NOT NULL, 
    text TEXT NOT NULL, 
    heading VARCHAR(400) NOT NULL, 
    page_start INTEGER NOT NULL, 
    page_end INTEGER NOT NULL, 
    token_count INTEGER NOT NULL, 
    structural_location VARCHAR(400) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(version_id) REFERENCES knowledge_document_versions (id), 
    UNIQUE (version_id, ordinal)
);

CREATE INDEX ix_knowledge_chunks_version_id ON knowledge_chunks (version_id);

CREATE TABLE knowledge_document_pages (
    version_id VARCHAR(36) NOT NULL, 
    physical_page INTEGER NOT NULL, 
    printed_label VARCHAR(80) NOT NULL, 
    text TEXT NOT NULL, 
    tables JSON NOT NULL, 
    provenance VARCHAR(100) NOT NULL, 
    uncertain BOOLEAN NOT NULL, 
    preview_key VARCHAR(400) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(version_id) REFERENCES knowledge_document_versions (id), 
    UNIQUE (version_id, physical_page)
);

CREATE INDEX ix_knowledge_document_pages_version_id ON knowledge_document_pages (version_id);

CREATE TABLE knowledge_processing_jobs (
    version_id VARCHAR(36) NOT NULL, 
    status VARCHAR(24) NOT NULL, 
    attempts INTEGER NOT NULL, 
    checkpoint VARCHAR(24) NOT NULL, 
    progress INTEGER NOT NULL, 
    error_code VARCHAR(100), 
    lease_token VARCHAR(80), 
    lease_until TIMESTAMP WITH TIME ZONE, 
    idempotency_key VARCHAR(100) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(version_id) REFERENCES knowledge_document_versions (id), 
    UNIQUE (idempotency_key), 
    UNIQUE (version_id)
);

CREATE INDEX ix_knowledge_processing_jobs_lease_until ON knowledge_processing_jobs (lease_until);

CREATE INDEX ix_knowledge_processing_jobs_status ON knowledge_processing_jobs (status);

CREATE TABLE chat_message_evidence (
    message_id VARCHAR(36) NOT NULL, 
    chunk_id VARCHAR(36) NOT NULL, 
    version_id VARCHAR(36) NOT NULL, 
    snapshot JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks (id), 
    FOREIGN KEY(message_id) REFERENCES chat_messages (id) ON DELETE CASCADE, 
    FOREIGN KEY(version_id) REFERENCES knowledge_document_versions (id), 
    UNIQUE (message_id, chunk_id)
);

CREATE INDEX ix_chat_message_evidence_message_id ON chat_message_evidence (message_id);

CREATE TABLE knowledge_embeddings (
    chunk_id VARCHAR(36) NOT NULL, 
    model VARCHAR(100) NOT NULL, 
    vector VECTOR(512) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks (id), 
    UNIQUE (chunk_id)
);

CREATE INDEX ix_knowledge_embeddings_model ON knowledge_embeddings (model);

CREATE TABLE knowledge_processing_job_events (
    job_id VARCHAR(36) NOT NULL, 
    stage VARCHAR(40) NOT NULL, 
    message VARCHAR(400) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(job_id) REFERENCES knowledge_processing_jobs (id)
);

CREATE INDEX ix_knowledge_processing_job_events_job_id ON knowledge_processing_job_events (job_id);

CREATE INDEX ix_knowledge_chunks_fts ON knowledge_chunks USING gin (to_tsvector('english', text));

CREATE INDEX ix_knowledge_embeddings_hnsw ON knowledge_embeddings USING hnsw (vector vector_cosine_ops);

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

COMMIT;

