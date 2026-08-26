import os

class ApexGlobalConfiguration:
    """
    🛰️ APEX OPERATING SYSTEM: GLOBAL SYSTEM CONFIGURATION
    The single, permanent source of truth for portfolio settings and environment paths.
    """
    # System Architecture Paths
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DATABASE_PATH = os.path.join(BASE_DIR, 'data_pipeline', 'historical_warehouse.db')
    LOG_FILE_PATH = os.path.join(BASE_DIR, 'utils', 'apex_system.log')

    # Institutional Asset Core Matrix
    PORTFOLIO_ASSETS = {
        "CRYPTO": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "FOREX": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
        "METALS": ["XAUUSD", "XAGUSD"],
        "INDICES": ["NAS100", "SPX500", "US30"]
    }

    # Hierarchical Timeframe Multi-Sets
    STRATEGY_SETS = {
        1: {"name": "SET_1_MACRO_INVESTING", "htf": "1d", "mtf": "4h", "ltf": "1h"},  # Scaled to available tracking limits
        2: {"name": "SET_2_SWING_HORIZON",   "htf": "1d", "mtf": "4h", "ltf": "1h"},
        3: {"name": "SET_3_POSITION_PLAY",   "htf": "1d", "mtf": "4h", "ltf": "1h"},
        4: {"name": "SET_4_INTRADAY_SCALP",  "htf": "4h", "mtf": "1h", "ltf": "15m"}
    }

    # Strict Risk Management Parameters
    RISK_PER_TRADE_PCT = 0.01  # Hardcoded max 1% equity risk exposure limit
    MINIMUM_REQUIRED_RR = 4.0  # Entry firewall ratio barrier

    # Broker Configuration Target Routing
    ACTIVE_BROKER = "VANTAGE"  # Swappable execution target parameter

if __name__ == "__main__":
    print(f"🟢 [CONFIG LOADED] Database Destination Path: {ApexGlobalConfiguration.DATABASE_PATH}")
