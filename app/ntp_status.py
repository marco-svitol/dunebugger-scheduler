from dunebugger_logging import logger


class NTPStatusManager:
    """Manages NTP availability status."""
    
    def __init__(self):
        # NTP availability flag - assume available at start
        self.ntp_available = True
    
    def set_ntp_status(self, is_available):
        """Set the NTP availability status."""
        if self.ntp_available != is_available:
            self.ntp_available = is_available
            status = "available" if is_available else "unavailable"
            logger.warning(f"NTP status changed to: {status}")
            if is_available:
                logger.info("Mode execution re-enabled (NTP is available)")
            else:
                logger.warning("Mode execution disabled (NTP is unavailable)")
        return self.ntp_available
    
    def is_ntp_available(self):
        """Check if NTP is available."""
        return self.ntp_available
