# Database Configuration

The Aria Cluster Dispatcher supports multiple database backends for storing tasks and worker information. This document explains the available options and how to configure them.

## Available Database Backends

### 1. In-Memory Database

The in-memory database is the default option. It stores all data in memory, which means that all data is lost when the dispatcher is restarted.

**Pros:**
- Fast performance
- No external dependencies
- Simple setup

**Cons:**
- No persistence (data is lost on restart)
- Not suitable for production environments where data persistence is required

### 2. SQLite Database

The SQLite database provides persistent storage using SQLite. This allows data to be preserved across restarts.

**Pros:**
- Data persistence across restarts
- No need for external database servers
- Good performance for small to medium workloads
- File-based storage that's easy to back up

**Cons:**
- Not as fast as in-memory database
- Not suitable for high-concurrency environments
- Limited scalability

## Configuration

You can configure the database backend in two ways:

### 1. Using Environment Variables

Set the following environment variables:

```bash
# To use SQLite database
export DISPATCHER_DB_TYPE=sqlite
export DISPATCHER_DB_PATH=/path/to/your/database.db

# To use in-memory database (default)
export DISPATCHER_DB_TYPE=memory
```

### 2. Using Configuration File

Edit the `config/dispatcher.json` file:

```json
{
    "database": {
        "type": "sqlite",  // or "memory"
        "path": "data/dispatcher.db"
    }
}
```

## Database Schema

Both database implementations use the same data models:

- **Tasks**: Download tasks with their status, progress, and assignment information
- **Workers**: Worker nodes with their status, capabilities, and current workload

The SQLite implementation stores complex data types (like dictionaries and lists) as JSON strings in the database.

## Backup and Recovery (SQLite)

To backup the SQLite database:

```bash
# Simple file copy
cp data/dispatcher.db data/dispatcher.db.backup

# Using sqlite3 tools for a consistent backup
sqlite3 data/dispatcher.db .dump > dispatcher_backup.sql
```

To restore from a backup:

```bash
# Simple file copy
cp data/dispatcher.db.backup data/dispatcher.db

# Using sqlite3 tools
sqlite3 data/dispatcher.db < dispatcher_backup.sql
```

## Migrating Between Database Types

The system includes a migration utility to help transfer data between different database types.

### Using the Migration Script

The easiest way to migrate data is to use the provided script:

```bash
# Migrate from memory to SQLite
python scripts/migrate_database.py --source memory --target sqlite

# Migrate from SQLite to memory
python scripts/migrate_database.py --source sqlite --target memory

# Specify a custom SQLite database path
python scripts/migrate_database.py --source memory --target sqlite --sqlite-path /path/to/database.db

# Enable verbose logging
python scripts/migrate_database.py --source memory --target sqlite -v
```

### Using the Migration API

You can also use the migration utility programmatically:

```python
from dispatcher.database_factory import get_database, DatabaseType
from dispatcher.database_migration import migrate_memory_to_sqlite, migrate_sqlite_to_memory

# Create database instances
memory_db = get_database(DatabaseType.MEMORY)
sqlite_db = get_database(DatabaseType.SQLITE, "data/dispatcher.db")

# Migrate from memory to SQLite
async def migrate_to_sqlite():
    stats = await migrate_memory_to_sqlite(memory_db, sqlite_db)
    print(f"Migration completed: {stats['tasks_migrated']} tasks, {stats['workers_migrated']} workers")

# Migrate from SQLite to memory
async def migrate_to_memory():
    stats = await migrate_sqlite_to_memory(sqlite_db, memory_db)
    print(f"Migration completed: {stats['tasks_migrated']} tasks, {stats['workers_migrated']} workers")
```

The migration utility handles:
- Transferring all tasks with their properties
- Transferring all workers with their properties
- Maintaining relationships between tasks and workers
- Providing statistics about the migration process

## Performance Considerations

- The in-memory database is faster but doesn't persist data
- The SQLite database provides persistence but may be slower for high-volume operations
- For production environments with high concurrency needs, consider implementing a more robust database backend like PostgreSQL (not currently available) 