"""API client for interacting with the Home Monitor API."""

import aiohttp
from datetime import datetime
from typing import Dict, List, Any

API_BASE_URL = "http://localhost:8000/api"


async def fetch_data(endpoint: str) -> Any:
    """Fetch data from the Home Monitor API.

    Args:
        endpoint: The API endpoint to fetch data from

    Returns:
        The JSON response from the API

    Raises:
        Exception: If there's an error fetching data from the API
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/{endpoint}") as response:
            return await response.json()


async def get_recent_measurements() -> List[Dict[str, Any]]:
    """Get the most recent measurements from all sensors.

    Returns:
        List of measurement dictionaries
    """
    return await fetch_data("measurements/recent")


async def get_sensors() -> List[Dict[str, Any]]:
    """Get all registered sensors.

    Returns:
        List of sensor dictionaries
    """
    return await fetch_data("sensors")


async def get_sensor_stats(
    sensor_id: int, start_time: datetime, end_time: datetime
) -> Dict[str, float]:
    """Get statistics for a specific sensor over a time period.

    Args:
        sensor_id: The ID of the sensor
        start_time: Start of the time period
        end_time: End of the time period

    Returns:
        Dictionary containing average temperature and humidity
    """
    return await fetch_data(
        f"measurements/{sensor_id}/stats?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}"
    )


async def get_sensor_measurements(
    sensor_id: int, start_time: datetime, end_time: datetime
) -> List[Dict[str, Any]]:
    """Get measurements for a specific sensor over a time period.

    Args:
        sensor_id: The ID of the sensor
        start_time: Start of the time period
        end_time: End of the time period

    Returns:
        List of measurement dictionaries
    """
    return await fetch_data(
        f"measurements/{sensor_id}?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}"
    )
