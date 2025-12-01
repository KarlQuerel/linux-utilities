"""Utility functions for Linux Utilities."""

import os
import sys
import subprocess
from pathlib import Path

from linux_utils.config import OPTION_FLAG

# Constants
SCRIPT_NAME = "linux-utilities.py"
SUDO_PATH = "/usr/bin/sudo"
PYTHON3_CMD = "python3"


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def restart_with_sudo(menu_option: str = None) -> None:
    """Restart the script with sudo, optionally jumping to a menu option."""
    script_path = Path(__file__).parent.parent / SCRIPT_NAME
    if not script_path.exists():
        script_path = Path(sys.argv[0]).resolve()
    
    cmd = ['sudo', PYTHON3_CMD, str(script_path)]
    if menu_option:
        cmd.extend([OPTION_FLAG, menu_option])
    
    os.execv(SUDO_PATH, cmd)


def check_sudo_available() -> bool:
    """Check if sudo is available on the system."""
    try:
        result = subprocess.run(
            ['which', 'sudo'],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False

