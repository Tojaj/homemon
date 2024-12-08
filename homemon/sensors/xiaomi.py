"""Xiaomi Mi Temperature and Humidity Monitor 2 (LYWSD03MMC) sensor interface.

This module provides functionality to read temperature, humidity, and battery data
from the Xiaomi Mi Temperature and Humidity Monitor 2 Bluetooth Low Energy sensor.
It handles the specific data format and characteristics of this sensor model.

Sensor Specifications:
    - Model: LYWSD03MMC
    - Protocol: Bluetooth Low Energy (BLE)
    - Measurements:
        * Temperature: 0°C to 60°C (±0.1°C resolution)
        * Humidity: 0-99% RH (±1% resolution)
        * Battery Voltage: 2.5V - 3.0V

The module implements a robust polling mechanism with:
    - Automatic retries on failure (up to 3 attempts)
    - Increasing delay between retries (0s -> 5s -> 10s)
    - Controlled concurrent polling of multiple sensors
    - Error handling and logging
"""

import logging
import asyncio
from bleak import BleakClient

# Characteristic UUID specific to LYWSD03MMC sensor
CHAR_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

# Global semaphore to control concurrent Bluetooth operations
# Only allow one Bluetooth operation at a time
BLE_SEMAPHORE = asyncio.Semaphore(1)


async def read_sensor_data(client: BleakClient):
    """Read data from Xiaomi Mi Temperature and Humidity Monitor 2 sensor.

    This function reads the raw data from the sensor's BLE characteristic and
    converts it to human-readable values using the sensor's data format:
        - Temperature: 2 bytes, little-endian, *0.01 scale
        - Humidity: 1 byte, direct percentage
        - Battery: 2 bytes, little-endian, *0.001 scale

    Args:
        client (BleakClient): Connected BLE client instance for the sensor

    Returns:
        dict: A dictionary containing the sensor readings:
            - temperature (float): Temperature in Celsius
            - humidity (int): Relative humidity percentage (0-100)
            - battery_voltage (float): Battery voltage in Volts
        Returns None if there was an error reading the data.

    Raises:
        Exception: If there's an error reading the characteristic or parsing data
    """
    try:
        raw_data = await client.read_gatt_char(CHAR_UUID)
        temperature = (raw_data[0] | (raw_data[1] << 8)) * 0.01
        humidity = raw_data[2]
        battery_voltage = (raw_data[3] | (raw_data[4] << 8)) * 0.001

        return {
            "temperature": temperature,
            "humidity": humidity,
            "battery_voltage": battery_voltage,
        }

    except Exception as e:
        logging.error(f"Error reading sensor data: {e}")
        return None


async def poll_single_sensor(sensor):
    """Read data from a single LYWSD03MMC sensor with retry mechanism.

    This function attempts to read from a sensor up to 3 times with increasing
    delays between attempts:
        1. First attempt: immediate
        2. Second attempt: after 5 seconds
        3. Third attempt: after 10 seconds

    Args:
        sensor (dict): Sensor configuration dictionary containing:
            - mac_address (str): The sensor's MAC address
            - alias (str, optional): A friendly name for the sensor

    Returns:
        dict: A dictionary containing either:
            Success case:
                - mac_address (str): Sensor's MAC address
                - alias (str, optional): Sensor's alias if provided
                - temperature (float): Temperature in Celsius
                - humidity (int): Relative humidity percentage
                - battery_voltage (float): Battery voltage in Volts
            Error case:
                - mac_address (str): Sensor's MAC address
                - alias (str, optional): Sensor's alias if provided
                - error (str): Description of the error
    """
    mac_address = sensor["mac_address"]
    alias = sensor.get("alias")

    # First attempt
    result = await try_poll_sensor(mac_address, alias)
    if not result.get("error"):
        return result

    # Second attempt after 5 seconds
    logging.info(f"First attempt failed for {mac_address}, retrying in 5 seconds...")
    await asyncio.sleep(5)
    result = await try_poll_sensor(mac_address, alias)
    if not result.get("error"):
        return result

    # Third attempt after 10 seconds
    logging.info(f"Second attempt failed for {mac_address}, retrying in 10 seconds...")
    await asyncio.sleep(10)
    return await try_poll_sensor(mac_address, alias)


async def try_poll_sensor(mac_address: str, alias: str):
    """Attempt to poll a single LYWSD03MMC sensor.

    This function handles a single attempt to connect to and read from a sensor,
    including connection management and error handling. It uses a semaphore to
    ensure only one Bluetooth operation occurs at a time.

    Args:
        mac_address (str): The MAC address of the sensor (format: XX:XX:XX:XX:XX:XX)
        alias (str): The alias/name of the sensor (can be None)

    Returns:
        dict: A dictionary containing either:
            Success case:
                - mac_address (str): Sensor's MAC address
                - alias (str): Sensor's alias
                - temperature (float): Temperature in Celsius
                - humidity (int): Relative humidity percentage
                - battery_voltage (float): Battery voltage in Volts
            Error case:
                - mac_address (str): Sensor's MAC address
                - alias (str): Sensor's alias
                - error (str): Description of what went wrong
    """
    try:
        # Use semaphore to ensure only one Bluetooth operation at a time
        async with BLE_SEMAPHORE:
            logging.info(f"Connecting to sensor: {mac_address}")

            # Add a small delay between connection attempts to different sensors
            await asyncio.sleep(0.5)

            async with BleakClient(mac_address, timeout=20.0) as client:
                logging.info(f"Connected to the sensor: {mac_address}")
                data = await read_sensor_data(client)

                if data:
                    return {"mac_address": mac_address, "alias": alias, **data}
                else:
                    return {
                        "mac_address": mac_address,
                        "alias": alias,
                        "error": "Failed to read data",
                    }

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error with sensor {mac_address}: {error_msg}")
        return {"mac_address": mac_address, "alias": alias, "error": error_msg}


async def poll_multiple_sensors(sensors):
    """Poll multiple LYWSD03MMC sensors sequentially.

    This function creates tasks to poll multiple sensors, but uses a semaphore
    to ensure only one Bluetooth operation occurs at a time, preventing
    "Operation already in progress" errors.

    Args:
        sensors (list): List of sensor configuration dictionaries, each containing:
            - mac_address (str): The sensor's MAC address
            - alias (str, optional): A friendly name for the sensor

    Returns:
        list: List of dictionaries, one for each sensor, each containing either:
            Success case:
                - mac_address (str): Sensor's MAC address
                - alias (str, optional): Sensor's alias if provided
                - temperature (float): Temperature in Celsius
                - humidity (int): Relative humidity percentage
                - battery_voltage (float): Battery voltage in Volts
            Error case:
                - mac_address (str): Sensor's MAC address
                - alias (str, optional): Sensor's alias if provided
                - error (str): Description of what went wrong

    Note:
        Even if some sensors fail, results will be returned for all sensors.
        Failed sensors will have an 'error' key in their result dictionary.
    """
    tasks = []
    for sensor in sensors:
        tasks.append(poll_single_sensor(sensor))

    # Create tasks but let the semaphore control actual execution
    sensor_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error results
    processed_results = []
    for i, result in enumerate(sensor_results):
        if isinstance(result, Exception):
            processed_results.append(
                {
                    "mac_address": sensors[i]["mac_address"],
                    "alias": sensors[i].get("alias"),
                    "error": str(result),
                }
            )
        else:
            processed_results.append(result)

    return processed_results
