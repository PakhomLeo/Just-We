"""Helpers for initializing a fresh production database."""

from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.database import close_db, get_engine
from app.models import Base


ALEMBIC_VERSION_TABLE = "alembic_version"


def _get_head_revision() -> str:
    """Return the single Alembic head revision for the repository."""
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one Alembic head, found: {heads}")
    return heads[0]


async def initialize_empty_database() -> None:
    """Create the current schema and stamp Alembic on a completely empty DB.

    The historical migration chain starts from an already-existing legacy schema.
    For first-time Docker installs there are no legacy tables, so we materialize
    the current SQLAlchemy metadata and mark the database at the current Alembic
    head. Non-empty databases are left for normal Alembic migrations.
    """
    engine = get_engine()
    async with engine.begin() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: set(inspect(sync_connection).get_table_names())
        )
        app_tables = table_names - {ALEMBIC_VERSION_TABLE}
        if app_tables:
            return

        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
                """
            )
        )
        await connection.execute(text("DELETE FROM alembic_version"))
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": _get_head_revision()},
        )
        print("Initialized an empty database from SQLAlchemy metadata.")

    await close_db()
