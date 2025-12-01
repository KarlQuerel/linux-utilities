# Linux Utilities

Collection of Linux utility scripts and systemd services to automate common tasks.

## Quick Start

```bash
# Make the script executable (if not already)
chmod +x linux-utilities.py

# Run the interactive menu
./linux-utilities.py
```

**No dependencies required!** Uses only Python standard library.

## Usage

Interactive menu:
- **1** - 🚀 Auto-Update Setup
- **2** - 🧹 Disk Cleanup
- **3** - 📊 System Report
- **4** - ❓ Help
- **5** - 🚪 Exit

Press `ESC` to exit anytime.

## Installation

1. Clone this repository
2. Make the script executable:
   ```bash
   chmod +x linux-utilities.py
   ```
3. Run it:
   ```bash
   ./linux-utilities.py
   ```

## Utilities

### 🚀 Auto-Update Setup

Set up automatic APT updates via systemd. Configure updates to run on boot or on a daily schedule.

**Note:** Requires root privileges. The tool will automatically prompt you to restart with sudo if needed - no need to run with sudo upfront!

### 🧹 Disk Cleanup

Clean up disk space by removing unnecessary files:
- APT package cache
- Old log files (journalctl, older than 7 days)
- Temporary files (/tmp, /var/tmp, older than 7 days)
- Old kernel packages (autoremove)

**Note:** Requires root privileges. The tool will automatically prompt you to restart with sudo if needed.

### 📊 System Report

Generate comprehensive system information reports including:
- Operating system and kernel version
- CPU information (model, cores, threads)
- Memory usage (total, used, free)
- Disk usage and filesystem information
- Network interfaces and IP addresses
- System uptime

## Project Structure

```
linux-utilities/
├── linux-utilities.py      # Main executable entry point
├── linux_utils/            # Python package
│   ├── main.py            # Main entry point
│   ├── ui.py              # Menu interface and UI components
│   ├── config.py          # Configuration constants
│   ├── output.py          # Output formatting utilities
│   ├── auto_update.py      # Auto-update functionality
│   ├── disk_cleanup.py     # Disk cleanup functionality
│   ├── system_report.py    # System report functionality
│   └── utils.py            # Utility functions
└── README.md
```

## Features

- **Menu-driven interface** - Easy navigation with numbered options
- **No dependencies** - Uses only Python standard library
- **Interactive** - Press keys directly, no need to press Enter
- **Clean UI** - Beautiful terminal interface with colors and formatting
