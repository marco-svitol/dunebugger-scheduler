#!/usr/bin/env python3
import asyncio
from version import get_version_info
print(f"Dunebugger core version: {get_version_info()['full_version']}, build type: {get_version_info()['build_type']}, build number: {get_version_info()['build_number']}")

from class_factory import mqueue, mqueue_handler, schedule_interpreter, state_tracker
from dunebugger_logging import logger

async def main():
    try:
        await mqueue.start_listener()
        # wait that NATS is connected before continuing
        while not mqueue.is_connected:
            await asyncio.sleep(1)
        
        # Request NTP status from controller to initialize state
        await mqueue_handler.request_ntp_status()
        
        # Wait a bit for lists to be received
        await asyncio.sleep(2)
        
        # Start the state monitoring task
        await state_tracker.start_state_monitoring()

        # Initialize schedule after validation
        await schedule_interpreter.init_schedule()

        # Start the scheduler service
        scheduler_task = asyncio.create_task(schedule_interpreter.run_scheduler())
        
        # Keep the main loop running
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("Scheduler task was cancelled")


    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

    finally:
        # Clean up resources when exiting
        logger.info("Cleaning up resources...")
        
        # Cancel scheduler task if it's still running
        if 'scheduler_task' in locals() and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled successfully")
        
        # Close NATS connection
        await mqueue.close_listener()
 
        logger.info("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(main())
