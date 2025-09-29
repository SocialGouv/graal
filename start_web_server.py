#!/usr/bin/env python3
"""
Startup script for GRAAL Web API server.
Run with: poetry run python start_web_server.py
"""

import os

import uvicorn

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "localhost")
    port = int(os.getenv("BACKEND_PORT", "8000"))

    uvicorn.run(
        "graal.api.main:app", host=host, port=port, reload=True, log_level="info"
    )
