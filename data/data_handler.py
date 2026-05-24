import ccxt
import pandas as pd
import time
import os

class CryptoDataIngestion:
    def __init__(self, exchange_id='binance'):
        # Initialize the CCXT exchange connector
        # We enable rate limiting to prevent Binance from IP-banning the server
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'} # Targeting high-liquidity perpetual futures
        })

    def fetch_historical_candles(self, symbol: str, timeframe: str, since_date_str: str, limit_per_request: int = 1000):
        """
        Fetches historical OHLCV data from the exchange, handling pagination limits.
        """
        print(f"📡 Establishing connection to {self.exchange.id} for {symbol} [{timeframe}]...")
        
        # Convert human-readable date (e.g., '2022-01-01T00:00:00Z') to millisecond timestamp
        since_ms = self.exchange.parse8601(since_date_str)
        all_candles = []
        
        while True:
            try:
                # Fetch a batch of candles
                print(f"   -> Fetching batch starting from: {self.exchange.iso8601(since_ms)}")
                candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit_per_request)
                
                if len(candles) == 0:
                    print("   -> End of historical data reached.")
                    break
                    
                all_candles.extend(candles)
                
                # Get the timestamp of the very last candle in this batch, add 1 millisecond, 
                # and use it as the starting point for the next request.
                last_candle_timestamp = candles[-1][0]
                since_ms = last_candle_timestamp + 1
                
                # If we received fewer candles than the limit, we've hit the present moment
                if len(candles) < limit_per_request:
                    print("   -> Present moment reached. Data sync complete.")
                    break
                    
            except Exception as e:
                print(f"⚠️ API Error encountered: {e}")
                print("   -> Pausing for 5 seconds before retrying...")
                time.sleep(5)
                
        # Convert the raw arrays into a powerful Pandas DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert timestamp to a readable datetime format
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Set datetime as the index for easier manipulation later
        df.set_index('datetime', inplace=True)
        
        return df

    def save_to_csv(self, df, filename):
        """Saves the downloaded array to local storage to avoid repeated API calls."""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df.to_csv(filename)
        print(f"💾 Data successfully saved to: {filename}")

# --- TEST THE INGESTION ENGINE ---
if __name__ == "__main__":
    engine = CryptoDataIngestion(exchange_id='binance')
    
    # Let's download 1 Hour data for BTC from the start of the 2024 Bull Run to present
    symbol = 'BTC/USDT'
    timeframe = '1h'
    start_date = '2024-01-01T00:00:00Z'
    
    historical_df = engine.fetch_historical_candles(symbol, timeframe, start_date)
    
    print("\n--- INGESTION COMPLETE ---")
    print(f"Total Candles Extracted: {len(historical_df)}")
    print("\nFirst 3 Rows:")
    print(historical_df.head(3))
    print("\nLast 3 Rows:")
    print(historical_df.tail(3))
    
    # Save to our local data folder
    engine.save_to_csv(historical_df, f"data/{symbol.replace('/', '_')}_{timeframe}.csv")
