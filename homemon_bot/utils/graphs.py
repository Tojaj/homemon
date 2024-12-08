"""Utilities for generating measurement graphs."""

import io
from datetime import datetime
import matplotlib.pyplot as plt
from typing import Dict, List, Any


async def generate_graphs(
    measurements: List[Dict[str, Any]], hours: int
) -> List[io.BytesIO]:
    """Generate line graphs for sensor measurements.

    Creates three graphs:
        1. Temperature over time for all sensors
        2. Humidity over time for all sensors
        3. Battery levels over time for all sensors

    Args:
        measurements: List of measurement dictionaries
        hours: Time period in hours to display

    Returns:
        list: List of BytesIO objects containing the generated graphs as PNG images
    """
    graphs = []
    metrics = [
        ("Temperature", "temperature", "°C"),
        ("Humidity", "humidity", "%"),
        ("Battery", "battery_voltage", "V"),
    ]

    for title, field, unit in metrics:
        plt.figure(figsize=(10, 6))

        # Group data by sensor
        sensor_data = {}
        for m in measurements:
            sensor_id = m["sensor_id"]
            if sensor_id not in sensor_data:
                sensor_data[sensor_id] = {"timestamps": [], "values": []}
            sensor_data[sensor_id]["timestamps"].append(
                datetime.fromisoformat(m["timestamp"])
            )
            sensor_data[sensor_id]["values"].append(m[field])

        # Plot each sensor's data
        for sensor_id, data in sensor_data.items():
            plt.plot(data["timestamps"], data["values"], label=f"Sensor {sensor_id}")

        plt.title(f"{title} over last {hours}h")
        plt.xlabel("Time")
        plt.ylabel(f"{title} ({unit})")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        graphs.append(buf)
        plt.close()

    return graphs
