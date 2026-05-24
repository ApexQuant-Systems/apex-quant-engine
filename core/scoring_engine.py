import pandas as pd
import pandas_ta as ta
import numpy as np

class ScoringEngine:
    def __init__(self):
        # Minimum score required to authorize a trade
        self.minimum_authorization_score = 80

    def score_displacement(self, df):
        """
        Grades structural quality and applies the Macro Directional Filter (200 EMA).
        """
        # Calculate the absolute size of the candle body (Close - Open)
        df['body_size'] = abs(df['close'] - df['open'])
        
        # Calculate rolling averages for volume and body size
        df['avg_body_size'] = df['body_size'].rolling(window=20).mean()
        df['avg_volume'] = df['volume'].rolling(window=20).mean()

        # --- NEW: MACRO DIRECTIONAL FILTER (200 EMA) ---
        # Calculate the 200-period Exponential Moving Average
        df.ta.ema(length=200, append=True)
        ema_column = 'EMA_200'
        
        # Determine current trend relationship
        # True if price is above 200 EMA (Bullish Macro), False if below (Bearish Macro)
        df['Above_200_EMA'] = df['close'] > df[ema_column]

        # Initialize the score column
        df['setup_score'] = 0

        # --- SCORING MATRIX ---
        
        # Criteria 1: Volume Expansion (Max 40 points)
        df.loc[df['volume'] > (df['avg_volume'] * 2.0), 'setup_score'] += 40
        df.loc[(df['volume'] > (df['avg_volume'] * 1.5)) & (df['volume'] <= (df['avg_volume'] * 2.0)), 'setup_score'] += 20

        # Criteria 2: Body Displacement Expansion (Max 40 points)
        df.loc[df['body_size'] > (df['avg_body_size'] * 2.0), 'setup_score'] += 40
        df.loc[(df['body_size'] > (df['avg_body_size'] * 1.5)) & (df['body_size'] <= (df['avg_body_size'] * 2.0)), 'setup_score'] += 20

        # Criteria 3: Regime Bonus (Max 20 points)
        if 'Execution_Unlocked' in df.columns:
            df.loc[df['Execution_Unlocked'] == True, 'setup_score'] += 20

        # --- FINAL AUTHORIZATION GATE ---
        # We now require the score to be >= 80 AND the price must be above the 200 EMA for LONGS
        # (Assuming our system is currently only looking for LONG setups as built in the truth machine)
        
        df['Trade_Authorized'] = np.where(
            (df['setup_score'] >= self.minimum_authorization_score) & 
            (df['Above_200_EMA'] == True), 
            True, 
            False
        )

        return df
