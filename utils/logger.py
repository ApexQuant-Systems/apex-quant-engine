# filename: utils/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_apex_logger(name: str = "ApexOS") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s'
    )
    
    # Console Output Channel
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Asynchronous File Rotation Pipeline Boundary
    file_handler = RotatingFileHandler(
        "data/apex_system.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

apex_logger = setup_apex_logger()
