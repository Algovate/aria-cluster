"""
SQLite database for the dispatcher.
"""
import json
import logging
import sqlite3
# aiosqlite is added to requirements.txt for async SQLite operations
import aiosqlite
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from common.models import Task, Worker, TaskStatus, WorkerStatus, TaskPriority
from common.utils import generate_id
from dispatcher.database_interface import DatabaseInterface

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseInterface):
    """SQLite database for the dispatcher."""

    def __init__(self, db_path: str = "data/dispatcher.db"):
        """Initialize the database."""
        self.db_path = db_path
        self._ensure_dir_exists()
        self._create_tables()

    def _ensure_dir_exists(self):
        """Ensure the directory for the database exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _create_tables(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create tasks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                worker_id TEXT,
                aria2_gid TEXT,
                options TEXT,
                progress REAL DEFAULT 0.0,
                download_speed INTEGER,
                error_message TEXT,
                result TEXT
            )
            ''')

            # Create workers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                address TEXT NOT NULL,
                port INTEGER NOT NULL,
                status TEXT NOT NULL,
                connected_at TEXT,
                last_heartbeat TEXT,
                capabilities TEXT,
                current_tasks TEXT,
                total_slots INTEGER DEFAULT 5,
                used_slots INTEGER DEFAULT 0,
                health_metrics TEXT,
                error_history TEXT,
                performance_stats TEXT
            )
            ''')

            conn.commit()
            logger.info(f"Database tables created at {self.db_path}")

    def _task_from_row(self, row) -> Task:
        """Convert a database row to a Task object."""
        options_json = row['options']
        result_json = row['result']
        
        options = json.loads(options_json) if options_json else {}
        result = json.loads(result_json) if result_json else None
        
        return Task(
            id=row['id'],
            url=row['url'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            status=TaskStatus(row['status']),
            priority=TaskPriority(int(row['priority'])),
            worker_id=row['worker_id'],
            aria2_gid=row['aria2_gid'],
            options=options,
            progress=float(row['progress']),
            download_speed=row['download_speed'],
            error_message=row['error_message'],
            result=result
        )

    def _worker_from_row(self, row) -> Worker:
        """Convert a database row to a Worker object."""
        capabilities_json = row['capabilities']
        current_tasks_json = row['current_tasks']
        health_metrics_json = row['health_metrics']
        error_history_json = row['error_history']
        performance_stats_json = row['performance_stats']
        
        capabilities = json.loads(capabilities_json) if capabilities_json else {}
        current_tasks = json.loads(current_tasks_json) if current_tasks_json else []
        health_metrics = json.loads(health_metrics_json) if health_metrics_json else {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_rx": 0,
            "network_tx": 0,
            "error_count": 0,
            "success_count": 0,
            "uptime": 0
        }
        error_history = json.loads(error_history_json) if error_history_json else []
        performance_stats = json.loads(performance_stats_json) if performance_stats_json else {
            "avg_download_speed": 0,
            "peak_download_speed": 0,
            "total_bytes_downloaded": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
        
        return Worker(
            id=row['id'],
            hostname=row['hostname'],
            address=row['address'],
            port=int(row['port']),
            status=WorkerStatus(row['status']),
            connected_at=datetime.fromisoformat(row['connected_at']) if row['connected_at'] else None,
            last_heartbeat=datetime.fromisoformat(row['last_heartbeat']) if row['last_heartbeat'] else None,
            capabilities=capabilities,
            current_tasks=current_tasks,
            total_slots=int(row['total_slots']),
            used_slots=int(row['used_slots']),
            health_metrics=health_metrics,
            error_history=error_history,
            performance_stats=performance_stats
        )

    # Task methods
    async def create_task(
        self, 
        url: str, 
        options: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Task:
        """Create a new task."""
        if options is None:
            options = {}

        task_id = generate_id("task")
        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''
                INSERT INTO tasks (
                    id, url, created_at, updated_at, status, priority,
                    options, progress
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id, url, now, now, TaskStatus.PENDING.value,
                    priority.value,
                    json.dumps(options), 0.0
                )
            )
            await db.commit()

        logger.info(f"Created task {task_id} for URL {url} with priority {priority.name}")

        task = Task(
            id=task_id,
            url=url,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            status=TaskStatus.PENDING,
            priority=priority,
            options=options,
            progress=0.0
        )

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = await cursor.fetchone()

            if not row:
                return None

            return self._task_from_row(row)

    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        tasks = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM tasks')
            rows = await cursor.fetchall()

            for row in rows:
                tasks.append(self._task_from_row(row))

        return tasks

    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        tasks = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM tasks WHERE status = ?', (status.value,))
            rows = await cursor.fetchall()

            for row in rows:
                tasks.append(self._task_from_row(row))

        return tasks

    async def get_tasks_by_worker(self, worker_id: str) -> List[Task]:
        """Get tasks assigned to a worker."""
        tasks = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM tasks WHERE worker_id = ?', (worker_id,))
            rows = await cursor.fetchall()

            for row in rows:
                tasks.append(self._task_from_row(row))

        return tasks

    async def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task."""
        # First check if the task exists
        task = await self.get_task(task_id)
        if not task:
            return None

        # Prepare update fields
        update_fields = []
        update_values = []

        for key, value in kwargs.items():
            if hasattr(task, key):
                if key == 'options' or key == 'result':
                    update_fields.append(f"{key} = ?")
                    update_values.append(json.dumps(value))
                elif key == 'status':
                    update_fields.append(f"{key} = ?")
                    update_values.append(value.value)
                elif key == 'priority':
                    update_fields.append(f"{key} = ?")
                    update_values.append(value.value if hasattr(value, 'value') else value)
                else:
                    update_fields.append(f"{key} = ?")
                    update_values.append(value)

        # Always update the updated_at timestamp
        now = datetime.now().isoformat()
        update_fields.append("updated_at = ?")
        update_values.append(now)

        # Add task_id to values
        update_values.append(task_id)

        # Execute update
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f'''
                UPDATE tasks
                SET {", ".join(update_fields)}
                WHERE id = ?
                ''',
                tuple(update_values)
            )
            await db.commit()

        logger.debug(f"Updated task {task_id}: {kwargs}")

        # Get the updated task
        return await self.get_task(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            await db.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted task {task_id}")
                return True
            return False

    # Worker methods
    async def register_worker(
        self,
        hostname: str,
        address: str,
        port: int,
        capabilities: Dict[str, Any] = None,
        total_slots: int = 5
    ) -> Worker:
        """Register a new worker."""
        if capabilities is None:
            capabilities = {}

        worker_id = generate_id("worker")
        now = datetime.now().isoformat()

        # Default values for complex fields
        health_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_rx": 0,
            "network_tx": 0,
            "error_count": 0,
            "success_count": 0,
            "uptime": 0
        }

        performance_stats = {
            "avg_download_speed": 0,
            "peak_download_speed": 0,
            "total_bytes_downloaded": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''
                INSERT INTO workers (
                    id, hostname, address, port, status, connected_at, last_heartbeat,
                    capabilities, current_tasks, total_slots, used_slots,
                    health_metrics, error_history, performance_stats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    worker_id, hostname, address, port, WorkerStatus.ONLINE.value,
                    now, now, json.dumps(capabilities), json.dumps([]),
                    total_slots, 0, json.dumps(health_metrics),
                    json.dumps([]), json.dumps(performance_stats)
                )
            )
            await db.commit()

        logger.info(f"Registered worker {worker_id} at {address}:{port}")

        worker = Worker(
            id=worker_id,
            hostname=hostname,
            address=address,
            port=port,
            status=WorkerStatus.ONLINE,
            connected_at=datetime.fromisoformat(now),
            last_heartbeat=datetime.fromisoformat(now),
            capabilities=capabilities,
            total_slots=total_slots,
            used_slots=0,
            current_tasks=[]
        )

        return worker

    async def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM workers WHERE id = ?', (worker_id,))
            row = await cursor.fetchone()

            if not row:
                return None

            return self._worker_from_row(row)

    async def get_all_workers(self) -> List[Worker]:
        """Get all workers."""
        workers = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM workers')
            rows = await cursor.fetchall()

            for row in rows:
                workers.append(self._worker_from_row(row))

        return workers

    async def get_workers_by_status(self, status: WorkerStatus) -> List[Worker]:
        """Get workers by status."""
        workers = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('SELECT * FROM workers WHERE status = ?', (status.value,))
            rows = await cursor.fetchall()

            for row in rows:
                workers.append(self._worker_from_row(row))

        return workers

    async def get_available_workers(self) -> List[Worker]:
        """Get workers with available slots."""
        workers = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                '''
                SELECT * FROM workers
                WHERE status = ? AND used_slots < total_slots
                ''',
                (WorkerStatus.ONLINE.value,)
            )
            rows = await cursor.fetchall()

            for row in rows:
                workers.append(self._worker_from_row(row))

        return workers

    async def update_worker(self, worker_id: str, **kwargs) -> Optional[Worker]:
        """Update a worker."""
        # First check if the worker exists
        worker = await self.get_worker(worker_id)
        if not worker:
            return None

        # Prepare update fields
        update_fields = []
        update_values = []

        for key, value in kwargs.items():
            if hasattr(worker, key):
                if key in ['capabilities', 'health_metrics', 'error_history', 'performance_stats']:
                    update_fields.append(f"{key} = ?")
                    update_values.append(json.dumps(value))
                elif key == 'current_tasks':
                    update_fields.append(f"{key} = ?")
                    update_values.append(json.dumps(value))
                elif key == 'status':
                    update_fields.append(f"{key} = ?")
                    update_values.append(value.value)
                else:
                    update_fields.append(f"{key} = ?")
                    update_values.append(value)

        # Add worker_id to values
        update_values.append(worker_id)

        # Execute update
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f'''
                UPDATE workers
                SET {", ".join(update_fields)}
                WHERE id = ?
                ''',
                tuple(update_values)
            )
            await db.commit()

        logger.debug(f"Updated worker {worker_id}: {kwargs}")

        # Get the updated worker
        return await self.get_worker(worker_id)

    async def update_worker_heartbeat(self, worker_id: str) -> Optional[Worker]:
        """Update a worker's heartbeat timestamp."""
        worker = await self.get_worker(worker_id)
        if not worker:
            return None

        now = datetime.now().isoformat()
        status_update = ""
        params = [now, worker_id]

        if worker.status == WorkerStatus.OFFLINE:
            status_update = ", status = ?"
            params.insert(1, WorkerStatus.ONLINE.value)
            logger.info(f"Worker {worker_id} is back online")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f'UPDATE workers SET last_heartbeat = ?{status_update} WHERE id = ?',
                tuple(params)
            )
            await db.commit()

        return await self.get_worker(worker_id)

    async def delete_worker(self, worker_id: str) -> bool:
        """Delete a worker."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('DELETE FROM workers WHERE id = ?', (worker_id,))
            await db.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted worker {worker_id}")
                return True
            return False

    # Task assignment methods
    async def assign_task_to_worker(self, task_id: str, worker_id: str) -> bool:
        """Assign a task to a worker."""
        task = await self.get_task(task_id)
        worker = await self.get_worker(worker_id)

        if not task or not worker:
            return False

        if worker.used_slots >= worker.total_slots:
            logger.warning(f"Worker {worker_id} has no available slots")
            return False

        async with aiosqlite.connect(self.db_path) as db:
            # Start a transaction
            await db.execute('BEGIN TRANSACTION')

            try:
                # Update task
                now = datetime.now().isoformat()
                await db.execute(
                    '''
                    UPDATE tasks
                    SET worker_id = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    ''',
                    (worker_id, TaskStatus.QUEUED.value, now, task_id)
                )

                # Update worker
                current_tasks = worker.current_tasks.copy()
                current_tasks.append(task_id)
                used_slots = worker.used_slots + 1
                status = WorkerStatus.BUSY.value if used_slots >= worker.total_slots else worker.status.value

                await db.execute(
                    '''
                    UPDATE workers
                    SET current_tasks = ?, used_slots = ?, status = ?
                    WHERE id = ?
                    ''',
                    (json.dumps(current_tasks), used_slots, status, worker_id)
                )

                # Commit the transaction
                await db.commit()
                logger.info(f"Assigned task {task_id} to worker {worker_id}")
                return True

            except Exception as e:
                # Rollback in case of error
                await db.execute('ROLLBACK')
                logger.error(f"Error assigning task {task_id} to worker {worker_id}: {str(e)}")
                return False

    async def unassign_task_from_worker(self, task_id: str) -> bool:
        """Unassign a task from its worker."""
        task = await self.get_task(task_id)
        if not task or not task.worker_id:
            return False

        worker_id = task.worker_id
        worker = await self.get_worker(worker_id)

        async with aiosqlite.connect(self.db_path) as db:
            # Start a transaction
            await db.execute('BEGIN TRANSACTION')

            try:
                # Update task
                now = datetime.now().isoformat()
                await db.execute(
                    '''
                    UPDATE tasks
                    SET worker_id = NULL, updated_at = ?
                    WHERE id = ?
                    ''',
                    (now, task_id)
                )

                # Update worker if it exists
                if worker:
                    current_tasks = worker.current_tasks.copy()
                    if task_id in current_tasks:
                        current_tasks.remove(task_id)

                    used_slots = max(0, worker.used_slots - 1)
                    status = worker.status.value
                    if status == WorkerStatus.BUSY.value and used_slots < worker.total_slots:
                        status = WorkerStatus.ONLINE.value

                    await db.execute(
                        '''
                        UPDATE workers
                        SET current_tasks = ?, used_slots = ?, status = ?
                        WHERE id = ?
                        ''',
                        (json.dumps(current_tasks), used_slots, status, worker_id)
                    )

                # Commit the transaction
                await db.commit()
                logger.info(f"Unassigned task {task_id} from worker {worker_id}")
                return True

            except Exception as e:
                # Rollback in case of error
                await db.execute('ROLLBACK')
                logger.error(f"Error unassigning task {task_id}: {str(e)}")
                return False

    # Statistics methods
    async def get_task_counts_by_status(self) -> Dict[TaskStatus, int]:
        """Get task counts grouped by status."""
        counts = {status: 0 for status in TaskStatus}

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
                '''
            )
            rows = await cursor.fetchall()

            for status_str, count in rows:
                try:
                    status = TaskStatus(status_str)
                    counts[status] = count
                except ValueError:
                    logger.warning(f"Unknown task status in database: {status_str}")

        return counts

    async def get_worker_counts_by_status(self) -> Dict[WorkerStatus, int]:
        """Get worker counts grouped by status."""
        counts = {status: 0 for status in WorkerStatus}

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''
                SELECT status, COUNT(*) as count
                FROM workers
                GROUP BY status
                '''
            )
            rows = await cursor.fetchall()

            for status_str, count in rows:
                try:
                    status = WorkerStatus(status_str)
                    counts[status] = count
                except ValueError:
                    logger.warning(f"Unknown worker status in database: {status_str}")

        return counts

    async def get_system_load(self) -> float:
        """Calculate the overall system load."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''
                SELECT SUM(total_slots) as total, SUM(used_slots) as used
                FROM workers
                '''
            )
            row = await cursor.fetchone()

            if not row or row[0] is None or row[0] == 0:
                return 0.0

            total_slots, used_slots = row
            return (used_slots / total_slots) * 100.0