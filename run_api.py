#!/usr/bin/env python
"""Script to run the FastAPI server using uvicorn.

This script sets up and runs a FastAPI server that:
    - Serves the web UI static files
    - Mounts the API endpoints
    - Handles CORS for cross-origin requests
    - Provides development-specific middleware for caching control

Command line arguments:
    --db: Path to the SQLite database file (default: homemon.db)
    --host: Host to bind the server to (default: 0.0.0.0)
    --port: Port to bind the server to (default: 8000)

Example usage:
    ./run_api.py
    ./run_api.py --db custom.db --port 8080
"""

import argparse
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from homemon.api import init_app


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to disable caching for static files during development.

    This middleware adds headers to prevent caching of static files, which is
    useful during development to ensure changes are immediately visible.

    Args:
        app: The FastAPI application instance

    Note:
        Remove this middleware in production to enable default caching behavior
        for better performance.
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and add no-cache headers for static files.

        Args:
            request (Request): The incoming HTTP request
            call_next: The next middleware or route handler in the chain

        Returns:
            Response: The HTTP response with added cache control headers for
                static files
        """
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


def main():
    """Set up and run the FastAPI server.

    This function:
        1. Parses command line arguments for server configuration
        2. Creates and configures the FastAPI application:
            - Adds CORS middleware for cross-origin requests
            - Adds no-cache middleware for development
            - Mounts static files from the webui directory
            - Initializes and mounts the API endpoints
            - Sets up the root route to serve index.html
        3. Starts the uvicorn server with the specified configuration

    The server provides:
        - Static file serving for the web UI
        - API endpoints under /api
        - Web UI access at the root path (/)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Home Monitor API server.")
    parser.add_argument(
        "--db",
        default="homemon.db",
        help="Path to the SQLite database file (default: homemon.db)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    args = parser.parse_args()

    # Create the main FastAPI app
    app = FastAPI()

    # Add CORS middleware to the main app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add no-cache middleware for development
    # TODO: Remove this in production to enable default caching behavior
    app.add_middleware(NoCacheMiddleware)

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    webui_dir = os.path.join(script_dir, "webui")

    # Mount the static files
    app.mount("/static", StaticFiles(directory=webui_dir), name="static")

    # Initialize and mount the API app
    api_app = init_app(args.db)
    app.mount("/api", api_app)

    # Serve index.html at the root path
    @app.get("/")
    async def read_root():
        """Serve the main web UI page.

        Returns:
            FileResponse: The index.html file from the webui directory
        """
        return FileResponse(os.path.join(webui_dir, "index.html"))

    # Run the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,  # Disable reload in production
    )


if __name__ == "__main__":
    main()
