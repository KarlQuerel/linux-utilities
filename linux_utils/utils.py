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


def handle_root_requirement(menu_option: str) -> bool:
    """Handle root requirement. Returns True if should continue, False if should return."""
    from linux_utils.output import print_error, print_info, print_bold
    from linux_utils.ui import get_yes_no
    
    if is_root():
        return True

    print_error("This utility requires root privileges")
    print()
    print_info("Options:")
    print_bold("  1. Restart with sudo (recommended)")
    print_bold("  2. Run manually: sudo ./linux-utilities.py")
    print()

    if not check_sudo_available():
        print_error("sudo is not available on this system")
        print_info("Please run this script as root")
        return False

    restart_choice = get_yes_no("Restart with sudo now? (y/n): ")
    if restart_choice is None:  # ESC pressed, return to menu
        return False

    if restart_choice:
        print()
        print_info("Restarting with sudo...")
        print()
        restart_with_sudo(menu_option)
        return False

    print()
    print_info("Please run: sudo ./linux-utilities.py")
    return False

