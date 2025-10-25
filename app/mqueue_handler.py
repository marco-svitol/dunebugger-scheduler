import json
from dunebugger_logging import logger
from dunebugger_settings import settings

class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self):
        self.mqueue_sender = None
        self.config_parser = None

    def set_config_parser(self, config_parser):
        self.config_parser = config_parser
        logger.debug("set_config_parser: Config parser set for MessagingQueueHandler")

    async def process_mqueue_message(self, mqueue_message):
        """Callback method to process received messages."""
        # Parse the JSON string back into a dictionary
        try:
            data = mqueue_message.data.decode()
            message_json = json.loads(data)
        except (AttributeError, UnicodeDecodeError) as decode_error:
            logger.error(f"process_mqueue_message: Failed to decode message data: {decode_error}. Raw message: {mqueue_message.data}")
            return
        except json.JSONDecodeError as json_error:
            logger.error(f"process_mqueue_message: Failed to parse message as JSON: {json_error}. Raw message: {data}")
            return

        try:
            subject = (mqueue_message.subject).split(".")[2]
            logger.debug(f"process_mqueue_message: Processing message: {str(message_json)[:20]}. Subject: {subject}. Reply to: {mqueue_message.reply}")

            if subject in ["refresh"]:
                # Send both the schedule configuration and next state information
                await self.dispatch_message(self.config_parser.get_schedule(), "schedule", "remote")
                await self.dispatch_message(self.config_parser.get_next_state_schedule(), "schedule_next", "remote")
            else:
                logger.warning(f"process_mqueue_message: Unknown subjcet: {subject}. Ignoring message.")
        except KeyError as key_error:
            logger.error(f"process_mqueue_message: KeyError: {key_error}. Message: {message_json}")
        except Exception as e:
            logger.error(f"process_mqueue_message: Error processing message: {e}. Message: {message_json}")

    async def dispatch_message(self, message_body, subject, recipient, reply_subject=None):
        message = {
            "body": message_body,
            "subject": subject,
            "source": settings.mQueueClientID,
        }
        await self.mqueue_sender.send(message, recipient, reply_subject)

