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
                self.schedule_handler.state_tracker.force_update()
            elif subject in ["heartbeat"]:
                await self.dispatch_message("alive", "heartbeat", "remote")
            elif subject in ["commands_list"]:
                commands = message_json["body"]
                return await self.schedule_interpreter.store_list(commands, "commands")
            elif subject in ["states_list"]:
                states = message_json["body"]
                return await self.schedule_interpreter.store_list(states, "states")
            elif subject in ["schedule_update"]:
                schedule_data = message_json["body"]
                return await self.schedule_interpreter.update_schedule(schedule_data)
            else:
                logger.warning(f"Unknown subjcet: {subject}. Ignoring message.")
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

