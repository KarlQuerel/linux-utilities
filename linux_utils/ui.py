"""User interface components for Linux Utilities."""

import os
import re
import sys
import termios
import tty
import unicodedata

from linux_utils.config import (
    BOLD_BLUE,
    YELLOW,
    ESC_KEY,
    MENU_OPTIONS,
    MSG_WAIT_KEY,
    MSG_EXITING,
    NC,
    BOLD,
)
from linux_utils.output import (
    format_message,
    format_unindented,
    print_bold,
    print_info,
)


def _setup_raw_input() -> tuple[int, list]:
    """Setup terminal for raw input. Returns (fd, old_settings)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    return fd, old_settings


def getch() -> str:
    """Read a single character from stdin without requiring Enter."""
    fd, old_settings = _setup_raw_input()
    try:
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def getch_timeout(timeout: float = 0.1) -> str:
    """Read a single character with timeout. Returns empty string if timeout."""
    fd, old_settings = _setup_raw_input()
    try:
        new_settings = termios.tcgetattr(fd)
        new_settings[6][termios.VMIN] = 0
        new_settings[6][termios.VTIME] = int(timeout * 10)
        termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
        return sys.stdin.read(1) or ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def _get_display_width(text: str) -> int:
    """Calculate the display width of text, accounting for emojis and wide characters."""
    # Strip ANSI codes first
    text = _strip_ansi(text)
    width = 0
    for char in text:
        # Check if character is an emoji or wide character
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2  # Wide characters (including most emojis) take 2 columns
        else:
            width += 1  # Regular characters take 1 column
    return width


def _get_menu_items() -> dict[str, str]:
    """Get menu items with root warnings if needed."""
    from linux_utils.utils import is_root
    
    menu_items = {}
    for key, description in MENU_OPTIONS.items():
        if key == "1" and not is_root():  # Auto-update requires root
            menu_items[key] = f"{description} {YELLOW}(needs sudo){NC}"
        else:
            menu_items[key] = description
    return menu_items


def _get_menu_width() -> int:
    """Calculate the menu box width."""
    menu_items = _get_menu_items()
    menu_lines = [f"  {key}. {description}" for key, description in menu_items.items()]
    return max(_get_display_width(line) for line in menu_lines) + 8


def print_header() -> None:
    """Print the application header centered above the menu."""
    print()
    header_art = [
        "   ▖ ▄▖▖ ▖▖▖▖▖  ▖▖▄▖▄▖▖ ▄▖▄▖▄▖▄▖▄▖",
        "   ▌ ▐ ▛▖▌▌▌▚▘  ▌▌▐ ▐ ▌ ▐ ▐ ▐ ▙▖▚ ",
        "   ▙▖▟▖▌▝▌▙▌▌▌  ▙▌▐ ▟▖▙▖▟▖▐ ▟▖▙▖▄▌",
    ]
    menu_width = _get_menu_width()
    
    for line in header_art:
        stripped = line.lstrip()
        line_width = _get_display_width(stripped)
        left_padding = (menu_width - line_width) // 2
        right_padding = menu_width - line_width - left_padding
        print(format_unindented(" " * left_padding + stripped + " " * right_padding, BOLD_BLUE))
    print()


def _draw_box_border(width: int, left: str, right: str) -> str:
    """Draw a box border line."""
    return left + "═" * (width - 2) + right


def _print_menu_line(line: str, width: int) -> None:
    """Print a single menu line with borders, centered."""
    line_width = _get_display_width(line)
    # -3 accounts for: left border (1) + left space (1) + right border (1)
    right_padding = max(0, width - line_width - 3)
    
    print(format_unindented("║", BOLD_BLUE), end="")
    print(f"{BOLD} {line}{' ' * right_padding}{NC}", end="")
    print(format_unindented("║", BOLD_BLUE))


def print_menu() -> None:
    """Print the main menu with retro pixel borders."""
    menu_items = _get_menu_items()
    menu_lines = [f"  {key}. {description}" for key, description in menu_items.items()]
    width = _get_menu_width()

    print(format_unindented(_draw_box_border(width, "╔", "╗"), BOLD_BLUE))
    for line in menu_lines:
        _print_menu_line(line, width)
    print(format_unindented(_draw_box_border(width, "╚", "╝"), BOLD_BLUE))
    print()


def wait_for_key(message: str = MSG_WAIT_KEY) -> None:
    """Wait for user to press any key."""
    print(format_message(message), end="", flush=True)
    getch()


_CLEAR_LINE = "\r" + " " * 60 + "\r"


def get_yes_no(prompt: str) -> bool:
    """Get yes/no input without requiring Enter. Returns True for yes, False for no."""
    while True:
        print(format_message(prompt), end="", flush=True)
        choice = getch().strip().lower()
        print(choice)
        
        if choice == 'y':
            return True
        if choice == 'n':
            return False
        # Invalid choice, clear and retry
        print(_CLEAR_LINE, end="", flush=True)


def get_choice_12(prompt: str) -> str:
    """Get 1 or 2 choice without requiring Enter. Returns '1' or '2'."""
    while True:
        print(format_message(prompt), end="", flush=True)
        choice = getch().strip()
        print(choice)
        
        if choice in ('1', '2'):
            return choice
        # Invalid choice, clear and retry
        print(_CLEAR_LINE, end="", flush=True)


def exit_app(message: str = MSG_EXITING) -> None:
    """Exit the application with a message."""
    print(f"\n{format_message(message)}")
    sys.exit(0)


def run_auto_update() -> None:
    """Run the auto-update setup."""
    from linux_utils.auto_update import setup_auto_update
    setup_auto_update()


def run_disk_cleanup() -> None:
    """Run disk cleanup utility."""
    print()
    print(format_message("🧹 Disk Cleanup", BOLD_BLUE))
    print()
    print_info("This feature is coming soon!")
    print()
    print_bold("It will clean:")
    print_bold("  • APT package cache")
    print_bold("  • Old log files")
    print_bold("  • Temporary files")
    print_bold("  • Old kernel packages (optional)")
    print()


def run_system_report() -> None:
    """Run system report utility."""
    print()
    print(format_message("📊 System Report", BOLD_BLUE))
    print()
    print_info("This feature is coming soon!")
    print()
    print_bold("It will show:")
    print_bold("  • System hardware information")
    print_bold("  • OS version and kernel")
    print_bold("  • Disk and memory usage")
    print_bold("  • Network configuration")
    print_bold("  • Running services")
    print()


def show_help() -> None:
    """Display help information."""
    print()
    print(format_message("❓ Help & Information", BOLD_BLUE))
    print()
    print(format_message("Menu Options:"))
    print()
    print_bold("1. 🚀 Auto-Update Setup")
    print_bold("   - Set up automatic APT updates via systemd")
    print_bold("   - Configure to run on boot or daily schedule")
    print_bold("   - Will prompt for sudo automatically when needed")
    print()
    print_bold("2. 🧹 Disk Cleanup")
    print_bold("   - Clean up disk space by removing unnecessary files")
    print_bold("   - Coming soon!")
    print()
    print_bold("3. 📊 System Report")
    print_bold("   - Generate comprehensive system information reports")
    print_bold("   - Coming soon!")
    print()
    print_bold("4. ❓ Help")
    print_bold("   - Shows this help information")
    print()
    print_bold("5. 🚪 Exit")
    print_bold("   - Exits the application")
    print()
    
    print(format_message("Tips:"))
    print()
    print_bold("• Press ESC to exit anytime")
    print_bold("• Auto-Update will prompt for sudo automatically when needed")
    print_bold("• No need to run with sudo upfront - the tool handles it!")
    print()


def handle_menu_choice(choice: str) -> None:
    """Handle user menu choice."""
    menu_actions = {
        "1": run_auto_update,
        "2": run_disk_cleanup,
        "3": run_system_report,
        "4": show_help,
    }
    
    if choice in menu_actions:
        print()
        menu_actions[choice]()
        print()
        wait_for_key()
    elif choice in ("q", "5"):
        exit_app()


def get_user_choice() -> str:
    """Get user menu choice."""
    while True:
        print(format_message("  Press [1-5] to select: "), end="", flush=True)
        choice = getch()

        if ord(choice) == ESC_KEY:
            if not getch_timeout(0.15):
                exit_app()
            while getch_timeout(0.05):
                pass
            print(_CLEAR_LINE, end="", flush=True)
            continue

        choice = choice.strip().lower()
        if choice in ("1", "2", "3", "4", "5", "q"):
            print(choice)
            return choice

        print(_CLEAR_LINE, end="", flush=True)

