"""FastAPI backend service for Home Monitor.

This module implements the REST API for accessing sensor data from the SQLite database.
It provides endpoints for:
    - Listing and retrieving sensor information
    - Getting recent measurements from all sensors
    - Retrieving historical measurements with optional time filtering
    - Calculating sensor statistics
    - Retrieving sensor measurement trends

All endpoints return JSON responses and use Pydantic models for validation.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from homemon.database import SensorDatabase


# Models for API responses
class Sensor(BaseModel):
    """Model representing a sensor's metadata.

    Attributes:
        id (int): Unique identifier for the sensor
        mac_address (str): MAC address of the sensor
        alias (Optional[str]): Human-readable name for the sensor, if set
    """
    id: int
    mac_address: str
    alias: Optional[str] = None


class Measurement(BaseModel):
    """Model representing a single sensor measurement.

    Attributes:
        timestamp (datetime): When the measurement was taken
        temperature (float): Temperature in Celsius
        humidity (int): Relative humidity percentage
        battery_voltage (float): Battery voltage in volts
    """
    timestamp: datetime
    temperature: float
    humidity: int
    battery_voltage: float


class RecentMeasurement(BaseModel):
    """Model representing the most recent measurement from a sensor.

    Attributes:
        sensor_id (int): ID of the sensor that took the measurement
        timestamp (datetime): When the measurement was taken
        temperature (float): Temperature in Celsius
        humidity (int): Relative humidity percentage
        battery_voltage (float): Battery voltage in volts
    """
    sensor_id: int
    timestamp: datetime
    temperature: float
    humidity: int
    battery_voltage: float


class SensorStats(BaseModel):
    """Model representing statistical data for a sensor's measurements.

    Attributes:
        average_temperature (float): Mean temperature in Celsius
        average_humidity (float): Mean relative humidity percentage
        min_temperature (float): Minimum recorded temperature
        max_temperature (float): Maximum recorded temperature
        min_humidity (int): Minimum recorded humidity
        max_humidity (int): Maximum recorded humidity
    """
    average_temperature: float
    average_humidity: float
    min_temperature: float
    max_temperature: float
    min_humidity: int
    max_humidity: int


# Global variable to store database path
db_path: str = None


def init_app(database_path: str) -> FastAPI:
    """Initialize FastAPI application with the specified database path.

    This function creates and configures a FastAPI application with all necessary
    routes and middleware. It sets up CORS for cross-origin requests and
    initializes the database connection.

    Args:
        database_path (str): Path to the SQLite database file

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    global db_path
    db_path = database_path

    app = FastAPI(
        title="Home Monitor API",
        description="API for retrieving sensor data and measurements from the SQLite database.",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    @app.get("/sensors", response_model=List[Sensor])
    async def list_sensors():
        """List all sensors and their metadata.

        Returns:
            List[Sensor]: List of all sensors in the database

        Raises:
            HTTPException: If there's an error accessing the database
        """
        try:
            db = SensorDatabase(db_path)
            db.cursor.execute("SELECT id, mac_address, alias FROM sensors")
            sensors = db.cursor.fetchall()
            db.close()
            return [{"id": s[0], "mac_address": s[1], "alias": s[2]} for s in sensors]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/sensors/{id}", response_model=Sensor)
    async def get_sensor(id: int):
        """Get metadata for a specific sensor.

        Args:
            id (int): The ID of the sensor to retrieve

        Returns:
            Sensor: The requested sensor's metadata

        Raises:
            HTTPException: If the sensor is not found or there's a database error
        """
        try:
            db = SensorDatabase(db_path)
            db.cursor.execute(
                "SELECT id, mac_address, alias FROM sensors WHERE id = ?", (id,)
            )
            sensor = db.cursor.fetchone()
            db.close()
            if not sensor:
                raise HTTPException(status_code=404, detail="Sensor not found")
            return {"id": sensor[0], "mac_address": sensor[1], "alias": sensor[2]}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/measurements/recent", response_model=List[RecentMeasurement])
    async def get_recent_measurements():
        """Get the most recent measurements for all sensors.

        Returns:
            List[RecentMeasurement]: List of the latest measurement from each sensor

        Raises:
            HTTPException: If there's an error accessing the database
        """
        try:
            db = SensorDatabase(db_path)
            db.cursor.execute(
                """
                WITH RankedMeasurements AS (
                    SELECT 
                        sensor_id,
                        timestamp,
                        temperature,
                        humidity,
                        battery_voltage,
                        ROW_NUMBER() OVER (PARTITION BY sensor_id ORDER BY timestamp DESC) as rn
                    FROM measurements
                )
                SELECT 
                    sensor_id,
                    timestamp,
                    temperature,
                    humidity,
                    battery_voltage
                FROM RankedMeasurements
                WHERE rn = 1
            """
            )
            measurements = db.cursor.fetchall()
            db.close()
            return [
                {
                    "sensor_id": m[0],
                    "timestamp": m[1],
                    "temperature": m[2],
                    "humidity": m[3],
                    "battery_voltage": m[4],
                }
                for m in measurements
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/measurements/{sensor_id}", response_model=List[Measurement])
    async def get_measurements(
        sensor_id: int,
        start_time: Optional[datetime] = Query(None),
        end_time: Optional[datetime] = Query(None),
    ):
        """Get measurements for a specific sensor within a time range.

        Args:
            sensor_id (int): ID of the sensor to get measurements for
            start_time (Optional[datetime]): Start of the time range (inclusive)
            end_time (Optional[datetime]): End of the time range (inclusive)

        Returns:
            List[Measurement]: List of measurements in descending timestamp order

        Raises:
            HTTPException: If there's an error accessing the database
        """
        try:
            db = SensorDatabase(db_path)
            query = """
                SELECT timestamp, temperature, humidity, battery_voltage
                FROM measurements
                WHERE sensor_id = ?
            """
            params = [sensor_id]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC"

            db.cursor.execute(query, params)
            measurements = db.cursor.fetchall()
            db.close()
            return [
                {
                    "timestamp": m[0],
                    "temperature": m[1],
                    "humidity": m[2],
                    "battery_voltage": m[3],
                }
                for m in measurements
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/measurements/{sensor_id}/stats", response_model=SensorStats)
    async def get_sensor_stats(
        sensor_id: int,
        start_time: Optional[datetime] = Query(None),
        end_time: Optional[datetime] = Query(None),
    ):
        """Get summary statistics for a specific sensor.

        Args:
            sensor_id (int): ID of the sensor to get statistics for
            start_time (Optional[datetime]): Start of the time range (inclusive)
            end_time (Optional[datetime]): End of the time range (inclusive)

        Returns:
            SensorStats: Statistical summary of the sensor's measurements

        Raises:
            HTTPException: If no measurements are found or there's a database error
        """
        try:
            db = SensorDatabase(db_path)
            query = """
                SELECT 
                    AVG(temperature) as avg_temp,
                    AVG(humidity) as avg_hum,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    MIN(humidity) as min_hum,
                    MAX(humidity) as max_hum
                FROM measurements
                WHERE sensor_id = ?
            """
            params = [sensor_id]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            db.cursor.execute(query, params)
            stats = db.cursor.fetchone()
            db.close()

            if not stats[0]:  # If no data found
                raise HTTPException(
                    status_code=404,
                    detail="No measurements found for this sensor in the specified time range",
                )

            return {
                "average_temperature": float(stats[0]),
                "average_humidity": float(stats[1]),
                "min_temperature": float(stats[2]),
                "max_temperature": float(stats[3]),
                "min_humidity": int(stats[4]),
                "max_humidity": int(stats[5]),
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/measurements/{sensor_id}/trend", response_model=List[Measurement])
    async def get_sensor_trend(
        sensor_id: int,
        start_time: Optional[datetime] = Query(None),
        end_time: Optional[datetime] = Query(None),
    ):
        """Get temperature and humidity trends for a specific sensor.

        Retrieves measurements ordered by timestamp ascending to show the trend
        over time.

        Args:
            sensor_id (int): ID of the sensor to get trends for
            start_time (Optional[datetime]): Start of the time range (inclusive)
            end_time (Optional[datetime]): End of the time range (inclusive)

        Returns:
            List[Measurement]: List of measurements in ascending timestamp order

        Raises:
            HTTPException: If there's an error accessing the database
        """
        try:
            db = SensorDatabase(db_path)
            query = """
                SELECT timestamp, temperature, humidity, battery_voltage
                FROM measurements
                WHERE sensor_id = ?
            """
            params = [sensor_id]

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp ASC"

            db.cursor.execute(query, params)
            measurements = db.cursor.fetchall()
            db.close()
            return [
                {
                    "timestamp": m[0],
                    "temperature": m[1],
                    "humidity": m[2],
                    "battery_voltage": m[3],
                }
                for m in measurements
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app
