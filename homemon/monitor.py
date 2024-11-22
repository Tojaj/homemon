#!/usr/bin/env python3
"""Main monitoring script for Home Monitor.

This module provides the main functionality for continuously polling sensors,
storing their data, and managing the monitoring process. It handles:
    - Loading configuration from config file
    - Initializing and managing the SQLite database connection
    - Polling multiple Xiaomi temperature/humidity sensors
    - Storing sensor readings in the database
    - Continuous monitoring with configurable polling intervals

The module expects a configuration file with:
    - polling_interval: Time between sensor polls in seconds
    - database_file: Path to the SQLite database file
    - sensors: List of sensor configurations (MAC addresses and aliases)
"""

import asyncio
import logging
from datetime import datetime

from .database import SensorDatabase
from .config import load_config
from .sensors.xiaomi import poll_multiple_sensors

# Set up logging
logging.basicConfig(level=logging.INFO)


async def main():
    """Main function to control the polling of multiple sensors.

    This asynchronous function manages the continuous monitoring process:
    1. Loads configuration from the config file
    2. Initializes the SQLite database
    3. Enters a continuous loop that:
        - Polls all configured sensors
        - Prints the sensor readings to console
        - Stores the readings in the database
        - Waits for the configured polling interval

    The function handles both successful readings and error cases for each sensor.
    For successful readings, it stores:
        - Temperature (°C)
        - Humidity (%)
        - Battery voltage (V)

    For error cases, it logs the error message associated with the sensor.

    Returns:
        None

    Raises:
        KeyboardInterrupt: When the program is manually interrupted
        Exception: For any other unexpected errors during execution

    Note:
        The function runs indefinitely until interrupted. It gracefully handles
        interruptions by completing the current operation before shutting down.
    """
    # Load configuration
    config = load_config()
    polling_interval = config["polling_interval"]
    db_path = config["database_file"]
    sensors = config["sensors"]

    # Initialize database using SensorDatabase class
    with SensorDatabase(db_path) as db:
        pass  # The database schema will be initialized in the constructor

    while True:
        # Poll all sensors and get the data
        sensor_data_list = await poll_multiple_sensors(sensors)

        # Process the collected data
        with SensorDatabase(db_path) as db:
            for sensor_data in sensor_data_list:
                mac_address = sensor_data.get("mac_address")
                alias = sensor_data.get("alias")
                sensor_id = f"{mac_address} ({alias})" if alias else mac_address

                if "error" in sensor_data:
                    print(f"Error with sensor {sensor_id}: {sensor_data['error']}")
                else:
                    # Print the data
                    print(f"Sensor {sensor_id}:")
                    print(f"  Temperature: {sensor_data['temperature']} °C")
                    print(f"  Humidity: {sensor_data['humidity']} %")
                    print(f"  Battery Voltage: {sensor_data['battery_voltage']} V")

                    # Store the data in the database
                    db_sensor_id = db.get_or_create_sensor(mac_address, alias)
                    db.store_measurement(
                        db_sensor_id,
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["battery_voltage"],
                    )

        # Wait for the polling interval before repeating
        print(f"Waiting for {polling_interval} seconds before polling again...")
        await asyncio.sleep(polling_interval)


# Start the program
if __name__ == "__main__":
    try:
        asyncio.run(main())  # Run the main asynchronous loop
    except KeyboardInterrupt:
        print("\nProgram interrupted. Disconnecting gracefully...")
