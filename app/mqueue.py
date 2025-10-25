from nats.aio.client import Client as NATS
import atexit
import json
from dunebugger_logging import logger


class NATSComm:
    def __init__(self, nat_servers, client_id, subject_root, mqueue_handler):
        self.nc = NATS()
        self.servers = nat_servers
        self.client_id = client_id
        self.subject_root = subject_root
        self.mqueue_handler = mqueue_handler

        self.nc.on_connect = lambda nc: logger.info(f"__init__: Connected to NATS server: {self.servers}")
        atexit.register(self.close)

    async def disconnected_cb(self):
        logger.warning("disconnected_cb: Disconnected from NATS server")

    async def reconnected_cb(self):
        logger.info(f"reconnected_cb: Got reconnected to {self.nc.connected_url.netloc}")

    async def error_cb(self, error):
        logger.error(f"error_cb: Error occurred: {error}")

    async def close(self):
        await self.nc.drain()
        logger.debug("close: NATS connection closed")

    async def connect(self):
        await self.nc.connect(
            servers=self.servers,
            name=self.client_id,
            ping_interval=5,
            max_outstanding_pings=3,
            reconnect_time_wait=2,
            reconnected_cb=self.reconnected_cb,
            disconnected_cb=self.disconnected_cb,
            error_cb=self.error_cb,
        )

    async def _handler(self, mqueue_message):
        try:
            await self.mqueue_handler.process_mqueue_message(mqueue_message)
        except Exception as e:
            logger.error(f"_handler: Error processing message: {e}")

    async def start(self):
        try:
            await self.connect()
            logger.info(f"start: Connected to NATS server: {self.servers}")
        except Exception as e:
            logger.error(f"start: Failed to connect to NATS server: {e}")
            raise

        try:
            await self.nc.subscribe(f"{self.subject_root}.{self.client_id}.*", cb=self._handler)
            await self.nc.flush()
            logger.info(f"start: Listening for messages on {self.subject_root}.{self.client_id}.")
        except Exception as e:
            logger.error(f"start: Failed to subscribe to {self.subject_root}.{self.client_id}.*: {e}")
            raise

    async def send(self, message: dict, recipient, reply_subject=None):
        try:
            # Convert dictionary to JSON string, then encode to bytes
            subject = message["subject"]
            message_json = json.dumps(message)
            if reply_subject:
                await self.nc.publish(f"{self.subject_root}.{recipient}.{subject}", message_json.encode(), reply_to=reply_subject)
            else:
                await self.nc.publish(f"{self.subject_root}.{recipient}.{subject}", message_json.encode())
            # TODO: Debug remove
            logger.debug(f"send: Sent message: {str(message)[:20]}")
        except Exception as e:
            logger.error(f"send: Error sending message: {e}")
