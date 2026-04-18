"""Command entrypoint for fresh database initialization."""

from __future__ import annotations

import asyncio

from app.utils.db_bootstrap import initialize_empty_database


def main() -> None:
    """Initialize a completely empty database for first-time deployments."""
    asyncio.run(initialize_empty_database())


if __name__ == "__main__":
    main()
