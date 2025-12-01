"""System report functionality - Generate comprehensive system information reports."""

import platform
import subprocess
import time
from pathlib import Path

from linux_utils.output import (
    print_bold,
    format_message,
)
from linux_utils.config import BOLD_BLUE, PREFIX_WIDTH


def _run_command(cmd: list[str], default: str = "N/A") -> str:
    """Run a command and return its output, or default if it fails."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return default


def _get_os_info() -> dict[str, str]:
    """Get operating system information."""
    info = {}
    
    # Try to read /etc/os-release
    os_release = Path("/etc/os-release")
    if os_release.exists():
        try:
            content = os_release.read_text()
            for line in content.split('\n'):
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == "PRETTY_NAME":
                        info["OS"] = value
                    elif key == "VERSION_ID":
                        info["Version"] = value
        except Exception:
            pass
    
    # Fallback to platform module
    if "OS" not in info:
        info["OS"] = platform.system()
    
    # Kernel information
    kernel = _run_command(["uname", "-r"])
    info["Kernel"] = kernel if kernel != "N/A" else platform.release()
    
    # Architecture
    info["Architecture"] = platform.machine()
    
    # Hostname
    hostname = _run_command(["hostname"])
    info["Hostname"] = hostname if hostname != "N/A" else platform.node()
    
    return info


def _get_cpu_info() -> dict[str, str]:
    """Get CPU information."""
    info = {}
    
    # Try to read /proc/cpuinfo
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        try:
            content = cpuinfo.read_text()
            max_processor = -1
            for line in content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "model name" and "CPU" not in info:
                        info["CPU"] = value
                    elif key == "cpu cores" and "Cores" not in info:
                        info["Cores"] = value
                    elif key == "processor":
                        # Count processors for threads
                        try:
                            processor_num = int(value)
                            max_processor = max(max_processor, processor_num)
                        except ValueError:
                            pass
            
            if max_processor >= 0:
                info["Threads"] = str(max_processor + 1)
        except Exception:
            pass
    
    # Fallback
    if "CPU" not in info:
        info["CPU"] = platform.processor() or "Unknown"
    
    return info


def _get_memory_info() -> dict[str, str]:
    """Get memory information including swap."""
    info = {}
    
    # Try free command
    free_output = _run_command(["free", "-h"])
    if free_output != "N/A":
        lines = free_output.split('\n')
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 2:
                    info["Total"] = parts[1]
                    if len(parts) >= 3:
                        info["Used"] = parts[2]
                    if len(parts) >= 4:
                        info["Free"] = parts[3]
            elif line.startswith("Swap:"):
                parts = line.split()
                if len(parts) >= 2:
                    info["Swap Total"] = parts[1]
                    if len(parts) >= 3:
                        info["Swap Used"] = parts[2]
    
    return info


def _get_disk_info() -> list[dict[str, str]]:
    """Get disk usage information for important mounted filesystems."""
    disks = []
    
    # Use df command for all filesystems
    df_output = _run_command(["df", "-h"])
    if df_output != "N/A":
        lines = df_output.split('\n')
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 6:
                mount_point = parts[5]
                filesystem = parts[0]
                # Filter out virtual filesystems but keep important ones
                skip_patterns = ['tmpfs', 'devtmpfs', 'sysfs', 'proc', 'devpts', 'cgroup']
                if any(filesystem.startswith(pattern) for pattern in skip_patterns):
                    continue
                # Keep root, home, and other important mount points
                if mount_point == '/' or mount_point.startswith('/home') or mount_point.startswith('/boot'):
                    disks.append({
                        "Filesystem": filesystem,
                        "Size": parts[1],
                        "Used": parts[2],
                        "Avail": parts[3],
                        "Use%": parts[4],
                        "Mounted": mount_point,
                    })
                # Also include if it's a real block device and not in /sys, /proc, /dev, /run
                elif filesystem.startswith('/dev/') and not any(mount_point.startswith(x) for x in ['/sys', '/proc', '/dev', '/run']):
                    disks.append({
                        "Filesystem": filesystem,
                        "Size": parts[1],
                        "Used": parts[2],
                        "Avail": parts[3],
                        "Use%": parts[4],
                        "Mounted": mount_point,
                    })
    
    return disks


def _get_network_info() -> dict[str, dict[str, str]]:
    """Get network interface information with IPs and MAC addresses."""
    interfaces = {}
    
    # Use ip command if available
    ip_output = _run_command(["ip", "addr", "show"])
    if ip_output != "N/A":
        current_interface = None
        for line in ip_output.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('inet') and not line.startswith('link'):
                # Interface name
                parts = line.split(':')
                if len(parts) >= 2:
                    current_interface = parts[1].strip().split()[0]
                    if current_interface not in interfaces:
                        interfaces[current_interface] = {"ips": [], "mac": ""}
            elif line.startswith('inet ') and current_interface:
                # IP address
                parts = line.split()
                if len(parts) >= 2:
                    ip_addr = parts[1].split('/')[0]
                    interfaces[current_interface]["ips"].append(ip_addr)
            elif line.startswith('link/ether ') and current_interface:
                # MAC address
                parts = line.split()
                if len(parts) >= 2:
                    interfaces[current_interface]["mac"] = parts[1]
    
    return interfaces


def _get_load_average() -> str:
    """Get system load average."""
    loadavg = Path("/proc/loadavg")
    if loadavg.exists():
        try:
            content = loadavg.read_text()
            parts = content.split()
            if len(parts) >= 3:
                return f"{parts[0]}, {parts[1]}, {parts[2]}"
        except Exception:
            pass
    return "N/A"


def _get_process_count() -> str:
    """Get number of running processes."""
    try:
        proc = Path("/proc")
        if proc.exists():
            count = sum(1 for p in proc.iterdir() if p.name.isdigit())
            return str(count)
    except Exception:
        pass
    return "N/A"


def _get_logged_in_users() -> str:
    """Get number of logged in users."""
    users_output = _run_command(["who", "-q"])
    if users_output != "N/A":
        lines = users_output.split('\n')
        for line in lines:
            if 'users' in line.lower() and '=' in line:
                # Format: "# users=1"
                parts = line.split('=')
                if len(parts) >= 2:
                    return parts[1].strip()
    # Fallback: count unique users
    who_output = _run_command(["who"])
    if who_output != "N/A":
        users = set()
        for line in who_output.split('\n'):
            if line.strip():
                parts = line.split()
                if parts:
                    users.add(parts[0])
        return str(len(users)) if users else "0"
    return "N/A"


def _get_boot_time() -> str:
    """Get system boot time."""
    uptime_sec = _run_command(["cat", "/proc/uptime"])
    if uptime_sec != "N/A":
        try:
            seconds = float(uptime_sec.split()[0])
            boot_time = time.time() - seconds
            boot_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time))
            return boot_time_str
        except (ValueError, IndexError):
            pass
    return "N/A"


def _get_uptime() -> str:
    """Get system uptime."""
    uptime_sec = _run_command(["cat", "/proc/uptime"])
    if uptime_sec != "N/A":
        try:
            seconds = float(uptime_sec.split()[0])
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            minutes = int((seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except (ValueError, IndexError):
            pass
    
    # Fallback to uptime command
    uptime = _run_command(["uptime", "-p"])
    if uptime != "N/A":
        return uptime.replace("up ", "")
    
    return "N/A"


def _print_info_line(label: str, value: str) -> None:
    """Print a formatted info line with consistent spacing."""
    print(format_message(f"{label:<{PREFIX_WIDTH}} {value}"))


def _print_section(title: str) -> None:
    """Print a section title."""
    print(format_message(f"{title}:", BOLD_BLUE))


def generate_system_report() -> None:
    """Generate and display comprehensive system report."""
    print()
    print(format_message("📊 System Report", BOLD_BLUE))
    print()
    
    # OS Information
    _print_section("Operating System")
    os_info = _get_os_info()
    for key, value in os_info.items():
        _print_info_line(f"  - {key}:", value)
    
    # CPU Information
    _print_section("CPU")
    cpu_info = _get_cpu_info()
    for key, value in cpu_info.items():
        _print_info_line(f"  - {key}:", value)
    load_avg = _get_load_average()
    _print_info_line("  - Load Average:", load_avg)
    
    # Memory Information
    _print_section("Memory")
    mem_info = _get_memory_info()
    if mem_info:
        for key, value in mem_info.items():
            _print_info_line(f"  - {key}:", value)
    else:
        _print_info_line("  - Status:", "Unable to retrieve memory information")
    
    # Disk Information - more compact
    _print_section("Disk Usage")
    disk_info = _get_disk_info()
    if disk_info:
        for disk in disk_info:
            mount = disk.get("Mounted", "N/A")
            size = disk.get("Size", "N/A")
            used = disk.get("Used", "N/A")
            avail = disk.get("Avail", "N/A")
            use_pct = disk.get("Use%", "N/A")
            _print_info_line(f"  - {mount}:", f"{size} total, {used} used, {avail} free ({use_pct})")
    else:
        _print_info_line("  - Status:", "Unable to retrieve disk information")
    
    # Network Information - only show interfaces with IPs
    _print_section("Network Interfaces")
    network_info = _get_network_info()
    if network_info:
        has_interfaces = False
        for interface, data in network_info.items():
            ips = data.get("ips", [])
            mac = data.get("mac", "")
            if ips:
                has_interfaces = True
                ip_str = ", ".join(ips)
                if mac:
                    _print_info_line(f"  - {interface}:", f"{ip_str} (MAC: {mac})")
                else:
                    _print_info_line(f"  - {interface}:", ip_str)
        if not has_interfaces:
            _print_info_line("  - Status:", "No interfaces with IP addresses")
    else:
        _print_info_line("  - Status:", "Unable to retrieve network information")
    
    # System Information
    _print_section("System")
    uptime = _get_uptime()
    _print_info_line("  - Uptime:", uptime)
    boot_time = _get_boot_time()
    _print_info_line("  - Boot Time:", boot_time)
    process_count = _get_process_count()
    _print_info_line("  - Processes:", process_count)
    users = _get_logged_in_users()
    _print_info_line("  - Logged In Users:", users)
    
    print()

