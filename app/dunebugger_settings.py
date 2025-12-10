from os import path
import configparser
from dunebugger_logging import logger, get_logging_level_from_name, set_logger_level
from utils import is_raspberry_pi

class DunebuggerSettings:
    def __init__(self):
        self.config = configparser.ConfigParser()
        # Set optionxform to lambda x: x to preserve case
        self.config.optionxform = lambda x: x
        self.dunebugger_config = path.join(path.dirname(path.abspath(__file__)), "config/dunebugger.conf")
        self.load_configuration(self.dunebugger_config)
        self.override_configuration()
        set_logger_level("dunebuggerLog", self.dunebuggerLogLevel)

    def show_configuration(self):
        print("Current Configuration:")
        for attr_name in dir(self):
            if not attr_name.startswith("__") and not callable(getattr(self, attr_name)):
                print(f"{attr_name}: {getattr(self, attr_name)}")

    def load_configuration(self, dunebugger_config=None):
        if dunebugger_config is None:
            dunebugger_config = self.dunebugger_config

        try:
            self.config.read(dunebugger_config)
            for section in ["General", "MessageQueue", "Log"]:
                if not self.config.has_section(section):
                    continue
                for option in self.config.options(section):
                    value = self.config.get(section, option)
                    setattr(self, option, self.validate_option(section, option, value))
                    logger.debug(f"{option}: {value}")

            self.ON_RASPBERRY_PI = is_raspberry_pi()
            logger.debug(f"ON_RASPBERRY_PI: {self.ON_RASPBERRY_PI}")
            logger.info("Configuration loaded successfully")
        except configparser.Error as e:
            logger.error(f"Error reading {dunebugger_config} configuration: {e}")

    def validate_option(self, section, option, value):
        # Validation for specific options
        try:
            if section == "General":
                pass
            elif section == "MessageQueue":
                if option in ["mQueueServers", "mQueueClientID", "mQueueSubjectRoot", "mQueueStateCheckIntervalSecs"]:
                    return str(value)
            elif section == "Log":
                logLevel = get_logging_level_from_name(value)
                if logLevel == "":
                    return get_logging_level_from_name("INFO")
                else:
                    return logLevel

        except (configparser.NoOptionError, ValueError) as e:
            raise ValueError(f"Invalid configuration: Section={section}, Option={option}, Value={value}. Error: {e}")

        # If no specific validation is required, return the original value
        return value

    def override_configuration(self):
        if not self.ON_RASPBERRY_PI:
            self.vlcdevice = ""


settings = DunebuggerSettings()
