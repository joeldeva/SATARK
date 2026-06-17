from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


sqlite_path = settings.sqlite_path
if sqlite_path:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models.survey  # noqa: F401
    import models.platform  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _repair_sqlite_dev_schema()


def _repair_sqlite_dev_schema() -> None:
    """Additive SQLite dev repair for columns introduced after create_all.

    SQLite does not apply Alembic migrations automatically in local demo mode,
    and ``create_all`` will not alter existing tables. Keep this deliberately
    narrow: it only adds missing columns/indexes used by the current models.
    Postgres still relies on Alembic.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "responses" in tables:
            columns = _columns(inspector, "responses")
            if "content_hash" not in columns:
                conn.execute(text("ALTER TABLE responses ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''"))
            if "prev_hash" not in columns:
                conn.execute(text("ALTER TABLE responses ADD COLUMN prev_hash TEXT"))
            if "chain_index" not in columns:
                conn.execute(text("ALTER TABLE responses ADD COLUMN chain_index INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_responses_chain_index ON responses (chain_index)"))

        if "validation_results" in tables and "confidence" not in _columns(inspector, "validation_results"):
            conn.execute(text("ALTER TABLE validation_results ADD COLUMN confidence FLOAT"))

        if "classification_codes" in tables:
            columns = _columns(inspector, "classification_codes")
            for name, ddl in {
                "family": "TEXT",
                "sector": "TEXT",
                "level": "TEXT",
                "section": "TEXT",
                "parent_code": "TEXT",
            }.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE classification_codes ADD COLUMN {name} {ddl}"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_classification_codes_sector ON classification_codes (sector)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_classification_codes_section ON classification_codes (section)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_classification_codes_parent_code ON classification_codes (parent_code)"))

        if "rag_chunks" not in tables:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id CHAR(36) PRIMARY KEY,
                    bucket VARCHAR(64) NOT NULL,
                    chunk_id VARCHAR(255) NOT NULL,
                    text TEXT NOT NULL,
                    embedding JSON NOT NULL,
                    metadata_json JSON NOT NULL,
                    source_id VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_rag_chunks_bucket_chunk_id UNIQUE (bucket, chunk_id)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_bucket ON rag_chunks (bucket)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_source_id ON rag_chunks (source_id)"))


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}
