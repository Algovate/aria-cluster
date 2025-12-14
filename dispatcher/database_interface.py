"""
Database interface for the dispatcher.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from common.models import Task, Worker, TaskStatus, WorkerStatus, TaskPriority


class DatabaseInterface(ABC):
    """Interface for database implementations."""

    # Task methods
    @abstractmethod
    async def create_task(
        self, 
        url: str, 
        options: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Task:
        """Create a new task."""
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        pass

    @abstractmethod
    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        pass

    @abstractmethod
    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        pass

    @abstractmethod
    async def get_tasks_by_worker(self, worker_id: str) -> List[Task]:
        """Get tasks assigned to a worker."""
        pass

    @abstractmethod
    async def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task."""
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        pass

    # Worker methods
    @abstractmethod
    async def register_worker(
        self,
        hostname: str,
        address: str,
        port: int,
        capabilities: Dict[str, Any] = None,
        total_slots: int = 5
    ) -> Worker:
        """Register a new worker."""
        pass

    @abstractmethod
    async def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        pass

    @abstractmethod
    async def get_all_workers(self) -> List[Worker]:
        """Get all workers."""
        pass

    @abstractmethod
    async def get_workers_by_status(self, status: WorkerStatus) -> List[Worker]:
        """Get workers by status."""
        pass

    @abstractmethod
    async def get_available_workers(self) -> List[Worker]:
        """Get workers with available slots."""
        pass

    @abstractmethod
    async def update_worker(self, worker_id: str, **kwargs) -> Optional[Worker]:
        """Update a worker."""
        pass

    @abstractmethod
    async def update_worker_heartbeat(self, worker_id: str) -> Optional[Worker]:
        """Update a worker's heartbeat timestamp."""
        pass

    @abstractmethod
    async def delete_worker(self, worker_id: str) -> bool:
        """Delete a worker."""
        pass

    # Task assignment methods
    @abstractmethod
    async def assign_task_to_worker(self, task_id: str, worker_id: str) -> bool:
        """Assign a task to a worker."""
        pass

    @abstractmethod
    async def unassign_task_from_worker(self, task_id: str) -> bool:
        """Unassign a task from its worker."""
        pass

    # Statistics methods
    @abstractmethod
    async def get_task_counts_by_status(self) -> Dict[TaskStatus, int]:
        """Get task counts grouped by status."""
        pass

    @abstractmethod
    async def get_worker_counts_by_status(self) -> Dict[WorkerStatus, int]:
        """Get worker counts grouped by status."""
        pass

    @abstractmethod
    async def get_system_load(self) -> float:
        """Calculate the overall system load."""
        pass 