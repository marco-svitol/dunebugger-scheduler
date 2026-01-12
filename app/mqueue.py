from nats.aio.client import Client as NATS
import json
import asyncio
from dunebugger_logging import logger

class NATSComm:
    def __init__(self, nat_servers, client_id, subject_root, mqueue_handler):
        self.nc = NATS()
        self.servers = nat_servers
        self.client_id = client_id
        self.subject_root = subject_root
        self.mqueue_handler = mqueue_handler
        self.is_connected = False
        self.connection_task = None
        self.retry_interval = 10  # seconds between connection attempts

        self.nc.on_connect = lambda nc: logger.info(f"Connected to NATS messaging server: {self.servers}")

    async def disconnected_cb(self):
        self.is_connected = False
        logger.warning("Disconnected from NATS messaging server")

    async def reconnected_cb(self):
        self.is_connected = True
        logger.info(f"Got reconnected to {self.nc.connected_url.netloc}")

    async def error_cb(self, error):
        logger.error(f"Error occurred: {error}")

    async def close_listener(self):
        """Async method to properly close NATS connection"""
        try:
            # Stop the connection task if it's running
            if self.connection_task and not self.connection_task.done():
                self.connection_task.cancel()
                try:
                    await self.connection_task
                except asyncio.CancelledError:
                    pass
            
            if self.nc.is_connected:
                await self.nc.drain()
                logger.debug("NATS connection closed")
        except Exception as e:
            logger.error(f"Error closing NATS connection: {e}")

    async def connect(self):
        try:
            await self.nc.connect(
                servers=self.servers,
                name=self.client_id,
                ping_interval=5,
                max_outstanding_pings=3,
                reconnect_time_wait=10,
                reconnected_cb=self.reconnected_cb,
                disconnected_cb=self.disconnected_cb,
                error_cb=self.error_cb,
                max_reconnect_attempts=-1,  # Unlimited reconnect attempts
            )
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            logger.debug(f"Failed to connect to NATS: {e}")
            return False

    async def _connection_loop(self):
        """Background task that continuously tries to establish NATS connection"""
        while True:
            try:
                if not self.is_connected:
                    logger.debug("Attempting to connect to NATS messaging server...")
                    success = await self.connect()
                    if success:
                        logger.info(f"Connected to NATS messaging server: {self.servers}")
                        # Subscribe to messages once connected
                        try:
                            await self.nc.subscribe(f"{self.subject_root}.{self.client_id}.*", cb=self._handler)
                            await self.nc.flush()
                            logger.info(f"Listening for messages on queue {self.subject_root}.{self.client_id}.")
                        except Exception as e:
                            logger.error(f"Failed to subscribe to messaging queue: {e}")
                            self.is_connected = False
                    else:
                        logger.debug(f"Connection failed, retrying in {self.retry_interval} seconds...")
                        
                # Wait before next connection attempt or status check
                await asyncio.sleep(self.retry_interval)
                
            except asyncio.CancelledError:
                logger.debug("Connection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in connection loop: {e}")
                await asyncio.sleep(self.retry_interval)

    async def _handler(self, mqueue_message):
        try:
            command_reply_message = await self.mqueue_handler.process_mqueue_message(mqueue_message)
            if command_reply_message:
                if isinstance(command_reply_message, dict) and "message" in command_reply_message:
                    logger.debug(command_reply_message["message"])
                else:
                    logger.debug(f"Received reply: {command_reply_message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def start_listener(self):
        """Start the non-blocking NATS connection process"""
        logger.info("Starting NATS connection manager (non-blocking)")
        self.connection_task = asyncio.create_task(self._connection_loop())
        return self.connection_task

    def get_connection_status(self):
        """Return current connection status"""
        return self.is_connected

    async def send(self, message: dict, recipient, reply_to=None):
        if not self.is_connected:
            logger.warning("NATS not connected, cannot send message")
            return False
            
        try:
            # Convert dictionary to JSON string, then encode to bytes
            subject = message["subject"]
            message_json = json.dumps(message)
            if reply_to:
                await self.nc.publish(f"{self.subject_root}.{recipient}.{subject}", message_json.encode(), reply_to=reply_to)
            else:
                await self.nc.publish(f"{self.subject_root}.{recipient}.{subject}", message_json.encode())
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
