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
    MSG_RETURN_TO_MENU,
    MSG_EXITING,
    NC,
    BOLD,
)
from linux_utils.output import (
    format_message,
    format_unindented,
    print_bold,
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
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _get_display_width(text: str) -> int:
    """Calculate the display width of text, accounting for emojis and wide characters."""
    # Strip ANSI codes first
    text = _strip_ansi(text)
    width = 0
    for char in text:
        # Check if character is an emoji or wide character
        if unicodedata.east_asian_width(char) in ("W", "F"):
            width += 2  # Wide characters (including most emojis) take 2 columns
        else:
            width += 1  # Regular characters take 1 column
    return width


def _get_menu_items() -> dict[str, tuple[str, bool]]:
    """Get menu items with root requirement flags. Returns dict of (description, needs_sudo)."""
    from linux_utils.utils import is_root

    menu_items = {}
    for key, description in MENU_OPTIONS.items():
        needs_sudo = (key == "1" or key == "2") and not is_root()
        menu_items[key] = (description, needs_sudo)
    return menu_items


def _get_menu_width() -> int:
    """Calculate the menu box width."""
    menu_items = _get_menu_items()
    sudo_text = f" {YELLOW}(needs sudo){NC}"
    sudo_width = _get_display_width(sudo_text)

    max_width = 0
    for key, (description, needs_sudo) in menu_items.items():
        base_line = f"  {key}. {description}"
        if needs_sudo:
            line_width = _get_display_width(base_line) + sudo_width
        else:
            line_width = _get_display_width(base_line)
        max_width = max(max_width, line_width)

    return max_width + 8


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
        print(
            format_unindented(
                " " * left_padding + stripped + " " * right_padding, BOLD_BLUE
            )
        )
    print()


def _draw_box_border(width: int, left: str, right: str) -> str:
    """Draw a box border line."""
    return left + "═" * (width - 2) + right


def _print_menu_line(base_text: str, needs_sudo: bool, width: int) -> None:
    """Print a single menu line with borders, with (needs sudo) right-aligned if needed."""
    sudo_text = f"{YELLOW}(needs sudo){NC}"
    base_width = _get_display_width(base_text)
    sudo_width = _get_display_width(sudo_text) if needs_sudo else 0

    # -3 accounts for: left border (1) + left space (1) + right border (1)
    available_width = width - 3
    padding = max(0, available_width - base_width - sudo_width)

    print(format_unindented("║", BOLD_BLUE), end="")
    if needs_sudo:
        print(f"{BOLD} {base_text}{' ' * padding}{sudo_text}{NC}", end="")
    else:
        print(f"{BOLD} {base_text}{' ' * padding}{NC}", end="")
    print(format_unindented("║", BOLD_BLUE))


def print_menu() -> None:
    """Print the main menu with retro pixel borders."""
    menu_items = _get_menu_items()
    width = _get_menu_width()

    print(format_unindented(_draw_box_border(width, "╔", "╗"), BOLD_BLUE))
    for key, (description, needs_sudo) in menu_items.items():
        base_text = f"  {key}. {description}"
        _print_menu_line(base_text, needs_sudo, width)
    print(format_unindented(_draw_box_border(width, "╚", "╝"), BOLD_BLUE))


def wait_for_key(message: str = MSG_RETURN_TO_MENU) -> None:
    """Wait for user to press any key."""
    print(format_message(message), end="", flush=True)
    getch()


# Constants for UI behavior
CLEAR_LINE_WIDTH = 60
ESC_TIMEOUT_SHORT = 0.15
ESC_TIMEOUT_LONG = 0.05

_CLEAR_LINE = "\r" + " " * CLEAR_LINE_WIDTH + "\r"


def _handle_esc_key() -> bool:
    """Handle ESC key press. Returns True if ESC was pressed (should return None), False otherwise."""
    if not getch_timeout(ESC_TIMEOUT_SHORT):
        print(_CLEAR_LINE, end="", flush=True)
        return True
    while getch_timeout(ESC_TIMEOUT_LONG):
        pass
    print(_CLEAR_LINE, end="", flush=True)
    return True


def _get_choice_with_esc(prompt: str, valid_choices: set[str]) -> str | None:
    """Generic function to get choice with ESC handling."""
    while True:
        print(format_message(prompt), end="", flush=True)
        choice = getch()

        if ord(choice) == ESC_KEY:
            if _handle_esc_key():
                return None
            continue  # ESC handled, continue to next iteration

        choice = choice.strip()

        # Only print and accept valid choices
        if choice in valid_choices:
            print(choice)
            return choice
        # Invalid choice - silently ignore, don't print anything
        print(_CLEAR_LINE, end="", flush=True)


def get_yes_no(prompt: str) -> bool | None:
    """Get yes/no input without requiring Enter. Returns True for yes, False for no, None for ESC (return to menu)."""
    choice = _get_choice_with_esc(prompt, {"y", "n"})
    if choice is None:
        return None
    return choice == "y"


def get_choice_12(prompt: str) -> str | None:
    """Get 1 or 2 choice without requiring Enter. Returns '1' or '2', None for ESC (return to menu)."""
    return _get_choice_with_esc(prompt, {"1", "2"})


def get_choice_16(prompt: str) -> str | None:
    """Get 1-6 choice without requiring Enter. Returns '1'-'6', None for ESC (return to menu)."""
    return _get_choice_with_esc(prompt, {"1", "2", "3", "4", "5", "6"})


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
    from linux_utils.disk_cleanup import perform_disk_cleanup

    perform_disk_cleanup()


def run_system_report() -> None:
    """Run system report utility."""
    from linux_utils.system_report import generate_system_report

    generate_system_report()


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
    print_bold("   - APT cache, old logs, temp files, old kernels")
    print_bold("   - Requires root privileges")
    print()
    print_bold("3. 📊 System Report")
    print_bold("   - Generate comprehensive system information reports")
    print_bold("   - Shows OS, CPU, memory, disk, network, and uptime")
    print()
    print_bold("4. ❓ Help")
    print_bold("   - Shows this help information")
    print()
    print_bold("5. 🚪 Exit")
    print_bold("   - Exits the application")
    print()

    print(format_message("Tips:"))
    print()
    print_bold("• Press ESC to return to menu at any time (during prompts)")
    print_bold("• Press ESC in main menu to exit")
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
        menu_actions[choice]()
        print(format_message("─" * 50))
        wait_for_key(MSG_RETURN_TO_MENU)
    elif choice in ("q", "5"):
        exit_app()


def get_user_choice() -> str:
    """Get user menu choice."""
    valid_choices = {"1", "2", "3", "4", "5", "q"}
    while True:
        print(format_message("  Press [1-5] to select: "), end="", flush=True)
        choice = getch()

        if ord(choice) == ESC_KEY:
            if not getch_timeout(ESC_TIMEOUT_SHORT):
                exit_app()
            while getch_timeout(ESC_TIMEOUT_LONG):
                pass
            print(_CLEAR_LINE, end="", flush=True)
            continue

        choice = choice.strip().lower()
        # Only print and accept valid choices
        if choice in valid_choices:
            print(choice)
            return choice
        # Invalid choice - silently ignore, don't print anything
        print(_CLEAR_LINE, end="", flush=True)
