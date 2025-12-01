"""Main entry point for Linux Utilities."""

import sys

from linux_utils.ui import (
    clear_screen,
    print_header,
    print_menu,
    get_user_choice,
    handle_menu_choice,
)


def main() -> None:
    """Main entry point."""
    # Check for command-line arguments to jump to a menu option
    jump_to_option = None
    if '--option' in sys.argv:
        idx = sys.argv.index('--option')
        if idx + 1 < len(sys.argv):
            jump_to_option = sys.argv[idx + 1]
    
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        # If we have a jump option, use it once then continue normally
        choice = jump_to_option if jump_to_option else get_user_choice()
        if jump_to_option:
            jump_to_option = None  # Clear it so we don't loop on it
        
        handle_menu_choice(choice)


if __name__ == "__main__":
    main()

