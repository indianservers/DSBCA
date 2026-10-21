from sqlalchemy import select
from app.ai.models import AssistantConfig
from app.ai.schemas import ConfigInput
from app.ai.providers import DEFAULT_INSTRUCTIONS
from app.core.config import settings


def current_config(db):
    row = db.scalar(
        select(AssistantConfig)
        .order_by(AssistantConfig.created_at.desc(), AssistantConfig.id.desc())
        .limit(1)
    )
    if row:
        return row.id, ConfigInput.model_validate(row.configuration).model_dump()
    cfg = settings()
    return (
        None,
        ConfigInput(
            system_instructions=DEFAULT_INSTRUCTIONS,
            chat_model=cfg.ai_chat_model,
            fast_model=cfg.ai_fast_model,
            embedding_model=cfg.ai_embedding_model,
            retrieval_top_k=cfg.ai_retrieval_top_k,
            max_output_tokens=cfg.ai_max_output_tokens,
            minimum_evidence_score=cfg.ai_min_evidence_score,
            history_window=cfg.ai_history_window,
        ).model_dump(),
    )
