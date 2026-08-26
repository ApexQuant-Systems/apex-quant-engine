import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "APEX_OS") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)-12s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        os.makedirs("data", exist_ok=True)
        
        file_handler = RotatingFileHandler(
            "data/apex_system.log", maxBytes=5*1024*1024, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger

APEX_LOGGER = setup_logger()
