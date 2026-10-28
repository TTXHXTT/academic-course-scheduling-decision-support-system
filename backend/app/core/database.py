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
    return {}


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
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit  # noqa: F401
    Base.metadata.create_all(bind=engine)
