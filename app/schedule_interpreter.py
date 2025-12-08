from os import path
import asyncio
from datetime import datetime, timedelta, time
import re
from dunebugger_logging import logger

class ScheduleInterpreter:
    def __init__(self, mqueue_handler):
        self.mqueue_handler = mqueue_handler
        self.commands = []
        self.states = []
        self.schedule_config = path.join(path.dirname(path.abspath(__file__)), "config/schedule.conf")
        self.schedule = {}
        self.next_action = None
        self.next_action_time = None
        self.weekdays = ['domenica', 'lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato']
        self._validation_schedule = {}
        self._validation_mode = False

    async def request_lists(self):
        """Request the commands ans states list from the dunebugger core."""
        await self.mqueue_handler.dispatch_message("get_commands_list", "schedule_command", "core")
        await self.mqueue_handler.dispatch_message("get_states_list", "schedule_command", "core")
        logger.info("Requested commands and states lists from core")
        
    async def store_list(self, list_body, list_type):
        """Store the received commands list."""
        if list_type == "commands":
            self.commands = list_body
            logger.info(f"Stored commands list with {len(list_body)} items")
        elif list_type == "states":
            self.states = list_body
            logger.info(f"Stored states list with {len(list_body)} items")
    
    def validate_schedule_file(self, file_path):
        """Validate the schedule configuration file."""
        # Initialize empty schedule for validation
        self._validation_schedule = {'weekdays': {}, 'special_dates': {}}

        if not path.exists(file_path):
            raise FileNotFoundError(f"Schedule file not found: {file_path}")
        
        return self._validate_schedule_file(file_path)

    def load_schedule(self, file_path):
        """Read the schedule configuration file."""
        self.schedule = {'weekdays': {}, 'special_dates': {}}
        
        self._load_schedule(file_path)
        
        logger.info(f"Schedule loaded successfully. Weekdays: {len(self.schedule['weekdays'])}, Special dates: {len(self.schedule['special_dates'])}")

    def get_next_schedule(self):
        """Get the next scheduled action based on the current time."""
        now = datetime.now()
        current_date_str = now.strftime('%d-%m-%Y')
        current_time = now.time()
        current_weekday = now.weekday()
        
        # Check for special date first (overrides weekday)
        if current_date_str in self.schedule['special_dates']:
            schedule_items = self.schedule['special_dates'][current_date_str]
            next_action = self._find_next_action_in_day(schedule_items, current_time)
            if next_action:
                execution_time = datetime.combine(now.date(), next_action['time'])
                if execution_time <= now:
                    execution_time += timedelta(days=1)
                wait_seconds = (execution_time - now).total_seconds()
                return next_action['action'], wait_seconds, execution_time
        
        # Check current weekday schedule
        if current_weekday in self.schedule['weekdays']:
            schedule_items = self.schedule['weekdays'][current_weekday]
            next_action = self._find_next_action_in_day(schedule_items, current_time)
            if next_action:
                execution_time = datetime.combine(now.date(), next_action['time'])
                if execution_time <= now:
                    # Look for next day's first action
                    return self._get_next_day_first_action(now)
                wait_seconds = (execution_time - now).total_seconds()
                return next_action['action'], wait_seconds, execution_time
        
        # No action found for today, get next day's first action
        return self._get_next_day_first_action(now)

    async def update_schedule(self, schedule_data):
        """Update the schedule with the received data."""
        try:
            # Create a backup of current schedule file
            backup_file = f"{self.schedule_config}.backup"
            with open(self.schedule_config, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # Write new schedule data to file
            with open(self.schedule_config, 'w', encoding='utf-8') as f:
                f.write(schedule_data)
            
            # Validate the new schedule
            self.validate_schedule_file(self.schedule_config)
            
            # If validation passes, reload the schedule
            self.schedule = {}
            self.load_schedule(self.schedule_config)
            
            logger.info("Schedule updated successfully")
            
        except Exception as e:
            # Restore backup on failure
            try:
                with open(backup_file, 'r', encoding='utf-8') as src:
                    with open(self.schedule_config, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                logger.error(f"Schedule update failed, restored backup: {e}")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup after schedule update failure: {restore_error}")
            raise e

    async def run_scheduler(self):
        """Run the scheduler to execute actions based on the schedule."""
        logger.info("Starting scheduler service")
        
        while True:
            try:
                # Get next scheduled action
                result = self.get_next_schedule()
                if not result:
                    # No schedule found, wait and try again
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                action, wait_seconds, execution_time = result
                
                # Store next action info
                self.next_action = action
                self.next_action_time = execution_time
                
                logger.info(f"Next action: '{action}' scheduled at {execution_time} (waiting {wait_seconds:.0f} seconds)")
                
                # Wait until execution time
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                # Execute the action
                logger.info(f"Executing scheduled action: {action}")
                await self._execute_scheduled_action(action)
                
                # Small delay before checking for next action
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait before retrying to avoid tight error loops
                await asyncio.sleep(30)
    
    def _is_special_date(self, section_name):
        """Check if section name represents a special date."""
        # Match DD-MM-YYYY or DD/MM/YYYY format
        # Replace '/' with '-' for uniformity
        section_name = section_name.replace('/', '-')
        date_pattern = r'^\d{1,2}-\d{1,2}-\d{4}$'
        return bool(re.match(date_pattern, section_name))
    
    def _validate_date_format(self, date_str):
        """Validate date format DD-MM-YYYY or DD/MM/YYYY."""
        # Replace '/' with '-' for uniformity
        date_str = date_str.replace('/', '-')
        for fmt in ['%d-%m-%Y']:
            datetime.strptime(date_str, fmt)
    
    def _validate_time_format(self, time_str):
        """Validate time format HH:MM, H:MM, H:M, or HH:M."""
        time_pattern = r'^\d{1,2}:\d{1,2}$'
        if not re.match(time_pattern, time_str):
            raise ValueError(f"Time string does not match pattern HH:MM: {time_str}")
        
        # Additional validation for valid time values
        #try:
        self._parse_time(time_str)
        return True
        #except ValueError:
        #    return False
    
    def _parse_time(self, time_str):
        """Parse time string to time object."""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {time_str}")
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if hour < 0 or hour > 23:
                raise ValueError(f"Invalid hour: {hour}")
            if minute < 0 or minute > 59:
                raise ValueError(f"Invalid minute: {minute}")
                
            return time(hour, minute)
        except Exception as e:
            raise ValueError(f"Failed to parse time '{time_str}': {e}")
    
    def _find_next_action_in_day(self, schedule_items, current_time):
        """Find the next action in the given day's schedule."""
        for item in schedule_items:
            if item['time'] > current_time:
                return item
        return None
    
    def _get_next_day_first_action(self, now):
        """Get the first action of the next available day."""
        # Look for the next 7 days to find a schedule
        for days_ahead in range(1, 8):
            future_date = now + timedelta(days=days_ahead)
            future_date_str = future_date.strftime('%d-%m-%Y')
            future_weekday = future_date.weekday()
            
            # Check special dates first
            if future_date_str in self.schedule['special_dates']:
                schedule_items = self.schedule['special_dates'][future_date_str]
                if schedule_items:
                    first_action = schedule_items[0]
                    execution_time = datetime.combine(future_date.date(), first_action['time'])
                    wait_seconds = (execution_time - now).total_seconds()
                    return first_action['action'], wait_seconds, execution_time
            
            # Check weekday schedule
            if future_weekday in self.schedule['weekdays']:
                schedule_items = self.schedule['weekdays'][future_weekday]
                if schedule_items:
                    first_action = schedule_items[0]
                    execution_time = datetime.combine(future_date.date(), first_action['time'])
                    wait_seconds = (execution_time - now).total_seconds()
                    return first_action['action'], wait_seconds, execution_time
        
        # No schedule found in next 7 days
        logger.warning("No schedule found in the next 7 days")
        return None
    
    async def _execute_command(self, command):
        """Execute a single command via message queue."""
        try:
            logger.info(f"Executing command: {command}")
            await self.mqueue_handler.dispatch_message(command, "dunebugger_set", "core")
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            raise
    
    async def _execute_scheduled_action(self, state_name):
        """Execute a state by retrieving and executing its associated commands."""
        try:
            logger.info(f"Executing state: {state_name}")
            
            # Execute commands associated with the state
            commands = self.states[state_name]['commands']

            if not commands:
                logger.warning(f"State '{state_name}' has no associated commands")
                return
            
            for i, command in enumerate(commands):
                logger.info(f"Executing state command {i+1}/{len(commands)}: {command}")
                await self._execute_command(command)
                
                # Small delay between commands to avoid overwhelming the system
                if i < len(commands) - 1:  # Don't delay after the last command
                    await asyncio.sleep(1.5)
                    
        except Exception as e:
            logger.error(f"Failed to execute state '{state_name}': {e}")
            raise
    
    def get_scheduler_status(self):
        """Get current scheduler status for monitoring."""
        status = {
            'schedule_loaded': bool(self.schedule),
            'weekdays_configured': len(self.schedule.get('weekdays', {})),
            'special_dates_configured': len(self.schedule.get('special_dates', {})),
            'commands_available': len(self.commands),
            'states_available': len(self.states),
            'next_action': self.next_action,
            'next_action_time': self.next_action_time.isoformat() if self.next_action_time else None
        }
        return status
    
    def get_today_schedule(self):
        """Get today's complete schedule for debugging and monitoring."""
        now = datetime.now()
        current_date_str = now.strftime('%d-%m-%Y')
        current_weekday = now.weekday()
        
        # Check for special date first
        if current_date_str in self.schedule['special_dates']:
            return {
                'date': current_date_str,
                'type': 'special',
                'items': self.schedule['special_dates'][current_date_str]
            }
        
        # Get weekday schedule
        if current_weekday in self.schedule['weekdays']:
            weekday_names = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
            return {
                'date': current_date_str,
                'type': 'weekday',
                'weekday': weekday_names[current_weekday],
                'items': self.schedule['weekdays'][current_weekday]
            }
        
        return None
    
    def get_validation_report(self):
        """Get a report of all actions and their validation status."""
        validation_report = {
            'valid_actions': [],
            'invalid_actions': [],
            'unknown_actions': []  # Actions that can't be validated due to missing lists
        }
        
        # Check if we have commands and states lists
        has_commands = bool(self.commands)
        has_states = bool(self.states)
        
        # Collect all actions from schedule
        all_actions = set()
        
        # From weekdays
        for day_schedule in self._validation_schedule.get('weekdays', {}).values():
            for item in day_schedule:
                all_actions.add(item['action'])
        
        # From special dates
        for date_schedule in self._validation_schedule.get('special_dates', {}).values():
            for item in date_schedule:
                all_actions.add(item['action'])
        
        # Validate each unique action
        for action in all_actions:
            # It's a state
            if not has_states:
                validation_report['unknown_actions'].append({
                    'action': action,
                    'reason': 'States list not loaded'
                })
            elif self._is_state_valid(action):
                validation_report['valid_actions'].append(action)
            else:
                validation_report['invalid_actions'].append({
                    'action': action,
                    'reason': f'State "{action}" not found in states list'
                })
        
        return validation_report
    
    def _is_command_valid(self, command):
        """Check if a command exists in the commands list."""
        for cmd in self.commands:
            if isinstance(cmd, dict):
                if cmd.get('name') == command or cmd.get('command') == command:
                    return True
            elif isinstance(cmd, str) and cmd == command:
                return True
        return False
    
    def _is_state_valid(self, state_name):
        """Check if a state exists in the states list."""
        for state in self.states:
            if isinstance(state, dict):
                if state.get('name') == state_name:
                    return True
            elif isinstance(state, str) and state == state_name:
                return True
        return False
    
    def _store_schedule_section(self, section_name, schedule_items):
        """Store schedule items in the appropriate section."""
        if self._validation_mode:
            active_schedule = self._validation_schedule
        else:
            active_schedule = self.schedule

        # Sort by time
        schedule_items.sort(key=lambda x: x['time'])
        
        if self._is_special_date(section_name):
            self._validate_date_format(section_name)
            active_schedule['special_dates'][section_name] = schedule_items
        else:
            # Map Italian weekday names to Python weekday numbers
            weekday_map = {
                'domenica': 6, 'lunedì': 0, 'martedì': 1, 'mercoledì': 2,
                'giovedì': 3, 'venerdì': 4, 'sabato': 5
            }
            weekday_num = weekday_map.get(section_name.lower())
            if weekday_num is not None:
                active_schedule['weekdays'][weekday_num] = schedule_items
            else:
                logger.warning(f"Unknown section name '{section_name}', skipping storage")

    def _load_schedule(self, file_path):
        """Parse the schedule file to handle duplicates and edge cases."""
        current_section = None
        schedule_items = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                original_line = line
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Check for section headers
                if line.startswith('[') and line.endswith(']'):
                    # Store previous section if exists
                    if current_section and schedule_items:
                        self._store_schedule_section(current_section, schedule_items)
                    
                    # Start new section
                    current_section = line[1:-1]
                    schedule_items = []
                    #logger.debug(f"Starting section: {current_section}")
                    continue
                
                # Parse time and action lines
                if current_section:
                    try:
                        # Look for time pattern at the beginning of the line
                        time_pattern = re.match(r'^(\d{1,2}:\d{1,2})\s*(.*)', line)
                        if time_pattern:
                            time_str = time_pattern.group(1)
                            action = time_pattern.group(2).strip()
                        else:
                            # Fallback to simple split
                            parts = line.split(' ', 1)
                            if len(parts) >= 2:
                                time_str = parts[0]
                                action = parts[1].strip()
                            elif len(parts) == 1 and ':' in parts[0]:
                                time_str = parts[0]
                                action = ''
                            else:
                                logger.warning(f"Skipping malformed line {line_num}: {original_line}")
                                continue
                        
                        # Validate and parse time
                        if self._validate_time_format(time_str):
                            time_obj = self._parse_time(time_str)
                            
                            # Check for duplicates in this section
                            duplicate = any(item['time'] == time_obj for item in schedule_items)
                            if duplicate:
                                logger.warning(f"Duplicate time {time_str} in section {current_section}, line {line_num} - skipping")
                                continue
                                
                            # Validate action if we're in validation mode
                            if self._validation_mode:
                                self._validate_action(action, current_section, time_str)
                            
                            schedule_items.append({
                                'time': time_obj,
                                'action': action,
                                'raw_time': time_str
                            })
                            #logger.debug(f"Added schedule item: {time_str} -> {action}")
                        else:
                            logger.warning(f"Invalid time format on line {line_num}: {time_str}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse line {line_num}: '{original_line}' - {e}")
        
        # Store the last section
        if current_section and schedule_items:
            self._store_schedule_section(current_section, schedule_items)
    
    def _validate_schedule_file(self, file_path):
        """Validate schedule file"""
        try:
            # Set validation mode to enable action validation
            self._validation_mode = True
            try:
                self._load_schedule(file_path)
            finally:
                # Always reset validation mode flag
                self._validation_mode = False
            
            # Check that all weekdays are present
            found_weekdays = set(self._validation_schedule.get('weekdays', {}).keys())
            expected_weekdays = set(range(7))  # 0-6 for Monday-Sunday
            
            if len(found_weekdays) < 7:
                missing = expected_weekdays - found_weekdays
                logger.warning(f"Missing weekdays: {missing}")
            
            logger.info("Schedule file validation completed")
            
            # Keep the loaded schedule since validation passed
            return True
            
        except Exception as e:
            raise ValueError(f"Validation failed: {e}")
    
    def _validate_action(self, action, section_name, time_str):
        """Validate action against commands or states lists."""
        # Only validate if we have the states list loaded
        if self.states:
            # Check if state exists in states list
            state_found = False
            for state in self.states:
                if isinstance(state, dict):
                    if state.get('name') == action:
                        state_found = True
                        break
                elif isinstance(state, str) and state == action:
                    state_found = True
                    break
            
            if not state_found:
                logger.warning(f"State '{action}' not found in states list for time slot {time_str} in section {section_name}")
        else:
            logger.debug(f"States list not loaded, skipping validation for state '{action}'")