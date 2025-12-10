import asyncio
from dunebugger_settings import settings

class StateTracker:
    def __init__(self):
        # Dictionary to track state changes
        self.state_changes = {
            "schedule": False,
            "near_actions": False,
        }
        self.mqueue_handler = None
        self.monitor_task = None
        self.running = True
        self.check_interval = int(settings.mQueueStateCheckIntervalSecs)

    def notify_update(self, attribute):
        if attribute in self.state_changes:
            self.state_changes[attribute] = True

    def clear_update(self, attribute):
        if attribute in self.state_changes:
            self.state_changes[attribute] = False

    def force_update(self):
        self.notify_update("schedule")
        self.notify_update("near_actions")


    def has_changes(self):
        return any(self.state_changes.values())

    def get_changes(self):
        return [key for key, value in self.state_changes.items() if value]

    def reset_changes(self):
        for key in self.state_changes:
            self.state_changes[key] = False

    async def start_state_monitoring(self):
        """Start the state monitoring task"""
        self.monitor_task = asyncio.create_task(self._monitor_states())

    async def stop_state_monitoring(self):
        """Stop the state monitoring task"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_states(self):
        """
        Monitor the state tracker for changes and react accordingly.
        """
        while self.running:
            if self.has_changes():
                changed_states = self.get_changes()
                for state in changed_states:
                    if state == "schedule":
                        # React to GPIO state changes
                        await self.mqueue_handler.handle_get_schedule()
                        await self.mqueue_handler.handle_get_next_actions()
                        await self.mqueue_handler.handle_get_last_executed_action()
                    elif state == "near_actions":
                        # Handle sequence changes
                        await self.mqueue_handler.handle_get_next_actions()
                        await self.mqueue_handler.handle_get_last_executed_action()
                # Reset the state tracker after handling changes
                self.reset_changes()
            await asyncio.sleep(self.check_interval)

state_tracker = StateTracker()
