import json
import os
import sys
import urllib.request
import pandas as pd
from datetime import datetime
from collections import deque

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from structure_engine.displacement_detector import DisplacementEngine
from core.scoring_engine import ConcurrencyScoringEngine
from master_orchestrator import MasterOrchestrator
from denial_analyzer import DenialAnalyticsEngine
from strategies.profile_manifest import IntradaySniperProfile, SwingVanguardProfile

class DynamicReplayChamber:
    def __init__(self, profile: IntradaySniperProfile):
        self.profile = profile
        self.orchestrator = MasterOrchestrator()
        self.denial_engine = DenialAnalyticsEngine()
        
        # Hydrate production intelligence components with profile-specific limits
        self.regime_engine = RegimeEngine()
        self.structure_engine = StructureEngine(lookback=5)
        self.displacement_engine = DisplacementEngine(lookback=5, threshold_multiplier=profile.displacement_threshold)
        self.scoring_engine = ConcurrencyScoringEngine(target_threshold=profile.target_threshold)

        print(f"[*] Dynamic Replay Chamber primed with profile cartridge: [{profile.name}]")

    def run_time_warp(self, symbol, lookback_minutes=300):
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={self.profile.timeframe}&limit={lookback_minutes}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                klines = json.loads(response.read().decode())
            
            df_raw = pd.DataFrame([{
                "start_time": datetime.fromtimestamp(k[0] / 1000.0),
                "open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4])
            } for k in klines])
            
            print(f"[▶] Executing warp simulation on {symbol} using timeframe ({self.profile.timeframe})...")
            
            history_buffer = deque(maxlen=50)
            for idx in range(0, 20):
                history_buffer.append(df_raw.iloc[idx].to_dict())

            for i in range(20, len(df_raw)):
                current_tick = df_raw.iloc[i]
                history_buffer.append(current_tick.to_dict())
                df_state = pd.DataFrame(list(history_buffer))

                df_analyzed = self.regime_engine.classify_market_regime(df_state)
                current_regime = df_analyzed.iloc[-1].get('regime', 'UNDETERMINED')
                df_structured = self.structure_engine.detect_swings(df_analyzed)
                
                struct_signals = {
                    "high_signal": bool(df_structured.iloc[-1].get('Swing_High', False)),
                    "low_signal": bool(df_structured.iloc[-1].get('Swing_Low', False))
                }

                disp_metrics = self.displacement_engine.validate_displacement(df_structured)
                score_payload = self.scoring_engine.calculate_execution_score(
                    current_regime, struct_signals, disp_metrics
                )

                if not score_payload["execution_authorized"]:
                    if struct_signals["high_signal"] or struct_signals["low_signal"]:
                        self.denial_engine.log_denied_signal(
                            symbol=symbol, regime=current_regime, 
                            displacement=disp_metrics['ratio'], score=score_payload["conviction_score"],
                            reason=f"Profile [{self.profile.name}] Strategy-Gate Failure", price=current_tick['close']
                        )
                    continue

                # Verify portfolio clearance via global risk rules using profile risk scale
                clearance = self.orchestrator.request_execution_clearance(symbol, "LONG", self.profile.risk_per_trade)
                if clearance["status"] == "DENIED":
                    self.denial_engine.log_denied_signal(
                        symbol=symbol, regime=current_regime, 
                        displacement=disp_metrics['ratio'], score=score_payload["conviction_score"],
                        reason=f"Orchestrator Block -> {clearance['reason']}", price=current_tick['close']
                    )
                else:
                    print(f"🔥 [{self.profile.name} TRANSACTION] {symbol} execution clear at ${current_tick['close']:.2f}")
                    self.orchestrator.register_active_position(symbol, "LONG", current_tick['close'], self.profile.risk_per_trade)
                    self.orchestrator.deregister_position(symbol)

        except Exception as e:
            print(f"[-] Time warp simulation aborted: {e}")

if __name__ == "__main__":
    # Test execution by swapping cartridges on the fly
    print("\n--- RUNNING INTRADAY CARTRIDGE SIMULATION ---")
    intraday_chamber = DynamicReplayChamber(IntradaySniperProfile())
    intraday_chamber.run_time_warp("SOLUSDT", lookback_minutes=100)

    print("\n--- RUNNING SWING VANGUARD CARTRIDGE SIMULATION ---")
    swing_chamber = DynamicReplayChamber(SwingVanguardProfile())
    swing_chamber.run_time_warp("SOLUSDT", lookback_minutes=100)
