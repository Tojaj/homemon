#!/usr/bin/env python3
"""Entry point script for Home Monitor.

This script provides a simple way to start the Home Monitor system.
"""

import asyncio
from homemon.monitor import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Disconnecting gracefully...")
