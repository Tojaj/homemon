"""Help command handler."""

from telegram import Update
from telegram.ext import ContextTypes
from ..config import load_config, is_authorized


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
/scan_wifi - Shows available WiFi networks sorted by signal strength
/ping [address] - Pings specified address or gateway
/ota - Updates code from git repository (git pull)
/reboot - Reboots the system
/shutdown - Safely shuts down the system
/restart_homemon - Restarts configured homemon services
/help, /commands - Shows this help message"""

    await update.message.reply_text(help_text)
