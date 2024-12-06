"""WiFi-related command handlers."""

from telegram import Update
from telegram.ext import ContextTypes
from ..config import load_config, is_authorized
from ..utils.system import get_wifi_info, scan_wifi_networks


async def wifi_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def scan_wifi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scan_wifi command - show available WiFi networks.

    Scans for available WiFi networks and displays them sorted by signal strength.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    networks = await scan_wifi_networks()
    if isinstance(networks, str):  # Error message
        await update.message.reply_text(networks)
    else:
        if not networks:
            await update.message.reply_text("No WiFi networks found.")
            return

        response = ["Available WiFi Networks:"]
        for net in networks:
            response.append(
                f"\n📶 {net['ssid']}\n"
                f"Signal Strength: {net['signal']}%\n"
                f"Security: {net['security']}"
            )

        await update.message.reply_text("\n".join(response))