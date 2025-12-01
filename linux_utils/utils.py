"""Utility functions for Linux Utilities."""

import os
import sys
import subprocess
from pathlib import Path


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def restart_with_sudo(menu_option: str = None) -> None:
    """Restart the script with sudo, optionally jumping to a menu option."""
    script_path = Path(__file__).parent.parent / 'linux-utilities.py'
    if not script_path.exists():
        script_path = Path(sys.argv[0]).resolve()
    
    cmd = ['sudo', 'python3', str(script_path)]
    if menu_option:
        cmd.extend(['--option', menu_option])
    
    os.execv('/usr/bin/sudo', cmd)


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

