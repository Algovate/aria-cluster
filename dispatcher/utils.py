"""
Utility functions for the dispatcher module.
"""
from typing import Dict, Any, List
from common.models import TaskStatus, WorkerStatus


def extract_task_update_fields(data: Dict[str, Any], allowed_fields: List[str]) -> Dict[str, Any]:
    """
    Extract allowed fields from a dictionary for task updates.
    
    Args:
        data: Dictionary containing update data
        allowed_fields: List of field names that are allowed to be updated
        
    Returns:
        Dictionary containing only allowed fields with their values
    """
    return {field: data[field] for field in allowed_fields if field in data}


def extract_worker_update_fields(data: Dict[str, Any], allowed_fields: List[str]) -> Dict[str, Any]:
    """
    Extract allowed fields from a dictionary for worker updates.
    
    Args:
        data: Dictionary containing update data
        allowed_fields: List of field names that are allowed to be updated
        
    Returns:
        Dictionary containing only allowed fields with their values
    """
    return {field: data[field] for field in allowed_fields if field in data}


def is_final_task_status(status: str) -> bool:
    """
    Check if a task status is a final state (completed, failed, or canceled).
    
    Args:
        status: Task status string
        
    Returns:
        True if the status is a final state, False otherwise
    """
    final_statuses = [
        TaskStatus.COMPLETED.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELED.value
    ]
    return status in final_statuses

