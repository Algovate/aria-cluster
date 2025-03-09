#!/usr/bin/env python3
"""
Script to migrate data between database types.
"""
import os
import sys
import logging
import asyncio
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dispatcher.database_factory import get_database, DatabaseType
from dispatcher.database_migration import migrate_memory_to_sqlite, migrate_sqlite_to_memory


async def main():
    """Run the database migration."""
    parser = argparse.ArgumentParser(description='Migrate data between database types')
    parser.add_argument('--source', choices=['memory', 'sqlite'], required=True,
                        help='Source database type')
    parser.add_argument('--target', choices=['memory', 'sqlite'], required=True,
                        help='Target database type')
    parser.add_argument('--sqlite-path', default='data/dispatcher.db',
                        help='Path to SQLite database file (default: data/dispatcher.db)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Validate arguments
    if args.source == args.target:
        logger.error("Source and target database types must be different")
        return 1

    # Create database instances
    source_db = get_database(
        args.source,
        args.sqlite_path if args.source == 'sqlite' else None
    )
    target_db = get_database(
        args.target,
        args.sqlite_path if args.target == 'sqlite' else None
    )

    # Perform migration
    try:
        if args.source == 'memory' and args.target == 'sqlite':
            stats = await migrate_memory_to_sqlite(source_db, target_db)
        else:
            stats = await migrate_sqlite_to_memory(source_db, target_db)

        logger.info(f"Migration completed successfully:")
        logger.info(f"  - Tasks migrated: {stats['tasks_migrated']}")
        logger.info(f"  - Workers migrated: {stats['workers_migrated']}")
        logger.info(f"  - Errors: {stats['errors']}")

        return 0
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)