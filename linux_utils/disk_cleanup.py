"""Disk cleanup functionality - Clean up disk space by removing unnecessary files."""

import shutil
import subprocess
import time
from pathlib import Path

from linux_utils.output import (
    print_success,
    print_error,
    print_info,
    print_bold,
    format_message,
)
from linux_utils.config import BOLD_BLUE, GREEN, BOLD, NC
from linux_utils.ui import get_yes_no, get_choice_16, clear_screen
from linux_utils.utils import is_root


def _get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, OSError):
        pass
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def _clean_apt_cache(dry_run: bool = False) -> int:
    """Clean APT package cache. Returns bytes freed."""
    if dry_run:
        # Estimate size
        cache_dir = Path("/var/cache/apt/archives")
        if cache_dir.exists():
            return _get_directory_size(cache_dir)
        return 0
    
    try:
        # Get size before cleanup
        cache_dir = Path("/var/cache/apt/archives")
        size_before = _get_directory_size(cache_dir) if cache_dir.exists() else 0
        
        # Clean APT cache
        subprocess.run(["apt", "clean"], check=True, capture_output=True)
        subprocess.run(["apt", "autoclean"], check=True, capture_output=True)
        
        # Get size after cleanup
        size_after = _get_directory_size(cache_dir) if cache_dir.exists() else 0
        
        return size_before - size_after
    except subprocess.CalledProcessError as e:
        print_error(f"Error cleaning APT cache: {e}")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 0


def _parse_journal_size(output: str) -> int:
    """Parse journal size from journalctl --disk-usage output. Returns size in bytes."""
    for line in output.split('\n'):
        if 'G' in line:
            try:
                size_str = line.split()[-1].replace('G', '')
                return int(float(size_str) * 1024 * 1024 * 1024)
            except (ValueError, IndexError):
                pass
        elif 'M' in line:
            try:
                size_str = line.split()[-1].replace('M', '')
                return int(float(size_str) * 1024 * 1024)
            except (ValueError, IndexError):
                pass
    return 0


