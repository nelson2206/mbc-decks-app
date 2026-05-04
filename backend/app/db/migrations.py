"""Schema migrations idempotentes (mientras no usamos Alembic).

Cada función agrega una columna si no existe. Se ejecuta en el startup.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


def add_column_if_missing(engine: Engine, table: str, column: str, ddl: str):
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{table}' AND column_name = '{column}'
        """))
        exists = result.fetchone() is not None
        if not exists:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            conn.commit()
            logger.info(f"Added column {table}.{column}")


def run_migrations(engine: Engine):
    add_column_if_missing(engine, "decks", "progress_step", "VARCHAR(50) DEFAULT ''")
    add_column_if_missing(engine, "decks", "progress_percentage", "INTEGER DEFAULT 0")
    add_column_if_missing(engine, "decks", "last_error", "TEXT DEFAULT ''")
