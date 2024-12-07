"""System utilities for WiFi and system operations."""

import re
import subprocess
import ipaddress
from typing import Dict, List, Union, Optional


def is_valid_hostname(hostname: str) -> bool:
    """Check if the hostname is valid according to RFC 1123."""
    if len(hostname) > 255:
        return False
    hostname_regex = re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
    return bool(hostname_regex.match(hostname))


def is_valid_ip(ip: str) -> bool:
    """Check if the string is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


async def get_wifi_info() -> Union[Dict[str, str], str]:
    """Get current WiFi connection information.

    Returns:
        dict: WiFi connection details including:
            - device: WiFi device name (e.g., wlan0)
            - mac: MAC address of the WiFi device
            - ssid: Network name
            - signal: Signal strength
            - ip: IP address
            - netmask: Network mask
            - gateway: Gateway address
        str: Error message if there was a problem getting the information
    """
    try:
        # Get the active WiFi device name
        device_info = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"]).decode()
        wifi_device = None
        for line in device_info.split("\n"):
            if line.strip():
                dev, typ, state = line.split(":")
                if typ == "wifi" and state == "connected":
                    wifi_device = dev
                    break
        
        if not wifi_device:
            return "No active WiFi connection found"

        # Get SSID and signal strength using nmcli
        nmcli_output = subprocess.check_output(["nmcli", "-t", "-f", "SIGNAL,SSID,IN-USE", "device", "wifi", "list"]).decode()
        ssid = None
        signal = None
        for line in nmcli_output.split("\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) >= 3 and parts[2] == "*":  # Connected network has "*" in IN-USE field
                    signal = parts[0]
                    ssid = parts[1]
                    break

        # Get IP information and MAC address using the detected WiFi device
        ip_info = subprocess.check_output(["ip", "addr", "show", wifi_device]).decode()
        ip_address = None
        netmask = None
        mac_address = None
        for line in ip_info.split("\n"):
            line = line.strip()
            if "link/ether" in line:
                mac_address = line.split()[1]
            elif "inet " in line:
                parts = line.split()
                ip_address = parts[1].split("/")[0]
                netmask = parts[1].split("/")[1]

        # Get gateway
        route_info = subprocess.check_output(["ip", "route"]).decode()
        gateway = None
        for line in route_info.split("\n"):
            if "default via" in line:
                gateway = line.split("via")[1].split()[0]

        return {
            "device": wifi_device,
            "mac": mac_address,
            "ssid": ssid,
            "signal": signal,
            "ip": ip_address,
            "netmask": netmask,
            "gateway": gateway,
        }
    except Exception as e:
        return f"Error getting WiFi info: {str(e)}"


async def scan_wifi_networks() -> Union[List[Dict[str, str]], str]:
    """Scan for available WiFi networks and sort by signal strength.

    Returns:
        list: List of dictionaries containing network information sorted by signal strength:
            - ssid: Network name
            - signal: Signal strength
            - security: Security type
            - mac: MAC address of the access point
        str: Error message if there was a problem scanning networks
    """
    try:
        # Rescan WiFi networks
        subprocess.run(["nmcli", "device", "wifi", "rescan"], check=True)
        
        # Get network list
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "SIGNAL,SSID,SECURITY,BSSID", "device", "wifi", "list"]
        ).decode()
        
        networks = []
        for line in output.split("\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) >= 4:
                    networks.append({
                        "signal": int(parts[0]),
                        "ssid": parts[1],
                        "security": parts[2] if parts[2] else "None",
                        "mac": parts[3]
                    })
        
        # Sort networks by signal strength (highest first)
        networks.sort(key=lambda x: x["signal"], reverse=True)
        
        return networks
    except Exception as e:
        return f"Error scanning WiFi networks: {str(e)}"


async def perform_git_pull() -> str:
    """Perform a git pull operation in the current directory.

    Returns:
        str: Output of the git pull command or error message
    """
    try:
        # Check if current directory is a git repository
        subprocess.check_output(["git", "rev-parse", "--git-dir"], stderr=subprocess.STDOUT)
        
        # Perform git pull
        output = subprocess.check_output(["git", "pull"], stderr=subprocess.STDOUT).decode()
        return output
    except subprocess.CalledProcessError as e:
        if "not a git repository" in e.output.decode():
            return "Error: Current directory is not a git repository"
        return f"Git pull failed: {e.output.decode()}"
    except Exception as e:
        return f"Error performing git pull: {str(e)}"


async def ping_address(address: str, count: int = 5) -> str:
    """Ping a network address.

    Args:
        address: The address to ping (hostname or IP address)
        count: Number of pings to send (default: 5)

    Returns:
        str: The ping command output or error message
    """
    # Input validation
    if not address or not isinstance(address, str):
        return "Error: Invalid address provided"

    # Remove any whitespace and check length
    address = address.strip()
    if not address or len(address) > 255:
        return "Error: Address is empty or too long"

    # Validate the address format (must be either a valid IP or hostname)
    if not is_valid_ip(address) and not is_valid_hostname(address):
        return "Error: Invalid IP address or hostname format"

    # Ensure count is within reasonable limits
    try:
        count = int(count)
        if count < 1 or count > 20:
            return "Error: Count must be between 1 and 20"
    except (ValueError, TypeError):
        return "Error: Invalid count value"

    try:
        # Use subprocess.run with a list of arguments to prevent shell injection
        # capture_output=True captures both stdout and stderr
        result = subprocess.run(
            ["ping", "-c", str(count), address],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Return combined output (stdout + stderr) regardless of exit code
        return result.stdout + result.stderr
    except subprocess.SubprocessError as e:
        return f"Error executing ping command: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
