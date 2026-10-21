from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.models import Base

config = context.config
url = settings().database_url_unpooled
if not url:
    raise RuntimeError("DATABASE_URL_UNPOOLED is required for explicit migrations")
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
if settings().app_env != "test" and make_url(url).query.get("sslmode") not in {
    "require",
    "verify-full",
}:
    raise RuntimeError("Migrations require SSL")
if settings().app_env in {"production", "staging"} and (
    make_url(url).query.get("sslmode") != "verify-full"
    or "-pooler" in (make_url(url).host or "")
):
    raise RuntimeError("Hosted migrations require verified TLS and a direct connection")
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    tls_args = {}
    if settings().app_env in {"production", "staging"}:
        import certifi

        tls_args["sslrootcert"] = certifi.where()
    with create_engine(
        url, poolclass=pool.NullPool, connect_args=tls_args
    ).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