def _clean_old_logs(dry_run: bool = False) -> int:
    """Clean old log files. Returns bytes freed."""
    try:
        result = subprocess.run(
            ["journalctl", "--disk-usage"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            return 0
        
        if dry_run:
            # Rough estimate - assume we can free 50% by keeping last 7 days
            size_before = _parse_journal_size(result.stdout)
            return int(size_before * 0.5)
        
        size_before = _parse_journal_size(result.stdout)
        
        # Clean logs older than 7 days
        subprocess.run(
            ["journalctl", "--vacuum-time=7d"],
            check=True,
            capture_output=True,
        )
        
        # Get journal size after
        result_after = subprocess.run(
            ["journalctl", "--disk-usage"],
            capture_output=True,
            text=True,
            check=False,
        )
        size_after = _parse_journal_size(result_after.stdout) if result_after.returncode == 0 else 0
        
        return size_before - size_after
    except subprocess.CalledProcessError as e:
        print_error(f"Error cleaning logs: {e}")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 0


def _clean_temp_files(dry_run: bool = False) -> int:
    """Clean temporary files. Returns bytes freed."""
    temp_dirs = [
        Path("/tmp"),
        Path("/var/tmp"),
    ]
    
    total_freed = 0
    
    for temp_dir in temp_dirs:
        if not temp_dir.exists():
            continue
        
        if dry_run:
            total_freed += _get_directory_size(temp_dir)
        else:
            try:
                size_before = _get_directory_size(temp_dir)
                
                # Remove files older than 7 days
                current_time = time.time()
                seven_days_ago = current_time - (7 * 24 * 60 * 60)
                
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            if item.stat().st_mtime < seven_days_ago:
                                item.unlink()
                        elif item.is_dir():
                            if item.stat().st_mtime < seven_days_ago:
                                shutil.rmtree(item)
                    except (PermissionError, OSError):
                        pass
                
                size_after = _get_directory_size(temp_dir)
                total_freed += size_before - size_after
            except Exception as e:
                print_error(f"Error cleaning {temp_dir}: {e}")
    
    return total_freed


def _clean_old_kernels(dry_run: bool = False) -> int:
    """Clean old kernel packages. Returns bytes freed."""
    if dry_run:
        # Estimate: check installed kernels
        try:
            result = subprocess.run(
                ["dpkg", "-l", "linux-image-*"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                # Rough estimate: each old kernel ~200MB
                lines = [l for l in result.stdout.split('\n') if 'linux-image' in l and 'ii' in l]
                # Assume we keep current + 1 backup, rest can be removed
                if len(lines) > 2:
                    return (len(lines) - 2) * 200 * 1024 * 1024
        except Exception:
            pass
        return 0
    
    try:
        # Get list of installed kernels before
        result_before = subprocess.run(
            ["dpkg", "-l", "linux-image-*"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Use apt autoremove to remove old kernels
        subprocess.run(
            ["apt", "autoremove", "--purge", "-y"],
            check=True,
            capture_output=True,
        )
        
        # Estimate freed space (rough calculation)
        # Each kernel package is typically 100-300MB
        result_after = subprocess.run(
            ["dpkg", "-l", "linux-image-*"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        kernels_before = len([l for l in result_before.stdout.split('\n') if 'linux-image' in l and 'ii' in l])
        kernels_after = len([l for l in result_after.stdout.split('\n') if 'linux-image' in l and 'ii' in l])
        kernels_removed = kernels_before - kernels_after
        
        # Estimate 200MB per kernel
        return kernels_removed * 200 * 1024 * 1024
    except subprocess.CalledProcessError as e:
        print_error(f"Error cleaning old kernels: {e}")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 0


def _get_cleanup_options(show_header: bool = True) -> dict[str, bool] | None:
    """Get cleanup options from user with multi-selection. Returns None if ESC pressed (return to menu)."""
    selected = {"apt": False, "logs": False, "temp": False, "kernels": False}
    first_iteration = True
    
    while True:
        if not first_iteration:
            clear_screen()
            if show_header:
                print()
                print(format_message("🧹 Disk Cleanup", BOLD_BLUE))
                print()
        
        print()
        print(format_message("Select what to clean:", BOLD_BLUE))
        print()
        
        # Show options with checkmarks for selected items (green and bold when selected)
        check_apt = f"{GREEN}{BOLD}✓{NC}" if selected["apt"] else " "
        check_logs = f"{GREEN}{BOLD}✓{NC}" if selected["logs"] else " "
        check_temp = f"{GREEN}{BOLD}✓{NC}" if selected["temp"] else " "
        check_kernels = f"{GREEN}{BOLD}✓{NC}" if selected["kernels"] else " "
        
        print_bold(f"  • 1) [{check_apt}] 📦 APT package cache")
        print_bold(f"  • 2) [{check_logs}] 📋 Old log files (journalctl, >7 days)")
        print_bold(f"  • 3) [{check_temp}] 🗑️  Temporary files (/tmp, /var/tmp, >7 days)")
        print_bold(f"  • 4) [{check_kernels}] 🪶 Old kernel packages (autoremove)")
        print_bold("  • 5) ✅ All of the above (and proceed)")
        print_bold("  • 6) ▶️  Proceed with selected options")
        print()
        
        # Show current selection status
        selected_count = sum(selected.values())
        if selected_count > 0:
            selected_items = []
            if selected["apt"]:
                selected_items.append("APT cache")
            if selected["logs"]:
                selected_items.append("Old logs")
            if selected["temp"]:
                selected_items.append("Temp files")
            if selected["kernels"]:
                selected_items.append("Old kernels")
            print_info(f"Selected: {', '.join(selected_items)}")
            print()
        
        choice = get_choice_16("Enter your choice (1-6): ")
        if choice is None:  # ESC pressed, return to menu
            return None
        
        # Mark that we've made a selection (so next iteration will clear screen)
        first_iteration = False
        
        if choice == "1":
            selected["apt"] = not selected["apt"]  # Toggle
        elif choice == "2":
            selected["logs"] = not selected["logs"]  # Toggle
        elif choice == "3":
            selected["temp"] = not selected["temp"]  # Toggle
        elif choice == "4":
            selected["kernels"] = not selected["kernels"]  # Toggle
        elif choice == "5":
            # Select all and proceed
            selected = {"apt": True, "logs": True, "temp": True, "kernels": True}
            return selected
        elif choice == "6":
            # Proceed with selected options
            if selected_count == 0:
                print()
                print_error("No options selected. Please select at least one option.")
                continue
            return selected


def _handle_root_requirement(menu_option: str) -> bool:
    """Handle root requirement. Returns True if should continue, False if should return."""
    if is_root():
        return True
    
    print_error("This utility requires root privileges")
    print()
    print_info("Options:")
    print_bold("  1. Restart with sudo (recommended)")
    print_bold("  2. Run manually: sudo ./linux-utilities.py")
    print()
    
    from linux_utils.utils import check_sudo_available, restart_with_sudo
    
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


def perform_disk_cleanup(dry_run: bool = False) -> None:
    """Main function to perform disk cleanup."""
    if not _handle_root_requirement('2'):
        return
    
    print()
    print(format_message("🧹 Disk Cleanup", BOLD_BLUE))
    print()
    
    if dry_run:
        print_info("🔍 Dry run mode - no files will be deleted")
        print()
    
    # Get cleanup options (show_header=True so it reprints the header when clearing)
    options = _get_cleanup_options(show_header=True)
    if options is None:  # ESC pressed, return to menu
        return
    
    # Define cleanup tasks
    cleanup_tasks = [
        ("apt", "📦 Cleaning APT package cache...", "No APT cache to clean", _clean_apt_cache),
        ("logs", "📋 Cleaning old log files...", "No old logs to clean", _clean_old_logs),
        ("temp", "🗑️  Cleaning temporary files...", "No temporary files to clean", _clean_temp_files),
        ("kernels", "🪶 Cleaning old kernel packages...", "No old kernels to clean", _clean_old_kernels),
    ]
    
    total_freed = 0
    print()
    for key, message, no_clean_msg, cleanup_func in cleanup_tasks:
        if options.get(key, False):
            print_bold(message)
            freed = cleanup_func(dry_run)
            total_freed += freed
            if freed > 0:
                action = "Would free" if dry_run else "Freed"
                print_success(f"{action} {_format_size(freed)}")
            else:
                print_info(no_clean_msg)
            print()
    
    # Summary
    print()
    if total_freed > 0:
        action = "Total space that would be freed" if dry_run else "Total space freed"
        print_success(f"{action}: {_format_size(total_freed)}")
    else:
        print_info("No cleanup needed - system is already clean!")
    print()

