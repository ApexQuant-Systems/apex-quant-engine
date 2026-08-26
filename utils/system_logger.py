import logging
import os
import sys

# Append parent path to enforce environment visibility boundaries
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.project_config import ApexGlobalConfiguration

class ApexSystemLogger:
    """
    🛰️ APEX OPERATING SYSTEM: DIAGNOSTIC LOGGER CORE
    Standardizes error outputs, transaction flags, and telemetry trace tracking.
    """
    @staticmethod
    def get_initialized_logger(module_name: str):
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s', '%Y-%m-%d %H:%M:%S')
            
            # Streaming Standard Out Console Router Handle
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Persistent Local Disk Text Logging File Handler
            log_file = ApexGlobalConfiguration.LOG_FILE_PATH
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        return logger

if __name__ == "__main__":
    log = ApexSystemLogger.get_initialized_logger("FOUNDATION_TEST")
    log.info("System logging layer successfully linked to database file boundaries.")
