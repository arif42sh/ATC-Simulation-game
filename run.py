"""
=============================================================================
SkyATC AI - Application Entry Point Wrapper
Forwards execution to main.py
=============================================================================
"""

import asyncio
from main import main

if __name__ == "__main__":
    asyncio.run(main())
