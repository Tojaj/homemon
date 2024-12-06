#!/usr/bin/env python3
"""Script to run a Telegram bot for Home Monitor.

This script sets up and runs a Telegram bot that:
    - Provides secure access through configurable allowed chat IDs
    - Retrieves real-time sensor data
    - Generates historical data analysis and visualizations
    - Offers system control and monitoring capabilities

The bot implements the following commands:
    /recent - Shows latest measurements from all sensors
    /average [hours] - Displays average values over specified hours (default: 24h)
    /graphs [hours] - Generates sensor data graphs for specified period (default: 24h)
    /wifi - Shows current WiFi connection details
    /ping [address] - Pings specified address or gateway
    /shutdown - Safely shuts down the system
    /help, /commands - Shows this help message

Configuration:
    The bot reads its configuration from config.telegram.yaml, which must contain:
        - bot_token: Your Telegram bot token from @BotFather
        - allowed_chat_ids: List of chat IDs allowed to interact with the bot

Example config.telegram.yaml:
    bot_token: "YOUR_BOT_TOKEN_HERE"
    allowed_chat_ids:
      - 123456789
"""

import os
import yaml
import asyncio
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp
import json
import subprocess
import sys

API_BASE_URL = "http://localhost:8000/api"


def load_config():
    """Load and validate the Telegram bot configuration.

    This function reads the config.telegram.yaml file and validates its contents
    to ensure all required fields are present and properly formatted.

    Returns:
        dict: The configuration dictionary containing bot_token and allowed_chat_ids

    Raises:
        SystemExit: If the config file is missing, invalid, or improperly formatted
    """
    config_path = "config.telegram.yaml"

    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        print("\nPlease create the configuration file with the following format:")
        print(
            """
# config.telegram.yaml example:
bot_token: "YOUR_BOT_TOKEN_HERE"
allowed_chat_ids:
  - 123456789  # Replace with your chat ID

To get started:
1. Create a new bot and get your token from @BotFather
2. Get your chat ID by sending /start to @userinfobot
3. Create config.telegram.yaml with your bot token and chat ID
"""
        )
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate required fields
        if not config:
            raise ValueError("Configuration file is empty")
        if "bot_token" not in config:
            raise ValueError("Bot token not found in configuration")
        if "allowed_chat_ids" not in config:
            raise ValueError("Allowed chat IDs not found in configuration")
        if not isinstance(config["allowed_chat_ids"], list):
            raise ValueError("Allowed chat IDs must be a list")
        if not config["allowed_chat_ids"]:
            raise ValueError("At least one chat ID must be specified")

        return config

    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {str(e)}")
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid configuration: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading configuration file: {str(e)}")
        sys.exit(1)


def is_authorized(chat_id, config):
    """Check if a chat ID is authorized to use the bot.

    Args:
        chat_id: The Telegram chat ID to check
        config: The bot configuration dictionary

    Returns:
        bool: True if the chat ID is in the allowed list, False otherwise
    """
    return chat_id in config["allowed_chat_ids"]


async def fetch_data(endpoint):
    """Fetch data from the Home Monitor API.

    Args:
        endpoint: The API endpoint to fetch data from

    Returns:
        dict: The JSON response from the API

    Raises:
        Exception: If there's an error fetching data from the API
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/{endpoint}") as response:
            return await response.json()


async def get_wifi_info():
    """Get current WiFi connection information.

    Returns:
        dict: WiFi connection details including:
            - ssid: Network name
            - signal: Signal strength
            - ip: IP address
            - netmask: Network mask
            - gateway: Gateway address
        str: Error message if there was a problem getting the information
    """
    try:
        # Get the active WiFi device name
        device_info = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"]).decode()
        wifi_device = None
        for line in device_info.split("\n"):
            if line.strip():
                dev, typ, state = line.split(":")
                if typ == "wifi" and state == "connected":
                    wifi_device = dev
                    break
        
        if not wifi_device:
            return "No active WiFi connection found"

        # Get SSID and signal strength using nmcli
        nmcli_output = subprocess.check_output(["nmcli", "-t", "-f", "SIGNAL,SSID,IN-USE", "device", "wifi", "list"]).decode()
        ssid = None
        signal = None
        for line in nmcli_output.split("\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) >= 3 and parts[2] == "*":  # Connected network has "*" in IN-USE field
                    signal = parts[0]
                    ssid = parts[1]
                    break

        # Get IP information using the detected WiFi device
        ip_info = subprocess.check_output(["ip", "addr", "show", wifi_device]).decode()
        ip_address = None
        netmask = None
        for line in ip_info.split("\n"):
            if "inet " in line:
                parts = line.strip().split()
                ip_address = parts[1].split("/")[0]
                netmask = parts[1].split("/")[1]

        # Get gateway
        route_info = subprocess.check_output(["ip", "route"]).decode()
        gateway = None
        for line in route_info.split("\n"):
            if "default via" in line:
                gateway = line.split("via")[1].split()[0]

        return {
            "ssid": ssid,
            "signal": signal,
            "ip": ip_address,
            "netmask": netmask,
            "gateway": gateway,
        }
    except Exception as e:
        return f"Error getting WiFi info: {str(e)}"


async def ping_address(address, count=5):
    """Ping a network address.

    Args:
        address: The address to ping
        count: Number of pings to send (default: 5)

    Returns:
        str: The ping command output or error message
    """
    try:
        output = subprocess.check_output(
            ["ping", "-c", str(count), address], stderr=subprocess.STDOUT
        ).decode()
        return output
    except subprocess.CalledProcessError as e:
        return f"Error pinging {address}: {e.output.decode()}"


async def generate_graphs(measurements, hours):
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


# Command handlers
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help and /commands - show available commands.

    Displays a list of all available commands and their descriptions.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    help_text = """Available commands:
