"""Database connection. Change DATABASE_URL in .env to switch SQLite -> Supabase."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite now:   sqlite:///./voting.db
# Supabase later: postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./voting.db")

engine = create_engine(DATABASE_URL)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def sqlite_settings(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")   # SQLite ignores FKs without this
        cur.execute("PRAGMA journal_mode = WAL")  # readers don't block the writer
        cur.close()

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
