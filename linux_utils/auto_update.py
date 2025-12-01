"""Auto-update functionality - Set up automatic APT updates via systemd."""

import os
import subprocess
from pathlib import Path

from linux_utils.output import (
    print_success,
    print_error,
    print_info,
    print_bold,
    format_message,
)
from linux_utils.config import BOLD_BLUE
from linux_utils.ui import get_yes_no, get_choice_12
from linux_utils.utils import handle_root_requirement


# Systemd paths and service names
SYSTEMD_DIR = Path("/etc/systemd/system")
SERVICE_FILE = SYSTEMD_DIR / "auto-update.service"
TIMER_FILE = SYSTEMD_DIR / "auto-update.timer"
SERVICE_NAME = "auto-update.service"
TIMER_NAME = "auto-update.timer"
APT_UPDATE_CMD = '/bin/bash -c "export DEBIAN_FRONTEND=noninteractive; apt update; apt upgrade -y"'


def disable_service_if_enabled(service_name: str) -> None:
    """Disable a service if it's enabled."""
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            subprocess.run(["systemctl", "disable", service_name], check=False)
    except Exception:
        pass  # Ignore errors


def create_service_file() -> None:
    """Create the systemd service file."""
    service_content = f"""[Unit]
Description=Automatic APT Update and Upgrade
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={APT_UPDATE_CMD}
User=root

[Install]
WantedBy=multi-user.target
"""
    
    try:
        SERVICE_FILE.write_text(service_content)
        print_success(f"Service file created at {SERVICE_FILE}")
    except PermissionError:
        print_error(f"Permission denied: Cannot write to {SERVICE_FILE}")
        return
    except Exception as e:
        print_error(f"Error creating service file: {e}")
        return


def setup_boot_schedule() -> None:
    """Set up the service to run on boot."""
    disable_service_if_enabled(TIMER_NAME)
    
    print()
    print_bold("⚙️  Configuring service to run on boot...")
    
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
        print_success("Service enabled (will run on boot)")
        
        # Ask if user wants to run it immediately
        print()
        run_now = get_yes_no("Do you want to run the update now? (y/n): ")
        
        if run_now is None:  # ESC pressed, return to menu
            return
        
        if run_now:
            print()
            print_bold(f"Starting {SERVICE_NAME}...")
            subprocess.run(["systemctl", "start", SERVICE_NAME], check=True)
            print_success("Service started")
        
        print()
        print_success("Setup complete!")
        print_info("The service will automatically run 'apt update && apt upgrade -y' on each reboot.")
        
    except subprocess.CalledProcessError as e:
        print_error(f"Error configuring service: {e}")
        return


def setup_daily_schedule(hour: int) -> None:
    """Set up the service to run daily at a specific hour."""
    disable_service_if_enabled(SERVICE_NAME)
    
    # Create the timer file
    timer_content = f"""[Unit]
Description=Automatic APT Update and Upgrade Timer
Requires={SERVICE_NAME}

[Timer]
OnCalendar=daily
OnCalendar=*-*-* {hour:02d}:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    
    try:
        TIMER_FILE.write_text(timer_content)
        print_success(f"Timer file created at {TIMER_FILE}")
        
        # Reload systemd daemon
        print()
        print_bold("⚙️  Reloading systemd daemon...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        print_success("Daemon reloaded")
        
        # Enable and start the timer
        print()
        print_bold(f"Enabling {TIMER_NAME}...")
        subprocess.run(["systemctl", "enable", TIMER_NAME], check=True)
        print_success("Timer enabled")
        
        print()
        print_bold(f"Starting {TIMER_NAME}...")
        subprocess.run(["systemctl", "start", TIMER_NAME], check=True)
        print_success("Timer started")
        
        # Show next run time
        try:
            result = subprocess.run(
                ["systemctl", "list-timers", TIMER_NAME, "--no-pager"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse the output to find next run time
            for line in result.stdout.split('\n'):
                if TIMER_NAME in line and 'n/a' not in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        next_run = ' '.join(parts[:5])
                        print()
                        print(format_message(f"🕐 Next scheduled run: {next_run}"))
                        break
        except Exception:
            pass  # Ignore if we can't get next run time
        
        print()
        print_success("Setup complete!")
        print_info(f"The service will automatically run 'apt update && apt upgrade -y' daily at {hour:02d}:00.")
        
    except PermissionError:
        print_error(f"Permission denied: Cannot write to {TIMER_FILE}")
        return
    except subprocess.CalledProcessError as e:
        print_error(f"Error configuring timer: {e}")
        return
    except Exception as e:
        print_error(f"Error: {e}")
        return


def print_helpful_commands(schedule_type: str) -> None:
    """Print helpful commands based on schedule type."""
    print(format_message("🔧 Useful commands:", BOLD_BLUE))
    
    if schedule_type == "boot":
        print_bold(f"  • Check service status: sudo systemctl status {SERVICE_NAME}")
        print_bold(f"  • View service logs: sudo journalctl -u {SERVICE_NAME}")
        print_bold(f"  • Disable the service: sudo systemctl disable {SERVICE_NAME}")
    else:
        print_bold(f"  • Check timer status: sudo systemctl status {TIMER_NAME}")
        print_bold(f"  • View timer list: sudo systemctl list-timers {TIMER_NAME}")
        print_bold(f"  • View service logs: sudo journalctl -u {SERVICE_NAME}")
        print_bold(f"  • Disable the timer: sudo systemctl disable {TIMER_NAME}")


def get_schedule_type() -> str | None:
    """Get schedule type from user. Returns None if ESC pressed (return to menu)."""
    print(format_message("📅 When should the update run?", BOLD_BLUE))
    print_bold("  • 1) 💻 On boot (after network is online)")
    print_bold("  • 2) 🕐 Daily at a specific hour")
    choice = get_choice_12("Enter your choice (1 or 2): ")
    if choice is None:  # ESC pressed, return to menu
        return None
    return "boot" if choice == "1" else "daily"


def get_hour() -> int:
    """Get hour from user (0-23)."""
    while True:
        hour_str = input(format_message("🕐 Enter the hour (0-23, 24-hour format): ")).strip()
        try:
            hour = int(hour_str)
            if 0 <= hour <= 23:
                return hour
        except ValueError:
            pass
        print_error("Invalid hour. Please enter a number between 0 and 23.")


def setup_auto_update() -> None:
    """Main function to set up auto-update."""
    if not handle_root_requirement('1'):
        return
    
    print(format_message("🚀 Automatic APT Update & Upgrade Setup", BOLD_BLUE))
    print_info("Setting up automatic APT update and upgrade service...")
    
    # Get schedule type from user
    schedule_type = get_schedule_type()
    if schedule_type is None:  # ESC pressed, return to menu
        return
    
    # If daily, get the hour
    if schedule_type == "daily":
        hour = get_hour()
    else:
        hour = None
    
    # Create the systemd service file
    create_service_file()
    
    # Handle scheduling based on user choice
    if schedule_type == "boot":
        setup_boot_schedule()
    else:  # daily
        setup_daily_schedule(hour)
    
    print_helpful_commands(schedule_type)

