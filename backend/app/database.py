import os
import urllib.parse
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.config import get_settings

settings = get_settings()


def resolve_database_url(configured_url: str, env: dict | None = None) -> str:
    """
    Resolves the database URL across local dev (SQLite) and cloud/Vercel deployments (PostgreSQL).
    Automatically detects Vercel's Neon/Postgres env vars (DATABASE_URL, POSTGRES_URL, POSTGRES_PRISMA_URL)
    and normalizes postgres:// / postgresql:// URLs to SQLAlchemy's psycopg v3 driver.
    """
    env_map = env if env is not None else os.environ
    raw = (configured_url or "").strip()

    # If configured URL is still default SQLite, check standard cloud Postgres env vars (e.g. Vercel Storage / Neon)
    if not raw or raw.startswith("sqlite"):
        for var in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING"):
            val = (env_map.get(var) or "").strip()
            if val and not val.startswith("sqlite"):
                raw = val
                break

    if not raw:
        raw = "sqlite:///./paperproof.db"

    # Normalize postgres:// or postgresql:// -> postgresql+psycopg://
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://") :]

    # Strip unsupported Prisma-only query params like pgbouncer=true if present
    if raw.startswith("postgresql+psycopg://") and "pgbouncer=" in raw:
        parsed = urllib.parse.urlsplit(raw)
        qs = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k.lower() != "pgbouncer"]
        raw = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(qs), parsed.fragment)
        )

    # Vercel serverless filesystem is read-only outside /tmp; switch relative SQLite path to /tmp
    if env_map.get("VERCEL") and raw.startswith("sqlite:///./"):
        raw = "sqlite:////tmp/paperproof.db"

    return raw


db_url = resolve_database_url(settings.database_url)
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
else:
    # Cloud PostgreSQL (Neon / Supabase / Render / Railway)
    engine_kwargs = {"pool_pre_ping": True}
    if os.environ.get("VERCEL"):
        # NullPool avoids exhausting serverless Postgres connections across ephemeral Lambda containers
        engine_kwargs["poolclass"] = NullPool
    engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