/recent - Shows latest measurements from all sensors
/average [hours] - Displays average values over specified hours (default: 24h)
/graphs [hours] - Generates sensor data graphs for specified period (default: 24h)
/wifi - Shows current WiFi connection details
/ping [address] - Pings specified address or gateway
/shutdown - Safely shuts down the system
/help, /commands - Shows this help message"""

    await update.message.reply_text(help_text)


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
        measurements = await fetch_data("measurements/recent")

        # Format response message
        response = []
        for m in measurements:
            nice_timestamp = datetime.fromisoformat(m['timestamp']).strftime("%Y.%m.%d  %H:%M:%S")
            sensor_info = f"Sensor {m['sensor_id']}:\n"
            sensor_info += f"Temperature: {m['temperature']}°C\n"
            sensor_info += f"Humidity: {m['humidity']}%\n"
            sensor_info += f"Battery: {m['battery_voltage']}V\n"
            sensor_info += f"Last update: {nice_timestamp}"
            response.append(sensor_info)

        await update.message.reply_text("\n\n".join(response))
    except Exception as e:
        await update.message.reply_text(f"Error fetching data: {str(e)}")


async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shutdown command - shutdown the system.

    Initiates a system shutdown using the shutdown command.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    await update.message.reply_text("Shutting down the system...")
    subprocess.run(["sudo", "shutdown", "-h", "now"])


async def wifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wifi command - show WiFi information.

    Displays current WiFi connection details including network name,
    signal strength, IP address, netmask, and gateway.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    info = await get_wifi_info()
    if isinstance(info, str):  # Error message
        await update.message.reply_text(info)
    else:
        response = f"WiFi Network: {info['ssid']}\n"
        response += f"Signal Strength: {info['signal']}\n"
        response += f"IP Address: {info['ip']}\n"
        response += f"Netmask: {info['netmask']}\n"
        response += f"Gateway: {info['gateway']}"
        await update.message.reply_text(response)


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command - ping a network address.

    Pings the specified address or the gateway if no address is provided.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    # Get gateway if no address specified
    address = context.args[0] if context.args else (await get_wifi_info())["gateway"]
    result = await ping_address(address)
    await update.message.reply_text(result)


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

    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get all sensors
        sensors = await fetch_data("sensors")

        response = []
        for sensor in sensors:
            # Get stats for each sensor
            stats = await fetch_data(
                f"measurements/{sensor['id']}/stats?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}"
            )

            sensor_info = f"Sensor {sensor['id']}:\n"
            sensor_info += (
                f"Average Temperature: {stats['average_temperature']:.1f}°C\n"
            )
            sensor_info += f"Average Humidity: {stats['average_humidity']:.1f}%"
            response.append(sensor_info)

        await update.message.reply_text(
            f"Averages over last {hours}h:\n\n" + "\n\n".join(response)
        )
    except Exception as e:
        await update.message.reply_text(f"Error calculating averages: {str(e)}")


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

    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get all sensors
        sensors = await fetch_data("sensors")

        # Collect all measurements
        all_measurements = []
        for sensor in sensors:
            measurements = await fetch_data(
                f"measurements/{sensor['id']}?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}"
            )
            all_measurements.extend(
                [{**m, "sensor_id": sensor["id"]} for m in measurements]
            )

        # Generate and send graphs
        graph_buffers = await generate_graphs(all_measurements, hours)

        for buf in graph_buffers:
            await update.message.reply_photo(photo=buf)

    except Exception as e:
        await update.message.reply_text(f"Error generating graphs: {str(e)}")


def main():
    """Set up and run the Telegram bot.

    This function:
        1. Loads and validates the bot configuration
        2. Creates the Telegram bot application
        3. Registers command handlers
        4. Starts the bot's event polling

    The bot provides the following commands:
        - /recent: Show latest measurements
        - /average [hours]: Show averages over time
        - /graphs [hours]: Generate measurement graphs
        - /wifi: Show WiFi information
        - /ping [address]: Ping network address
        - /shutdown: Shutdown the system
        - /help, /commands: Show help message
    """
    try:
        config = load_config()

        # Create application and add handlers
        application = Application.builder().token(config["bot_token"]).build()

        # Add command handlers
        application.add_handler(CommandHandler(["help", "commands"], help_cmd))
        application.add_handler(CommandHandler("recent", recent))
        application.add_handler(CommandHandler("shutdown", shutdown))
        application.add_handler(CommandHandler("wifi", wifi))
        application.add_handler(CommandHandler("ping", ping_cmd))
        application.add_handler(CommandHandler("average", average))
        application.add_handler(CommandHandler("graphs", graphs))

        print("Telegram bot is starting...")
        # Run the bot
        application.run_polling()
    except KeyboardInterrupt:
        print("\nBot shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
