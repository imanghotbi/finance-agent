import pandas as pd
import numpy as np
import io
from scipy import stats
from abc import ABC, abstractmethod

class BaseTechnicalAnalyzer(ABC):
    """
    Parent class for all technical analysis agents.
    Handles data ingestion, standardization, and common math operations.
    """
    def __init__(self, data_source, symbol="UNKNOWN"):
        self.symbol = symbol
        self.df = self._load_data(data_source)
        self._validate_data()

    def _load_data(self, source):
        """Unified data loader for CSV string, file path, or DataFrame."""
        if isinstance(source, pd.DataFrame):
            df = source.copy()
        elif isinstance(source, str):
            # Check if it's a file path or CSV string
            try:
                if source.endswith('.csv'):
                    df = pd.read_csv(source)
                else:
                    df = pd.read_csv(io.StringIO(source))
            except Exception:
                # Fallback for raw strings
                df = pd.read_csv(io.StringIO(source))
        else:
            raise ValueError("Unsupported data source format.")

        # Standardize columns
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Map common variations to standard OHLCV
        rename_map = {
            'date_time': 'date', 'timestamp': 'date',
            'real_close_price': 'close', 'real_close': 'close',
            'high_price': 'high', 'low_price': 'low', 
            'open_price': 'open', 'vol': 'volume'
        }
        df.rename(columns=rename_map, inplace=True)

        # Standardize Date Index
        if 'date' in df.columns:
            df.set_index('date', inplace=True)
        
        df.sort_index(inplace=True)
        return df

    def _validate_data(self):
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            raise ValueError(f"Data missing required columns: {missing}")

    def _calc_slope(self, series, horizon):
        """
        Returns (slope, r_squared) using linear regression.
        Commonly used by Oscillator, Volume, and Trend agents.
        """
        if len(series) < horizon:
            return 0.0, 0.0
        
        # Handle pandas Series or numpy array
        if isinstance(series, pd.Series):
            y = series.iloc[-horizon:].values
        else:
            y = series[-horizon:]
            
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Returns 0 if calculation fails (NaNs)
        if np.isnan(slope): return 0.0, 0.0
        return slope, r_value**2

    def _get_strength_r2(self, r2):
        """Standardized R2 strength labeling."""
        if r2 > 0.8: return "very_strong"
        if r2 > 0.5: return "strong"
        if r2 > 0.2: return "moderate"
        return "weak"

    def _calc_percentile(self, series, window=200):
        """Calculates percentile rank of the last value against a window."""
        if len(series) < 1: return 0.0
        # If series is pandas, take iloc, else slice
        recent = series.iloc[-window:] if hasattr(series, 'iloc') else series[-window:]
        current = series.iloc[-1] if hasattr(series, 'iloc') else series[-1]
        return stats.percentileofscore(recent, current)

    def _build_meta(self, current_price=None):
        """Standardized Meta Header Generation."""
        last_close = self.df['close'].iloc[-1]
        cur_price = current_price if current_price else last_close
        return {
            "symbol": self.symbol,
            "timestamp": self.df.index[-1].strftime('%Y-%m-%d') if hasattr(self.df.index, 'strftime') else str(self.df.index[-1]),
            "timeframe": "1D",
            "price": {
                "close": round(float(last_close), 2),
                "current_price": round(float(cur_price), 2)
            }
        }

    @abstractmethod
    def analyze(self, current_price=None):
        pass