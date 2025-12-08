from os import path

class ScheduleInterpreter:
    def __init__(self, mqueue_handler):
        self.mqueue_handler = mqueue_handler
        self.commands = []
        self.states = []
        self.schedule_config = path.join(path.dirname(path.abspath(__file__)), "config/schedule.conf")
        #self.read_schedule(self.schedule_config)
        self.parse_schedule(self.schedule_config)
        self.schedule = {}

    async def request_lists(self):
        """Request the commands ans states list from the dunebugger core."""
        await self.mqueue_handler.dispatch_message("get_commands_list", "schedule_command", "core")
        await self.mqueue_handler.dispatch_message("get_states_list", "schedule_command", "core")
        
    async def store_list(self, list_body, list_type):
        """Store the received commands list."""
        if list_type == "commands":
            self.commands = list_body
        elif list_type == "states":
            self.states = list_body
    
    def validate_schedule_file(self, file_path):
        """Validate the schedule configuration file."""
        # Validates the syntax and structure of the schedule file
        # All week day must be present from Domenica to Sabato
        # Inside each day the time slots must be contiguous and non overlapping
        # Time format must be HH:MM, but also H:MM or H:M or HH:M are allowed
        # each time slot must have at least one action
        # action can be states or commands 
        # States must be validated against the known states list
        # Commands must be validated against the known commands list
        # If just a time slot and an action is present, the action is supposed to be a state
        # To execute a commnad the action must be prefixed with "cmd:"
        # example: cmd:'sw 1 on' or cmd:"sw 1 on" or cmd:"dmx set 1 red"
        # States are defined as list of commands so each command of a state list must be validated as well
        # Special days are optional and can override the normal week days
        # A special day is defined by a date in format DD-MM-YYYY or DD/MM/YYYY
        # All rules valid for weekdays aplpies to special days as well
        # If validation passes, return True, else raise an exception
        pass

    def load_schedule(self, file_path):
        """Read the schedule configuration file."""
        # Implement reading the schedule configuration file
        # and create schedule entries that will run as a non-blocking coroutine in the main loop
        # Before loading, validate the file
        # When creating the schedule entries, consider that special days overrides the normal week day
        pass

    def get_next_schedule(self):
        """Get the next scheduled action based on the current time."""
        # returns the next scheduled action to be executed and the time to wait before executing it
        # and the absolute time of execution
        pass

    async def update_schedule(self, schedule_data):
        """Update the schedule with the received data."""
        # Update the schedule based on the received data
        # Validate the new schedule data before applying it
        # If validate then save the new schedule to the configuration file
        # and reload the schedule by cleaning all schedule and loading it again
        pass