#!/bin/bash

# Script to set up automatic APT update and upgrade
# This creates a systemd service that runs apt update and apt upgrade -y
# Can be configured to run on boot or daily at a specific hour

set -e  # Exit on error

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Emoji definitions
ROCKET="🚀"
GEAR="⚙️"
CHECK="✅"
CROSS="❌"
INFO="ℹ️"
CLOCK="🕐"
CALENDAR="📅"
COMPUTER="💻"
WRENCH="🔧"
BULLET="•"

SERVICE_FILE="/etc/systemd/system/auto-update.service"
TIMER_FILE="/etc/systemd/system/auto-update.timer"
SERVICE_NAME="auto-update.service"
TIMER_NAME="auto-update.timer"

# Helper functions for colored output
print_success() {
	echo -e "${GREEN}${CHECK}${NC} ${1}"
}

print_error() {
	echo -e "${RED}${CROSS}${NC} ${1}"
}

print_info() {
	echo -e "${BLUE}${INFO}${NC} ${1}"
}

print_warning() {
	echo -e "${YELLOW}⚠️${NC} ${1}"
}

print_header() {
	echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
	echo -e "${BOLD}${CYAN}  ${ROCKET}  Automatic APT Update & Upgrade Setup  ${ROCKET}${NC}"
	echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Helper function to disable a service if it's enabled
disable_service_if_enabled() {
	local service_name="$1"
	if systemctl is-enabled "$service_name" &>/dev/null; then
		systemctl disable "$service_name" 2>/dev/null || true
	fi
}

# Helper function to get schedule type from user
get_schedule_type() {
	local choice
	while true; do
		echo -e "${BOLD}${MAGENTA}${CALENDAR} When should the update run?${NC}\n" >&2
		echo -e "  ${BULLET} ${BOLD}1)${NC} ${COMPUTER} On boot (after network is online)" >&2
		echo -e "  ${BULLET} ${BOLD}2)${NC} ${CLOCK} Daily at a specific hour\n" >&2
		read -p "$(echo -e ${CYAN}Enter your choice ${BOLD}\(1 or 2\):${NC} ) " choice
		
		case "$choice" in
			1)
				echo "boot"
				return 0
				;;
			2)
				echo "daily"
				return 0
				;;
			*)
				print_error "Invalid choice. Please enter 1 or 2.\n" >&2
				;;
		esac
	done
}

# Helper function to get hour from user
get_hour() {
	local hour
	while true; do
		read -p "$(echo -e ${CYAN}${CLOCK} Enter the hour ${BOLD}\(0-23, 24-hour format\):${NC} ) " hour
		if [[ "$hour" =~ ^[0-9]+$ ]] && [ "$hour" -ge 0 ] && [ "$hour" -le 23 ]; then
			echo "$hour"
			return 0
		else
			print_error "Invalid hour. Please enter a number between 0 and 23.\n" >&2
		fi
	done
}

# Setup boot schedule
setup_boot_schedule() {
	disable_service_if_enabled "$TIMER_NAME"
		
	echo -e "\n${BOLD}${GEAR} Configuring service to run on boot...${NC}"
	systemctl daemon-reload
	systemctl enable "$SERVICE_NAME"
	print_success "Service enabled ${BOLD}(will run on boot)${NC}"
		
	# Ask if user wants to run it immediately
	echo ""
	local run_now
	read -p "$(echo -e ${CYAN}Do you want to run the update now? ${BOLD}\(y/n\):${NC} ) " run_now
	if [[ "$run_now" =~ ^[Yy]$ ]]; then
		echo -e "\n${BOLD}Starting $SERVICE_NAME...${NC}"
		systemctl start "$SERVICE_NAME"
		print_success "Service started"
	fi
		
	echo ""
	echo -e "${GREEN}${BOLD}${CHECK} Setup complete!${NC}"
	echo -e "${GREEN}The service will automatically run ${BOLD}'apt update && apt upgrade -y'${NC}${GREEN} on each reboot.${NC}"
}

