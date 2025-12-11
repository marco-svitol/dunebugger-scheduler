from os import path
import os
import tempfile
import asyncio
from datetime import datetime, timedelta, time
import re
from dunebugger_logging import logger

class ScheduleInterpreter:
    def __init__(self, mqueue_handler, state_tracker):
        self.mqueue_handler = mqueue_handler
        self.state_tracker = state_tracker
        self.commands = []
        self.states = []
        self.schedule_config = path.join(path.dirname(path.abspath(__file__)), "config/schedule.conf")
        self.schedule = {'weekdays': {}, 'special_dates': {}}
        self.next_action = None
        self.next_action_time = None
        self.weekdays = ['domenica', 'lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato']
        self._validation_schedule = {'weekdays': {}, 'special_dates': {}}
        self.last_executed_action = None
        self.last_executed_time = None
        self._schedule_changed = asyncio.Event()

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

    async def init_schedule(self):
        while True:
            try:
                await self.request_lists()
                self._validate_schedule_file(self.schedule_config)
                break
            except Exception as e:
                logger.error(f"Schedule validation failed: {e}. Retrying in 60 seconds...")
                await asyncio.sleep(60)

        self._load_schedule(self.schedule_config, self.schedule)
        
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
        temp_file = None
        backup_file = None
        
        try:
            # Create a temporary file with random name in the config folder
            config_dir = path.dirname(self.schedule_config)
            temp_fd, temp_file = tempfile.mkstemp(suffix='.conf', prefix='schedule_temp_', dir=config_dir)
            
            # Write new schedule data to temporary file
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(schedule_data)
            
            # Validate the temporary schedule file
            self._validate_schedule_file(temp_file)
            
            # If validation passes, create backup of current schedule
            backup_file = f"{self.schedule_config}.backup"
            with open(self.schedule_config, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # Promote temporary file to active schedule
            os.replace(temp_file, self.schedule_config)
            temp_file = None  # Don't delete in finally block since it's now the active file
            
            # Reload the schedule
            self.schedule = {'weekdays': {}, 'special_dates': {}}
            self._load_schedule(self.schedule_config, self.schedule)
            
            # Signal that schedule has changed to interrupt any waiting
            self._schedule_changed.set()
            
            # Notify state tracker about schedule update
            self.state_tracker.notify_update("schedule")

            logger.info("Schedule updated successfully")
            return {"success": True, "message": "Schedule updated successfully", "level": "info"}
        
        except Exception as e:
            logger.error(f"Schedule update failed: {e}")
            return {"success": False, "message": f"Schedule update error: {str(e)}", "level": "error"}
        finally:
            # Clean up temporary file if it still exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file {temp_file}: {cleanup_error}")

    async def _interruptible_sleep(self, seconds):
        """Sleep that can be interrupted by schedule changes."""
        try:
            await asyncio.wait_for(self._schedule_changed.wait(), timeout=seconds)
            # If we get here, the schedule was changed - clear the event for next time
            self._schedule_changed.clear()
            logger.info("Sleep interrupted by schedule change")
            return True  # Schedule was changed
        except asyncio.TimeoutError:
            # Normal timeout - no schedule change
            return False

    async def run_scheduler(self):
        """Run the scheduler to execute actions based on the schedule."""
        logger.info("Starting scheduler service")
        
        while True:
            try:
                # Get next scheduled action
                result = self.get_next_schedule()
                if not result:
                    # No schedule found, wait and try again (interruptible)
                    await self._interruptible_sleep(60)  # Check every minute
                    continue
                
                action, wait_seconds, execution_time = result
                
                # Store next action info
                self.next_action = action
                self.next_action_time = execution_time
                
                logger.info(f"Next action: '{action}' scheduled at {execution_time} (waiting {wait_seconds:.0f} seconds)")
                
                # Wait until execution time (interruptible)
                if wait_seconds > 0:
                    schedule_changed = await self._interruptible_sleep(wait_seconds)
                    if schedule_changed:
                        logger.info("Schedule changed during wait, recalculating next action")
                        continue  # Skip to recalculate with new schedule
                
                # Execute the action
                logger.info(f"Executing scheduled action: {action}")
                await self._execute_scheduled_action(action)
                
                # Small delay before checking for next action (also interruptible)
                await self._interruptible_sleep(10)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait before retrying to avoid tight error loops (interruptible)
                await self._interruptible_sleep(30)
    
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
                # Still track execution even if no commands
                self.last_executed_action = state_name
                self.last_executed_time = datetime.now()
                return
            
            for i, command in enumerate(commands):
                logger.info(f"Executing state command {i+1}/{len(commands)}: {command}")
                await self._execute_command(command)
                
                # Small delay between commands to avoid overwhelming the system
                if i < len(commands) - 1:  # Don't delay after the last command
                    await asyncio.sleep(1.5)
            
            # Track the successful execution
            self.last_executed_action = state_name
            self.last_executed_time = datetime.now()

            # Notify state tracker about schedule update
            self.state_tracker.notify_update("near_actions")

            logger.info(f"Successfully executed state '{state_name}' at {self.last_executed_time}")
                    
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

    def get_schedule(self):
        """Get the schedule as-is, exactly as stored in the active schedule config file."""
        try:
            with open(self.schedule_config, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Schedule config file not found: {self.schedule_config}")
            return ""
        except Exception as e:
            logger.error(f"Error reading schedule config file: {e}")
            return ""

    def get_next_actions(self):
        """Get the next three actions with date, time, action, commands and state description."""
        next_actions = []
        now = datetime.now()
        
        # Look for the next 3 actions across multiple days if needed
        search_date = now
        actions_found = 0
        max_days_search = 30  # Limit search to avoid infinite loops
        days_searched = 0
        
        while actions_found < 3 and days_searched < max_days_search:
            current_date_str = search_date.strftime('%d-%m-%Y')
            current_weekday = search_date.weekday()
            current_time = search_date.time() if search_date.date() == now.date() else time(0, 0)
            
            schedule_items = []
            
            # Check for special date first (overrides weekday)
            if current_date_str in self.schedule['special_dates']:
                schedule_items = self.schedule['special_dates'][current_date_str]
            elif current_weekday in self.schedule['weekdays']:
                schedule_items = self.schedule['weekdays'][current_weekday]
            
            # Find actions for this day
            for item in schedule_items:
                if item['time'] > current_time or search_date.date() > now.date():
                    if actions_found >= 3:
                        break
                        
                    action_datetime = datetime.combine(search_date.date(), item['time'])
                    
                    # Get state information
                    state_info = self._get_state_info(item['action'])
                    
                    action_data = {
                        'date': current_date_str,
                        'time': item['time'].strftime('%H:%M'),
                        'datetime': action_datetime.isoformat(),
                        'action': item['action'],
                        'commands': state_info.get('commands', []),
                        'description': state_info.get('description', '')
                    }
                    
                    next_actions.append(action_data)
                    actions_found += 1
            
            # Move to next day
            search_date += timedelta(days=1)
            days_searched += 1
        
        return next_actions

    def get_last_executed_action(self):
        """Get the last executed action with all details."""
        if not self.last_executed_action or not self.last_executed_time:
            return {
                'executed': False,
                'message': 'No actions have been executed yet'
            }
        
        # Get state information
        state_info = self._get_state_info(self.last_executed_action)
        
        return {
            'executed': True,
            'date': self.last_executed_time.strftime('%d-%m-%Y'),
            'time': self.last_executed_time.strftime('%H:%M'),
            'datetime': self.last_executed_time.isoformat(),
            'action': self.last_executed_action,
            'commands': state_info.get('commands', []),
            'description': state_info.get('description', '')
        }
    
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
        if isinstance(self.states, dict):
            # States is a dictionary with state names as keys
            return state_name in self.states
        else:
            # States is a list of state objects
            for state in self.states:
                if isinstance(state, dict):
                    if state.get('name') == state_name:
                        return True
                elif isinstance(state, str) and state == state_name:
                    return True
        return False
    
    def _store_schedule_section(self, section_name, schedule_items, schedule):
        """Store schedule items in the appropriate section."""
        # Sort by time
        schedule_items.sort(key=lambda x: x['time'])
        
        if self._is_special_date(section_name):
            self._validate_date_format(section_name)
            schedule['special_dates'][section_name] = schedule_items
        else:
            # Map Italian weekday names to Python weekday numbers
            weekday_map = {
                'domenica': 6, 'lunedì': 0, 'martedì': 1, 'mercoledì': 2,
                'giovedì': 3, 'venerdì': 4, 'sabato': 5
            }
            weekday_num = weekday_map.get(section_name.lower())
            if weekday_num is not None:
                schedule['weekdays'][weekday_num] = schedule_items
            else:
                logger.warning(f"Unknown section name '{section_name}', skipping storage")

    def _load_schedule(self, file_path, schedule):
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
                        self._store_schedule_section(current_section, schedule_items, schedule)
                    
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
                                
                            self._validate_action(action, current_section, time_str)
                            
                            schedule_items.append({
                                'time': time_obj,
                                'action': action,
                                'raw_time': time_str
                            })
                            #logger.debug(f"Added schedule item: {time_str} -> {action}")
                        else:
                            #logger.warning(f"Invalid time format on line {line_num}: {time_str}")
                            raise ValueError(f"Invalid time format on line {line_num}: {time_str}")

                    except Exception as e:
                        raise ValueError(f"Failed to parse line {line_num}: '{original_line}' - {e}")
                        #logger.warning(f"Failed to parse line {line_num}: '{original_line}' - {e}")
        
        # Store the last section
        if current_section and schedule_items:
            self._store_schedule_section(current_section, schedule_items, schedule)
        
        logger.info(f"Schedule loaded successfully. Weekdays: {len(schedule['weekdays'])}, Special dates: {len(schedule['special_dates'])}")
    
    def _validate_schedule_file(self, file_path):
        # Initialize empty schedule for validation
        self._validation_schedule = {'weekdays': {}, 'special_dates': {}}

        try:
            self._load_schedule(file_path, self._validation_schedule)

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
                raise ValueError(f"State '{action}' not found in states list for time slot {time_str} in section {section_name}")
        else:
            raise ValueError(f"States list not loaded, cannot validate state '{action}' at time {time_str} in section {section_name}")
            #logger.debug(f"States list not loaded, skipping validation for state '{action}'")

    def _get_state_info(self, state_name):
        """Get detailed information about a state including commands and description."""
        if not self.states:
            return {
                'commands': [],
                'description': f'State information not available (states list not loaded)'
            }
        
        # Check if states is a dictionary (expected format)
        if isinstance(self.states, dict):
            if state_name in self.states:
                state_data = self.states[state_name]
                return {
                    'commands': state_data.get('commands', []),
                    'description': state_data.get('description', f'State: {state_name}')
                }
        else:
            # Handle if states is a list (alternative format)
            for state in self.states:
                if isinstance(state, dict):
                    if state.get('name') == state_name:
                        return {
                            'commands': state.get('commands', []),
                            'description': state.get('description', f'State: {state_name}')
                        }
                elif isinstance(state, str) and state == state_name:
                    return {
                        'commands': [],
                        'description': f'State: {state_name}'
                    }
        
        # State not found
        return {
            'commands': [],
            'description': f'Unknown state: {state_name}'
        }