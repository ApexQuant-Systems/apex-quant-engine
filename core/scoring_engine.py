import pandas as pd
import pandas_ta as ta
import numpy as np

class ScoringEngine:
    def __init__(self):
        self.minimum_authorization_score = 40

    def score_displacement(self, df):
        df['body_size'] = abs(df['close'] - df['open'])
        df['avg_body_size'] = df['body_size'].rolling(window=20).mean()
        df['avg_volume'] = df['volume'].rolling(window=20).mean()

        df.ta.ema(length=200, append=True)
        df['Above_200_EMA'] = df['close'] > df['EMA_200']
        
        df['setup_score'] = 0

        # Scoring Matrix
        df.loc[df['volume'] > (df['avg_volume'] * 1.2), 'setup_score'] += 30
        df.loc[df['body_size'] > (df['avg_body_size'] * 1.2), 'setup_score'] += 30

        # --- REGIME INTELLIGENCE INTEGRATION ---
        # If the ADX trend is strong (Execution_Unlocked == True), give a 20 point bonus.
        # If it is FALSE, the system will find it much harder to reach the 40-point threshold.
        if 'Execution_Unlocked' in df.columns:
            df.loc[df['Execution_Unlocked'] == True, 'setup_score'] += 20

        df['Trade_Authorized'] = np.where(
            (df['setup_score'] >= self.minimum_authorization_score) & 
            (df['Above_200_EMA'] == True) &
            (df.get('Recent_Bullish_Sweep', False) == True), 
            True, 
            False
        )
        return df
