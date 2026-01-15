import talib 
import numpy as np

from src.services.technical.base import BaseTechnicalAnalyzer

class TrendAnalyzer(BaseTechnicalAnalyzer):
    def __init__(self, data_source, symbol="UNKNOWN"):
        super().__init__(data_source, symbol)
        # Pre-calc specific to Trend agent
        self.df['atr_14'] = talib.ATR(self.df['high'], self.df['low'], self.df['close'], timeperiod=14)

    def _analyze_swings(self, lookback=5, atr_threshold=0.5):
        highs, lows = self.df['high'].values, self.df['low'].values
        atr = self.df['atr_14'].values
        swings_h, swings_l = [], []
        
        for i in range(lookback, len(highs) - lookback):
            if highs[i] == max(highs[i-lookback:i+lookback+1]):
                if (highs[i] - np.mean(lows[i-lookback:i])) > (atr[i] * atr_threshold):
                    swings_h.append((i, highs[i]))
            if lows[i] == min(lows[i-lookback:i+lookback+1]):
                if (np.mean(highs[i-lookback:i]) - lows[i]) > (atr[i] * atr_threshold):
                    swings_l.append((i, lows[i]))
                
        structure = {"hh": None, "hl": None, "lh": None, "ll": None, "regime": "neutral"}
        
        if len(swings_h) >= 2:
            h_type = "hh" if swings_h[-1][1] > swings_h[-2][1] else "lh"
            structure[h_type] = {
                "cur_value": float(swings_h[-1][1]), "prev_value": float(swings_h[-2][1]),
                "distance_pct": round(((self.df['close'].iloc[-1] - swings_h[-1][1]) / swings_h[-1][1]) * 100, 2)
            }
        if len(swings_l) >= 2:
            l_type = "hl" if swings_l[-1][1] > swings_l[-2][1] else "ll"
            structure[l_type] = {
                "cur_value": float(swings_l[-1][1]), "prev_value": float(swings_l[-2][1]),
                "distance_pct": round(((self.df['close'].iloc[-1] - swings_l[-1][1]) / swings_l[-1][1]) * 100, 2)
            }
            
        if structure['hh'] and structure['hl']: structure['regime'] = "uptrend"
        elif structure['lh'] and structure['ll']: structure['regime'] = "downtrend"
        elif structure['hh'] and structure['ll']: structure['regime'] = "expanding_volatility"
        else: structure['regime'] = "consolidation"
        
        last_pivot_idx = max((swings_h[-1][0] if swings_h else 0), (swings_l[-1][0] if swings_l else 0))
        structure['bars_since'] = len(highs) - last_pivot_idx
        return structure

    def analyze(self, current_price=None):
        close, high, low, atr = self.df['close'], self.df['high'], self.df['low'], self.df['atr_14']
        
        # Trend Identity
        ema_config = {10: 5, 50: 14, 100: 30}
        trend_data = {}
        for period, horizon in ema_config.items():
            ema = talib.EMA(close, timeperiod=period)
            slope, r2 = self._calc_slope(ema, horizon)
            slope_norm = slope / atr.iloc[-1]
            
            regime = "flat"
            if slope_norm > 0.5: regime = "surging"
            elif slope_norm > 0.1: regime = "rising"
            elif slope_norm < -0.5: regime = "crashing"
            elif slope_norm < -0.1: regime = "falling"
            
            trend_data[f"ema_{period}"] = {
                "value": round(ema.iloc[-1], 2), "slope_atr_norm": round(slope_norm, 2),
                "slope_horizon_bars": horizon,
                "price_distance_pct": round(((close.iloc[-1] - ema.iloc[-1])/ema.iloc[-1])*100, 2),
                "regime": regime, "trend_quality_r2": round(r2, 2),
                "slope_strength": self._get_strength_r2(r2)
            }

        # Momentum
        adx = talib.ADX(high, low, close, timeperiod=14)
        adx_slope, _ = self._calc_slope(adx, 14)
        mom_regime = "strong_trend" if adx.iloc[-1] > 50 else "trending" if adx.iloc[-1] > 25 else "ranging"
        
        # Ichimoku
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1])
        cloud_bottom = min(senkou_a.iloc[-1], senkou_b.iloc[-1])
        ichi_regime = "bullish" if close.iloc[-1] > cloud_top else "bearish" if close.iloc[-1] < cloud_bottom else "neutral"

        # Geometry
        geo = self._analyze_swings()

        # Volatility Risk
        atr_slope = (atr.iloc[-1] - atr.iloc[-14]) / atr.iloc[-14]

        result = {
            "meta": self._build_meta(current_price),
            "trend_identity": trend_data,
            "momentum_strength": {
                "adx_14": {
                    "value": round(adx.iloc[-1], 2), "slope": round(adx_slope, 2),
                    "slope_horizon_bars": 14, "regime": mom_regime,
                    "trend_quality": "improving" if adx_slope > 0 else "decaying"
                }
            },
            "ichimoku_structure": {
                "parameters": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
                "features": {
                    "price_vs_cloud_pct": round(((close.iloc[-1] - cloud_top)/cloud_top)*100, 2),
                    "cloud_thickness_pct": round(((abs(senkou_a.iloc[-1] - senkou_b.iloc[-1]))/senkou_b.iloc[-1])*100, 2),
                    "cloud_slope_atr_norm": round((senkou_b.iloc[-1] - senkou_b.iloc[-26]) / atr.iloc[-1], 2),
                    "cloud_slope_horizon_bars": 26
                },
                "regime": ichi_regime,
                "stability": "stable" if abs(senkou_a.iloc[-1] - senkou_b.iloc[-1]) > (atr.iloc[-1] * 0.5) else "volatile"
            },
            "market_geometry": {
                "levels": {k: geo.get(k) for k in ["hh", "hl", "lh", "ll"]},
                "regime": geo['regime'],
                "integrity": "intact" if geo['regime'] in ["uptrend", "downtrend"] else "fragile",
                "bars_since_last_structure_break": geo['bars_since'],
                "calculation_logic": {"swing_threshold_atr": 1.0}
            },
            "volatility_risk": {
                "atr_14": {
                    "value": round(atr.iloc[-1], 2),
                    "percent": round((atr.iloc[-1] / close.iloc[-1]) * 100, 2),
                    "slope_atr_norm": round(atr_slope, 2),
                    "regime": "high" if (atr.iloc[-1] > atr.mean()) else "low",
                    "validity_horizon_bars": 7
                }
            }
        }
        return result