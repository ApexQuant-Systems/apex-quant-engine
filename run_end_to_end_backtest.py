# filename: run_end_to_end_backtest.py
import json
from backtesting.master_orchestrator import ApexBacktestOrchestrator

def generate_synthetic_trend_data():
    """Generates a 15-bar sequence that simulates a clear breakout and follow-through."""
    base_price = 50000.0
    data = []
    for i in range(15):
        # Create an artificial bullish trend that dips, then breaks out violently on bar 12
        modifier = 1.0 + (i * 0.001) if i < 10 else 1.0 - (i * 0.002)
        if i >= 12: modifier = 1.05 + (i * 0.01) # Breakout
        
        close_p = base_price * modifier
        data.append({
            "timestamp": f"2026-01-01 10:{i:02d}:00",
            "open": close_p * 0.999,
            "high": close_p * 1.01,
            "low": close_p * 0.99,
            "close": close_p,
            "volume": 100.0 + i
        })
    # Add a final massive wick bar to hit the Take Profit target
    data.append({
        "timestamp": "2026-01-01 10:16:00", "open": 55000.0, 
        "high": 60000.0, "low": 54000.0, "close": 58000.0, "volume": 500.0
    })
    return data

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 APEX OS V1: END-TO-END BACKTEST INITIATED")
    print("="*50 + "\n")
    
    historical_data = generate_synthetic_trend_data()
    orchestrator = ApexBacktestOrchestrator(symbol="BTCUSDT", starting_balance=10000.0)
    
    # Execute the master loop
    final_report = orchestrator.run_full_backtest(historical_data)
    
    print("\n" + "="*50)
    print("📊 APEX INSTITUTIONAL PERFORMANCE REPORT")
    print("="*50)
    print(json.dumps(final_report, indent=4))
    print("="*50 + "\n")
