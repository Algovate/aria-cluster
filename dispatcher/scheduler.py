"""
Task scheduler for the aria2c cluster.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

from common.models import Task, Worker, TaskStatus, WorkerStatus
from dispatcher.database import MemoryDatabase
from dispatcher.sqlite_database import SQLiteDatabase

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for assigning tasks to workers."""

    def __init__(self, database: Union[MemoryDatabase, SQLiteDatabase], config: Dict[str, Any]):
        """Initialize the scheduler."""
        self.db = database
        self.config = config
        self.running = False
        self.scheduling_lock = asyncio.Lock()

        # Extract configuration
        # The strategy used to select which worker a task should be assigned to.
        # Options:
        #   - "least_loaded": Assigns tasks to workers with the lowest load percentage (default)
        #   - "round_robin": Assigns tasks in sequence, rotating through available workers
        #   - "random": Randomly selects a worker from available ones
        #   - "tags": Matches tasks and workers based on matching key-value tags
        # This strategy directly impacts load balancing and overall cluster efficiency.
        self.task_assignment_strategy = config.get("task_assignment", {}).get("strategy", "least_loaded")
        self.max_retries = config.get("task_assignment", {}).get("max_retries", 3)
        self.retry_delay = config.get("task_assignment", {}).get("retry_delay", 300)

        self.worker_heartbeat_interval = config.get("worker_management", {}).get("heartbeat_interval", 30)
        self.worker_heartbeat_timeout = config.get("worker_management", {}).get("heartbeat_timeout", 90)
        self.auto_remove_offline = config.get("worker_management", {}).get("auto_remove_offline", True)
        self.offline_threshold = config.get("worker_management", {}).get("offline_threshold", 300)

    async def start(self):
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        logger.info("Starting task scheduler")

        # Start background tasks
        asyncio.create_task(self._schedule_pending_tasks())
        asyncio.create_task(self._monitor_workers())
        asyncio.create_task(self._monitor_tasks())

    async def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping task scheduler")

    async def _schedule_pending_tasks(self):
        """Periodically schedule pending tasks."""
        while self.running:
            try:
                async with self.scheduling_lock:
                    await self._process_pending_tasks()
            except Exception as e:
                logger.error(f"Error in task scheduling: {str(e)}")

            # Wait before next scheduling round
            await asyncio.sleep(5)

    async def _process_pending_tasks(self):
        """Process pending tasks and assign them to workers."""
        # Get pending tasks
        pending_tasks = await self.db.get_tasks_by_status(TaskStatus.PENDING)
        if not pending_tasks:
            return

        # Get available workers
        available_workers = await self.db.get_available_workers()
        if not available_workers:
            logger.warning("No available workers for pending tasks")
            return

        logger.info(f"Processing {len(pending_tasks)} pending tasks with {len(available_workers)} available workers")

        # Sort tasks by creation time (oldest first)
        pending_tasks.sort(key=lambda t: t.created_at)

        # Assign tasks to workers
        for task in pending_tasks:
            worker = await self._select_worker_for_task(task, available_workers)
            if not worker:
                logger.warning(f"No suitable worker found for task {task.id}")
                continue

            success = await self.db.assign_task_to_worker(task.id, worker.id)
            if success:
                logger.info(f"Assigned task {task.id} to worker {worker.id}")

                # Update available workers list
                for i, w in enumerate(available_workers):
                    if w.id == worker.id:
                        if w.available_slots <= 1:
                            available_workers.pop(i)
                        else:
                            w.used_slots += 1
                        break
            else:
                logger.error(f"Failed to assign task {task.id} to worker {worker.id}")

    async def _select_worker_for_task(self, task: Task, available_workers: List[Worker]) -> Optional[Worker]:
        """Select the best worker for a task based on the configured strategy."""
        if not available_workers:
            return None

        if self.task_assignment_strategy == "round_robin":
            # Simple round-robin
            return available_workers[0]

        elif self.task_assignment_strategy == "random":
            # Random selection
            import random
            return random.choice(available_workers)

        elif self.task_assignment_strategy == "tags":
            # Tag-based matching
            task_tags = task.options.get("tags", {})

            if not task_tags:
                # If task has no tags, fall back to least loaded strategy
                available_workers.sort(key=lambda w: w.load_percentage)
                return available_workers[0]

            # Find workers with matching tags
            matching_workers = []
            for worker in available_workers:
                worker_tags = worker.capabilities.get("tags", {})

                # Check if all task tags are matched by the worker
                is_match = True
                for key, value in task_tags.items():
                    if key not in worker_tags or worker_tags[key] != value:
                        is_match = False
                        break

                if is_match:
                    matching_workers.append(worker)

            if not matching_workers:
                # No matching workers, use least loaded as fallback
                logger.debug(f"No workers matching tags {task_tags} for task {task.id}")
                available_workers.sort(key=lambda w: w.load_percentage)
                return available_workers[0]

            # Sort matching workers by load
            matching_workers.sort(key=lambda w: w.load_percentage)
            logger.debug(f"Selected worker {matching_workers[0].id} matching tags {task_tags} for task {task.id}")
            return matching_workers[0]

        else:  # Default: "least_loaded"
            # Sort by load and select the least loaded worker
            available_workers.sort(key=lambda w: w.load_percentage)
            return available_workers[0]

    async def _monitor_workers(self):
        """Periodically check worker health and update status."""
        while self.running:
            try:
                await self._check_worker_health()
            except Exception as e:
                logger.error(f"Error in worker monitoring: {str(e)}")

            # Wait before next check
            await asyncio.sleep(self.worker_heartbeat_interval)

    async def _check_worker_health(self):
        """Check worker health and update status."""
        workers = await self.db.get_all_workers()
        now = datetime.now()

        for worker in workers:
            if not worker.last_heartbeat:
                continue

            time_since_heartbeat = (now - worker.last_heartbeat).total_seconds()

            # Mark as offline if heartbeat timeout exceeded
            if worker.status != WorkerStatus.OFFLINE and time_since_heartbeat > self.worker_heartbeat_timeout:
                logger.warning(f"Worker {worker.id} missed heartbeat, marking as offline")
                await self.db.update_worker(worker.id, status=WorkerStatus.OFFLINE)

                # Unassign tasks from this worker
                for task_id in worker.current_tasks:
                    await self.db.unassign_task_from_worker(task_id)
                    await self.db.update_task(task_id, status=TaskStatus.PENDING)

            # Remove worker if it's been offline for too long
            if (self.auto_remove_offline and
                worker.status == WorkerStatus.OFFLINE and
                time_since_heartbeat > self.offline_threshold):
                logger.info(f"Removing offline worker {worker.id}")
                await self.db.delete_worker(worker.id)

    async def _monitor_tasks(self):
        """Periodically check task status and handle retries."""
        while self.running:
            try:
                await self._check_failed_tasks()
            except Exception as e:
                logger.error(f"Error in task monitoring: {str(e)}")

            # Wait before next check
            await asyncio.sleep(60)

    async def _check_failed_tasks(self):
        """Check for failed tasks and retry if needed."""
        failed_tasks = await self.db.get_tasks_by_status(TaskStatus.FAILED)
        now = datetime.now()

        for task in failed_tasks:
            # Skip if no retry is needed
            if not task.options.get("retry_count", 0) < self.max_retries:
                continue

            # Check if retry delay has passed
            time_since_update = (now - task.updated_at).total_seconds()
            if time_since_update < self.retry_delay:
                continue

            # Increment retry count
            retry_count = task.options.get("retry_count", 0) + 1
            options = task.options.copy()
            options["retry_count"] = retry_count

            logger.info(f"Retrying failed task {task.id} (attempt {retry_count})")
            await self.db.update_task(
                task.id,
                status=TaskStatus.PENDING,
                options=options,
                worker_id=None,
                aria2_gid=None,
                error_message=None
            )