"""Output formatting and printing utilities."""

from linux_utils.config import BOLD, GREEN, RED, YELLOW, NC


def _ensure_indent(message: str) -> str:
    """Ensure message has 2-space indent (if it doesn't already have 2+ spaces)."""
    if len(message) >= 2 and message[:2] == "  ":
        return message
    return f"  {message.lstrip()}"


def format_message(message: str, color: str = "") -> str:
    """Format message: always bold, always 2-space indent."""
    return f"{BOLD}{color}{_ensure_indent(message)}{NC}"


def format_unindented(message: str, color: str = "") -> str:
    """Format message: always bold, no indent (for headers/boxes)."""
    return f"{BOLD}{color}{message}{NC}"


def print_bold(message: str, end: str = "\n", flush: bool = False) -> None:
    """Print message in bold with 2-space indent."""
    print(format_message(message), end=end, flush=flush)


def print_error(message: str) -> None:
    """Print error message in red and bold with 2-space indent."""
    print(format_message(f"❌ {message}", RED))


def print_success(message: str) -> None:
    """Print success message in green and bold with 2-space indent."""
    print(format_message(f"✅ {message}", GREEN))


def print_info(message: str) -> None:
    """Print info message in bold with 2-space indent."""
    print(format_message(message))


def print_warning(message: str) -> None:
    """Print warning message in yellow and bold with 2-space indent."""
    print(format_message(f"⚠️  {message}", YELLOW))

