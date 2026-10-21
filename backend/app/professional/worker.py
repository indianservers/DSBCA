"""Run bounded durable notification work independently of Flutter clients."""

import argparse, asyncio
from sqlalchemy.orm import Session
from app.core.database import engine
from app.professional.notifications import tick


async def main(steps):
    for _ in range(steps):
        with Session(engine(), expire_on_commit=False) as db:
            result = await tick(db)
            print(
                {
                    k: v
                    for k, v in result.items()
                    if k in ["job_id", "status", "error_code"]
                }
            )
            if result["status"] == "idle":
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-steps", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 500:
        raise SystemExit("Use 1–500 bounded steps")
    asyncio.run(main(args.max_steps))
