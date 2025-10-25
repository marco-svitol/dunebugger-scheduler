#!/usr/bin/python3

import asyncio
import schedule
import signal
import os
from datetime import datetime
from config_parser import ConfigParser
from dunebugger_logging import logger
from dunebugger_settings import settings

class SchedulerService:
    """
    Main scheduler service that integrates with the dunebugger message queue system
    """
    
    def __init__(self):
        self.running = True
        self.config_parser = None
        self.message_handler = None
        self.schedule_check_interval = 1  # seconds
        
    async def initialize(self):
        """Initialize the scheduler service"""
        logger.info("initialize: Initializing Dunebugger Scheduler Service")
        
        # Set up the config parser with the message handler
        # Use the config directory inside app folder since it was moved
        self.config_parser = ConfigParser(config_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config"))
        
        # Set the message handler if it was already set
        if self.message_handler:
            self.config_parser.set_message_handler(self.message_handler)
            self.message_handler.set_config_parser(self.config_parser)
        
        # Initialize from configuration files
        await self.config_parser.initialize_from_files()
        
        # Set up signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        logger.info("initialize: Dunebugger Scheduler Service initialized successfully")

    def set_message_handler(self, message_handler):
        self.message_handler = message_handler
        logger.debug("set_message_handler: Message handler set for SchedulerService")
        if self.config_parser:
            self.config_parser.set_message_handler(self.message_handler)
        else:
            logger.warning("set_message_handler: Config parser not initialized yet, message handler will be set during initialization")

    def handle_signal(self, sig, frame):
        """Handle interrupt signals for clean shutdown"""
        logger.info("handle_signal: Received signal to terminate, shutting down scheduler")
        self.running = False
    
    async def run_scheduler(self):
        """Main loop to run scheduled tasks"""
        logger.info("run_scheduler: Starting scheduler main loop")
        
        try:
            # The config_parser.initialize_from_files() already applies the current state
            # on startup through apply_current_state(), so we don't need handle_startup_tasks()
            
            # Get and log the current state for informational purposes
            current_state, task_id = self.config_parser.get_state_for_time()
            logger.info(f"run_scheduler: Current system state: {current_state} (from task: {task_id})")
            
            # Print next scheduled state changes
            next_runs = []
            for job in schedule.get_jobs():
                if job.tags:
                    # Fix: Convert tags set to list or get the first item safely
                    tag = next(iter(job.tags), "Unknown")
                    next_runs.append(f"Task: {tag} at {job.next_run}")
            
            if next_runs:
                logger.info(f"run_scheduler: Next scheduled state changes:")
                for run in next_runs:
                    logger.info(f"run_scheduler: {run}")
            else:
                logger.info("run_scheduler: No scheduled state changes found")
            
            # Main loop to run scheduled tasks
            while self.running:
                schedule.run_pending()
                await asyncio.sleep(self.schedule_check_interval)
                
        except Exception as e:
            logger.error(f"run_scheduler: Error in scheduler main loop: {str(e)}")
            return 1
        finally:
            await self.cleanup()
        
        return 0
        
    async def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("cleanup: Cleaning up scheduler resources")
        # Any cleanup needed before shutdown
