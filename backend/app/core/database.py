from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


@lru_cache
def engine():
    cfg = settings()
    url = cfg.database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if cfg.app_env == "test" and url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("PostgreSQL is required")
    from sqlalchemy.engine import make_url

    if make_url(url).query.get("sslmode") not in {"require", "verify-full"}:
        raise ValueError("PostgreSQL SSL is required")
    if cfg.app_env in {"production", "staging"}:
        if make_url(url).query.get("sslmode") != "verify-full":
            raise ValueError(
                "Hosted PostgreSQL requires certificate and hostname verification"
            )
    tls_args = {}
    if cfg.app_env in {"production", "staging"}:
        import certifi

        tls_args["sslrootcert"] = certifi.where()
    return create_engine(
        url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=8,
        pool_recycle=240,
        pool_pre_ping=True,
        connect_args={
            **tls_args,
            "connect_timeout": 8,
            "options": "-c statement_timeout=15000 -c lock_timeout=5000",
        },
    )


def db_session():
    with sessionmaker(engine(), expire_on_commit=False)() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
