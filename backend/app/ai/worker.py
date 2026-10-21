"""Explicit bounded worker. Each checkpoint commits independently and survives process loss."""

import argparse
import asyncio
from sqlalchemy.orm import Session
from app.core.database import engine
from app.ai.ingestion import claim_job, run_step


async def main(max_steps):
    for _ in range(max_steps):
        with Session(engine(), expire_on_commit=False) as db:
            claimed = claim_job(db)
            if not claimed:
                print("No queued or expired-leased jobs")
                break
            result = await run_step(db, *claimed)
            print(
                result
            )  # IDs, stage and sanitized codes only; never prompts/passages/provider payloads.


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-steps", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 1000:
        raise SystemExit("max-steps must be 1–1000")
    asyncio.run(main(args.max_steps))
