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
from linux_utils.config import BOLD_BLUE, GREEN
from linux_utils.ui import (
    get_yes_no,
    get_choice_16,
    clear_screen,
    getch,
    print_header,
    print_menu,
)
from linux_utils.utils import handle_root_requirement

# Constants for cleanup operations
LOG_RETENTION_DAYS = 7
TEMP_FILE_AGE_DAYS = 7
DRY_RUN_ESTIMATE_RATIO = 0.5  # Assume we can free 50% by keeping last N days
SECONDS_PER_DAY = 24 * 60 * 60
KERNEL_SIZE_ESTIMATE = 200 * 1024 * 1024  # 200MB per kernel
MIN_KERNELS_TO_KEEP = 2  # Keep current + 1 backup


def _get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, OSError):
        pass
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def _clean_apt_cache(dry_run: bool = False) -> int:
    """Clean APT package cache. Returns bytes freed."""
    cache_dir = Path("/var/cache/apt/archives")

    if dry_run:
        # Estimate size
        if cache_dir.exists():
            return _get_directory_size(cache_dir)
        return 0

    try:
        # Get size before cleanup
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
    for line in output.split("\n"):
        if "G" in line:
            try:
                size_str = line.split()[-1].replace("G", "")
                return int(float(size_str) * 1024 * 1024 * 1024)
            except (ValueError, IndexError):
                pass
        elif "M" in line:
            try:
                size_str = line.split()[-1].replace("M", "")
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
            # Rough estimate - assume we can free 50% by keeping last N days
            size_before = _parse_journal_size(result.stdout)
            return int(size_before * DRY_RUN_ESTIMATE_RATIO)

        size_before = _parse_journal_size(result.stdout)

        # Clean logs older than LOG_RETENTION_DAYS
        subprocess.run(
            ["journalctl", f"--vacuum-time={LOG_RETENTION_DAYS}d"],
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
        size_after = (
            _parse_journal_size(result_after.stdout)
            if result_after.returncode == 0
            else 0
        )

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

                # Remove files older than TEMP_FILE_AGE_DAYS
                current_time = time.time()
                age_threshold = current_time - (TEMP_FILE_AGE_DAYS * SECONDS_PER_DAY)

                for item in temp_dir.iterdir():
                    try:
                        if item.stat().st_mtime < age_threshold:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                    except (PermissionError, OSError):
                        pass

                size_after = _get_directory_size(temp_dir)
                total_freed += size_before - size_after
            except Exception as e:
                print_error(f"Error cleaning {temp_dir}: {e}")

    return total_freed


def _count_installed_kernels(output: str) -> int:
    """Count installed kernel packages from dpkg output."""
    return len(
        [line for line in output.split("\n") if "linux-image" in line and "ii" in line]
    )


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
                kernel_count = _count_installed_kernels(result.stdout)
                # Assume we keep current + 1 backup, rest can be removed
                if kernel_count > MIN_KERNELS_TO_KEEP:
                    return (kernel_count - MIN_KERNELS_TO_KEEP) * KERNEL_SIZE_ESTIMATE
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

        # Get list of installed kernels after
        result_after = subprocess.run(
            ["dpkg", "-l", "linux-image-*"],
            capture_output=True,
            text=True,
            check=False,
        )

        kernels_before = _count_installed_kernels(result_before.stdout)
        kernels_after = _count_installed_kernels(result_after.stdout)
        kernels_removed = kernels_before - kernels_after

        return kernels_removed * KERNEL_SIZE_ESTIMATE
    except subprocess.CalledProcessError as e:
        print_error(f"Error cleaning old kernels: {e}")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 0


def _get_cleanup_options(show_header: bool = True) -> dict[str, bool] | None:
    """Get cleanup options from user with multi-selection. Returns None if ESC pressed (return to menu)."""
    selected = {"apt": False, "logs": False, "temp": False, "kernels": False}

    while True:
        clear_screen()

        # Always show main header and menu
        print_header()
        print_menu()

        if show_header:
            print(format_message("🧹 Disk Cleanup", BOLD_BLUE))

        print(format_message("Select what to clean:", BOLD_BLUE))

        # Show options with checkmarks for selected items (green and bold when selected)
        # Always keep everything bold - don't use NC to reset formatting
        # The print_bold wrapper adds BOLD at start, so we just need GREEN for selected checkmarks
        check_apt = f"{GREEN}✓" if selected["apt"] else " "
        check_logs = f"{GREEN}✓" if selected["logs"] else " "
        check_temp = f"{GREEN}✓" if selected["temp"] else " "
        check_kernels = f"{GREEN}✓" if selected["kernels"] else " "

        print_bold(f"  • 1) [{check_apt}] 📦 APT package cache")
        print_bold(f"  • 2) [{check_logs}] 📋 Old log files (journalctl, >7 days)")
        print_bold(
            f"  • 3) [{check_temp}] 🗑️  Temporary files (/tmp, /var/tmp, >7 days)"
        )
        print_bold(f"  • 4) [{check_kernels}] 🪶 Old kernel packages (autoremove)")
        print_bold("  • 5) ✅ All of the above (and proceed)")
        print_bold("  • 6) ▶️  Proceed with selected options")

        # Show current selection status
        selected_count = sum(selected.values())
        if selected_count > 0:
            option_names = {
                "apt": "APT cache",
                "logs": "Old logs",
                "temp": "Temp files",
                "kernels": "Old kernels",
            }
            selected_items = [
                option_names[key] for key, value in selected.items() if value
            ]
            print_info(f"Selected: {', '.join(selected_items)}")

        choice = get_choice_16("Enter your choice (1-6): ")
        if choice is None:  # ESC pressed, return to menu
            return None

        # Toggle options 1-4
        option_map = {
            "1": "apt",
            "2": "logs",
            "3": "temp",
            "4": "kernels",
        }
        if choice in option_map:
            selected[option_map[choice]] = not selected[option_map[choice]]
        elif choice == "5":
            # Select all and proceed
            selected = {"apt": True, "logs": True, "temp": True, "kernels": True}
            print()
            print_info("Selected: APT cache, Old logs, Temp files, Old kernels")
            print()
            confirm = get_yes_no("Proceed with cleaning all options? (y/n): ")
            if confirm is None:  # ESC pressed, return to menu
                return None
            if not confirm:
                continue  # User said no, go back to menu
            return selected
        elif choice == "6":
            # Proceed with selected options
            if selected_count == 0:
                print()
                print_error("No options selected. Please select at least one option.")
                print()
                print_info("Press any key to continue...")
                getch()  # Wait for user to press any key
                continue
            print()
            confirm = get_yes_no("Proceed with cleaning selected options? (y/n): ")
            if confirm is None:  # ESC pressed, return to menu
                return None
            if not confirm:
                continue  # User said no, go back to menu
            return selected


def perform_disk_cleanup(dry_run: bool = False) -> None:
    """Main function to perform disk cleanup."""
    if not handle_root_requirement("2"):
        return

    print(format_message("🧹 Disk Cleanup", BOLD_BLUE))

    if dry_run:
        print_info("🔍 Dry run mode - no files will be deleted")
        print()

    # Get cleanup options (show_header=True so it reprints the header when clearing)
    options = _get_cleanup_options(show_header=True)
    if options is None:  # ESC pressed, return to menu
        return

    # Define cleanup tasks
    cleanup_tasks = [
        (
            "apt",
            "📦 Cleaning APT package cache...",
            "No APT cache to clean",
            _clean_apt_cache,
        ),
        (
            "logs",
            "📋 Cleaning old log files...",
            "No old logs to clean",
            _clean_old_logs,
        ),
        (
            "temp",
            "🗑️  Cleaning temporary files...",
            "No temporary files to clean",
            _clean_temp_files,
        ),
        (
            "kernels",
            "🪶 Cleaning old kernel packages...",
            "No old kernels to clean",
            _clean_old_kernels,
        ),
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
