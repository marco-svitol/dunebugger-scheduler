#!/usr/bin/env python3
import asyncio
from class_factory import mqueue, schedule_interpreter
from dunebugger_logging import logger

async def main():
    try:
        await mqueue.start_listener()
        # wait that NATS is connected before continuing
        while not mqueue.is_connected:
            await asyncio.sleep(1)
        await schedule_interpreter.request_lists()
        
        # toDo: implement the schedulrer service that executes actions based on schedules
        while True:
            await asyncio.sleep(1)


    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

    finally:
        # Clean up resources when exiting
        print("Cleaning up resources...")
        
        # Close NATS connection
        await mqueue.close_listener()
 
        print("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(main())
