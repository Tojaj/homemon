"""Database management for Home Monitor.

This module provides database functionality for storing and retrieving
sensor measurements, including temperature, humidity, and battery data.

Database Schema:
    sensors:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - mac_address: TEXT UNIQUE NOT NULL
        - alias: TEXT

    measurements:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - sensor_id: INTEGER NOT NULL (foreign key to sensors.id)
        - timestamp: DATETIME NOT NULL
        - temperature: REAL NOT NULL
        - humidity: INTEGER NOT NULL
        - battery_voltage: REAL NOT NULL

Indexes:
    - idx_measurements_sensor_id: For quick sensor lookups
    - idx_measurements_timestamp: For time-based queries
    - idx_measurements_sensor_timestamp: For combined sensor/time queries
"""

import sqlite3
import logging
from datetime import datetime


class SensorDatabase:
    """Database manager for sensor data storage.

    This class provides an interface for storing and retrieving sensor data
    in a SQLite database. It handles:
        - Database connection management
        - Schema initialization
        - Sensor registration and lookup
        - Measurement storage

    The class can be used as a context manager:
        with SensorDatabase('path/to/db.sqlite') as db:
            db.store_measurement(...)
    """

    def __init__(self, db_path: str, read_only: bool = False):
        """Initialize database connection and ensure schema exists.

        Args:
            db_path (str): Path to the SQLite database file
            read_only (bool, optional): Open database in read-only mode. Defaults to False.

        Raises:
            Exception: If database connection fails.
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.read_only = read_only
        self._connect()
        if not self.read_only:
            self._init_schema()

    def _connect(self):
        """Establish database connection.

        Raises:
            Exception: If connection to the database fails
        """
        try:
            if self.read_only:
                uri = f"file:{self.db_path}?mode=ro"
                self.conn = sqlite3.connect(uri, uri=True)  # Open database in read-only mode
            else:
                self.conn = sqlite3.connect(self.db_path)  # Default mode is read-write and create
            self.cursor = self.conn.cursor()
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise

    def _init_schema(self):
        """Initialize database schema if it doesn't exist.

        Creates the necessary tables and indexes if they don't already exist:
            - sensors table for storing sensor metadata
            - measurements table for storing sensor readings
            - indexes for optimizing common queries

        The schema is designed to efficiently store and retrieve time-series
        data from multiple sensors.
        """
        # Create sensors table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT UNIQUE NOT NULL,
                alias TEXT
            )
        """
        )

        # Create measurements table with appropriate indexes
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                temperature REAL NOT NULL,
                humidity INTEGER NOT NULL,
                battery_voltage REAL NOT NULL,
                FOREIGN KEY (sensor_id) REFERENCES sensors (id)
            )
        """
        )

        # Create indexes for common queries
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_measurements_sensor_id 
            ON measurements(sensor_id)
        """
        )
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_measurements_timestamp 
            ON measurements(timestamp)
        """
        )
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_measurements_sensor_timestamp 
            ON measurements(sensor_id, timestamp)
        """
        )

        self.conn.commit()

    def get_or_create_sensor(self, mac_address: str, alias: str = None) -> int:
        """Get sensor ID from database or create new entry if it doesn't exist.

        This method looks up a sensor by MAC address and returns its ID. If the
        sensor doesn't exist, it creates a new entry. If the sensor exists but
        the alias has changed, it updates the alias.

        Args:
            mac_address (str): MAC address of the sensor
            alias (str, optional): Human-readable name for the sensor

        Returns:
            int: Database ID of the sensor

        Raises:
            sqlite3.Error: If database operations fail
        """
        if self.read_only:
            raise sqlite3.Error("Cannot modify database in read-only mode.")

        # Try to get existing sensor
        self.cursor.execute(
            "SELECT id, alias FROM sensors WHERE mac_address = ?", (mac_address,)
        )
        result = self.cursor.fetchone()

        if result:
            sensor_id = result[0]
            current_alias = result[1]
            # Update alias if it has changed
            if alias != current_alias:
                self.cursor.execute(
                    "UPDATE sensors SET alias = ? WHERE id = ?", (alias, sensor_id)
                )
                self.conn.commit()
        else:
            # Create new sensor entry
            self.cursor.execute(
                "INSERT INTO sensors (mac_address, alias) VALUES (?, ?)",
                (mac_address, alias),
            )
            sensor_id = self.cursor.lastrowid
            self.conn.commit()

        return sensor_id

    def store_measurement(
        self, sensor_id: int, temperature: float, humidity: int, battery_voltage: float
    ):
        """Store sensor measurement in the database.

        Records a new measurement with the current timestamp. All measurements
        are associated with a sensor through the sensor_id.

        Args:
            sensor_id (int): Database ID of the sensor
            temperature (float): Temperature in Celsius
            humidity (int): Relative humidity percentage (0-100)
            battery_voltage (float): Battery voltage in volts

        Raises:
            sqlite3.Error: If the insert operation fails
            ValueError: If sensor_id doesn't exist in the database
        """
        if self.read_only:
            raise sqlite3.Error("Cannot modify database in read-only mode.")
        self.cursor.execute(
            """
            INSERT INTO measurements (
                sensor_id, timestamp, temperature, humidity, battery_voltage
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                sensor_id,
                datetime.now().isoformat(),
                temperature,
                humidity,
                battery_voltage,
            ),
        )
        self.conn.commit()

    def close(self):
        """Close database connection.

        This method ensures proper cleanup of database resources. It's
        automatically called when using the class as a context manager.
        """
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        """Context manager entry.

        Returns:
            SensorDatabase: The database instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Ensures the database connection is properly closed when exiting
        the context manager block.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        self.close()
