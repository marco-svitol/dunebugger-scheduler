from dunebugger_logging import logger
import os
import subprocess

def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model") as model_file:
            model = model_file.read()
            if "Raspberry Pi" in model:
                return True
            else:
                return False
    except Exception:
        return False


def validate_path(path):
    if os.path.exists(path):
        return True
    else:
        return False

def check_ntp_sync():
    try:
        # Run the timedatectl command and capture the output
        result = subprocess.run(["timedatectl", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Check if NTP is synchronized
            if "synchronized: yes" in result.stdout:
                return True
            else:
                return False
        else:
            logger.error(f"Error running timedatectl: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running timedatectl: ${str(e)}")
        return False