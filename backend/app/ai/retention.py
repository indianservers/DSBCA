"""Explicit retention maintenance. Dry-run by default; never run automatically during requests."""

import argparse
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import now
from app.ai.models import Conversation
from app.core.config import settings
from app.core.database import engine


def purge(db, execute=False):
    cutoff = now() - timedelta(days=settings().ai_retention_days)
    rows = list(
        db.scalars(
            select(Conversation).where(
                Conversation.deleted_at.is_not(None), Conversation.deleted_at < cutoff
            )
        )
    )
    if execute:
        for row in rows:
            db.delete(row)
        db.commit()
    return {
        "eligible_conversations": len(rows),
        "executed": execute,
        "retention_days": settings().ai_retention_days,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    with Session(engine()) as db:
        print(purge(db, args.execute))
