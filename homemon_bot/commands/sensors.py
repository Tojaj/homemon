"""Sensor data command handlers."""

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from ..config import load_config, is_authorized
from ..api_client import (
    get_recent_measurements,
    get_sensors,
    get_sensor_stats,
    get_sensor_measurements,
)
from ..utils.graphs import generate_graphs


async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command - show latest measurements.

    Retrieves and displays the most recent measurements from all sensors.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    try:
        # Get sensors first to have access to aliases
        sensors = {s['id']: s for s in await get_sensors()}
        measurements = await get_recent_measurements()

        # Format response message
        response = []
        for m in measurements:
            nice_timestamp = datetime.fromisoformat(m['timestamp']).strftime("%Y.%m.%d  %H:%M:%S")
            sensor = sensors.get(m['sensor_id'], {})
            sensor_name = sensor.get('alias') or sensor.get('mac_address', str(m['sensor_id']))
            sensor_info = f"{sensor_name}:\n"
            sensor_info += f"Temperature: {m['temperature']}°C\n"
            sensor_info += f"Humidity: {m['humidity']}%\n"
            sensor_info += f"Battery: {m['battery_voltage']}V\n"
            sensor_info += f"Last update: {nice_timestamp}"
            response.append(sensor_info)

        await update.message.reply_text("\n\n".join(response))
    except Exception as e:
        await update.message.reply_text(f"Error fetching data: {str(e)}")


async def average(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /average command - show average measurements.

    Calculates and displays average values for each sensor over the specified
    time period (default: 24 hours).

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    # Get hours from command or use default
    hours = 24
    if context.args:
        try:
            hours = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid number of hours specified.")
            return
        
        if hours < 1:
            await update.message.reply_text("Invalid number of hours specified.")
            return

    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get all sensors
        sensors = await get_sensors()
        if not sensors:
            await update.message.reply_text("No sensors found in the system.")
            return

        response = []
        no_data_sensors = []
        for sensor in sensors:
            try:
                # Get stats and measurements for each sensor
                stats = await get_sensor_stats(
                    sensor['id'], start_time, end_time
                )
                measurements = await get_sensor_measurements(
                    sensor['id'], start_time, end_time
                )
                measurement_count = len(measurements)

                if stats['average_temperature'] is None or stats['average_humidity'] is None:
                    no_data_sensors.append(sensor.get('alias') or sensor['mac_address'])
                    continue

                sensor_name = sensor.get('alias') or sensor['mac_address']
                sensor_info = f"{sensor_name}:\n"
                sensor_info += (
                    f"Average Temperature: {stats['average_temperature']:.1f}°C\n"
                )
                sensor_info += f"Average Humidity: {stats['average_humidity']:.1f}%\n"
                sensor_info += f"Number of measurements: {measurement_count}"
                response.append(sensor_info)
            except Exception:
                no_data_sensors.append(sensor.get('alias') or sensor['mac_address'])

        if not response and no_data_sensors:
            time_range = f"last {hours} hour{'s' if hours != 1 else ''}"
            await update.message.reply_text(
                f"No measurements found for sensor{'s' if len(no_data_sensors) > 1 else ''} "
                f"{', '.join(no_data_sensors)} in the {time_range}. Try increasing the time range "
                f"or check if the sensor{'s' if len(no_data_sensors) > 1 else ''} {'are' if len(no_data_sensors) > 1 else 'is'} working properly."
            )
            return

        message = f"Averages over last {hours}h:\n\n" + "\n\n".join(response)
        if no_data_sensors:
            message += f"\n\nNote: No data available for sensor{'s' if len(no_data_sensors) > 1 else ''} {', '.join(no_data_sensors)} in this time period."
        
        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(
            f"An unexpected error occurred while calculating averages: {str(e)}\n"
            "Please try again or contact the administrator if the problem persists."
        )


async def graphs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /graphs command - generate measurement graphs.

    Generates and sends three graphs showing temperature, humidity, and battery
    levels over the specified time period (default: 24 hours).

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    # Get hours from command or use default
    hours = 24
    if context.args:
        try:
            hours = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid number of hours specified.")
            return
        
        if hours < 1:
            await update.message.reply_text("Invalid number of hours specified.")
            return

    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get all sensors
        sensors = {s['id']: s for s in await get_sensors()}
        if not sensors:
            await update.message.reply_text("No sensors found in the system.")
            return

        # Collect measurements for each sensor
        all_measurements = []
        sensors_with_data = set()
        no_data_sensors = []

        for sensor_id, sensor in sensors.items():
            measurements = await get_sensor_measurements(
                sensor_id, start_time, end_time
            )
            if measurements:
                all_measurements.extend(
                    [{**m, "sensor_id": sensor_id} for m in measurements]
                )
                sensors_with_data.add(sensor.get('alias') or sensor['mac_address'])
            else:
                no_data_sensors.append(sensor.get('alias') or sensor['mac_address'])

        # Handle case where no sensors have data
        if not sensors_with_data:
            time_range = f"last {hours} hour{'s' if hours != 1 else ''}"
            await update.message.reply_text(
                f"No measurements found for sensor{'s' if len(no_data_sensors) > 1 else ''} "
                f"{', '.join(no_data_sensors)} in the {time_range}. Try increasing the time range "
                f"or check if the sensor{'s' if len(no_data_sensors) > 1 else ''} {'are' if len(no_data_sensors) > 1 else 'is'} working properly."
            )
            return

        # If some sensors have data, first send a message about sensors with no data
        if no_data_sensors:
            await update.message.reply_text(
                f"Note: No data available for sensor{'s' if len(no_data_sensors) > 1 else ''} "
                f"{', '.join(no_data_sensors)} in the last {hours}h. "
                f"Generating graphs for sensor{'s' if len(sensors_with_data) > 1 else ''} "
                f"{', '.join(sorted(sensors_with_data))}..."
            )

        # Generate and send graphs for sensors that have data
        graph_buffers = await generate_graphs(all_measurements, hours)
        for buf in graph_buffers:
            await update.message.reply_photo(photo=buf)

    except Exception as e:
        await update.message.reply_text(
            f"An unexpected error occurred while generating graphs: {str(e)}\n"
            "Please try again or contact the administrator if the problem persists."
        )
