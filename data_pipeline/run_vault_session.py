import os
import sys
import asyncio
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_pipeline.forward_vault import ApexForwardTestingVault

async def run_vault_campaign():
    print("=====================================================================")
    print(" 🛰️  APEX WEALTH PLATFORM: COMPILING FORWARD TESTING SIGNAL VAULT")
    print("=====================================================================")
    
    vault = ApexForwardTestingVault()
    
    # Simulating a concurrent slice of multi-market setups across all 4 strategy sets
    live_market_matrix = [
        {"set_id": 1, "name": "SET_1_MACRO", "tf": "1M->1W->1D", "symbol": "BTCUSDT", "entry": 64150.0, "htf_tp": 78000.0, "ltf_sl": 61200.0, "trend": "BULLISH"},
        {"set_id": 2, "name": "SET_2_SWING", "tf": "1W->1D->4H", "symbol": "NAS100", "entry": 19520.0, "htf_tp": 18100.0, "ltf_sl": 19700.0, "trend": "BEARISH"},
        {"set_id": 3, "name": "SET_3_INTRADAY", "tf": "1D->4H->1H", "symbol": "EURUSD", "entry": 1.0850, "htf_tp": 1.1300, "ltf_sl": 1.0750, "trend": "BULLISH"},
        {"set_id": 4, "name": "SET_4_SCALP", "tf": "4H->1H->15M", "symbol": "XAUUSD", "entry": 2355.0, "htf_tp": 2520.0, "ltf_sl": 2325.0, "trend": "BULLISH"}
    ]
    
    # Pipe the entire matrix through your structural verification check and database storage
    for setup in live_market_matrix:
        vault.process_and_vault_signal(
            set_id=setup["set_id"],
            set_name=setup["name"],
            tf_map=setup["tf"],
            symbol=setup["symbol"],
            entry=setup["entry"],
            htf_tp=setup["htf_tp"],
            ltf_sl=setup["ltf_sl"],
            mtf_trend=setup["trend"]
        )
        
    print("-" * 69)
    print("📖 CURRENT FORWARD JOURNAL ENTRIES RECONCILED DIRECTLY FROM DISK:")
    
    conn = sqlite3.connect(vault.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT signal_id, asset_class, strategy_version, calculated_rr, final_signal FROM forward_signal_vault")
    
    for row in cursor.fetchall():
        print(f"  ├── Signal: {row[0]:<24} | Class: {row[1]:<11} | Ver: {row[2]} | Structural RR: {row[3]:>5} | Type: {row[4]}")
        
    conn.close()
    print("=====================================================================")
    print("🏁 STEP 4 COMPLETED: STATISTICAL EVIDENCE GATHERING ENGINE IS ONLINE")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_vault_campaign())
