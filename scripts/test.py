#!/usr/bin/env python3
"""
Test script for the aria2c cluster.
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.client import DispatcherClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_system():
    """Test the aria2c cluster system."""
    client = DispatcherClient()

    # Test 1: Get system status
    logger.info("Test 1: Getting system status...")
    status = await client.get_status()
    if "error" in status:
        logger.error(f"Failed to get system status: {status['error']}")
        return False

    logger.info(f"System status: {json.dumps(status, indent=2)}")

    # Test 2: List workers
    logger.info("Test 2: Listing workers...")
    workers = await client.list_workers()
    if "error" in workers:
        logger.error(f"Failed to list workers: {workers['error']}")
        return False

    if not workers:
        logger.warning("No workers found. Make sure workers are running.")
    else:
        logger.info(f"Found {len(workers)} workers")
        for worker in workers:
            logger.info(f"Worker: {worker['id']} - {worker['status']}")

    # Test 3: Create a task
    logger.info("Test 3: Creating a test task...")
    test_url = "https://nbg1-speed.hetzner.com/100MB.bin"
    task = await client.create_task(test_url, {"out": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}.bin"})

    if "error" in task:
        logger.error(f"Failed to create task: {task['error']}")
        return False

    task_id = task["id"]
    logger.info(f"Created task {task_id} for URL {test_url}")

    # Test 4: Monitor task progress
    logger.info("Test 4: Monitoring task progress...")
    for _ in range(10):
        task_status = await client.get_task(task_id)
        if "error" in task_status:
            logger.error(f"Failed to get task status: {task_status['error']}")
            break

        logger.info(f"Task {task_id} status: {task_status['status']} - Progress: {task_status['progress']:.2f}%")

        if task_status["status"] in ["completed", "failed", "canceled"]:
            break

        await asyncio.sleep(2)

    # Test 5: List all tasks
    logger.info("Test 5: Listing all tasks...")
    tasks = await client.list_tasks()
    if "error" in tasks:
        logger.error(f"Failed to list tasks: {tasks['error']}")
        return False

    logger.info(f"Found {len(tasks)} tasks")

    logger.info("All tests completed successfully!")
    return True


async def main():
    """Run the tests."""
    logger.info("Starting aria2c cluster tests...")

    success = await test_system()

    if success:
        logger.info("All tests passed!")
        return 0
    else:
        logger.error("Tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)