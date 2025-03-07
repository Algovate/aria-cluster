"""
Data models for the aria2c cluster.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a download task."""
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkerStatus(str, Enum):
    """Status of a worker node."""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class Task(BaseModel):
    """Model representing a download task."""
    id: str = Field(..., description="Unique task identifier")
    url: str = Field(..., description="URL to download")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    worker_id: Optional[str] = Field(None, description="ID of the worker handling this task")
    aria2_gid: Optional[str] = Field(None, description="aria2c GID for this download")
    options: Dict[str, Any] = Field(default_factory=dict, description="aria2c options for this task")
    progress: float = Field(default=0.0, description="Download progress (0-100)")
    download_speed: Optional[int] = Field(None, description="Current download speed in bytes/sec")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data after completion")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "task-123456",
                "url": "https://example.com/file.zip",
                "options": {
                    "dir": "/downloads",
                    "out": "file.zip",
                    "max-connection-per-server": 16
                }
            }
        }


class Worker(BaseModel):
    """Model representing a worker node."""
    id: str = Field(..., description="Unique worker identifier")
    hostname: str = Field(..., description="Worker hostname")
    address: str = Field(..., description="Worker address (IP or domain)")
    port: int = Field(..., description="Worker RPC port")
    status: WorkerStatus = Field(default=WorkerStatus.OFFLINE, description="Current worker status")
    connected_at: Optional[datetime] = Field(None, description="Last connection time")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat time")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Worker capabilities")
    current_tasks: List[str] = Field(default_factory=list, description="List of task IDs currently being processed")
    total_slots: int = Field(default=5, description="Maximum concurrent downloads")
    used_slots: int = Field(default=0, description="Currently used download slots")

    @property
    def available_slots(self) -> int:
        """Calculate available download slots."""
        return max(0, self.total_slots - self.used_slots)

    @property
    def load_percentage(self) -> float:
        """Calculate worker load as a percentage."""
        if self.total_slots == 0:
            return 100.0
        return (self.used_slots / self.total_slots) * 100.0


class TaskCreate(BaseModel):
    """Model for creating a new task."""
    url: str = Field(..., description="URL to download")
    options: Dict[str, Any] = Field(default_factory=dict, description="aria2c options for this task")


class TaskUpdate(BaseModel):
    """Model for updating a task."""
    status: Optional[TaskStatus] = Field(None, description="New task status")
    worker_id: Optional[str] = Field(None, description="Worker ID assignment")
    aria2_gid: Optional[str] = Field(None, description="aria2c GID")
    progress: Optional[float] = Field(None, description="Download progress")
    download_speed: Optional[int] = Field(None, description="Current download speed")
    error_message: Optional[str] = Field(None, description="Error message")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data")


class WorkerCreate(BaseModel):
    """Model for registering a new worker."""
    hostname: str = Field(..., description="Worker hostname")
    address: str = Field(..., description="Worker address (IP or domain)")
    port: int = Field(..., description="Worker RPC port")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Worker capabilities")
    total_slots: int = Field(default=5, description="Maximum concurrent downloads")


class WorkerUpdate(BaseModel):
    """Model for updating a worker."""
    status: Optional[WorkerStatus] = Field(None, description="Worker status")
    current_tasks: Optional[List[str]] = Field(None, description="Current tasks")
    used_slots: Optional[int] = Field(None, description="Used download slots")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Worker capabilities")
    total_slots: Optional[int] = Field(None, description="Maximum concurrent downloads")


class SystemStatus(BaseModel):
    """Model for system status information."""
    active_workers: int = Field(..., description="Number of active workers")
    total_tasks: int = Field(..., description="Total number of tasks")
    tasks_by_status: Dict[TaskStatus, int] = Field(..., description="Tasks grouped by status")
    system_load: float = Field(..., description="Overall system load percentage")