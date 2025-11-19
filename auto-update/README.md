# Auto-Update Script

Interactive script to set up automatic APT updates via systemd. Choose to run updates on boot or daily at a specific hour.

## Usage

```bash
sudo ./setup-auto-update.sh
```

Follow the prompts to configure:

- **Option 1**: Run on boot (after network is online)
- **Option 2**: Run daily at a specific hour (0-23)

## Management Commands

```bash
# Check status
sudo systemctl status auto-update.service

# View logs
sudo journalctl -u auto-update.service

# For daily schedule - check timer
sudo systemctl list-timers auto-update.timer

# Disable
sudo systemctl disable auto-update.service  # or auto-update.timer
```

## Files Created

- `/etc/systemd/system/auto-update.service`
- `/etc/systemd/system/auto-update.timer` (for daily schedule)
