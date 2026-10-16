"""Create all tables + append-only triggers without starting the server.

Run from backend/:  python -m scripts.create_tables
(The server also does this automatically at startup.)
"""
from app import database
from app.config import settings
from pathlib import Path

if settings.database_url.startswith("sqlite:///"):
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
database.configure(settings.database_url)
database.init_db()
print("Tables created:", ", ".join(sorted(database.Base.metadata.tables)))
