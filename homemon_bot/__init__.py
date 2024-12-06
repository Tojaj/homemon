"""Telegram bot for Home Monitor.

This module provides a Telegram bot interface for the Home Monitor system,
allowing users to:
    - View sensor measurements and statistics
    - Generate data visualizations
    - Monitor and control system functions
    - Manage WiFi connections
"""

from telegram.ext import Application, CommandHandler

from .config import load_config
from .commands.help import help_cmd
from .commands.sensors import recent, average, graphs
from .commands.system import shutdown, reboot, ota, ping_cmd, restart_homemon
from .commands.wifi import wifi_info, scan_wifi_cmd


def create_bot() -> Application:
    """Create and configure the Telegram bot application.

    Returns:
        Application: The configured bot application ready to run
    """
    config = load_config()
    application = Application.builder().token(config["bot_token"]).build()

    # Register command handlers
    application.add_handler(CommandHandler(["help", "commands"], help_cmd))
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("average", average))
    application.add_handler(CommandHandler("graphs", graphs))
    application.add_handler(CommandHandler("wifi", wifi_info))
    application.add_handler(CommandHandler("scan_wifi", scan_wifi_cmd))
    application.add_handler(CommandHandler("ping", ping_cmd))
    application.add_handler(CommandHandler("ota", ota))
    application.add_handler(CommandHandler("reboot", reboot))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("restart_homemon", restart_homemon))

    return application
