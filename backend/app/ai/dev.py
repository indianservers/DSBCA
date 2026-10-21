"""Run the isolated Phase 2 local API; never changes the configured Neon database."""

from dotenv import load_dotenv

load_dotenv(".env.phase2.local", override=True)
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002)
