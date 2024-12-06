"""System utilities for WiFi and system operations."""

import subprocess
from typing import Dict, List, Union


async def get_wifi_info() -> Union[Dict[str, str], str]:
    """Get current WiFi connection information.

    Returns:
        dict: WiFi connection details including:
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

        # Get IP information using the detected WiFi device
        ip_info = subprocess.check_output(["ip", "addr", "show", wifi_device]).decode()
        ip_address = None
        netmask = None
        for line in ip_info.split("\n"):
            if "inet " in line:
                parts = line.strip().split()
                ip_address = parts[1].split("/")[0]
                netmask = parts[1].split("/")[1]

        # Get gateway
        route_info = subprocess.check_output(["ip", "route"]).decode()
        gateway = None
        for line in route_info.split("\n"):
            if "default via" in line:
                gateway = line.split("via")[1].split()[0]

        return {
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
        str: Error message if there was a problem scanning networks
    """
    try:
        # Rescan WiFi networks
        subprocess.run(["nmcli", "device", "wifi", "rescan"], check=True)
        
        # Get network list
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "SIGNAL,SSID,SECURITY", "device", "wifi", "list"]
        ).decode()
        
        networks = []
        for line in output.split("\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) >= 3:
                    networks.append({
                        "signal": int(parts[0]),
                        "ssid": parts[1],
                        "security": parts[2] if parts[2] else "None"
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
        address: The address to ping
        count: Number of pings to send (default: 5)

    Returns:
        str: The ping command output or error message
    """
    try:
        output = subprocess.check_output(
            ["ping", "-c", str(count), address], stderr=subprocess.STDOUT
        ).decode()
        return output
    except subprocess.CalledProcessError as e:
        return f"Error pinging {address}: {e.output.decode()}"
