#!/usr/bin/env python3

"""Script to generate sample data for the homemon database.

This script creates a sample SQLite database with simulated temperature and humidity
sensor data. It generates realistic patterns including:
    - Daily temperature variations (warmer in afternoon, cooler at night)
    - Inverse relationship between temperature and humidity
    - Random variations to simulate real-world conditions
    - Realistic battery voltage values

Example usage:
    ./generate_sample_data.py --db-path test/sample.db
    ./generate_sample_data.py --db-path test/sample.db --samples 100 --sensors 3 --interval 30
    ./generate_sample_data.py --db-path test/sample.db --start-date 2024-01-01 --end-date 2024-01-07
"""

import argparse
import random
from datetime import datetime, timedelta
from homemon.database import SensorDatabase


def generate_mac_address():
    """Generate a random MAC address.

    Returns:
        str: A randomly generated MAC address in the format "XX:XX:XX:XX:XX:XX"
            where X is a hexadecimal digit.
    """
    return ":".join(["%02x" % random.randint(0, 255) for _ in range(6)])


def generate_sample_data(
    db_path,
    num_samples=None,
    num_sensors=2,
    interval_mins=15,
    start_date=None,
    end_date=None,
):
    """Generate sample sensor data with realistic patterns.

    This function creates sample sensor data in the database with realistic patterns
    including daily temperature variations, inverse humidity relationships, and
    battery voltage fluctuations.

    Args:
        db_path (str): Path to the SQLite database file
        num_samples (int, optional): Number of samples to generate per sensor.
            If not provided and no date range is specified, defaults to 50.
        num_sensors (int, optional): Number of sensors to simulate. Defaults to 2.
        interval_mins (int, optional): Time interval between samples in minutes.
            Defaults to 15.
        start_date (datetime, optional): Start date for data generation. Must be
            provided together with end_date.
        end_date (datetime, optional): End date for data generation. Must be
            provided together with start_date.

    Note:
        If start_date and end_date are provided, num_samples is calculated based
        on the date range and interval_mins. Otherwise, samples are generated
        backwards from the current time.

    Temperature ranges: 18.0°C to 26.0°C
    Humidity ranges: 30% to 60%
    Battery voltage ranges: 2.8V to 3.0V
    """
    with SensorDatabase(db_path) as db:
        # Create sensors
        sensor_ids = []
        for i in range(num_sensors):
            mac = generate_mac_address()
            sensor_id = db.get_or_create_sensor(mac, f"Sample Sensor {i+1}")
            sensor_ids.append(sensor_id)

        # Generate data for each sensor
        base_temps = [random.uniform(20.0, 22.0) for _ in range(num_sensors)]
        base_humidities = [random.uniform(40.0, 50.0) for _ in range(num_sensors)]

        # Determine time range
        if start_date and end_date:
            start_time = start_date
            end_time = end_date
            # Calculate number of samples based on date range
            time_diff = end_time - start_time
            num_samples = int(time_diff.total_seconds() / (interval_mins * 60))
        else:
            # Default behavior: generate samples backwards from current time
            end_time = datetime.now()
            num_samples = num_samples or 50  # Default to 50 if not specified
            start_time = end_time - timedelta(minutes=interval_mins * num_samples)

        for idx, sensor_id in enumerate(sensor_ids):
            current_time = start_time
            current_temp = base_temps[idx]
            current_humidity = base_humidities[idx]

            for _ in range(num_samples):
                # Add some random variation to temperature (-0.3 to +0.3°C)
                temp_variation = random.uniform(-0.3, 0.3)

                # Add time-of-day variation (±1.5°C)
                hour = current_time.hour
                # Temperature peaks at 14:00 (2pm)
                time_variation = 1.5 * math.sin((hour - 6) * math.pi / 12)

                temperature = round(current_temp + temp_variation + time_variation, 1)
                # Ensure temperature stays within realistic bounds
                temperature = max(18.0, min(26.0, temperature))

                # Humidity varies inversely with temperature
                humidity_variation = random.uniform(-2, 2)
                humidity = int(
                    max(
                        30,
                        min(
                            60,
                            current_humidity - temp_variation * 2 + humidity_variation,
                        ),
                    )
                )

                # Battery voltage between 2.8V and 3.0V
                battery = round(random.uniform(2.8, 3.0), 2)

                # Store the measurement
                db.cursor.execute(
                    """
                    INSERT INTO measurements (
                        sensor_id, timestamp, temperature, humidity, battery_voltage
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        sensor_id,
                        current_time.isoformat(),
                        temperature,
                        humidity,
                        battery,
                    ),
                )

                # Update for next iteration
                current_time += timedelta(minutes=interval_mins)
                current_temp = temperature
                current_humidity = humidity

            db.conn.commit()


def main():
    """Parse command line arguments and generate sample sensor data.

    This function handles command line argument parsing and validation before
    calling generate_sample_data() with the appropriate parameters.

    Command line arguments:
        --db-path: Path to the SQLite database (required)
        --samples: Number of samples per sensor (optional, default: 50)
        --sensors: Number of sensors to simulate (optional, default: 2)
        --interval: Sampling interval in minutes (optional, default: 15)
        --start-date: Start date for data generation (optional, format: YYYY-MM-DD)
        --end-date: End date for data generation (optional, format: YYYY-MM-DD)

    Note:
        start-date and end-date must be provided together if used.
    """
    parser = argparse.ArgumentParser(
        description="Generate sample sensor data with realistic patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --db-path test/sample.db
  %(prog)s --db-path test/sample.db --samples 100 --sensors 3 --interval 30
  %(prog)s --db-path test/sample.db --start-date 2024-01-01 --end-date 2024-01-07
        """,
    )
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database")
    parser.add_argument(
        "--samples", type=int, help="Number of samples per sensor (default: 50)"
    )
    parser.add_argument(
        "--sensors",
        type=int,
        default=2,
        help="Number of sensors to simulate (default: 2)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Sampling interval in minutes (default: 15)",
    )
    parser.add_argument(
        "--start-date", help="Start date for data generation (format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", help="End date for data generation (format: YYYY-MM-DD)"
    )

    args = parser.parse_args()

    # Parse dates if provided
    start_date = None
    end_date = None
    if args.start_date and args.end_date:
        start_date = datetime.fromisoformat(args.start_date)
        end_date = datetime.fromisoformat(args.end_date)
        if end_date <= start_date:
            parser.error("End date must be after start date")
    elif bool(args.start_date) != bool(args.end_date):
        parser.error("Both --start-date and --end-date must be provided together")

    generate_sample_data(
        args.db_path,
        num_samples=args.samples,
        num_sensors=args.sensors,
        interval_mins=args.interval,
        start_date=start_date,
        end_date=end_date,
    )

    if start_date and end_date:
        print(
            f"Generated data from {args.start_date} to {args.end_date} "
            f"for {args.sensors} sensors with {args.interval} minute intervals"
        )
    else:
        print(
            f"Generated {args.samples} samples for {args.sensors} sensors "
            f"with {args.interval} minute intervals"
        )


if __name__ == "__main__":
    import math

    main()
