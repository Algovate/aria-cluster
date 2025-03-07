"""
Client script to interact with the aria2c cluster dispatcher.
"""
import os
import sys
import json
import argparse
import asyncio
import logging
from typing import Dict, List, Any, Optional

import aiohttp

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DispatcherClient:
    """Client for interacting with the dispatcher API."""

    def __init__(self, url: str = None, api_key: str = None):
        """Initialize the client."""
        config = load_config("config/dispatcher.json")

        self.url = url or config.get("host", "localhost")
        port = config.get("port", 8000)

        # Ensure URL has protocol
        if not self.url.startswith(("http://", "https://")):
            self.url = f"http://{self.url}"

        # Add port if not in URL
        if ":" not in self.url.split("/")[-1]:
            self.url = f"{self.url}:{port}"

        self.api_key = api_key
        self.headers = {}

        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    async def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return await self._request("GET", "/status")

    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks."""
        return await self._request("GET", "/tasks")

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a task by ID."""
        return await self._request("GET", f"/tasks/{task_id}")

    async def create_task(self, url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new task."""
        if options is None:
            options = {}

        payload = {
            "url": url,
            "options": options
        }

        return await self._request("POST", "/tasks", payload)

    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task."""
        return await self._request("DELETE", f"/tasks/{task_id}")

    async def list_workers(self) -> List[Dict[str, Any]]:
        """List all workers."""
        return await self._request("GET", "/workers")

    async def get_worker(self, worker_id: str) -> Dict[str, Any]:
        """Get a worker by ID."""
        return await self._request("GET", f"/workers/{worker_id}")

    async def _request(self, method: str, path: str, data: Any = None) -> Any:
        """Make a request to the dispatcher API."""
        url = f"{self.url}{path}"

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=self.headers) as response:
                        return await self._handle_response(response)
                elif method == "POST":
                    async with session.post(url, json=data, headers=self.headers) as response:
                        return await self._handle_response(response)
                elif method == "PUT":
                    async with session.put(url, json=data, headers=self.headers) as response:
                        return await self._handle_response(response)
                elif method == "DELETE":
                    async with session.delete(url, headers=self.headers) as response:
                        return await self._handle_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

        except aiohttp.ClientError as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle the API response."""
        if response.status == 200:
            return await response.json()

        try:
            error_data = await response.json()
            error_message = error_data.get("detail", f"HTTP error: {response.status}")
        except:
            error_message = f"HTTP error: {response.status}"

        logger.error(f"API error: {error_message}")
        return {"error": error_message}


async def main():
    """Run the client."""
    parser = argparse.ArgumentParser(description="Aria2c Cluster Client")

    # Global options
    parser.add_argument("--url", help="Dispatcher URL")
    parser.add_argument("--api-key", help="API key for authentication")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get system status")

    # Tasks commands
    tasks_parser = subparsers.add_parser("tasks", help="List all tasks")

    task_parser = subparsers.add_parser("task", help="Get a task by ID")
    task_parser.add_argument("task_id", help="Task ID")

    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("url", help="URL to download")
    create_parser.add_argument("--dir", help="Download directory")
    create_parser.add_argument("--out", help="Output filename")
    create_parser.add_argument("--options", help="Additional options as JSON")

    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("task_id", help="Task ID")

    # Workers commands
    workers_parser = subparsers.add_parser("workers", help="List all workers")

    worker_parser = subparsers.add_parser("worker", help="Get a worker by ID")
    worker_parser.add_argument("worker_id", help="Worker ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    client = DispatcherClient(args.url, args.api_key)

    if args.command == "status":
        result = await client.get_status()
        print(json.dumps(result, indent=2))

    elif args.command == "tasks":
        result = await client.list_tasks()
        print(json.dumps(result, indent=2))

    elif args.command == "task":
        result = await client.get_task(args.task_id)
        print(json.dumps(result, indent=2))

    elif args.command == "create":
        options = {}

        if args.dir:
            options["dir"] = args.dir

        if args.out:
            options["out"] = args.out

        if args.options:
            try:
                additional_options = json.loads(args.options)
                options.update(additional_options)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in --options")
                return

        result = await client.create_task(args.url, options)
        print(json.dumps(result, indent=2))

    elif args.command == "delete":
        result = await client.delete_task(args.task_id)
        print(json.dumps(result, indent=2))

    elif args.command == "workers":
        result = await client.list_workers()
        print(json.dumps(result, indent=2))

    elif args.command == "worker":
        result = await client.get_worker(args.worker_id)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())