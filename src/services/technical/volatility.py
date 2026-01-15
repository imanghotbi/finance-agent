import talib
import numpy as np
from src.services.technical.base import BaseTechnicalAnalyzer


class VolatilityAnalyzer(BaseTechnicalAnalyzer):
    
    def _determine_regime(self, slope, position_pct):
        if slope > 0.05 and position_pct > 70: return "EXPANSION"
        elif slope < -0.05 and position_pct < 30: return "COMPRESSION"
        elif slope > 0: return "RISING_VOL"
        elif slope < 0: return "COOLING_OFF"
        else: return "NEUTRAL"

    def analyze(self, current_price=None):
        if len(self.df) < 50: raise ValueError("Insufficient data points")
        
        close, high, low = self.df['close'], self.df['high'], self.df['low']
        
        # Calculations
        keltner_mult = 2.0
        ema_16 = talib.EMA(close, timeperiod=16)
        atr_16 = talib.ATR(high, low, close, timeperiod=16)
        k_upper = ema_16 + (atr_16 * keltner_mult)
        k_lower = ema_16 - (atr_16 * keltner_mult)
        keltner_width = k_upper - k_lower
        
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        bb_width = bb_upper - bb_lower
        
        log_returns = np.log(close / close.shift(1))
        log_ret_std = log_returns.rolling(window=20).std()
        hist_vol = log_returns.rolling(window=30).std() * np.sqrt(252)

        # Metrics
        k_slope, k_r2 = self._calc_slope(keltner_width, 15)
        k_pct = self._calc_percentile(keltner_width, 120)
        
        b_slope, b_r2 = self._calc_slope(bb_width, 15)
        b_pct = self._calc_percentile(bb_width, 120)
        
        l_slope, l_r2 = self._calc_slope(log_ret_std, 10)
        l_pct = self._calc_percentile(log_ret_std, 120)
        
        h_slope, h_r2 = self._calc_slope(hist_vol, 10)
        h_pct = self._calc_percentile(hist_vol, 120)

        is_squeeze = (bb_upper.iloc[-1] < k_upper.iloc[-1]) and (bb_lower.iloc[-1] > k_lower.iloc[-1])
        main_driver = "bollinger_20" if b_r2 > k_r2 else "keltner_16"

        result = {
            "meta": self._build_meta(current_price),
            "volatility_signals": {
                "keltner_16": {
                    "value": round(keltner_width.iloc[-1], 2),
                    "slope": round(k_slope, 4),
                    "slope_horizon_bars": 15,
                    "trend_quality_r2": round(k_r2, 2),
                    "position_pct": round(k_pct, 1),
                    "regime": self._determine_regime(k_slope, k_pct)
                },
                "bollinger_20": {
                    "upper_band": round(bb_upper.iloc[-1], 2),
                    "lower_band": round(bb_lower.iloc[-1], 2),
                    "middle_band": round(bb_middle.iloc[-1], 2),
                    "band_width": round(bb_width.iloc[-1], 2),
                    "slope": round(b_slope, 4),
                    "slope_horizon_bars": 15,
                    "trend_quality_r2": round(b_r2, 2),
                    "position_pct": round(b_pct, 1),
                    "regime": self._determine_regime(b_slope, b_pct)
                },
                "log_return_std": {
                    "final": round(log_ret_std.iloc[-1], 4),
                    "slope": round(l_slope, 4),
                    "slope_horizon_bars": 10,
                    "trend_quality_r2": round(l_r2, 2),
                    "position_pct": round(l_pct, 1),
                    "regime": self._determine_regime(l_slope, l_pct)
                },
                "historical_volatility": {
                    "final": round(hist_vol.iloc[-1], 4),
                    "slope": round(h_slope, 4),
                    "slope_horizon_bars": 10,
                    "trend_quality_r2": round(h_r2, 2),
                    "position_pct": round(h_pct, 1),
                    "regime": self._determine_regime(h_slope, h_pct)
                }
            },
            "signal_synthesis": {
                "is_squeeze": bool(is_squeeze),
                "regime": "COMPRESSION" if is_squeeze else "EXPANSION",
                "main_driver": main_driver
            }
        }
        return result
    

