#!/usr/bin/env python3
"""
Setup script for the aria2c cluster.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directories():
    """Create necessary directories for the aria2c cluster."""
    directories = [
        "data",
        "downloads/worker1",
        "downloads/worker2"
    ]

    for directory in directories:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", directory))
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created directory: {path}")
        else:
            logger.info(f"Directory already exists: {path}")

if __name__ == "__main__":
    logger.info("Setting up aria2c cluster...")
    create_directories()
    logger.info("Setup complete!")