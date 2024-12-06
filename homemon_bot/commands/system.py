"""System-related command handlers."""

import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from ..config import load_config, is_authorized
from ..utils.system import perform_git_pull, ping_address, get_wifi_info


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


async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reboot command - reboot the system.

    Initiates a system reboot using the reboot command.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    await update.message.reply_text("Rebooting the system...")
    subprocess.run(["sudo", "reboot"])


async def ota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ota command - update code from git repository.

    Performs a git pull operation in the current directory to update the code.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    result = await perform_git_pull()
    await update.message.reply_text(result)


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
