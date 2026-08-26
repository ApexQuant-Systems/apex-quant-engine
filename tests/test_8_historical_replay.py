import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.historical_replay import HistoricalReplay

class TestHistoricalReplay(unittest.TestCase):
    def test_replay_flow(self):
        replay = HistoricalReplay()
        result = replay.run_replay("BTCUSDT", "1h")
        self.assertIn(result, ["BUY", "SELL", "WAIT"])
        print(f"\n[DIAGNOSTIC] Historical Replay pipeline verified. Signal: {result}")

if __name__ == '__main__':
    unittest.main()
