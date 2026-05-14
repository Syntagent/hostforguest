#!/usr/bin/env python
"""
Development startup script for TouristGuideLocal.

This script provides an easy way to start the development server.
"""

import uvicorn
from app.core.config import settings


if __name__ == "__main__":
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Server: http://{settings.host}:{settings.port}")
    print(f"API Docs: http://{settings.host}:{settings.port}{settings.api_v1_str}/docs")
    print(f"Health Check: http://{settings.host}:{settings.port}/health")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

