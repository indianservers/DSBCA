from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.database import db_session
from app.api import auth, resources
from app.ai.api import router as ai_router
from app.professional.api import router as professional_router

from app.core.operations import OperationsMiddleware

app = FastAPI(title="DSBCA Research API", version="4.0.0")
app.add_middleware(OperationsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(professional_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "phase": 4}


@app.get("/api/v1/ready")
def ready(db=Depends(db_session)):
    try:
        db.execute(text("SELECT 1"))
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != "0004":
            raise HTTPException(503, "Database migration is required")
    except SQLAlchemyError:
        raise HTTPException(503, "Database or schema is not ready")
    return {"status": "ready", "schema_revision": revision}


@app.exception_handler(IntegrityError)
def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={"detail": "Record conflicts with existing or related data"},
    )


@app.exception_handler(OperationalError)
def database_error(request, exc):
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "3"},
        content={"detail": "Database temporarily unavailable"},
    )
