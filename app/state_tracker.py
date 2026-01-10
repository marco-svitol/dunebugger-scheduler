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
        from dunebugger_logging import logger
        
        while self.running:
            try:
                if self.has_changes():
                    changed_states = self.get_changes()
                    for state in changed_states:
                        try:
                            if state == "schedule":
                                logger.debug("StateTracker detected schedule change.")
                                # React to GPIO state changes with timeout protection
                                await asyncio.wait_for(
                                    self.mqueue_handler.handle_get_schedule(), 
                                    timeout=5.0
                                )
                                await asyncio.wait_for(
                                    self.mqueue_handler.handle_get_next_actions(), 
                                    timeout=5.0
                                )
                                await asyncio.wait_for(
                                    self.mqueue_handler.handle_get_last_executed_action(), 
                                    timeout=5.0
                                )
                            elif state == "near_actions":
                                logger.debug("StateTracker detected near actions change.")
                                # Handle sequence changes with timeout protection
                                await asyncio.wait_for(
                                    self.mqueue_handler.handle_get_next_actions(), 
                                    timeout=5.0
                                )
                                await asyncio.wait_for(
                                    self.mqueue_handler.handle_get_last_executed_action(), 
                                    timeout=5.0
                                )
                        except asyncio.TimeoutError:
                            logger.error(f"Timeout while handling state change: {state}")
                        except Exception as e:
                            logger.error(f"Error handling state change '{state}': {e}", exc_info=True)
                    
                    # Reset the state tracker after handling changes
                    self.reset_changes()
                    
            except Exception as e:
                logger.error(f"Unexpected error in state monitor loop: {e}", exc_info=True)
                
            await asyncio.sleep(self.check_interval)

state_tracker = StateTracker()
