#!/usr/bin/env python3
import asyncio
from class_factory import mqueue, scheduler_service
from dunebugger_logging import logger

async def main():
    """Main entry point for the scheduler service"""
    try:
        await mqueue.start()

        # Initialize and run the scheduler service
        await scheduler_service.initialize()
        return await scheduler_service.run_scheduler()
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {str(e)}")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
