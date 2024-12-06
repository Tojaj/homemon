"""Configuration handling for the Telegram bot.

This module provides functionality to load and validate the bot's configuration
from the config.telegram.yaml file.
"""

import os
import sys
import yaml
from typing import Dict, List, Union


def load_config() -> Dict[str, Union[str, List[int]]]:
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


def is_authorized(chat_id: int, config: Dict[str, Union[str, List[int]]]) -> bool:
    """Check if a chat ID is authorized to use the bot.

    Args:
        chat_id: The Telegram chat ID to check
        config: The bot configuration dictionary

    Returns:
        bool: True if the chat ID is in the allowed list, False otherwise
    """
    return chat_id in config["allowed_chat_ids"]
