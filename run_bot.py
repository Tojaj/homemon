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
    /scan_wifi - Shows available WiFi networks sorted by signal strength
    /ping [address] - Pings specified address or gateway
    /ota - Updates code from git repository (git pull)
    /reboot - Reboots the system
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

import sys
from homemon_bot import create_bot


def main():
    """Set up and run the Telegram bot."""
    try:
        print("Telegram bot is starting...")
        application = create_bot()
        application.run_polling()
    except KeyboardInterrupt:
        print("\nBot shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
