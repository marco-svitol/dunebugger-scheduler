import json
from dunebugger_logging import logger
from dunebugger_settings import settings
from version import get_version_info

class MessagingQueueHandler:
    """Class to handle messaging queue operations."""

    def __init__(self):
        self.mqueue_sender = None
        self.schedule_interpreter = None
        self.ntp_status_manager = None

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
            elif subject in ["ntp_status"]:
                await self.handle_ntp_status(message_json)
            elif subject in ["get_version"]:
                #TODO : make use of reply field more consistently in mqueue handling
                recipient = mqueue_message.reply if mqueue_message.reply else message_json.get("source")
                await self.handle_get_version(recipient)
            else:
                logger.warning(f"Unknown subject: {subject}. Ignoring message.")
        except KeyError as key_error:
            logger.error(f"KeyError: {key_error}. Message: {message_json}")
        except Exception as e:
            logger.error(f"Error processing message: {e}. Message: {message_json}")
    
    async def handle_refresh(self):
        await self.handle_get_schedule()
        await self.handle_get_next_actions()
        await self.handle_get_last_executed_action()

    async def handle_heartbeat(self):
        await self.dispatch_message(get_version_info(), "heartbeat", "remote")

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

    async def request_ntp_status(self):
        """Request the current NTP status from the controller."""
        await self.dispatch_message("get_ntp_status", "get_ntp_status", "remote")
        logger.debug("Requested NTP status from controller")

    async def handle_ntp_status(self, message_json):
        """Handle NTP status updates from the controller."""
        body = message_json.get("body", {})
        ntp_available = body.get("ntp_available", False)
        timestamp = body.get("timestamp", "unknown")
        
        logger.debug(f"Received NTP status: available={ntp_available}, timestamp={timestamp}")
        
        # Update the NTP status in NTP status manager
        if self.ntp_status_manager:
            self.ntp_status_manager.set_ntp_status(ntp_available)
        else:
            logger.error("NTP status manager not available to update NTP status")

    async def handle_get_version(self, recipient):
        """Handle get_version requests by returning version information."""
        version_info = get_version_info()
        await self.dispatch_message(version_info, "version_info", recipient)
        logger.debug(f"Sent version info: {version_info['full_version']}")
    
    async def dispatch_message(self, message_body, subject, recipient, reply_to=None):
        message = {
            "body": message_body,
            "subject": subject,
            "source": settings.mQueueClientID,
        }
        await self.mqueue_sender.send(message, recipient, reply_to)