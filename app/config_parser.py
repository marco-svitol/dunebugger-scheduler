#!/usr/bin/python3

import json
import os
import datetime
import schedule
import jsonschema
import asyncio
from typing import Dict, List, Any, Union, Callable, Coroutine, Optional, Tuple
from dunebugger_logging import logger

class ConfigParser:
    """
    Class responsible for parsing and validating dunebugger scheduler configurations.
    Manages both scheduling and state configuration files and creates internal scheduling
    based on validated configurations.
    """
    
    def __init__(self, config_dir: str = None):
        """
        Initialize the ConfigParser with the configuration directory
        
        Args:
            config_dir: Path to the configuration directory. Defaults to "../config"
        """
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
        self.schedule_config = None
        self.states_config = None
        self.current_state = None
        self.state_handlers = {}  # Mapping of state names to handler functions
        self.message_handler = None  # Will be set later to send messages
        
        # Define JSON schemas for validation
        self.schedule_schema = {
            "type": "object",
            "properties": {
                "daily": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "state", "time"],
                        "properties": {
                            "id": {"type": "string"},
                            "state": {"type": "string"},
                            "description": {"type": "string"},
                            "time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"}
                        }
                    }
                },
                "weekly": {
                    "type": "object",
                    "properties": {
                        "monday": {"$ref": "#/definitions/daySchedule"},
                        "tuesday": {"$ref": "#/definitions/daySchedule"},
                        "wednesday": {"$ref": "#/definitions/daySchedule"},
                        "thursday": {"$ref": "#/definitions/daySchedule"},
                        "friday": {"$ref": "#/definitions/daySchedule"},
                        "saturday": {"$ref": "#/definitions/daySchedule"},
                        "sunday": {"$ref": "#/definitions/daySchedule"}
                    }
                },
                "onetime": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "state", "date", "time"],
                        "properties": {
                            "id": {"type": "string"},
                            "state": {"type": "string"},
                            "description": {"type": "string"},
                            "date": {"type": "string", "pattern": "^\\d{4}/\\d{2}/\\d{2}$"},
                            "time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"}
                        }
                    }
                }
            },
            "definitions": {
                "daySchedule": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "state", "time"],
                        "properties": {
                            "id": {"type": "string"},
                            "state": {"type": "string"},
                            "description": {"type": "string"},
                            "time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"}
                        }
                    }
                }
            }
        }
        
        self.states_schema = {
            "type": "object",
            "required": ["states"],
            "properties": {
                "states": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "commands"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "commands": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }

    def set_message_handler(self, message_handler):
        self.message_handler = message_handler
        logger.debug("set_message_handler: Message handler set for ConfigParser")
    
    def load_schedule_config(self, filename: str = "schedule.json") -> Dict:
        """
        Load and validate the scheduling configuration
        
        Args:
            filename: Name of the schedule configuration file
            
        Returns:
            Dict: The validated schedule configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration is invalid
            jsonschema.exceptions.ValidationError: If the schema validation fails
        """
        file_path = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Schedule configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            self.schedule_config = json.load(f)
        
        # Validate against schema
        try:
            jsonschema.validate(instance=self.schedule_config, schema=self.schedule_schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Invalid schedule configuration: {str(e)}")
            
        # Additional validation: dates and times format
        self._validate_times_and_dates()
        
        logger.info(f"load_schedule_config: Successfully loaded schedule configuration from {file_path}")
        return self.schedule_config
    
    def _validate_times_and_dates(self):
        """
        Validate time and date formats in the schedule configuration
        
        Raises:
            ValueError: If any time or date format is invalid
        """
        # Validate daily times
        for task in self.schedule_config.get("daily", []):
            task_id = task.get("id")
            time_str = task.get("time")
            try:
                datetime.datetime.strptime(time_str, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid time format in daily task {task_id}: {time_str}")
                
        # Validate weekly times
        for day, tasks in self.schedule_config.get("weekly", {}).items():
            for task in tasks:
                task_id = task.get("id")
                time_str = task.get("time")
                try:
                    datetime.datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    raise ValueError(f"Invalid time format in weekly task {task_id} for {day}: {time_str}")
        
        # Validate onetime dates and times
        for task in self.schedule_config.get("onetime", []):
            task_id = task.get("id")
            time_str = task.get("time")
            date_str = task.get("date")
            
            try:
                datetime.datetime.strptime(time_str, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid time format in onetime task {task_id}: {time_str}")
                
            try:
                datetime.datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                raise ValueError(f"Invalid date format in onetime task {task_id}: {date_str}")
    
    def load_states_config(self, filename: str = "states.json") -> Dict:
        """
        Load and validate the states configuration
        
        Args:
            filename: Name of the states configuration file
            
        Returns:
            Dict: The validated states configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration is invalid
            jsonschema.exceptions.ValidationError: If the schema validation fails
        """
        file_path = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"States configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            self.states_config = json.load(f)
        
        # Validate against schema
        try:
            jsonschema.validate(instance=self.states_config, schema=self.states_schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Invalid states configuration: {str(e)}")
        
        logger.info(f"load_states_config: Successfully loaded states configuration from {file_path}")
        return self.states_config
    
    def validate_configurations(self) -> bool:
        """
        Validate that all states referenced in the schedule exist in the states configuration
        
        Returns:
            bool: True if all validations pass
            
        Raises:
            ValueError: If validation fails
        """
        if not self.schedule_config or not self.states_config:
            raise ValueError("Both schedule and states configurations must be loaded before validation")
        
        # Get all available state definitions
        available_states = {state["name"] for state in self.states_config.get("states", [])}
        
        # Check if all states in daily schedule exist in states config
        for task in self.schedule_config.get("daily", []):
            state_name = task.get("state")
            if state_name not in available_states:
                raise ValueError(f"Daily task '{task.get('id')}' references undefined state: '{state_name}'")
        
        # Check if all states in weekly schedule exist in states config
        for day, tasks in self.schedule_config.get("weekly", {}).items():
            for task in tasks:
                state_name = task.get("state")
                if state_name not in available_states:
                    raise ValueError(f"Weekly task '{task.get('id')}' for {day} references undefined state: '{state_name}'")
        
        # Check if all states in onetime schedule exist in states config
        for task in self.schedule_config.get("onetime", []):
            state_name = task.get("state")
            if state_name not in available_states:
                raise ValueError(f"Onetime task '{task.get('id')}' references undefined state: '{state_name}'")
        
        logger.info("validate_configurations: All configuration validations passed successfully")
        return True
    
    def get_state_commands(self, state_name: str) -> List[str]:
        """
        Get the commands for a specific state
        
        Args:
            state_name: Name of the state
            
        Returns:
            List[str]: List of commands for the state
            
        Raises:
            ValueError: If the state doesn't exist
        """
        if not self.states_config:
            raise ValueError("States configuration not loaded")
        
        for state in self.states_config.get("states", []):
            if state["name"] == state_name:
                return state["commands"]
                
        raise ValueError(f"State definition not found for: {state_name}")
    
    async def execute_state(self, state_name: str, task_id: str = None) -> bool:
        """
        Execute the commands for the specified state
        
        Args:
            state_name: Name of the state to execute
            task_id: Optional task ID for logging purposes
            
        Returns:
            bool: True if execution was successful
            
        Raises:
            ValueError: If the state doesn't exist or handler not registered
        """
        if not self.message_handler:
            raise ValueError("Message handler not set for ConfigParser")
        
        # Update the current state
        self.current_state = state_name
            
        try:
            commands = self.get_state_commands(state_name)
            task_info = f"Task {task_id} - " if task_id else ""
            logger.info(f"execute_state: {task_info}Executing state: {state_name} (definition: {state_name})")
            
            # Execute commands sequentially
            for command in commands:
                logger.debug(f"execute_state: Sending command: {command}")
                # Send command through message queue
                await self.message_handler.dispatch_message(command, "dunebugger_set", "core")
                await asyncio.sleep(0.5)  # Small delay between commands
            
            # Send the updated next state schedule information
            next_state_schedule = self.get_next_state_schedule()
            logger.info(f"execute_state: next scheduled state={next_state_schedule['next_state']}, id={next_state_schedule['task_id']}, type={next_state_schedule['schedule_type']}, day={next_state_schedule['day_of_week']} at {next_state_schedule['next_time']}")
            await self.message_handler.dispatch_message(next_state_schedule, "schedule_next", "remote")
                
            return True
        except Exception as e:
            logger.error(f"execute_state: Error executing state {state_name}: {str(e)}")
            return False
    
    def get_state_for_time(self, target_datetime: Optional[datetime.datetime] = None) -> Tuple[str, str]:
        """
        Determine the appropriate state for a given time based on schedule priorities:
        1. Onetime events take highest priority - if it's the specific date, no daily/weekly are executed
        2. Based on schedule_type setting, check either weekly or daily schedules
        
        Args:
            target_datetime: The datetime to check for (defaults to current time)
            
        Returns:
            Tuple[str, str]: A tuple containing (state_name, task_id)
        """
        if target_datetime is None:
            target_datetime = datetime.datetime.now()
            
        target_date = target_datetime.date()
        target_time = target_datetime.time()
        day_of_week = target_datetime.strftime("%A").lower()
        
        # Get the schedule type from settings
        from dunebugger_settings import settings
        schedule_type = getattr(settings, "schedule_type", "daily").strip('"')
        
        # Variables to track the latest scheduled state before the target time
        latest_state = None
        latest_time = None
        latest_task_id = None
        
        # Check onetime schedule first (highest priority)
        has_onetime_for_today = False
        for task in self.schedule_config.get("onetime", []):
            task_date = datetime.datetime.strptime(task["date"], "%Y/%m/%d").date()
            
            # If this task is scheduled for today - mark that we have a onetime task for this day
            if task_date == target_date:
                has_onetime_for_today = True
                task_time = datetime.datetime.strptime(task["time"], "%H:%M").time()
                
                # If this task is scheduled before the target time and later than our current latest
                if task_time <= target_time and (latest_time is None or task_time > latest_time):
                    latest_state = task["state"]
                    latest_time = task_time
                    latest_task_id = task["id"]
        
        # If we found a onetime task for today, return it (and ignore weekly/daily)
        if has_onetime_for_today:
            if latest_state is not None:
                return latest_state, latest_task_id
            else:
                # If there's a onetime task for today but none before current time,
                # return default state
                return "off", "default"
            
        # Based on schedule_type, check either weekly or daily
        if schedule_type.lower() == "weekly":
            # Check weekly schedule
            has_weekly_for_today = day_of_week in self.schedule_config.get("weekly", {})
            if has_weekly_for_today:
                for task in self.schedule_config["weekly"][day_of_week]:
                    task_time = datetime.datetime.strptime(task["time"], "%H:%M").time()
                    
                    # If this task is scheduled before the target time and later than our current latest
                    if task_time <= target_time and (latest_time is None or task_time > latest_time):
                        latest_state = task["state"]
                        latest_time = task_time
                        latest_task_id = task["id"]
        else:
            # Check daily schedule
            for task in self.schedule_config.get("daily", []):
                task_time = datetime.datetime.strptime(task["time"], "%H:%M").time()
                
                # If this task is scheduled before the target time and later than our current latest
                if task_time <= target_time and (latest_time is None or task_time > latest_time):
                    latest_state = task["state"]
                    latest_time = task_time
                    latest_task_id = task["id"]
        
        if latest_state is not None:
            return latest_state, latest_task_id
        
        # If no state is found, return a default
        return "off", "default"
    
    def create_task_job(self, task: Dict, schedule_type: str, day: str = None) -> None:
        """
        Create a scheduled job for a task
        
        Args:
            task: The task configuration
            schedule_type: Type of schedule (daily, weekly, onetime)
            day: Day of week for weekly tasks
            
        Raises:
            ValueError: If task execution details are invalid
        """
        task_id = task.get("id")
        state_name = task.get("state")
        time_str = task.get("time")
        
        # Create a function to execute this specific task
        def execute_task_job():
            try:
                logger.info(f"execute_task_job: Executing scheduled task: {task_id} to set state: {state_name}")
                
                # Get the current event loop instead of creating a new one
                loop = asyncio.get_event_loop()
                
                # Schedule the coroutine to run soon in the existing loop
                if loop.is_running():
                    # If the event loop is already running, create a future to run the coroutine
                    asyncio.create_task(self.execute_state(state_name, task_id))
                else:
                    # If no event loop is running yet, run the coroutine directly
                    loop.run_until_complete(self.execute_state(state_name, task_id))
                
            except Exception as e:
                logger.error(f"execute_task_job: Error in scheduled task {task_id}: {str(e)}")
        
        # Schedule based on type
        if schedule_type == "daily":
            logger.info(f"create_task_job: Scheduling task {task_id} to run daily at {time_str}")
            schedule.every().day.at(time_str).do(execute_task_job).tag(task_id)
                
        elif schedule_type == "weekly" and day:
            logger.info(f"create_task_job: Scheduling task {task_id} to run every {day} at {time_str}")
            getattr(schedule.every(), day).at(time_str).do(execute_task_job).tag(task_id)
                
        elif schedule_type == "onetime":
            date_str = task.get("date")
            
            # Parse the date and time
            task_datetime = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M")
            now = datetime.datetime.now()
            
            # Only schedule if the task is in the future
            if task_datetime > now:
                # Calculate seconds until execution
                delta = (task_datetime - now).total_seconds()
                
                logger.info(f"create_task_job: Scheduling one-time task {task_id} at {date_str} {time_str} ({delta} seconds from now)")
                schedule.every(delta).seconds.do(execute_task_job).tag(task_id)
            else:
                logger.warning(f"create_task_job: Skipping one-time task {task_id} as its scheduled time has passed: {date_str} {time_str}")
    
    def setup_scheduling(self) -> None:
        """
        Set up scheduling for all tasks in the configuration, respecting priority rules:
        1. If there's a onetime event for a particular day, don't execute any other tasks for that day
        2. Based on schedule_type setting, only schedule weekly or daily tasks
        
        Always schedule all tasks according to schedule_type, but they will only execute 
        if no higher priority schedule exists for that particular day.
        
        Raises:
            ValueError: If configurations have not been loaded or validated
        """
        if not self.schedule_config or not self.states_config:
            raise ValueError("Configurations must be loaded and validated before setting up scheduling")
            
        # Clear all existing schedules
        schedule.clear()
        
        # Get the schedule type from settings
        from dunebugger_settings import settings
        schedule_type = getattr(settings, "schedule_type", "daily").strip('"')
        logger.info(f"setup_scheduling: Using schedule_type: {schedule_type}")
        
        # Track which days have onetime schedules (for logging only)
        dates_with_onetime_events = set()
        
        # First, schedule all onetime events - these always have highest priority
        for task in self.schedule_config.get("onetime", []):
            task_date = datetime.datetime.strptime(task["date"], "%Y/%m/%d").date()
            dates_with_onetime_events.add(task_date)
            
            # Only schedule if the task is in the future
            task_time = datetime.datetime.strptime(task["time"], "%H:%M").time()
            task_datetime = datetime.datetime.combine(task_date, task_time)
            now = datetime.datetime.now()
            
            if task_datetime > now:
                # Schedule the onetime task at the exact date and time
                logger.info(f"setup_scheduling: Scheduling one-time task {task['id']} at {task['date']} {task['time']}")
                
                # Create a job that runs only once
                job = schedule.every()
                
                # Set the job to run at the specific time on the specific date
                job.at(task["time"]).on(task_date.strftime("%Y-%m-%d")).do(
                    lambda t=task: self._execute_onetime_task(t)
                ).tag(task["id"])
                
            else:
                logger.warning(f"setup_scheduling: Skipping one-time task {task['id']} as its scheduled time has passed: {task['date']} {task['time']}")
        
        # Schedule either weekly or daily tasks based on schedule_type setting
        if schedule_type.lower() == "weekly":
            # Only schedule weekly tasks
            for day, tasks in self.schedule_config.get("weekly", {}).items():
                for task in tasks:
                    logger.info(f"setup_scheduling: Scheduling task {task['id']} to run every {day} at {task['time']}")
                    # Create a wrapper function that checks for onetime overrides before executing
                    def create_weekly_task_with_override_check(task=task, day=day):
                        def execute_if_no_override():
                            now = datetime.datetime.now()
                            today_date = now.date()
                            
                            # Check for onetime override
                            has_onetime_today = False
                            for onetime_task in self.schedule_config.get("onetime", []):
                                onetime_date = datetime.datetime.strptime(onetime_task["date"], "%Y/%m/%d").date()
                                if onetime_date == today_date:
                                    has_onetime_today = True
                                    logger.info(f"execute_if_no_override: Skipping weekly task {task['id']} because onetime event exists for today ({today_date})")
                                    break
                            
                            # No onetime override, execute the task
                            if not has_onetime_today:
                                logger.info(f"execute_if_no_override: Executing weekly task {task['id']} because no onetime override exists for today")
                                self._create_execute_task_job(task)()
                        
                        return execute_if_no_override
                    
                    # Schedule the weekly task with the override check
                    getattr(schedule.every(), day).at(task["time"]).do(
                        create_weekly_task_with_override_check()
                    ).tag(task["id"])
            
            logger.info("setup_scheduling: Only scheduling weekly tasks because schedule_type is set to 'weekly'")
        else:
            # Only schedule daily tasks
            for task in self.schedule_config.get("daily", []):
                logger.info(f"setup_scheduling: Scheduling daily task {task['id']} to run at {task['time']}")
                # Create a wrapper function that checks for onetime overrides before executing
                def create_daily_task_with_override_check(task=task):
                    def execute_if_no_override():
                        now = datetime.datetime.now()
                        today_date = now.date()
                        
                        # Check for onetime override
                        has_onetime_today = False
                        for onetime_task in self.schedule_config.get("onetime", []):
                            onetime_date = datetime.datetime.strptime(onetime_task["date"], "%Y/%m/%d").date()
                            if onetime_date == today_date:
                                has_onetime_today = True
                                logger.info(f"execute_if_no_override: Skipping daily task {task['id']} because onetime event exists for today ({today_date})")
                                break
                        
                        # No onetime override, execute the task
                        if not has_onetime_today:
                            logger.info(f"execute_if_no_override: Executing daily task {task['id']} because no onetime override exists for today")
                            self._create_execute_task_job(task)()
                    
                    return execute_if_no_override
                
                # Schedule the daily task with the override check
                schedule.every().day.at(task["time"]).do(
                    create_daily_task_with_override_check()
                ).tag(task["id"])
            
            logger.info("setup_scheduling: Only scheduling daily tasks because schedule_type is set to 'daily'")
        
        # Log the current day's overrides
        current_date = datetime.datetime.now().date()
        has_onetime_for_today = current_date in dates_with_onetime_events
        
        if has_onetime_for_today:
            logger.info(f"setup_scheduling: Tasks will not execute today because onetime event exists")
        
        # Count total tasks
        job_count = len(schedule.get_jobs())
        logger.info(f"setup_scheduling: Successfully set up scheduling for {job_count} tasks")
        
    def _execute_onetime_task(self, task: Dict) -> None:
        """
        Execute a onetime task and remove it from the schedule after execution
        
        Args:
            task: The task configuration
        """
        task_id = task.get("id")
        state_name = task.get("state")
        
        try:
            logger.info(f"_execute_onetime_task: Executing one-time task: {task_id} to set state: {state_name}")
            
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Execute the task
            if loop.is_running():
                asyncio.create_task(self.execute_state(state_name, task_id))
            else:
                loop.run_until_complete(self.execute_state(state_name, task_id))
                
            # Find and remove this job from the schedule after execution
            # This ensures it only runs once
            for job in schedule.get_jobs():
                if job.tags and task_id in job.tags:
                    schedule.cancel_job(job)
                    logger.info(f"_execute_onetime_task: Removed one-time task {task_id} from schedule after execution")
                    break
                
        except Exception as e:
            logger.error(f"_execute_onetime_task: Error in one-time task {task_id}: {str(e)}")
    
    async def apply_current_state(self) -> bool:
        """
        Apply the current state based on the schedule and current time.
        This should be called on startup to ensure the system is in the correct state.
        
        Returns:
            bool: True if state was applied successfully
        """
        state_name, task_id = self.get_state_for_time()
        logger.info(f"apply_current_state: Applying current state on startup: {state_name} (from task: {task_id})")
        return await self.execute_state(state_name, task_id)
    
    async def initialize_from_files(self) -> bool:
        """
        Initialize the configuration parser by loading and validating all configurations,
        setting up the scheduling, and applying the current state
        
        Returns:
            bool: True if initialization was successful
            
        Raises:
            Exception: If any part of the initialization fails
        """
        try:
            # Load and validate configurations
            self.load_schedule_config()
            self.load_states_config()
            self.validate_configurations()
            
            # Set up scheduling for all configured tasks
            self.setup_scheduling()
            
            # Apply the current state based on the schedule
            await self.apply_current_state()
            
            # Send scheduler state to remote for monitoring
            # if self.message_handler:
            #     scheduler_state = self._get_scheduler_state()
            #     await self.message_handler.dispatch_message(scheduler_state, "scheduler_state", "remote")
            
            return True
        except Exception as e:
            logger.error(f"initialize_from_files: Error initializing configuration: {str(e)}")
            raise
    
    def get_schedule(self) -> Dict:
        if not self.schedule_config:
            raise ValueError("Schedule configuration has not been loaded")
            
        return self.schedule_config
    
    def get_next_state_schedule(self) -> Dict:
        """
        Get information about the next scheduled state change that will actually execute,
        respecting:
        1. schedule_type setting from configuration (weekly or daily)
        2. Onetime events always have highest priority
        
        Returns:
            Dict: JSON-compatible dictionary containing:
                - next_state: Name of the next scheduled state
                - next_time: Datetime when the state change will occur
                - task_id: ID of the task that will trigger the state change
                - current_state: Name of the current state
                - schedule_type: Type of schedule (daily, weekly, onetime)
                - day_of_week: Day of week for weekly tasks
                
        Raises:
            ValueError: If schedule configuration has not been loaded
        """
        if not self.schedule_config:
            raise ValueError("Schedule configuration has not been loaded")
        
        # Get schedule type from settings
        from dunebugger_settings import settings
        config_schedule_type = getattr(settings, "schedule_type", "daily").strip('"')
        
        # Get current state
        current_state_name, _ = self.get_state_for_time()
        
        # Get all jobs and find the next ones
        jobs = schedule.get_jobs()
        if not jobs:
            return {
                "current_state": current_state_name,
                "next_state": None,
                "next_time": None,
                "task_id": None,
                "schedule_type": None,
                "day_of_week": None
            }
        
        # Sort jobs by next_run time
        sorted_jobs = sorted(jobs, key=lambda job: job.next_run)
        
        # Group jobs by date
        jobs_by_date = {}
        for job in sorted_jobs:
            job_date = job.next_run.date()
            if job_date not in jobs_by_date:
                jobs_by_date[job_date] = []
            job_tag = next(iter(job.tags), None) if job.tags else None
            job_info = self._find_task_by_id(job_tag) if job_tag else None
            if job_info:
                jobs_by_date[job_date].append({
                    "job": job,
                    "task_id": job_tag,
                    "schedule_type": job_info["schedule_type"],
                    "state": job_info["state"],
                    "day_of_week": job_info.get("day_of_week")
                })
        
        # For each date, determine which tasks will actually run based on priority
        actual_next_job = None
        
        for date, jobs_for_date in sorted(jobs_by_date.items()):
            # Check if there are any onetime tasks for this date
            onetime_jobs = [j for j in jobs_for_date if j["schedule_type"] == "onetime"]
            if onetime_jobs:
                # Onetime exists, it has highest priority regardless of schedule_type
                actual_next_job = min(onetime_jobs, key=lambda j: j["job"].next_run)
                break
            
            # Based on config_schedule_type, check either weekly or daily tasks
            if config_schedule_type.lower() == "weekly":
                # Check for weekly tasks on this date's day of week
                day_of_week = date.strftime("%A").lower()
                weekly_jobs = [j for j in jobs_for_date if j["schedule_type"] == "weekly" and j["day_of_week"] == day_of_week]
                if weekly_jobs:
                    actual_next_job = min(weekly_jobs, key=lambda j: j["job"].next_run)
                    break
            else:
                # Check for daily tasks
                daily_jobs = [j for j in jobs_for_date if j["schedule_type"] == "daily"]
                if daily_jobs:
                    actual_next_job = min(daily_jobs, key=lambda j: j["job"].next_run)
                    break
        
        # If no job will actually run, return empty state
        if not actual_next_job:
            return {
                "current_state": current_state_name,
                "next_state": None,
                "next_time": None,
                "task_id": None,
                "schedule_type": None,
                "day_of_week": None
            }
        
        # Return the next job that will actually run
        return {
            "current_state": current_state_name,
            "next_state": actual_next_job["state"],
            "next_time": actual_next_job["job"].next_run.strftime("%Y-%m-%d %H:%M:%S"),
            "task_id": actual_next_job["task_id"],
            "schedule_type": actual_next_job["schedule_type"],
            "day_of_week": actual_next_job.get("day_of_week")
        }
    
    def _find_task_by_id(self, task_id: str) -> Optional[Dict]:
        """
        Find a task by its ID in the schedule configurations
        
        Args:
            task_id: The ID of the task to find
            
        Returns:
            Optional[Dict]: A dictionary with the task information or None if not found
        """
        # Look in daily schedule
        for task in self.schedule_config.get("daily", []):
            if task.get("id") == task_id:
                return {"task": task, "state": task.get("state"), "schedule_type": "daily"}
        
        # Look in weekly schedule
        for day, tasks in self.schedule_config.get("weekly", {}).items():
            for task in tasks:
                if task.get("id") == task_id:
                    return {"task": task, "state": task.get("state"), "schedule_type": "weekly", "day_of_week": day}
        
        # Look in onetime schedule
        for task in self.schedule_config.get("onetime", []):
            if task.get("id") == task_id:
                return {"task": task, "state": task.get("state"), "schedule_type": "onetime"}
        
        return None
