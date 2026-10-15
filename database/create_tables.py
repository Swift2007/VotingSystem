"""Run once from the backend/ folder:  python create_tables.py"""
from app.database import Base, engine
import app.models  # noqa: F401  (registers all tables)

Base.metadata.create_all(engine)
print("Tables created:", ", ".join(Base.metadata.tables))
