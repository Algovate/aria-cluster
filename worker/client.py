"""
Worker client for the aria2c cluster.
"""
import os
import json
import logging
import asyncio
import socket
import platform
from typing import Dict, List, Any, Optional
from datetime import datetime

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

from common.models import Task, TaskStatus
from common.utils import load_config, generate_id
from worker.aria2c import Aria2cClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerClient:
    """Client for a worker node in the aria2c cluster."""

    def __init__(self, config_path: str = "config/worker.json"):
        """Initialize the worker client."""
        self.config = load_config(config_path)
        self.worker_config = self.config.get("worker", {})
        self.dispatcher_config = self.config.get("dispatcher", {})

        # Set up dispatcher connection info
        self.dispatcher_url = self.dispatcher_config.get("url", "http://localhost:8000")
        self.heartbeat_interval = self.dispatcher_config.get("heartbeat_interval", 30)

        # Set up worker info
        self.worker_id = None
        self.hostname = self.worker_config.get("name", socket.gethostname())
        self.address = socket.gethostbyname(socket.gethostname())
        self.capabilities = self.worker_config.get("capabilities", {})
        self.max_tasks = self.worker_config.get("max_tasks", 5)

        # Add system info to capabilities
        self.capabilities.update({
            "os": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        })

        # Initialize aria2c client
        self.aria2c = Aria2cClient(self.config)

        # Task management
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.ws = None

    async def start(self):
        """Start the worker client."""
        if self.running:
            return

        self.running = True
        logger.info("Starting worker client")

        # Start aria2c
        aria2c_started = await self.aria2c.start()
        if not aria2c_started:
            logger.error("Failed to start aria2c, worker cannot start")
            self.running = False
            return

        # Register with the dispatcher
        registered = await self.register_with_dispatcher()
        if not registered:
            logger.error("Failed to register with dispatcher, worker cannot start")
            self.running = False
            return

        # Start background tasks
        asyncio.create_task(self.connect_to_dispatcher())
        asyncio.create_task(self.monitor_tasks())

    async def stop(self):
        """Stop the worker client."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping worker client")

        # Close WebSocket connection
        if self.ws:
            await self.ws.close()
            self.ws = None

        # Stop aria2c
        await self.aria2c.stop()

    async def register_with_dispatcher(self) -> bool:
        """Register the worker with the dispatcher."""
        if self.worker_id:
            logger.info(f"Worker already registered with ID {self.worker_id}")
            return True

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.dispatcher_url}/workers"
                payload = {
                    "hostname": self.hostname,
                    "address": self.address,
                    "port": self.aria2c.port,
                    "capabilities": self.capabilities,
                    "total_slots": self.max_tasks
                }

                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Registration error: {response.status} - {error_text}")
                        return False

                    data = await response.json()
                    self.worker_id = data.get("id")

                    if not self.worker_id:
                        logger.error("Registration response missing worker ID")
                        return False

                    logger.info(f"Registered with dispatcher as worker {self.worker_id}")
                    return True

        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to dispatcher: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return False

    async def connect_to_dispatcher(self):
        """Connect to the dispatcher via WebSocket and maintain the connection."""
        while self.running:
            try:
                if not self.worker_id:
                    registered = await self.register_with_dispatcher()
                    if not registered:
                        await asyncio.sleep(10)
                        continue

                ws_url = f"{self.dispatcher_url.replace('http', 'ws')}/ws/worker/{self.worker_id}"
                logger.info(f"Connecting to dispatcher WebSocket at {ws_url}")

                async with websockets.connect(ws_url) as websocket:
                    self.ws = websocket
                    logger.info("Connected to dispatcher WebSocket")

                    # Send initial heartbeat
                    await self.send_heartbeat()

                    # Start heartbeat task
                    heartbeat_task = asyncio.create_task(self.heartbeat_loop())

                    # Handle incoming messages
                    try:
                        while self.running:
                            message = await websocket.recv()
                            await self.handle_dispatcher_message(message)
                    finally:
                        heartbeat_task.cancel()
                        try:
                            await heartbeat_task
                        except asyncio.CancelledError:
                            pass

            except ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                self.ws = None
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                self.ws = None
                await asyncio.sleep(10)

    async def heartbeat_loop(self):
        """Send periodic heartbeats to the dispatcher."""
        try:
            while self.running and self.ws:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_heartbeat()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {str(e)}")

    async def send_heartbeat(self):
        """Send a heartbeat to the dispatcher."""
        if not self.ws:
            return

        try:
            # Get current task count
            used_slots = len(self.tasks)

            message = {
                "action": "heartbeat",
                "status": "busy" if used_slots >= self.max_tasks else "online",
                "used_slots": used_slots,
                "timestamp": datetime.now().isoformat()
            }

            await self.ws.send(json.dumps(message))

        except Exception as e:
            logger.error(f"Error sending heartbeat: {str(e)}")

    async def handle_dispatcher_message(self, message: str):
        """Handle a message from the dispatcher."""
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "initial_tasks":
                # Handle initial task list
                tasks = data.get("tasks", [])
                logger.info(f"Received {len(tasks)} initial tasks from dispatcher")

                for task_data in tasks:
                    task_id = task_data.get("id")
                    if task_id and task_id not in self.tasks:
                        await self.add_task(task_data)

            elif action == "add_task":
                # Handle new task
                task_data = data.get("task")
                if task_data:
                    task_id = task_data.get("id")
                    logger.info(f"Received new task {task_id} from dispatcher")
                    await self.add_task(task_data)

            elif action == "cancel_task":
                # Handle task cancellation
                task_id = data.get("task_id")
                if task_id and task_id in self.tasks:
                    logger.info(f"Received cancellation for task {task_id}")
                    await self.cancel_task(task_id)

            elif action == "pause_task":
                # Handle task pause
                task_id = data.get("task_id")
                if task_id and task_id in self.tasks:
                    logger.info(f"Received pause for task {task_id}")
                    await self.pause_task(task_id)

            elif action == "resume_task":
                # Handle task resume
                task_id = data.get("task_id")
                if task_id and task_id in self.tasks:
                    logger.info(f"Received resume for task {task_id}")
                    await self.resume_task(task_id)

            else:
                logger.warning(f"Unknown action '{action}' from dispatcher")

        except json.JSONDecodeError:
            logger.error("Invalid JSON from dispatcher")
        except Exception as e:
            logger.error(f"Error handling message from dispatcher: {str(e)}")

    async def add_task(self, task_data: Dict[str, Any]):
        """Add a new download task."""
        task_id = task_data.get("id")
        url = task_data.get("url")
        options = task_data.get("options", {})

        if not task_id or not url:
            logger.error("Invalid task data: missing id or url")
            return

        if task_id in self.tasks:
            logger.warning(f"Task {task_id} already exists")
            return

        # Add the task to aria2c
        success, gid = await self.aria2c.add_uri(url, options)
        if not success or not gid:
            logger.error(f"Failed to add task {task_id} to aria2c")

            # Report failure to dispatcher
            await self.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message="Failed to add download to aria2c"
            )
            return

        # Store task information
        self.tasks[task_id] = {
            "id": task_id,
            "url": url,
            "options": options,
            "gid": gid,
            "status": TaskStatus.DOWNLOADING,
            "progress": 0.0,
            "download_speed": 0,
            "added_at": datetime.now().isoformat()
        }

        # Report to dispatcher
        await self.update_task_status(
            task_id,
            TaskStatus.DOWNLOADING,
            aria2_gid=gid
        )

        logger.info(f"Added task {task_id} with GID {gid}")

    async def cancel_task(self, task_id: str):
        """Cancel a download task."""
        if task_id not in self.tasks:
            logger.warning(f"Cannot cancel unknown task {task_id}")
            return

        task = self.tasks[task_id]
        gid = task.get("gid")

        if not gid:
            logger.warning(f"Task {task_id} has no GID")
            return

        # Cancel the download in aria2c
        success = await self.aria2c.cancel(gid)
        if not success:
            logger.error(f"Failed to cancel task {task_id} in aria2c")

        # Update task status
        await self.update_task_status(task_id, TaskStatus.CANCELED)

        # Remove from local tasks
        del self.tasks[task_id]

        logger.info(f"Canceled task {task_id}")

    async def pause_task(self, task_id: str):
        """Pause a download task."""
        if task_id not in self.tasks:
            logger.warning(f"Cannot pause unknown task {task_id}")
            return

        task = self.tasks[task_id]
        gid = task.get("gid")

        if not gid:
            logger.warning(f"Task {task_id} has no GID")
            return

        # Pause the download in aria2c
        success = await self.aria2c.pause(gid)
        if not success:
            logger.error(f"Failed to pause task {task_id} in aria2c")
            return

        # Update task status
        task["status"] = TaskStatus.QUEUED
        await self.update_task_status(task_id, TaskStatus.QUEUED)

        logger.info(f"Paused task {task_id}")

    async def resume_task(self, task_id: str):
        """Resume a download task."""
        if task_id not in self.tasks:
            logger.warning(f"Cannot resume unknown task {task_id}")
            return

        task = self.tasks[task_id]
        gid = task.get("gid")

        if not gid:
            logger.warning(f"Task {task_id} has no GID")
            return

        # Resume the download in aria2c
        success = await self.aria2c.resume(gid)
        if not success:
            logger.error(f"Failed to resume task {task_id} in aria2c")
            return

        # Update task status
        task["status"] = TaskStatus.DOWNLOADING
        await self.update_task_status(task_id, TaskStatus.DOWNLOADING)

        logger.info(f"Resumed task {task_id}")

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: float = None,
        download_speed: int = None,
        aria2_gid: str = None,
        error_message: str = None,
        result: Dict[str, Any] = None
    ):
        """Update task status and report to the dispatcher."""
        if not self.ws:
            logger.warning("Cannot update task status: not connected to dispatcher")
            return

        update_data = {
            "action": "task_update",
            "task_id": task_id,
            "status": status.value
        }

        # Add optional fields if provided
        if progress is not None:
            update_data["progress"] = progress

        if download_speed is not None:
            update_data["download_speed"] = download_speed

        if aria2_gid is not None:
            update_data["aria2_gid"] = aria2_gid

        if error_message is not None:
            update_data["error_message"] = error_message

        if result is not None:
            update_data["result"] = result

        try:
            await self.ws.send(json.dumps(update_data))
        except Exception as e:
            logger.error(f"Error sending task update: {str(e)}")

    async def monitor_tasks(self):
        """Monitor the status of all active tasks."""
        while self.running:
            try:
                task_ids = list(self.tasks.keys())
                for task_id in task_ids:
                    await self.check_task_status(task_id)
            except Exception as e:
                logger.error(f"Error in task monitoring: {str(e)}")

            # Wait before next check
            await asyncio.sleep(5)

    async def check_task_status(self, task_id: str):
        """Check the status of a task and update if needed."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        gid = task.get("gid")

        if not gid:
            logger.warning(f"Task {task_id} has no GID")
            return

        # Get status from aria2c
        status_info = await self.aria2c.get_status(gid)

        if "error" in status_info:
            logger.error(f"Error getting status for task {task_id}: {status_info['error']}")
            return

        # Extract status information
        aria2_status = status_info.get("status", "unknown")
        progress = status_info.get("progress", 0.0)
        download_speed = status_info.get("download_speed", 0)

        # Map aria2c status to our status
        task_status = task["status"]
        if aria2_status == "downloading":
            task_status = TaskStatus.DOWNLOADING
        elif aria2_status == "completed":
            task_status = TaskStatus.COMPLETED
        elif aria2_status == "failed":
            task_status = TaskStatus.FAILED
        elif aria2_status == "canceled":
            task_status = TaskStatus.CANCELED

        # Check if status has changed
        status_changed = task["status"] != task_status
        progress_changed = abs(task.get("progress", 0) - progress) > 0.5
        speed_changed = abs(task.get("download_speed", 0) - download_speed) > 1024

        # Update local task info
        task["status"] = task_status
        task["progress"] = progress
        task["download_speed"] = download_speed

        # Report to dispatcher if something significant changed
        if status_changed or progress_changed or speed_changed:
            await self.update_task_status(
                task_id,
                task_status,
                progress=progress,
                download_speed=download_speed
            )

        # Handle completed or failed tasks
        if status_changed and task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
            logger.info(f"Task {task_id} {task_status.value}")

            # For completed tasks, add result information
            if task_status == TaskStatus.COMPLETED:
                result = {
                    "files": status_info.get("files", []),
                    "total_length": status_info.get("total_length", 0),
                    "completed_at": datetime.now().isoformat()
                }

                await self.update_task_status(
                    task_id,
                    task_status,
                    result=result
                )

            # For failed tasks, add error information
            elif task_status == TaskStatus.FAILED:
                error_message = "Download failed"
                await self.update_task_status(
                    task_id,
                    task_status,
                    error_message=error_message
                )

            # Remove from local tasks
            del self.tasks[task_id]


# Main entry point
def main():
    """Run the worker client."""
    config_path = os.environ.get("CONFIG_PATH", "config/worker.json")

    # Create and start the worker client
    worker = WorkerClient(config_path)

    async def run():
        await worker.start()

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await worker.stop()

    # Run the event loop
    asyncio.run(run())


if __name__ == "__main__":
    main()