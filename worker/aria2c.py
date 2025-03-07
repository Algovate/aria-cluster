"""
Aria2c client for the worker node.
"""
import os
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional, Tuple

from common.utils import aria2_rpc_call, parse_aria2_status

logger = logging.getLogger(__name__)


class Aria2cClient:
    """Client for interacting with an aria2c instance."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the client."""
        self.config = config
        self.aria2_config = config.get("aria2", {})

        self.host = self.aria2_config.get("host", "localhost")
        self.port = self.aria2_config.get("port", 6800)
        self.rpc_secret = self.aria2_config.get("rpc_secret", "")
        self.rpc_path = self.aria2_config.get("rpc_path", "/jsonrpc")
        self.download_dir = self.aria2_config.get("download_dir", "/downloads")
        self.global_options = self.aria2_config.get("global_options", {})

        self.rpc_url = f"http://{self.host}:{self.port}{self.rpc_path}"
        self.process = None
        self.running = False

    async def start(self) -> bool:
        """Start the aria2c process if not already running."""
        # Check if aria2c is already running
        if await self.is_running():
            logger.info("aria2c is already running")
            self.running = True
            return True

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

        # Build command line arguments
        args = [
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={self.port}",
            f"--dir={self.download_dir}",
            "--daemon=true"
        ]

        # Add RPC secret if provided
        if self.rpc_secret:
            args.append(f"--rpc-secret={self.rpc_secret}")

        # Add global options
        for key, value in self.global_options.items():
            if value is True:
                args.append(f"--{key}")
            elif value is not False:  # Skip False values
                args.append(f"--{key}={value}")

        try:
            # Start aria2c
            logger.info(f"Starting aria2c: {' '.join(args)}")
            self.process = subprocess.Popen(args)

            # Wait for aria2c to start
            for _ in range(10):
                await asyncio.sleep(1)
                if await self.is_running():
                    self.running = True
                    logger.info("aria2c started successfully")
                    return True

            logger.error("Failed to start aria2c")
            return False

        except Exception as e:
            logger.error(f"Error starting aria2c: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the aria2c process."""
        if not self.running:
            return True

        try:
            # Try to shutdown gracefully via RPC
            result = await aria2_rpc_call(self.rpc_url, "aria2.shutdown", rpc_secret=self.rpc_secret)
            if "error" not in result:
                logger.info("aria2c shutdown successfully via RPC")
                self.running = False
                return True

            # If RPC shutdown fails, kill the process
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                logger.info("aria2c process terminated")
                self.running = False
                return True

            return False

        except Exception as e:
            logger.error(f"Error stopping aria2c: {str(e)}")
            return False

    async def is_running(self) -> bool:
        """Check if aria2c is running."""
        try:
            result = await aria2_rpc_call(self.rpc_url, "aria2.getVersion", rpc_secret=self.rpc_secret)
            return "error" not in result
        except Exception:
            return False

    async def add_uri(self, uri: str, options: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
        """
        Add a download URI to aria2c.

        Args:
            uri: The URI to download
            options: Download options

        Returns:
            Tuple of (success, gid)
        """
        if options is None:
            options = {}

        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.addUri",
                [[uri], options],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error adding URI: {result['error']}")
                return False, None

            gid = result.get("result")
            if gid:
                logger.info(f"Added URI {uri} with GID {gid}")
                return True, gid

            return False, None

        except Exception as e:
            logger.error(f"Error adding URI: {str(e)}")
            return False, None

    async def get_status(self, gid: str) -> Dict[str, Any]:
        """
        Get the status of a download.

        Args:
            gid: The GID of the download

        Returns:
            Status information
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.tellStatus",
                [gid],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error getting status for GID {gid}: {result['error']}")
                return {"error": result["error"]}

            status_info = result.get("result", {})
            return parse_aria2_status(status_info)

        except Exception as e:
            logger.error(f"Error getting status for GID {gid}: {str(e)}")
            return {"error": str(e)}

    async def pause(self, gid: str) -> bool:
        """
        Pause a download.

        Args:
            gid: The GID of the download

        Returns:
            Success status
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.pause",
                [gid],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error pausing GID {gid}: {result['error']}")
                return False

            logger.info(f"Paused download with GID {gid}")
            return True

        except Exception as e:
            logger.error(f"Error pausing GID {gid}: {str(e)}")
            return False

    async def resume(self, gid: str) -> bool:
        """
        Resume a download.

        Args:
            gid: The GID of the download

        Returns:
            Success status
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.unpause",
                [gid],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error resuming GID {gid}: {result['error']}")
                return False

            logger.info(f"Resumed download with GID {gid}")
            return True

        except Exception as e:
            logger.error(f"Error resuming GID {gid}: {str(e)}")
            return False

    async def cancel(self, gid: str) -> bool:
        """
        Cancel a download.

        Args:
            gid: The GID of the download

        Returns:
            Success status
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.remove",
                [gid],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error canceling GID {gid}: {result['error']}")
                return False

            logger.info(f"Canceled download with GID {gid}")
            return True

        except Exception as e:
            logger.error(f"Error canceling GID {gid}: {str(e)}")
            return False

    async def get_global_stat(self) -> Dict[str, Any]:
        """
        Get global statistics.

        Returns:
            Global statistics
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.getGlobalStat",
                [],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error getting global stats: {result['error']}")
                return {"error": result["error"]}

            return result.get("result", {})

        except Exception as e:
            logger.error(f"Error getting global stats: {str(e)}")
            return {"error": str(e)}

    async def get_active_downloads(self) -> List[Dict[str, Any]]:
        """
        Get all active downloads.

        Returns:
            List of active downloads
        """
        try:
            result = await aria2_rpc_call(
                self.rpc_url,
                "aria2.tellActive",
                [],
                self.rpc_secret
            )

            if "error" in result:
                logger.error(f"Error getting active downloads: {result['error']}")
                return []

            downloads = result.get("result", [])
            return [parse_aria2_status(download) for download in downloads]

        except Exception as e:
            logger.error(f"Error getting active downloads: {str(e)}")
            return []