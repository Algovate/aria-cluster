"""
API server for the aria2c cluster dispatcher.
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from common.models import (
    Task, Worker, TaskStatus, WorkerStatus,
    TaskCreate, TaskUpdate, WorkerCreate, WorkerUpdate, SystemStatus
)
from common.utils import load_config, generate_id, validate_url
from dispatcher.database_factory import get_database, DatabaseType
from dispatcher.scheduler import TaskScheduler
from dispatcher.utils import extract_task_update_fields, extract_worker_update_fields, is_final_task_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
config_path = os.environ.get("CONFIG_PATH", "config/dispatcher.json")
config = load_config(config_path)

# Initialize database based on configuration or environment variables
db_type = os.environ.get("DISPATCHER_DB_TYPE", config.get("database", {}).get("type", DatabaseType.MEMORY))
db_path = os.environ.get("DISPATCHER_DB_PATH", config.get("database", {}).get("path", "data/dispatcher.db"))
database = get_database(db_type, db_path)

scheduler = TaskScheduler(database, config)
connected_workers = {}


# API key authentication
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify the API key if required."""
    if not config.get("security", {}).get("api_key_required", False):
        return True

    api_keys = config.get("security", {}).get("api_keys", [])
    if not api_keys:
        # If API key is required but no keys are configured, log a warning
        # but allow access (configuration might be in progress)
        logger.warning(
            "API key authentication is required but no API keys are configured. "
            "All requests will be allowed. Configure 'security.api_keys' in your config."
        )
        return True

    if not x_api_key or x_api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting aria2c cluster dispatcher")
    await scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down aria2c cluster dispatcher")
    await scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Aria2c Cluster Dispatcher",
    description="API server for the aria2c cluster task dispatcher",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configurable via config file)
