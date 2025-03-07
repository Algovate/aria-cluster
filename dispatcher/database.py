"""
In-memory database for the dispatcher.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from common.models import Task, Worker, TaskStatus, WorkerStatus
from common.utils import generate_id

logger = logging.getLogger(__name__)


class MemoryDatabase:
    """Simple in-memory database for the dispatcher."""

    def __init__(self):
        """Initialize the database."""
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}

    # Task methods
    async def create_task(self, url: str, options: Dict[str, Any] = None) -> Task:
        """Create a new task."""
        if options is None:
            options = {}

        task_id = generate_id("task")
        task = Task(
            id=task_id,
            url=url,
            options=options,
            status=TaskStatus.PENDING
        )
        self.tasks[task_id] = task
        logger.info(f"Created task {task_id} for URL {url}")
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())

    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return [task for task in self.tasks.values() if task.status == status]

    async def get_tasks_by_worker(self, worker_id: str) -> List[Task]:
        """Get tasks assigned to a worker."""
        return [task for task in self.tasks.values() if task.worker_id == worker_id]

    async def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now()
        self.tasks[task_id] = task
        logger.debug(f"Updated task {task_id}: {kwargs}")
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
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
        worker = Worker(
            id=worker_id,
            hostname=hostname,
            address=address,
            port=port,
            status=WorkerStatus.ONLINE,
            connected_at=datetime.now(),
            last_heartbeat=datetime.now(),
            capabilities=capabilities,
            total_slots=total_slots,
            used_slots=0,
            current_tasks=[]
        )
        self.workers[worker_id] = worker
        logger.info(f"Registered worker {worker_id} at {address}:{port}")
        return worker

    async def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        return self.workers.get(worker_id)

    async def get_all_workers(self) -> List[Worker]:
        """Get all workers."""
        return list(self.workers.values())

    async def get_workers_by_status(self, status: WorkerStatus) -> List[Worker]:
        """Get workers by status."""
        return [worker for worker in self.workers.values() if worker.status == status]

    async def get_available_workers(self) -> List[Worker]:
        """Get workers with available slots."""
        return [
            worker for worker in self.workers.values()
            if worker.status == WorkerStatus.ONLINE and worker.available_slots > 0
        ]

    async def update_worker(self, worker_id: str, **kwargs) -> Optional[Worker]:
        """Update a worker."""
        worker = self.workers.get(worker_id)
        if not worker:
            return None

        for key, value in kwargs.items():
            if hasattr(worker, key):
                setattr(worker, key, value)

        self.workers[worker_id] = worker
        logger.debug(f"Updated worker {worker_id}: {kwargs}")
        return worker

    async def update_worker_heartbeat(self, worker_id: str) -> Optional[Worker]:
        """Update a worker's heartbeat timestamp."""
        worker = self.workers.get(worker_id)
        if not worker:
            return None

        worker.last_heartbeat = datetime.now()
        if worker.status == WorkerStatus.OFFLINE:
            worker.status = WorkerStatus.ONLINE
            logger.info(f"Worker {worker_id} is back online")

        self.workers[worker_id] = worker
        return worker

    async def delete_worker(self, worker_id: str) -> bool:
        """Delete a worker."""
        if worker_id in self.workers:
            del self.workers[worker_id]
            logger.info(f"Deleted worker {worker_id}")
            return True
        return False

    # Task assignment methods
    async def assign_task_to_worker(self, task_id: str, worker_id: str) -> bool:
        """Assign a task to a worker."""
        task = self.tasks.get(task_id)
        worker = self.workers.get(worker_id)

        if not task or not worker:
            return False

        if worker.used_slots >= worker.total_slots:
            logger.warning(f"Worker {worker_id} has no available slots")
            return False

        # Update task
        task.worker_id = worker_id
        task.status = TaskStatus.QUEUED
        task.updated_at = datetime.now()
        self.tasks[task_id] = task

        # Update worker
        worker.current_tasks.append(task_id)
        worker.used_slots += 1
        if worker.used_slots >= worker.total_slots:
            worker.status = WorkerStatus.BUSY
        self.workers[worker_id] = worker

        logger.info(f"Assigned task {task_id} to worker {worker_id}")
        return True

    async def unassign_task_from_worker(self, task_id: str) -> bool:
        """Unassign a task from its worker."""
        task = self.tasks.get(task_id)
        if not task or not task.worker_id:
            return False

        worker_id = task.worker_id
        worker = self.workers.get(worker_id)
        if not worker:
            # Just update the task if the worker doesn't exist
            task.worker_id = None
            task.updated_at = datetime.now()
            self.tasks[task_id] = task
            return True

        # Update task
        task.worker_id = None
        task.updated_at = datetime.now()
        self.tasks[task_id] = task

        # Update worker
        if task_id in worker.current_tasks:
            worker.current_tasks.remove(task_id)
        worker.used_slots = max(0, worker.used_slots - 1)
        if worker.status == WorkerStatus.BUSY and worker.used_slots < worker.total_slots:
            worker.status = WorkerStatus.ONLINE
        self.workers[worker_id] = worker

        logger.info(f"Unassigned task {task_id} from worker {worker_id}")
        return True

    # Statistics methods
    async def get_task_counts_by_status(self) -> Dict[TaskStatus, int]:
        """Get task counts grouped by status."""
        counts = {status: 0 for status in TaskStatus}
        for task in self.tasks.values():
            counts[task.status] += 1
        return counts

    async def get_worker_counts_by_status(self) -> Dict[WorkerStatus, int]:
        """Get worker counts grouped by status."""
        counts = {status: 0 for status in WorkerStatus}
        for worker in self.workers.values():
            counts[worker.status] += 1
        return counts

    async def get_system_load(self) -> float:
        """Calculate the overall system load."""
        total_slots = sum(worker.total_slots for worker in self.workers.values())
        used_slots = sum(worker.used_slots for worker in self.workers.values())

        if total_slots == 0:
            return 0.0

        return (used_slots / total_slots) * 100.0