# Setup daily schedule
setup_daily_schedule() {
	local hour="$1"
		
	disable_service_if_enabled "$SERVICE_NAME"
		
	# Create the timer file
	cat > "$TIMER_FILE" << EOF
[Unit]
Description=Automatic APT Update and Upgrade Timer
Requires=$SERVICE_NAME

[Timer]
OnCalendar=daily
OnCalendar=*-*-* $hour:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
		
	print_success "Timer file created at ${CYAN}$TIMER_FILE${NC}"
		
	# Reload systemd daemon
	echo -e "\n${BOLD}${GEAR} Reloading systemd daemon...${NC}"
	systemctl daemon-reload
	print_success "Daemon reloaded"
		
	# Enable and start the timer
	echo -e "\n${BOLD}Enabling $TIMER_NAME...${NC}"
	systemctl enable "$TIMER_NAME"
	print_success "Timer enabled"
		
	echo -e "\n${BOLD}Starting $TIMER_NAME...${NC}"
	systemctl start "$TIMER_NAME"
	print_success "Timer started"
		
	# Show next run time
	local next_run
	next_run=$(systemctl list-timers "$TIMER_NAME" --no-pager 2>/dev/null | grep "$TIMER_NAME" | awk '{print $1, $2, $3, $4, $5}')
	echo ""
	echo -e "${GREEN}${BOLD}${CHECK} Setup complete!${NC}"
	echo -e "${GREEN}The service will automatically run ${BOLD}'apt update && apt upgrade -y'${NC}${GREEN} daily at ${BOLD}${hour}:00${NC}${GREEN}.${NC}"
	if [ -n "$next_run" ]; then
		echo -e "\n${CYAN}${CLOCK} Next scheduled run: ${BOLD}$next_run${NC}"
	fi
}

# Print helpful commands based on schedule type
print_helpful_commands() {
	local schedule_type="$1"
		
	echo ""
	echo -e "${BOLD}${MAGENTA}${WRENCH} Useful commands:${NC}\n"
		
	if [ "$schedule_type" = "boot" ]; then
		echo -e "  ${BULLET} ${CYAN}Check service status:${NC} ${BOLD}sudo systemctl status $SERVICE_NAME${NC}"
		echo -e "  ${BULLET} ${CYAN}View service logs:${NC} ${BOLD}sudo journalctl -u $SERVICE_NAME${NC}"
		echo -e "  ${BULLET} ${CYAN}Disable the service:${NC} ${BOLD}sudo systemctl disable $SERVICE_NAME${NC}"
	else
		echo -e "  ${BULLET} ${CYAN}Check timer status:${NC} ${BOLD}sudo systemctl status $TIMER_NAME${NC}"
		echo -e "  ${BULLET} ${CYAN}View timer list:${NC} ${BOLD}sudo systemctl list-timers $TIMER_NAME${NC}"
		echo -e "  ${BULLET} ${CYAN}View service logs:${NC} ${BOLD}sudo journalctl -u $SERVICE_NAME${NC}"
		echo -e "  ${BULLET} ${CYAN}Disable the timer:${NC} ${BOLD}sudo systemctl disable $TIMER_NAME${NC}"
	fi
	echo ""
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
	print_error "This script must be run as root (use sudo)"
	exit 1
fi

print_header
print_info "Setting up automatic APT update and upgrade service...\n"

# Get schedule type from user
SCHEDULE_TYPE=$(get_schedule_type)

# If daily, get the hour
if [ "$SCHEDULE_TYPE" = "daily" ]; then
	echo ""
	hour=$(get_hour)
	echo ""
fi

# Create the systemd service file
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Automatic APT Update and Upgrade
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c "export DEBIAN_FRONTEND=noninteractive; apt update; apt upgrade -y"
User=root

[Install]
WantedBy=multi-user.target
EOF

print_success "Service file created at ${CYAN}$SERVICE_FILE${NC}"

# Handle scheduling based on user choice
if [ "$SCHEDULE_TYPE" = "boot" ]; then
	setup_boot_schedule
elif [ "$SCHEDULE_TYPE" = "daily" ]; then
	setup_daily_schedule "$hour"
fi

print_helpful_commands "$SCHEDULE_TYPE"

