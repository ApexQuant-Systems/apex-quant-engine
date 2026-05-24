import pandas as pd
import pandas_ta as ta
import numpy as np

class RegimeEngine:
    def __init__(self, adx_period=14, adx_threshold=25):
        # ADX > 25 indicates a strong trending regime.
        # ADX < 25 indicates a choppy, consolidating regime.
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def classify_market_regime(self, df):
        """
        Ingests OHLCV data, calculates ADX, and flags the current market regime.
        """
        # Calculate ADX using pandas_ta
        adx_data = df.ta.adx(length=self.adx_period)
        
        # Merge the ADX values back into our main dataframe
        # pandas_ta returns ADX, DMP (Positive Directional Indicator), and DMN
        adx_column = f"ADX_{self.adx_period}"
        df[adx_column] = adx_data[adx_column]
        
        # Create the mathematical boolean flag for Execution
        df['Regime_Status'] = np.where(df[adx_column] >= self.adx_threshold, 'EXPANSION', 'CONSOLIDATION')
        df['Execution_Unlocked'] = np.where(df['Regime_Status'] == 'EXPANSION', True, False)

        return df

# --- TEST THE ENGINE ---
if __name__ == "__main__":
    print("INITIALIZING REGIME CLASSIFICATION ENGINE...")
    
    # Generating 20 days of mock volatile data to calculate a 14-period ADX
    np.random.seed(42)
    mock_data = {
        'high': np.random.uniform(65000, 67000, 20),
        'low': np.random.uniform(63000, 64999, 20),
        'close': np.random.uniform(64000, 66000, 20)
    }
    df = pd.DataFrame(mock_data)
    
    engine = RegimeEngine()
    processed_data = engine.classify_market_regime(df)
    
    print("\nRecent Market Regime Analysis:")
    # Print the last 3 rows to see the current regime state
    print(processed_data[['close', f'ADX_{engine.adx_period}', 'Regime_Status', 'Execution_Unlocked']].tail(3))
