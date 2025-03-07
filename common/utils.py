"""
Utility functions for the aria2c cluster.
"""
import json
import uuid
import logging
import aiohttp
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix."""
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}-{unique_id}"
    return unique_id


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format a datetime object as an ISO 8601 string."""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


async def aria2_rpc_call(
    url: str,
    method: str,
    params: List[Any] = None,
    rpc_secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Make an RPC call to an aria2c instance.

    Args:
        url: The aria2c RPC URL
        method: The RPC method to call
        params: Parameters for the RPC call
        rpc_secret: Optional RPC secret token

    Returns:
        The response from aria2c
    """
    if params is None:
        params = []

    # Add the secret token if provided
    if rpc_secret:
        params.insert(0, f"token:{rpc_secret}")

    payload = {
        "jsonrpc": "2.0",
        "id": generate_id("rpc"),
        "method": method,
        "params": params
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"aria2 RPC error: {response.status} - {error_text}")
                    return {"error": f"HTTP error: {response.status}", "details": error_text}

                result = await response.json()
                if "error" in result:
                    logger.error(f"aria2 RPC error: {result['error']}")
                    return {"error": result["error"]}

                return result
    except aiohttp.ClientError as e:
        logger.error(f"aria2 RPC connection error: {str(e)}")
        return {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in aria2 RPC call: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


def parse_aria2_status(status_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse aria2c status information into a standardized format.

    Args:
        status_info: Status information from aria2c

    Returns:
        Parsed status information
    """
    result = {
        "gid": status_info.get("gid", ""),
        "status": "unknown",
        "progress": 0.0,
        "download_speed": 0,
        "upload_speed": 0,
        "completed_length": 0,
        "total_length": 0,
        "remaining_time": -1,
        "files": []
    }

    # Extract status
    if "status" in status_info:
        status_map = {
            "active": "downloading",
            "waiting": "queued",
            "paused": "paused",
            "error": "failed",
            "complete": "completed",
            "removed": "canceled"
        }
        result["status"] = status_map.get(status_info["status"], status_info["status"])

    # Extract progress
    if "totalLength" in status_info and "completedLength" in status_info:
        total = int(status_info["totalLength"])
        completed = int(status_info["completedLength"])

        if total > 0:
            result["progress"] = (completed / total) * 100
            result["completed_length"] = completed
            result["total_length"] = total

    # Extract speeds
    if "downloadSpeed" in status_info:
        result["download_speed"] = int(status_info["downloadSpeed"])

    if "uploadSpeed" in status_info:
        result["upload_speed"] = int(status_info["uploadSpeed"])

    # Calculate remaining time
    if result["download_speed"] > 0 and result["total_length"] > 0:
        remaining_bytes = result["total_length"] - result["completed_length"]
        result["remaining_time"] = remaining_bytes / result["download_speed"]

    # Extract file information
    if "files" in status_info:
        result["files"] = []
        for file_info in status_info["files"]:
            file_data = {
                "path": file_info.get("path", ""),
                "length": int(file_info.get("length", 0)),
                "completed_length": int(file_info.get("completedLength", 0))
            }
            result["files"].append(file_data)

    return result


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading config from {config_path}: {str(e)}")
        return {}