cors_origins = config.get("cors", {}).get("allowed_origins", ["http://localhost:8080"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Task endpoints
@app.post("/tasks", response_model=Task, dependencies=[Depends(verify_api_key)])
async def create_task(task_data: TaskCreate):
    """Create a new download task."""
    # Validate URL format
    if not validate_url(task_data.url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    task = await database.create_task(
        task_data.url, 
        task_data.options,
        task_data.priority
    )
    return task


@app.get("/tasks", response_model=List[Task], dependencies=[Depends(verify_api_key)])
async def get_all_tasks():
    """Get all tasks."""
    return await database.get_all_tasks()


@app.get("/tasks/{task_id}", response_model=Task, dependencies=[Depends(verify_api_key)])
async def get_task(task_id: str):
    """Get a task by ID."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=Task, dependencies=[Depends(verify_api_key)])
async def update_task(task_id: str, task_data: TaskUpdate):
    """Update a task."""
    # Convert the model to a dict and remove None values (Pydantic v2 compatible)
    update_data = {k: v for k, v in task_data.model_dump().items() if v is not None}

    task = await database.update_task(task_id, **update_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
async def delete_task(task_id: str):
    """Delete a task."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If the task is assigned to a worker, cancel it first
    if task.worker_id and task.status in [TaskStatus.QUEUED, TaskStatus.DOWNLOADING]:
        worker = await database.get_worker(task.worker_id)
        if worker and worker.status != WorkerStatus.OFFLINE:
            # Notify the worker to cancel the task
            worker_ws = connected_workers.get(worker.id)
            if worker_ws:
                await worker_ws.send_text(json.dumps({
                    "action": "cancel_task",
                    "task_id": task_id
                }))

    # Unassign from worker if needed
    if task.worker_id:
        await database.unassign_task_from_worker(task_id)

    # Delete the task
    success = await database.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete task")

    return {"message": f"Task {task_id} deleted"}


# Worker endpoints
@app.post("/workers", response_model=Worker, dependencies=[Depends(verify_api_key)])
async def register_worker(worker_data: WorkerCreate):
    """Register a new worker."""
    worker = await database.register_worker(
        worker_data.hostname,
        worker_data.address,
        worker_data.port,
        worker_data.capabilities,
        worker_data.total_slots
    )
    return worker


@app.get("/workers", response_model=List[Worker], dependencies=[Depends(verify_api_key)])
async def get_all_workers():
    """Get all workers."""
    return await database.get_all_workers()


@app.get("/workers/{worker_id}", response_model=Worker, dependencies=[Depends(verify_api_key)])
async def get_worker(worker_id: str):
    """Get a worker by ID."""
    worker = await database.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@app.put("/workers/{worker_id}", response_model=Worker, dependencies=[Depends(verify_api_key)])
async def update_worker(worker_id: str, worker_data: WorkerUpdate):
    """Update a worker."""
    # Convert the model to a dict and remove None values
    update_data = {k: v for k, v in worker_data.model_dump().items() if v is not None}

    worker = await database.update_worker(worker_id, **update_data)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@app.delete("/workers/{worker_id}", dependencies=[Depends(verify_api_key)])
async def delete_worker(worker_id: str):
    """Delete a worker."""
    worker = await database.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Unassign all tasks from this worker
    for task_id in worker.current_tasks:
        await database.unassign_task_from_worker(task_id)
        await database.update_task(task_id, status=TaskStatus.PENDING)

    # Delete the worker
    success = await database.delete_worker(worker_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete worker")

    return {"message": f"Worker {worker_id} deleted"}


# System status endpoint (support both /api/status and /status for backward compatibility)
@app.get("/api/status", response_model=SystemStatus, dependencies=[Depends(verify_api_key)])
@app.get("/status", response_model=SystemStatus, dependencies=[Depends(verify_api_key)])
async def get_system_status():
    """Get system status information."""
    active_workers = len(await database.get_workers_by_status(WorkerStatus.ONLINE))
    active_workers += len(await database.get_workers_by_status(WorkerStatus.BUSY))

    tasks = await database.get_all_tasks()
    tasks_by_status = await database.get_task_counts_by_status()

    system_load = await database.get_system_load()

    return SystemStatus(
        active_workers=active_workers,
        total_tasks=len(tasks),
        tasks_by_status=tasks_by_status,
        system_load=system_load
    )


# WebSocket endpoint for worker communication
@app.websocket("/ws/worker/{worker_id}")
async def worker_websocket(websocket: WebSocket, worker_id: str):
    """WebSocket endpoint for worker communication."""
    await websocket.accept()

    # Check if the worker exists
    worker = await database.get_worker(worker_id)
    if not worker:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Worker not found")
        return

    # Store the WebSocket connection
    connected_workers[worker_id] = websocket

    try:
        # Update worker status
        await database.update_worker_heartbeat(worker_id)

        # Send initial tasks
        worker_tasks = await database.get_tasks_by_worker(worker_id)
        if worker_tasks:
            await websocket.send_text(json.dumps({
                "action": "initial_tasks",
                "tasks": [task.model_dump() for task in worker_tasks]
            }))

        # Handle messages
        while True:
            data = await websocket.receive_text()
            await handle_worker_message(worker_id, data)

    except WebSocketDisconnect:
        logger.info(f"Worker {worker_id} disconnected")
    finally:
        # Remove the connection
        if worker_id in connected_workers:
            del connected_workers[worker_id]

        # Update worker status
        worker = await database.get_worker(worker_id)
        if worker:
            await database.update_worker(worker_id, status=WorkerStatus.OFFLINE)


async def handle_worker_message(worker_id: str, message: str):
    """Handle a message from a worker."""
    try:
        data = json.loads(message)
        action = data.get("action")

        if action == "heartbeat":
            # Update worker heartbeat
            await database.update_worker_heartbeat(worker_id)

            # Prepare update data
            update_data = {}

            # Update worker status if provided
            if "status" in data:
                status_str = data["status"]
                if status_str in [s.value for s in WorkerStatus]:
                    update_data["status"] = WorkerStatus(status_str)

            # Update worker slots if provided
            if "used_slots" in data:
                update_data["used_slots"] = data["used_slots"]

            # Update health metrics if provided
            if "health_metrics" in data:
                update_data["health_metrics"] = data["health_metrics"]

            # Update performance stats if provided
            if "performance_stats" in data:
                update_data["performance_stats"] = data["performance_stats"]

            # Apply all updates at once
            if update_data:
                await database.update_worker(worker_id, **update_data)

        elif action == "task_update":
            # Update task status
            task_id = data.get("task_id")
            if not task_id:
                logger.error(f"Missing task_id in task_update from worker {worker_id}")
                return

            task = await database.get_task(task_id)
            if not task:
                logger.error(f"Unknown task {task_id} in update from worker {worker_id}")
                return

            # Extract update data
            allowed_task_fields = ["status", "progress", "download_speed", "aria2_gid", "error_message", "result"]
            update_data = extract_task_update_fields(data, allowed_task_fields)

            # Update the task
            await database.update_task(task_id, **update_data)

            # Handle task completion or failure
            if "status" in data and is_final_task_status(data["status"]):
                # Unassign the task from the worker
                await database.unassign_task_from_worker(task_id)

        elif action == "worker_update":
            # Update worker information
            allowed_worker_fields = ["capabilities", "total_slots", "used_slots"]
            update_data = extract_worker_update_fields(data, allowed_worker_fields)

            if update_data:
                await database.update_worker(worker_id, **update_data)

        else:
            logger.warning(f"Unknown action '{action}' from worker {worker_id}")

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from worker {worker_id}")
    except Exception as e:
        logger.error(f"Error handling message from worker {worker_id}: {str(e)}")


# Main entry point
def main():
    """Run the server."""
    host = config.get("host", "0.0.0.0")
    port = config.get("port", 8000)

    uvicorn.run(
        "dispatcher.server:app",
        host=host,
        port=port,
        reload=False
    )


if __name__ == "__main__":
    main()