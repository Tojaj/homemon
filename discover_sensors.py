#!/usr/bin/env python3

import argparse
import sys
import yaml
import asyncio
from bleak import BleakScanner


async def discover_xiaomi_sensors():
    """Scan for Xiaomi LYWSD03MMC sensors and return their MAC addresses.

    This function performs a Bluetooth Low Energy (BLE) scan for 10 seconds to
    discover Xiaomi LYWSD03MMC temperature and humidity sensors in range.

    Returns:
        list: A list of dictionaries containing discovered sensors. Each dictionary
            contains:
            - mac_address (str): The MAC address of the sensor
            - name (str): The advertised name of the sensor

    Raises:
        Exception: If there's an error during the BLE scanning process
    """
    print("Scanning for Xiaomi sensors... (this will take 10 seconds)")
    xiaomi_sensors = []

    try:
        devices = await BleakScanner.discover(timeout=10.0)
        for device in devices:
            # LYWSD03MMC sensors advertise with this name
            if device.name and "LYWSD03MMC" in device.name:
                xiaomi_sensors.append(
                    {"mac_address": device.address, "name": device.name}
                )
    except Exception as e:
        print(f"Error during scanning: {e}")
        sys.exit(1)

    return xiaomi_sensors


def load_config(config_path):
    """Load existing configuration file.

    Args:
        config_path (str): Path to the YAML configuration file

    Returns:
        dict: Configuration dictionary containing sensor information. If the file
            doesn't exist, returns a dictionary with an empty sensors list.
            Structure: {'sensors': []}

    Raises:
        Exception: If there's an error reading the configuration file
    """
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {"sensors": []}
    except FileNotFoundError:
        return {"sensors": []}
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)


def save_config(config, config_path):
    """Save updated configuration file.

    Args:
        config (dict): Configuration dictionary to save
        config_path (str): Path where the configuration file should be saved

    Raises:
        Exception: If there's an error saving the configuration file
    """
    try:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"\nConfiguration saved to {config_path}")
    except Exception as e:
        print(f"Error saving config file: {e}")
        sys.exit(1)


async def main():
    """Main function to discover and configure Xiaomi sensors.

    This function handles the main program flow:
    1. Parses command line arguments
    2. Discovers Xiaomi sensors via BLE
    3. If a config file is specified:
       - Loads existing configuration
       - Identifies new sensors
       - Prompts user to add new sensors
       - Allows setting aliases for new sensors
       - Saves updated configuration

    Command line arguments:
        --config: Optional path to config.yaml file
    """
    parser = argparse.ArgumentParser(
        description="Discover Xiaomi temperature and humidity sensors"
    )
    parser.add_argument("--config", help="Path to config.yaml file", required=False)
    args = parser.parse_args()

    # Discover sensors
    discovered_sensors = await discover_xiaomi_sensors()

    if not discovered_sensors:
        print("\nNo Xiaomi sensors found.")
        return

    print("\nDiscovered sensors:")
    for sensor in discovered_sensors:
        print(f"MAC Address: {sensor['mac_address']}, Name: {sensor['name']}")

    # If no config file provided, exit here
    if not args.config:
        return

    # Load existing config
    config = load_config(args.config)
    existing_macs = {sensor["mac_address"] for sensor in config["sensors"]}
    new_sensors = [
        s for s in discovered_sensors if s["mac_address"] not in existing_macs
    ]

    if not new_sensors:
        print("\nNo new sensors found to add to config.")
        return

    print("\nNew sensors found:")
    for i, sensor in enumerate(new_sensors, 1):
        print(f"{i}. MAC Address: {sensor['mac_address']}, Name: {sensor['name']}")

    while True:
        response = input(
            "\nWould you like to add these sensors to the config? (yes/no): "
        ).lower()
        if response in ["yes", "y", "no", "n"]:
            break
        print("Please answer 'yes' or 'no'")

    if response.startswith("y"):
        for sensor in new_sensors:
            alias = input(
                f"Enter alias for sensor {sensor['mac_address']} (press Enter to skip): "
            ).strip()
            config["sensors"].append(
                {
                    "mac_address": sensor["mac_address"],
                    "alias": alias if alias else sensor["mac_address"],
                }
            )
        save_config(config, args.config)
        print("Sensors added successfully!")


if __name__ == "__main__":
    asyncio.run(main())
