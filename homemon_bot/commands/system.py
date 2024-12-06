"""System-related command handlers."""

import subprocess
import re
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


def is_valid_service_name(service: str) -> bool:
    """Validate a systemd service name for safety.

    Ensures the service name:
    - Contains only alphanumeric characters, hyphens, and underscores
    - Has a reasonable length
    - Doesn't contain any shell special characters or spaces
    - Doesn't contain any command injection attempts

    Args:
        service: Name of the service to validate

    Returns:
        bool: True if the service name is valid, False otherwise
    """
    # Check if service name is empty or too long
    if not service or len(service) > 50:
        return False

    # Only allow alphanumeric characters, hyphens, and underscores
    # This automatically prevents shell command injection
    if not re.match(r'^[a-zA-Z0-9_-]+$', service):
        return False

    # Additional checks for common command injection patterns
    suspicious_patterns = [
        '&&', '||', '|', ';', '>', '<', '`', '$', '(', ')',
        'bash', 'sh', 'cmd', 'exec', 'eval', 'sudo'
    ]
    
    service_lower = service.lower()
    if any(pattern in service_lower for pattern in suspicious_patterns):
        return False

    return True


def service_exists(service: str) -> bool:
    """Check if a systemd service exists.

    Args:
        service: Name of the service to check

    Returns:
        bool: True if the service exists, False otherwise
    """
    try:
        # Use systemctl status without sudo to check if service exists
        subprocess.run(["systemctl", "status", service], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except subprocess.CalledProcessError as e:
        # Return code 3 means service exists but is stopped
        # Return code 4 means service exists but has never been started
        return e.returncode in [3, 4]
    except Exception:
        return False


async def restart_homemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /restart_homemon command - restart configured homemon services.

    Restarts the systemd services specified in the config.telegram.yaml file.
    If no services are configured, informs the user.
    Before attempting to restart a service:
    - Validates the service name for safety
    - Verifies it exists to prevent potential command injection attacks

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    services = config.get("services_to_restart", [])
    if not services:
        await update.message.reply_text("No services configured to restart. Please check config.telegram.yaml")
        return

    for service in services:
        # First validate the service name
        if not is_valid_service_name(service):
            await update.message.reply_text(f"❌ Invalid service name: {service}")
            continue

        # Then verify the service exists without sudo
        if not service_exists(service):
            await update.message.reply_text(f"❌ Service {service} does not exist")
            continue

        # Only attempt to restart if service exists and name is valid
        try:
            subprocess.run(["sudo", "systemctl", "restart", service], check=True)
            await update.message.reply_text(f"✅ Service {service} restarted successfully")
        except subprocess.CalledProcessError:
            await update.message.reply_text(f"❌ Failed to restart service {service}")
