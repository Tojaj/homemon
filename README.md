# Home Monitor

## Features of Home Monitor

- Continuously polls specified Xiaomi sensors.
- Stores sensor data in an SQLite database.
- Configurable polling interval and database path.
- Supports multiple sensors with aliases.

## Usage of Home Monitor

### How to find out MAC address of your Xiaomi Mi Temperature and Humidity Monitor 2 (LYWSD03MMC)

#### Using the Discovery Script

The project includes a sensor discovery script that can automatically find your Xiaomi sensors and optionally add them to your configuration:

To just discover sensors and print their MAC addresses:

    ./discover_sensors.py

To discover sensors and add them to your config file:

    ./discover_sensors.py --config config.yaml

When run with the `--config` option, the script will:
- Show only newly discovered sensors (not already in your config)
- Allow you to set friendly aliases for each sensor
- Automatically update your config file

#### Manual Discovery Method

If you prefer to find sensors manually, you can use the bluetoothctl command:

    bluetoothctl
    power on
    scan on
    ...
    [bluetooth]# [NEW] Device A4:C1:38:DE:EA:B9 LYWSD03MMC
    ...
    scan off
    exit

### Configuration

The script reads configuration from `config.yaml`.

**Configuration Options (config.yaml):**

- `polling_interval`: The time interval (in seconds) between sensor readings. Defaults to 900 seconds (15 minutes if not set).
- `database_file`: The path to the SQLite database file. Defaults to `sensor_data.db` if not set.
- `sensors`: A list of dictionaries, each defining a sensor with `mac_address` (required) and an optional `alias`.

Example `config.yaml`:

```yaml
# Polling interval in seconds (default: 900 seconds = 15 minutes if not set)
polling_interval: 900

# Database filename (default: sensor_data.db if not set)
database_file: "sensor_data.db"

# List of sensors with their MAC addresses and optional aliases
sensors:
  - mac_address: "A4:C1:38:DE:EA:B9"
    alias: "Living Room"
   - mac_address: "A4:C1:38:DE:EA:BF"
     alias: "Bedroom"
```

### Running the Monitor

To start monitoring:

    ./monitor.py

The script will continuously poll the specified sensors and store the data in the database.  Press Ctrl+C to stop.


# Sample Data Generation

The project includes a script `generate_sample_data.py` that can create sample SQLite databases in the homemon format. This is useful for testing and development purposes.

## Features of Sample Data Generation

- Generates realistic temperature patterns (18-26°C range with daily variations)
- Creates correlated humidity data (30-60% range)
- Includes battery voltage values (2.8-3.0V)
- Configurable number of sensors and samples
- Adjustable sampling interval
- Uses the homemon SensorDatabase class

## Usage of Sample Data Generation

Basic usage with default values (2 sensors, 50 samples each, 15-minute intervals):

    ./generate_sample_data.py --db-path test/sample.db

All available options:

    ./generate_sample_data.py --db-path test/sample.db --samples 100 --sensors 3 --interval 30

Options:
- `--db-path`: Path to the output SQLite database (required)
- `--samples`: Number of samples per sensor (default: 50)
- `--sensors`: Number of sensors to simulate (default: 2)
- `--interval`: Sampling interval in minutes (default: 15)
