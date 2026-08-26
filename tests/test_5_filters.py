# filename: tests/test_5_filters.py
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.filters import FilterEngine

class TestFilterEngine(unittest.TestCase):
    def test_filter_gatekeeping(self):
        engine = FilterEngine(max_spread=0.02)
        
        # Test 1: High Impact News
        news_result = engine.validate_news("HIGH")
        self.assertFalse(news_result.passed)
        
        # Test 2: High Spread
        spread_result = engine.validate_spread(0.05) # 0.05 > 0.02
        self.assertFalse(spread_result.passed)
        
        # Test 3: Session
        session_result = engine.validate_session(12, [8, 9, 10, 11]) # 12 not in list
        self.assertFalse(session_result.passed)
        
        print(f"\n[DIAGNOSTIC] Filter Engine (Decision Engine) Gatekeeping Verified.")

if __name__ == '__main__':
    unittest.main()
