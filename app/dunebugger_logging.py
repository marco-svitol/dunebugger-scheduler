import logging
import logging.config
from os import path
import asyncio

logConfig = path.join(path.dirname(path.abspath(__file__)), "config/dunebuggerlogging.conf")
logging.config.fileConfig(logConfig)  # load logging config file
logger = logging.getLogger("dunebuggerLog")

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "RESET": "\033[0m",
}


class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = self._style._fmt
        if record.levelno == logging.ERROR:
            log_fmt = COLORS["RED"] + log_fmt + COLORS["RESET"]
        elif record.levelno == logging.WARNING:
            log_fmt = COLORS["YELLOW"] + log_fmt + COLORS["RESET"]
        elif record.levelno == logging.DEBUG:
            log_fmt = COLORS["BLUE"] + log_fmt + COLORS["RESET"]
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


class QueueHandler(logging.Handler):
    """Custom logging handler that forwards logs to the message queue."""
    
    def __init__(self, mqueue_handler=None):
        super().__init__()
        self.mqueue_handler = mqueue_handler
        self._loop = None
        # Try to get the current event loop when the handler is created
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running yet, will try to get it later
            pass
    
    def set_mqueue_handler(self, mqueue_handler):
        """Set the message queue handler after initialization."""
        self.mqueue_handler = mqueue_handler
        # Try to get the event loop again when mqueue_handler is set
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
    
    def emit(self, record):
        """Emit a log record to the message queue."""
        if not self.mqueue_handler or not self.mqueue_handler.mqueue_sender:
            return
        
        try:
            # Create log message JSON
            log_data = {
                "level": record.levelname,
                "message": record.getMessage()
            }
            
            # Get the event loop
            try:
                # First try to get the running loop (works if we're in the event loop thread)
                loop = asyncio.get_running_loop()
                # We're in the event loop thread, create task directly
                asyncio.create_task(
                    self.mqueue_handler.dispatch_message(
                        log_data, 
                        "log_message", 
                        "terminal"
                    )
                )
            except RuntimeError:
                # We're not in the event loop thread, use stored loop reference
                if self._loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self.mqueue_handler.dispatch_message(
                            log_data, 
                            "log_message", 
                            "terminal"
                        ),
                        self._loop
                    )
                    # Note: We don't wait for the future to complete to avoid blocking the thread
                    
        except Exception:
            # Silently ignore errors to prevent logging loops
            pass


def get_logging_level_from_name(level_str):
    # Convert the string level to a logging level
    level = getattr(logging, level_str.upper(), None)
    if not isinstance(level, int):
        return ""
    else:
        return level


def set_logger_level(logger_name, level):
    try:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logging.getLogger(logger_name).debug(f"Logger {logger_name} level set to {logging.getLevelName(logger.level)}")
    except Exception as exc:
        logging.getLogger(logger_name).error(f"Error while setting logger ${logger_name} level to {logging.getLevelName(logger.level)}: ${str(exc)}")


# Global queue handler instance
_queue_handler = None


def enable_queue_logging(mqueue_handler):
    """Enable logging to message queue."""
    global _queue_handler
    
    if _queue_handler is None:
        _queue_handler = QueueHandler(mqueue_handler)
        logger.addHandler(_queue_handler)
        logger.debug("Queue logging enabled")
    else:
        _queue_handler.set_mqueue_handler(mqueue_handler)
    
    # Try to capture the event loop if it's running
    try:
        _queue_handler._loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop running yet, will be captured later
        pass


def update_queue_logging_handler_loop():
    """Update the queue handler with the current event loop."""
    global _queue_handler
    if _queue_handler is not None:
        try:
            _queue_handler._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass


def disable_queue_logging():
    """Disable logging to message queue."""
    global _queue_handler
    
    if _queue_handler is not None:
        logger.removeHandler(_queue_handler)
        _queue_handler = None
        logger.debug("Queue logging disabled")


# Get the console handler and set the custom formatter
console_handler = logger.handlers[0]
console_handler.setFormatter(CustomFormatter("%(levelname)s - %(asctime)s : %(message)s", "%d/%m/%Y %H:%M:%S"))
