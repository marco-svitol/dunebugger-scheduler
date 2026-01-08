import json
from dunebugger_logging import logger
from dunebugger_settings import settings

class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self):
        self.mqueue_sender = None
        self.schedule_interpreter = None

    async def process_mqueue_message(self, mqueue_message):
        """Callback method to process received messages."""
        # Parse the JSON string back into a dictionary
        try:
            data = mqueue_message.data.decode()
            message_json = json.loads(data)
        except (AttributeError, UnicodeDecodeError) as decode_error:
            logger.error(f"Failed to decode message data: {decode_error}. Raw message: {mqueue_message.data}")
            return
        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse message as JSON: {json_error}. Raw message: {data}")
            return

        try:
            subject = (mqueue_message.subject).split(".")[2]
            #TODO: too much verbosity
            logger.debug(f"Processing message: {str(message_json)[:20]}. Subject: {subject}. Reply to: {mqueue_message.reply}")

            if subject in ["refresh"]:
                await self.handle_refresh()
            elif subject in ["heartbeat"]:
                await self.handle_heartbeat()
            elif subject in ["modes_list"]:
                await self.handle_modes_list(message_json)
            elif subject in ["update_schedule"]:
                return await self.handle_update_schedule(message_json)
            elif subject in ["get_schedule"]:
                await self.handle_get_schedule()
            elif subject in ["get_next_actions"]:
                await self.handle_get_next_actions()
            elif subject in ["get_last_executed_action"]:
                await self.handle_get_last_executed_action()
            else:
                logger.warning(f"Unknown subject: {subject}. Ignoring message.")
        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {message_json}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {message_json}")

    async def dispatch_message(self, message_body, subject, recipient, reply_subject=None):
        message = {
            "body": message_body,
            "subject": subject,
            "source": settings.mQueueClientID,
        }
        await self.mqueue_sender.send(message, recipient, reply_subject)
    
    async def handle_refresh(self):
        await self.handle_get_schedule()
        await self.handle_get_next_actions()
        await self.handle_get_last_executed_action()

    async def handle_heartbeat(self):
        await self.dispatch_message("alive", "heartbeat", "remote")

    async def handle_modes_list(self, message_json):
        modes_list = message_json["body"]
        return await self.schedule_interpreter.store_modes_list(modes_list) 

    async def handle_update_schedule(self, message_json):
        schedule_data = message_json["body"]
        command_reply_message =await self.schedule_interpreter.update_schedule(schedule_data)
        if command_reply_message["level"] == "error":
            await self.dispatch_message(command_reply_message, "log", "remote")
        return command_reply_message
    
    async def handle_get_schedule(self):
        schedule = self.schedule_interpreter.get_schedule()
        await self.dispatch_message(schedule, "current_schedule", "remote")

    async def handle_get_next_actions(self):
        next_actions = self.schedule_interpreter.get_next_actions()
        await self.dispatch_message(next_actions, "next_actions", "remote")
    
    async def handle_get_last_executed_action(self):
        last_action = self.schedule_interpreter.get_last_executed_action()
        await self.dispatch_message(last_action, "last_executed_action", "remote")
    