from fastapi import HTTPException
from sqlalchemy import select, or_, and_, exists
from app.models import Company
from app.ai.models import (
    KnowledgeDocument,
    OrganizationMember,
    Conversation,
    ChatMessage,
    MessageEvidence,
)


def document_access_clause(user_id):
    org_member = exists(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == KnowledgeDocument.organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    company_owner = exists(
        select(Company.id).where(
            Company.id == KnowledgeDocument.company_id, Company.owner_id == user_id
        )
    )
    return or_(
        KnowledgeDocument.scope.in_(["shared", "demo"]),
        and_(
            KnowledgeDocument.scope == "private", KnowledgeDocument.owner_id == user_id
        ),
        and_(KnowledgeDocument.scope == "organization", org_member),
        and_(KnowledgeDocument.scope == "client", company_owner),
    )


def accessible_document(db, document_id, user):
    row = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id, document_access_clause(user.id)
        )
    )
    if not row:
        raise HTTPException(404, "Document not found")
    return row


def validate_scope(db, metadata, user):
    if metadata.organization_id and not db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == metadata.organization_id,
            OrganizationMember.user_id == user.id,
        )
    ):
        raise HTTPException(403, "Organization membership required")
    if metadata.company_id and not db.scalar(
        select(Company.id).where(
            Company.id == metadata.company_id, Company.owner_id == user.id
        )
    ):
        raise HTTPException(403, "Company ownership required")


def owned_conversation(db, id, user):
    row = db.scalar(
        select(Conversation).where(
            Conversation.id == id,
            Conversation.owner_id == user.id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not row:
        raise HTTPException(404, "Conversation not found")
    return row


def owns_evidence(db, user_id, chunk_id):
    return (
        db.scalar(
            select(MessageEvidence.id)
            .join(ChatMessage)
            .join(Conversation)
            .where(
                Conversation.owner_id == user_id,
                Conversation.deleted_at.is_(None),
                MessageEvidence.chunk_id == chunk_id,
            )
        )
        is not None
    )
