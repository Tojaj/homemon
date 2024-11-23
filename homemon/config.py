"""Configuration management for Home Monitor.

This module handles loading and managing configuration from YAML files,
providing default values when needed.

Configuration Structure:
    polling_interval: Time between sensor polls in seconds (default: 900)
    database_file: Path to SQLite database file (default: sensor_data.db)
    sensors: List of sensor configurations, each containing:
        - mac_address: MAC address of the sensor
        - alias: Optional human-readable name for the sensor

Example config.yaml:
    polling_interval: 300
    database_file: sensor_data.db
    sensors:
      - mac_address: "A4:C1:38:DE:EA:B9"
        alias: "Living Room"
      - mac_address: "A4:C1:38:FF:BB:CC"
        alias: "Bedroom"
"""

import logging
import yaml

# Default configuration values
DEFAULT_POLLING_INTERVAL = 900  # 15 minutes in seconds
DEFAULT_DB_PATH = "sensor_data.db"


def load_config():
    """Load configuration from config.yaml file.

    This function attempts to load configuration from a config.yaml file in the
    current directory. If the file is not found or contains invalid data, default
    values are used.

    Returns:
        dict: Configuration dictionary containing:
            - polling_interval (int): Time between sensor polls in seconds
            - database_file (str): Path to the SQLite database file
            - sensors (list): List of dictionaries, each containing:
                - mac_address (str): MAC address of the sensor
                - alias (str|None): Optional human-readable name for the sensor

    Default Values:
        - polling_interval: 900 seconds (15 minutes)
        - database_file: "sensor_data.db"
        - sensors: Single sensor with MAC "A4:C1:38:DE:EA:B9" and no alias

    Raises:
        FileNotFoundError: If config.yaml is not found (caught and handled)
        Exception: For any other errors (caught and handled)
    """
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        # Extract polling interval with default fallback
        polling_interval = config.get("polling_interval", DEFAULT_POLLING_INTERVAL)

        # Extract database filename with default fallback
        database_file = config.get("database_file", DEFAULT_DB_PATH)

        # Extract sensors configuration
        sensors = []
        sensor_configs = config.get("sensors", [])
        for sensor in sensor_configs:
            if "mac_address" in sensor:
                sensors.append(
                    {
                        "mac_address": sensor["mac_address"],
                        "alias": sensor.get("alias", None),
                    }
                )

        return {
            "polling_interval": polling_interval,
            "database_file": database_file,
            "sensors": sensors,
        }
    except FileNotFoundError:
        logging.warning("Config file not found, using default values")
        return {
            "polling_interval": DEFAULT_POLLING_INTERVAL,
            "database_file": DEFAULT_DB_PATH,
            "sensors": [{"mac_address": "A4:C1:38:DE:EA:B9", "alias": None}],
        }
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {
            "polling_interval": DEFAULT_POLLING_INTERVAL,
            "database_file": DEFAULT_DB_PATH,
            "sensors": [{"mac_address": "A4:C1:38:DE:EA:B9", "alias": None}],
        }
