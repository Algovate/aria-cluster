"""
Database factory for the dispatcher.
"""
import logging
import os
from typing import Union, Optional

from .database import MemoryDatabase
from .sqlite_database import SQLiteDatabase
from .database_interface import DatabaseInterface

logger = logging.getLogger(__name__)


class DatabaseType:
    """Database type enum."""
    MEMORY = "memory"
    SQLITE = "sqlite"


def get_database(db_type: str = None, db_path: str = None) -> DatabaseInterface:
    """
    Get a database instance based on the specified type.

    Args:
        db_type: The database type (memory or sqlite)
        db_path: The path to the SQLite database file (only used for SQLite)

    Returns:
        A database instance
    """
    # If db_type is not specified, check environment variable
    if db_type is None:
        db_type = os.environ.get("DISPATCHER_DB_TYPE", DatabaseType.MEMORY)

    # If db_path is not specified, check environment variable
    if db_path is None and db_type == DatabaseType.SQLITE:
        db_path = os.environ.get("DISPATCHER_DB_PATH", "data/dispatcher.db")

    # Create the appropriate database instance
    if db_type == DatabaseType.SQLITE:
        logger.info(f"Using SQLite database at {db_path}")
        return SQLiteDatabase(db_path=db_path)
    else:
        logger.info("Using in-memory database")
        return MemoryDatabase()