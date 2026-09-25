"""Database connection management for AgentRedTeam.

Uses psycopg3 (the modern PostgreSQL driver for Python).
Connection strings come from the DATABASE_URL environment variable.

Usage:
    from app.db.connection import get_connection

    with get_connection() as conn:
        conn.execute("SELECT 1")
"""
import logging
import os
from contextlib import contextmanager
from typing import Generator

import psycopg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get the database URL from the environment.

    Raises EnvironmentError if DATABASE_URL is not set.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL is not set. "
            "Add it to your .env file. "
            "See .env.example for the format."
        )
    return url


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """Context manager that provides a database connection.

    Automatically commits on success and rolls back on error.
    Always closes the connection when done.

    Usage:
        with get_connection() as conn:
            conn.execute("INSERT INTO ...")
            # commits automatically on exit
    """
    url = get_database_url()
    conn = None
    try:
        conn = psycopg.connect(url)
        logger.debug("Database connection opened")
        yield conn
        conn.commit()
        logger.debug("Transaction committed")
    except Exception as e:
        if conn:
            conn.rollback()
            logger.warning("Transaction rolled back due to error: %s", e)
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


def create_tables() -> None:
    """Create all tables from schema.sql if they don't exist.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS.
    """
    schema_path = os.path.join(
        os.path.dirname(__file__), "schema.sql"
    )

    with open(schema_path) as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.execute(schema_sql)

    logger.info("Database tables created (or already exist)")


def test_connection() -> dict:
    """Verify the database connection works and return server info."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT version(), current_database(), NOW()"
        ).fetchone()

    return {
        "version": row[0].split(" on ")[0],  # just "PostgreSQL 16.x"
        "database": row[1],
        "server_time": row[2].isoformat(),
        "status": "connected",
    }
