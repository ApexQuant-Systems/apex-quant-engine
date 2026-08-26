import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logger import APEX_LOGGER

class TestLogger(unittest.TestCase):
    def test_logger_initialization(self):
        self.assertEqual(APEX_LOGGER.name, "APEX_OS")
        self.assertTrue(len(APEX_LOGGER.handlers) >= 2)
        
        log_path = "data/apex_system.log"
        APEX_LOGGER.debug("Initialization diagnostic check.")
        self.assertTrue(os.path.exists(log_path))

if __name__ == '__main__':
    unittest.main()
