#!/usr/bin/env python3
"""
Check if aria2c is installed and install it if needed.
"""
import os
import sys
import subprocess
import platform
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_aria2c():
    """Check if aria2c is installed."""
    try:
        result = subprocess.run(
            ["aria2c", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            logger.info(f"aria2c is installed: {version}")
            return True
        else:
            logger.warning("aria2c is not installed or not in PATH")
            return False
    except FileNotFoundError:
        logger.warning("aria2c is not installed or not in PATH")
        return False


def install_aria2c():
    """Install aria2c."""
    system = platform.system().lower()

    if system == "linux":
        # Try to detect the Linux distribution
        try:
            with open("/etc/os-release", "r") as f:
                os_info = {}
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os_info[key] = value.strip('"')

            if "ID" in os_info:
                distro = os_info["ID"].lower()

                if distro in ["ubuntu", "debian", "linuxmint"]:
                    logger.info("Installing aria2c using apt...")
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y", "aria2"], check=True)
                    return True
                elif distro in ["fedora", "rhel", "centos"]:
                    logger.info("Installing aria2c using dnf/yum...")
                    subprocess.run(["sudo", "dnf", "install", "-y", "aria2"], check=True)
                    return True
                elif distro in ["arch", "manjaro"]:
                    logger.info("Installing aria2c using pacman...")
                    subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "aria2"], check=True)
                    return True
                else:
                    logger.error(f"Unsupported Linux distribution: {distro}")
                    return False
            else:
                logger.error("Could not determine Linux distribution")
                return False
        except Exception as e:
            logger.error(f"Error detecting Linux distribution: {str(e)}")
            return False

    elif system == "darwin":
        # macOS
        try:
            logger.info("Installing aria2c using Homebrew...")
            # Check if Homebrew is installed
            try:
                subprocess.run(["brew", "--version"], check=True, stdout=subprocess.PIPE)
            except (FileNotFoundError, subprocess.CalledProcessError):
                logger.error("Homebrew is not installed. Please install Homebrew first: https://brew.sh/")
                return False

            # Install aria2c
            subprocess.run(["brew", "install", "aria2"], check=True)
            return True
        except Exception as e:
            logger.error(f"Error installing aria2c: {str(e)}")
            return False

    elif system == "windows":
        logger.error("Automatic installation on Windows is not supported.")
        logger.info("Please download and install aria2c manually from: https://github.com/aria2/aria2/releases")
        return False

    else:
        logger.error(f"Unsupported operating system: {system}")
        return False


def main():
    """Main function."""
    logger.info("Checking dependencies...")

    if check_aria2c():
        logger.info("All dependencies are installed!")
        return 0

    logger.info("aria2c is not installed. Attempting to install...")

    if install_aria2c():
        logger.info("aria2c has been installed successfully!")
        return 0
    else:
        logger.error("Failed to install aria2c. Please install it manually.")
        return 1


if __name__ == "__main__":
    sys.exit(main())