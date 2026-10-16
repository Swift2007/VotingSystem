"""Database connection, session factory and append-only protections.

* `configure(url)` (re)binds the engine. The app factory calls it at startup,
  and tests call it with a temporary SQLite file.
* `init_db()` creates every table, then installs SQLite triggers that make
  the vote tables append-only. Even someone with SQL access through the app
  cannot UPDATE or DELETE a ballot, a voter-status row, a receipt or a chain
  block (README §4 Integrity: "Admins have no edit/delete vote function").
* `get_db()` is the FastAPI dependency: one session per request.

SQLite notes
------------
Every transaction starts with `BEGIN IMMEDIATE`, which takes the write lock
up front. With the default deferred mode, two concurrent vote requests can
both read, then both try to write, and one fails with SQLITE_BUSY
instead of waiting. IMMEDIATE + `busy_timeout` makes them queue safely. That
matters for README critical requirement 1 (concurrent submissions).
"""
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal = sessionmaker(expire_on_commit=False)

# Tables that may only ever be INSERTed into.
APPEND_ONLY_TABLES = (
    "ballots",
    "voter_status",
    "receipts",
    "chain_blocks",
    "block_transactions",
    "audit_log",
)


def configure(database_url: str) -> Engine:
    """Create the engine for `database_url` and bind the session factory to it."""
    global engine
    if engine is not None:
        engine.dispose()

    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args)

    if is_sqlite:
        _install_sqlite_hooks(engine)

    SessionLocal.configure(bind=engine)
    return engine


def _install_sqlite_hooks(eng: Engine) -> None:
    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn, _record):
        # Hand transaction control to SQLAlchemy so our BEGIN below is used
        # (pysqlite would otherwise issue its own deferred BEGIN).
        dbapi_conn.isolation_level = None
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")   # SQLite ignores FKs without this
        cur.execute("PRAGMA journal_mode = WAL")  # readers don't block the writer
        cur.execute("PRAGMA busy_timeout = 30000")
        cur.close()

    @event.listens_for(eng, "begin")
    def _on_begin(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")


def init_db() -> None:
    """Create all tables (idempotent) and the append-only triggers."""
    import app.models  # noqa: F401  (registers every table on Base.metadata)

    if engine is None:
        raise RuntimeError("database.configure() must be called first")

    Base.metadata.create_all(engine)

    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            for table in APPEND_ONLY_TABLES:
                for op in ("UPDATE", "DELETE"):
                    conn.execute(text(
                        f"CREATE TRIGGER IF NOT EXISTS trg_{table}_no_{op.lower()} "
                        f"BEFORE {op} ON {table} "
                        f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"
                    ))


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
