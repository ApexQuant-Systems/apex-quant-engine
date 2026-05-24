# config/system_settings.py

SYSTEM_CONFIG = {
    "name": "Fractal Multi-Timeframe Liquidity Expansion System",
    "version": "1.0.0",
    "target_assets": ["BTC/USDT", "ETH/USDT"],
    
    # Unified Tri-Engine Multi-Timeframe Stacks
    "engines": {
        "style_1_macro": {"HTF": "1M", "MTF": "1W", "LTF": "1D"},
        "style_2_swing": {"HTF": "1W", "MTF": "1D", "LTF": "4H"},
        "style_3_active": {"HTF": "1D", "MTF": "4H", "LTF": "1H"}
    },
    
    # Hardcoded Quantitative Parameters
    "logic_parameters": {
        "swing_lookback_candles": 2,      # Requires N candles on each side to validate structure
        "displacement_std_dev": 1.5,      # Body size threshold above the mean range
        "atr_stop_multiplier": 1.5,       # Calculates dynamic protection boundaries
        "minimum_risk_reward_ratio": 4.0  # Absolute floor for capital allocation
    },
    
    # Absolute Risk Firewall Configurations
    "risk_governance": {
        "max_account_risk_percent": 0.01, # Absolute 1% risk allocation rule
        "max_daily_drawdown_percent": 0.05,
        "max_open_positions": 2
    }
}

if __name__ == "__main__":
    print(f"System Configuration Framework initialized for: {SYSTEM_CONFIG['name']}")
    print(f"Operational Framework: Engines frozen across {len(SYSTEM_CONFIG['engines'])} distinct fractal speeds.")
