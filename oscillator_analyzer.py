from base_analyzer import BaseTechnicalAnalyzer
import talib
import pandas as pd


class OscillatorAnalyzer(BaseTechnicalAnalyzer):
    
    def analyze(self, current_price=None):
        # 1. Technical Indicators
        c = self.df['close'].values.astype(float)
        h = self.df['high'].values.astype(float)
        l = self.df['low'].values.astype(float)
        
        rsi = talib.RSI(c, timeperiod=14)
        adx = talib.ADX(h, l, c, timeperiod=14)
        macd, macd_sig, macd_hist = talib.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)

        # Scalars
        last_rsi, last_adx, last_hist = rsi[-1], adx[-1], macd_hist[-1]
        
        # 2. Slopes (Using Base Class)
        rsi_slope, rsi_r2 = self._calc_slope(pd.Series(rsi), 5)
        adx_slope, adx_r2 = self._calc_slope(pd.Series(adx), 7)
        hist_slope, hist_r2 = self._calc_slope(pd.Series(macd_hist), 4)

        # 3. Regime Logic
        state = "indeterminate_transition"
        direction = "bullish" if last_hist > 0 else "bearish"
        
        if last_adx < 20 and (40 <= last_rsi <= 60): state = "choppy_noise"
        elif last_adx > 40 and last_hist > 0 and last_rsi > 75: state = "bullish_climax"
        elif last_adx > 40 and last_hist < 0 and last_rsi < 25: state = "bearish_capitulation"
        elif last_adx > 25 and last_hist > 0 and (50 <= last_rsi <= 75): state = "strong_bull_trend"
        elif last_adx > 25 and last_hist < 0 and (25 <= last_rsi <= 50): state = "strong_bear_trend"
        elif last_adx < 25 and last_hist > 0 and last_rsi > 60: state = "weak_bullish"
        elif last_adx < 25 and last_hist < 0 and last_rsi < 40: state = "weak_bearish"

        regime_factors = {
            "trend_strength": "high" if last_adx > 25 else "low",
            "direction_bias": direction,
            "extension_risk": "high" if last_rsi > 70 or last_rsi < 30 else "moderate"
        }

        # Helper States
        def get_rsi_state(val, slope):
            if val > 70: return "overbought"
            if val < 30: return "oversold"
            return "bullish_accelerating" if slope > 0 else "bearish_decelerating"

        def get_macd_state(hist, slope):
            if hist > 0 and slope > 0: return "positive_momentum_expanding"
            if hist > 0 and slope < 0: return "positive_momentum_waning"
            if hist < 0 and slope < 0: return "negative_momentum_expanding"
            return "negative_momentum_waning"

        result = {
            "meta": self._build_meta(current_price),
            "indicators": {
                "rsi_14": {
                    "value": round(float(last_rsi), 1),
                    "slope_horizon_bars": 5,
                    "slope": round(float(rsi_slope), 2),
                    "trend_quality_r2": round(float(rsi_r2), 2),
                    "strength_r2": self._get_strength_r2(rsi_r2),
                    "regime": get_rsi_state(last_rsi, rsi_slope)
                },
                "adx_14": {
                    "value": round(float(last_adx), 1),
                    "slope_horizon_bars": 7,
                    "slope": round(float(adx_slope), 2),
                    "trend_quality_r2": round(float(adx_r2), 2),
                    "strength_r2": self._get_strength_r2(adx_r2),
                    "state": "trending" if last_adx > 25 else "ranging"
                },
                "macd_26": {
                    "histogram_value": round(float(last_hist), 2),
                    "slope_horizon_bars": 4,
                    "histogram_slope": round(float(hist_slope), 2),
                    "trend_quality_r2": round(float(hist_r2), 2),
                    "strength_r2": self._get_strength_r2(hist_r2),
                    "state": get_macd_state(last_hist, hist_slope)
                }
            },
            "market_regime": {
                "state": state,
                "factors": regime_factors
            }
        }
        return result
    

