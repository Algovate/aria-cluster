"""
Utilities for migrating data between database implementations.
"""
import logging
from typing import Dict, Any

from dispatcher.database_interface import DatabaseInterface

logger = logging.getLogger(__name__)


async def migrate_data(source_db: DatabaseInterface, target_db: DatabaseInterface) -> Dict[str, Any]:
    """
    Migrate all data from one database implementation to another.
    
    Args:
        source_db: The source database to migrate from
        target_db: The target database to migrate to
        
    Returns:
        A dictionary with migration statistics
    """
    stats = {
        "tasks_migrated": 0,
        "workers_migrated": 0,
        "errors": 0
    }
    
    # Migrate tasks
    logger.info("Migrating tasks...")
    tasks = await source_db.get_all_tasks()
    
    for task in tasks:
        try:
            # Create the task in the target database
            new_task = await target_db.create_task(
                url=task.url,
                options=task.options
            )
            
            # Update the task with all properties
            await target_db.update_task(
                new_task.id,
                status=task.status,
                priority=task.priority,
                worker_id=task.worker_id,
                aria2_gid=task.aria2_gid,
                progress=task.progress,
                download_speed=task.download_speed,
                error_message=task.error_message,
                result=task.result
            )
            
            stats["tasks_migrated"] += 1
        except Exception as e:
            logger.error(f"Error migrating task {task.id}: {str(e)}")
            stats["errors"] += 1
    
    # Migrate workers
    logger.info("Migrating workers...")
    workers = await source_db.get_all_workers()
    
    for worker in workers:
        try:
            # Register the worker in the target database
            new_worker = await target_db.register_worker(
                hostname=worker.hostname,
                address=worker.address,
                port=worker.port,
                capabilities=worker.capabilities,
                total_slots=worker.total_slots
            )
            
            # Update the worker with all properties
            await target_db.update_worker(
                new_worker.id,
                status=worker.status,
                connected_at=worker.connected_at,
                last_heartbeat=worker.last_heartbeat,
                current_tasks=worker.current_tasks,
                used_slots=worker.used_slots,
                health_metrics=worker.health_metrics,
                error_history=worker.error_history,
                performance_stats=worker.performance_stats
            )
            
            stats["workers_migrated"] += 1
        except Exception as e:
            logger.error(f"Error migrating worker {worker.id}: {str(e)}")
            stats["errors"] += 1
    
    # Log migration summary
    logger.info(f"Migration completed: {stats['tasks_migrated']} tasks, "
                f"{stats['workers_migrated']} workers, {stats['errors']} errors")
    
    return stats


async def migrate_memory_to_sqlite(memory_db: DatabaseInterface, sqlite_db: DatabaseInterface) -> Dict[str, Any]:
    """
    Migrate data from memory database to SQLite database.
    
    Args:
        memory_db: The memory database to migrate from
        sqlite_db: The SQLite database to migrate to
        
    Returns:
        A dictionary with migration statistics
    """
    logger.info("Migrating from memory database to SQLite database...")
    return await migrate_data(memory_db, sqlite_db)


async def migrate_sqlite_to_memory(sqlite_db: DatabaseInterface, memory_db: DatabaseInterface) -> Dict[str, Any]:
    """
    Migrate data from SQLite database to memory database.
    
    Args:
        sqlite_db: The SQLite database to migrate from
        memory_db: The memory database to migrate to
        
    Returns:
        A dictionary with migration statistics
    """
    logger.info("Migrating from SQLite database to memory database...")
    return await migrate_data(sqlite_db, memory_db) 