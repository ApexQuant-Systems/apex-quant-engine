import pandas as pd
import pandas_ta as ta
import numpy as np

class ScoringEngine:
    def __init__(self):
        # Sensitivity Adjustment: Lowered from 80 to 70 to allow "High Quality" vs "Perfect" setups
        self.minimum_authorization_score = 70

    def score_displacement(self, df):
        """
        Grades structural quality and applies the Macro Directional Filter (200 EMA).
        """
        # Calculate body size and rolling averages for volume/body
        df['body_size'] = abs(df['close'] - df['open'])
        df['avg_body_size'] = df['body_size'].rolling(window=20).mean()
        df['avg_volume'] = df['volume'].rolling(window=20).mean()

        # --- MACRO DIRECTIONAL FILTER (200 EMA) ---
        df.ta.ema(length=200, append=True)
        df['Above_200_EMA'] = df['close'] > df['EMA_200']

        # Initialize the score column
        df['setup_score'] = 0

        # --- SCORING MATRIX ---
        # Criteria 1: Volume Expansion (Max 40 points)
        # Even if volume is just 1.5x average, we award 20 pts. 2x gets 40.
        df.loc[df['volume'] > (df['avg_volume'] * 2.0), 'setup_score'] += 40
        df.loc[(df['volume'] > (df['avg_volume'] * 1.5)) & (df['volume'] <= (df['avg_volume'] * 2.0)), 'setup_score'] += 20

        # Criteria 2: Body Displacement Expansion (Max 40 points)
        df.loc[df['body_size'] > (df['avg_body_size'] * 2.0), 'setup_score'] += 40
        df.loc[(df['body_size'] > (df['avg_body_size'] * 1.5)) & (df['body_size'] <= (df['avg_body_size'] * 2.0)), 'setup_score'] += 20

        # Criteria 3: Regime Bonus (Max 20 points)
        # Assuming Regime Classifier has been run
        if 'Execution_Unlocked' in df.columns:
            df.loc[df['Execution_Unlocked'] == True, 'setup_score'] += 20

        # --- FINAL AUTHORIZATION GATE ---
        # 1. Score >= 70 (Relaxed from 80)
        # 2. Above 200 EMA (Macro Trend)
        # 3. Recent_Bullish_Sweep (3-hour memory liquidity grab)
        
        df['Trade_Authorized'] = np.where(
            (df['setup_score'] >= self.minimum_authorization_score) & 
            (df['Above_200_EMA'] == True) &
            (df.get('Recent_Bullish_Sweep', False) == True), 
            True, 
            False
        )

        return df
