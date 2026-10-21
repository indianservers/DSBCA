"""Dry-run by default. Only the named loopback QA database can be reset."""

import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.phase4.local", override=True)
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.release_qa import guard
from app.core.database import engine
from app.models import Base


def reset(confirm=None):
    guard()
    if confirm not in (None, "dsbca_phase4_qa"):
        raise RuntimeError("Confirmation must exactly name the isolated QA database")
    with Session(engine()) as db:
        count = sum(
            db.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        )
        if confirm:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()
    return {
        "database": "dsbca_phase4_qa",
        "rows": count,
        "executed": bool(confirm),
        "private_files_purged": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm")
    print(reset(parser.parse_args().confirm))
