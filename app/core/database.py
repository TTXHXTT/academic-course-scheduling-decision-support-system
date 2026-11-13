"""
Database session management.
Supports both SQLite (development) and PostgreSQL (Docker/production).
Implements AC-02 (clean-state initialization).
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from .config import settings


class Base(DeclarativeBase):
    pass


def _get_engine_kwargs(database_url: str) -> dict:
    """Build engine kwargs appropriate for the database backend."""
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


engine = create_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs(settings.DATABASE_URL),
    echo=settings.DEBUG,
)

# Enable WAL mode for SQLite for better concurrency
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize all tables. Used for development and testing."""
    # Import all models so Base knows about them
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit, student_schedule  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Safe lightweight schema alignment for existing SQLite databases
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                result = conn.exec_driver_sql("PRAGMA table_info(recommendations)")
                existing_cols = {row[1] for row in result.fetchall()}
                if existing_cols:
                    if "action_status" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE recommendations ADD COLUMN action_status VARCHAR(50) DEFAULT 'PENDING'")
                    if "decision_notes" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE recommendations ADD COLUMN decision_notes TEXT")
                    if "reviewed_by_id" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE recommendations ADD COLUMN reviewed_by_id INTEGER")
                    if "reviewed_at" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE recommendations ADD COLUMN reviewed_at TIMESTAMP")
                    conn.commit()
        except Exception:
            pass
