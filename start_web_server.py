#!/usr/bin/env python3
"""
Startup script for GRAAL Web API server.
Run with: poetry run python start_web_server.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "graal.api.main:app", host="localhost", port=8000, reload=True, log_level="info"
    )
