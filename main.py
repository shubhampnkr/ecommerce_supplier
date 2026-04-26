#!/usr/bin/env python3
"""
Direct entry point – python main.py
Equivalent to: meesho-agent run
"""
import asyncio
import sys
from core.orchestrator import run_pipeline
from core.logger import logger


async def main():
    skip_email = "--skip-email" in sys.argv or "-n" in sys.argv
    state = await run_pipeline(skip_email=skip_email)
    if not state.success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
