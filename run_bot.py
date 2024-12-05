#!/usr/bin/env python3

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

API_BASE_URL = "http://localhost:8000"

def load_config():
    """Load telegram bot configuration from config.telegram.yaml."""
    with open("config.telegram.yaml", "r") as f:
        return yaml.safe_load(f)

def is_authorized(chat_id, config):
    """Check if the chat_id is in the allowed list."""
    return chat_id in config["allowed_chat_ids"]

async def fetch_data(endpoint):
    """Fetch data from the API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/{endpoint}") as response:
            return await response.json()

async def get_wifi_info():
    """Get WiFi connection information."""
    try:
        # Get SSID and signal strength
        iwconfig = subprocess.check_output(["iwconfig", "wlan0"]).decode()
        ssid = None
        signal = None
        for line in iwconfig.split("\n"):
            if "ESSID:" in line:
                ssid = line.split("ESSID:")[1].strip('"')
            if "Signal level=" in line:
                signal = line.split("Signal level=")[1].split()[0]

        # Get IP information
        ip_info = subprocess.check_output(["ip", "addr", "show", "wlan0"]).decode()
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
            "gateway": gateway
        }
    except Exception as e:
        return f"Error getting WiFi info: {str(e)}"

async def ping_address(address, count=5):
    """Ping an address and return results."""
    try:
        output = subprocess.check_output(
            ["ping", "-c", str(count), address],
            stderr=subprocess.STDOUT
        ).decode()
        return output
    except subprocess.CalledProcessError as e:
        return f"Error pinging {address}: {e.output.decode()}"

async def generate_graphs(measurements, hours):
    """Generate temperature, humidity, and battery graphs."""
    graphs = []
    metrics = [
        ("Temperature", "temperature", "°C"),
        ("Humidity", "humidity", "%"),
        ("Battery", "battery_voltage", "V")
    ]
    
    for title, field, unit in metrics:
        plt.figure(figsize=(10, 6))
        
        # Group data by sensor
        sensor_data = {}
        for m in measurements:
            sensor_id = m["sensor_id"]
            if sensor_id not in sensor_data:
                sensor_data[sensor_id] = {"timestamps": [], "values": []}
            sensor_data[sensor_id]["timestamps"].append(datetime.fromisoformat(m["timestamp"]))
            sensor_data[sensor_id]["values"].append(m[field])

        # Plot each sensor's data
        for sensor_id, data in sensor_data.items():
            plt.plot(data["timestamps"], data["values"], label=f'Sensor {sensor_id}')
        
        plt.title(f"{title} over last {hours}h")
        plt.xlabel('Time')
        plt.ylabel(f"{title} ({unit})")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        graphs.append(buf)
        plt.close()
    
    return graphs

# Command handlers
async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command - show latest measurements."""
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    try:
        measurements = await fetch_data("measurements/recent")
        
        # Format response message
        response = []
        for m in measurements:
            sensor_info = f"Sensor {m['sensor_id']}:\n"
            sensor_info += f"Temperature: {m['temperature']}°C\n"
            sensor_info += f"Humidity: {m['humidity']}%\n"
            sensor_info += f"Battery: {m['battery_voltage']}V\n"
            sensor_info += f"Last update: {m['timestamp']}"
            response.append(sensor_info)
        
        await update.message.reply_text("\n\n".join(response))
    except Exception as e:
        await update.message.reply_text(f"Error fetching data: {str(e)}")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shutdown command."""
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    await update.message.reply_text("Shutting down the system...")
    subprocess.run(["sudo", "shutdown", "-h", "now"])

async def wifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wifi command."""
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
    """Handle /ping command."""
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    # Get gateway if no address specified
    address = context.args[0] if context.args else (await get_wifi_info())['gateway']
    result = await ping_address(address)
    await update.message.reply_text(result)

async def average(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /average command."""
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
            stats = await fetch_data(f"measurements/{sensor['id']}/stats?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}")
            
            sensor_info = f"Sensor {sensor['id']}:\n"
            sensor_info += f"Average Temperature: {stats['average_temperature']:.1f}°C\n"
            sensor_info += f"Average Humidity: {stats['average_humidity']:.1f}%"
            response.append(sensor_info)
        
        await update.message.reply_text(f"Averages over last {hours}h:\n\n" + "\n\n".join(response))
    except Exception as e:
        await update.message.reply_text(f"Error calculating averages: {str(e)}")

async def graphs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /graphs command."""
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
            all_measurements.extend([{**m, "sensor_id": sensor['id']} for m in measurements])

        # Generate and send graphs
        graph_buffers = await generate_graphs(all_measurements, hours)
        
        for buf in graph_buffers:
            await update.message.reply_photo(photo=buf)
            
    except Exception as e:
        await update.message.reply_text(f"Error generating graphs: {str(e)}")

def main():
    """Main function to run the bot."""
    config = load_config()
    
    # Create application and add handlers
    application = Application.builder().token(config["bot_token"]).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("wifi", wifi))
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("average", average))
    application.add_handler(CommandHandler("graphs", graphs))
    
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
