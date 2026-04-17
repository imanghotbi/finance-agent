import numpy as np
import talib

from src.services.technical.base import BaseTechnicalAnalyzer


class TrendAnalyzer(BaseTechnicalAnalyzer):
    def __init__(self, data_source, symbol="UNKNOWN"):
        super().__init__(data_source, symbol)
        self.df["atr_14"] = talib.ATR(self.df["high"], self.df["low"], self.df["close"], timeperiod=14)

    def _analyze_swings(self, lookback=5, atr_threshold=0.75):
        highs = self.df["high"].values
        lows = self.df["low"].values
        atr = self.df["atr_14"].values
        swings_h = []
        swings_l = []

        for i in range(lookback, len(highs) - lookback):
            if np.isnan(atr[i]) or atr[i] <= 0:
                continue
            is_confirmed_high = all(highs[i] > highs[i - x] for x in range(1, lookback + 1)) and all(
                highs[i] > highs[i + x] for x in range(1, lookback + 1)
            )
            is_confirmed_low = all(lows[i] < lows[i - x] for x in range(1, lookback + 1)) and all(
                lows[i] < lows[i + x] for x in range(1, lookback + 1)
            )

            if is_confirmed_high and (highs[i] - np.mean(lows[i - lookback : i])) > (atr[i] * atr_threshold):
                swings_h.append((i, highs[i]))
            if is_confirmed_low and (np.mean(highs[i - lookback : i]) - lows[i]) > (atr[i] * atr_threshold):
                swings_l.append((i, lows[i]))

        structure = {"hh": None, "hl": None, "lh": None, "ll": None, "regime": "neutral"}
        if len(swings_h) >= 2:
            h_type = "hh" if swings_h[-1][1] > swings_h[-2][1] else "lh"
            structure[h_type] = {
                "cur_value": float(swings_h[-1][1]),
                "prev_value": float(swings_h[-2][1]),
                "distance_pct": self._safe_pct_distance(swings_h[-1][1], float(self.df["close"].iloc[-1])),
            }
        if len(swings_l) >= 2:
            l_type = "hl" if swings_l[-1][1] > swings_l[-2][1] else "ll"
            structure[l_type] = {
                "cur_value": float(swings_l[-1][1]),
                "prev_value": float(swings_l[-2][1]),
                "distance_pct": self._safe_pct_distance(swings_l[-1][1], float(self.df["close"].iloc[-1])),
            }

        if structure["hh"] and structure["hl"]:
            structure["regime"] = "uptrend"
        elif structure["lh"] and structure["ll"]:
            structure["regime"] = "downtrend"
        elif structure["hh"] and structure["ll"]:
            structure["regime"] = "expanding_volatility"
        else:
            structure["regime"] = "consolidation"

        last_pivot_idx = max((swings_h[-1][0] if swings_h else 0), (swings_l[-1][0] if swings_l else 0))
        pivot_count = len(swings_h) + len(swings_l)
        structure["bars_since"] = len(highs) - last_pivot_idx
        structure["confirmed_pivot_count"] = pivot_count
        structure["confidence"] = self._score_confidence(
            data_quality=min(1.0, len(self.df) / 100),
            agreement=1.0 if pivot_count >= 4 else 0.6 if pivot_count >= 2 else 0.2,
            stability=0.9 if structure["regime"] in {"uptrend", "downtrend"} else 0.5,
        )
        return structure

    def analyze(self, current_price=None):
        close = self.df["close"]
        high = self.df["high"]
        low = self.df["low"]
        atr = self.df["atr_14"]

        atr_last = atr.dropna().iloc[-1] if not atr.dropna().empty else None
        atr_ref = atr_last if atr_last and atr_last > 1e-9 else max(float(close.iloc[-1]) * 0.01, 1e-9)

        ema_config = {10: 5, 50: 14, 100: 30}
        ema_last_values = {}
        trend_data = {}
        for period, horizon in ema_config.items():
            ema = talib.EMA(close, timeperiod=period)
            slope, r2 = self._calc_slope(ema, horizon)
            ema_value = None
            if hasattr(ema, "iloc"):
                ema_valid = ema.dropna()
                ema_value = float(ema_valid.iloc[-1]) if not ema_valid.empty else None
            slope_norm = None if slope is None else slope / atr_ref

            regime = "insufficient_data"
            if slope_norm is not None:
                regime = "flat"
                if slope_norm > 0.5:
                    regime = "surging"
                elif slope_norm > 0.1:
                    regime = "rising"
                elif slope_norm < -0.5:
                    regime = "crashing"
                elif slope_norm < -0.1:
                    regime = "falling"

            ema_last_values[period] = ema_value
            trend_data[f"ema_{period}"] = {
                "value": None if ema_value is None else round(ema_value, 2),
                "slope_atr_norm": None if slope_norm is None else round(slope_norm, 2),
                "slope_horizon_bars": horizon,
                "price_distance_pct": None if ema_value in (None, 0) else round(((close.iloc[-1] - ema_value) / ema_value) * 100, 2),
                "regime": regime,
                "trend_quality_r2": None if r2 is None else round(r2, 2),
                "slope_strength": self._get_strength_r2(r2),
                "confidence": self._score_confidence(
                    data_quality=self._data_quality_score(ema, horizon),
                    trend_quality=r2,
                    stability=0.9 if slope_norm is not None else 0.0,
                ),
            }

        adx = talib.ADX(high, low, close, timeperiod=14)
        adx_slope, adx_r2 = self._calc_slope(adx, 14)
        adx_valid = adx.dropna()
        adx_last = float(adx_valid.iloc[-1]) if not adx_valid.empty else None
        mom_regime = "insufficient_data"
        if adx_last is not None:
            mom_regime = "strong_trend" if adx_last > 50 else "trending" if adx_last > 25 else "ranging"

        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        senkou_a_last = senkou_a.dropna().iloc[-1] if not senkou_a.dropna().empty else None
        senkou_b_last = senkou_b.dropna().iloc[-1] if not senkou_b.dropna().empty else None

        cloud_top = None
        cloud_bottom = None
        ichi_regime = "insufficient_data"
        price_vs_cloud_pct = None
        cloud_thickness_pct = None
        cloud_slope_atr_norm = None
        if senkou_a_last is not None and senkou_b_last is not None:
            cloud_top = max(senkou_a_last, senkou_b_last)
            cloud_bottom = min(senkou_a_last, senkou_b_last)
            ichi_regime = "bullish" if close.iloc[-1] > cloud_top else "bearish" if close.iloc[-1] < cloud_bottom else "neutral"
            price_vs_cloud_pct = round(((close.iloc[-1] - cloud_top) / cloud_top) * 100, 2) if cloud_top else None
            cloud_thickness_pct = round((abs(senkou_a_last - senkou_b_last) / max(abs(senkou_b_last), 1e-9)) * 100, 2)
            if len(senkou_b.dropna()) >= 26:
                cloud_slope_atr_norm = round((senkou_b.dropna().iloc[-1] - senkou_b.dropna().iloc[-26]) / atr_ref, 2)

        geo = self._analyze_swings()
        atr_slope = None
        if len(atr.dropna()) >= 14:
            past_atr = atr.dropna().iloc[-14]
            if past_atr not in (None, 0):
                atr_slope = (atr.dropna().iloc[-1] - past_atr) / past_atr

        ema_stack_score = 0.5
        if all(ema_last_values.get(p) is not None for p in (10, 50, 100)):
            if ema_last_values[10] > ema_last_values[50] > ema_last_values[100]:
                ema_stack_score = 1.0
            elif ema_last_values[10] < ema_last_values[50] < ema_last_values[100]:
                ema_stack_score = 0.0

        adx_score = min((adx_last or 0) / 50, 1.0) if adx_last is not None else 0.0
        geometry_score = 1.0 if geo["regime"] == "uptrend" else 0.0 if geo["regime"] == "downtrend" else 0.5
        trend_score = round((0.45 * ema_stack_score) + (0.3 * geometry_score) + (0.25 * adx_score), 2)
        trend_bias = "bullish" if trend_score >= 0.65 else "bearish" if trend_score <= 0.35 else "neutral"

        result = {
            "meta": self._build_meta(current_price),
            "trend_identity": trend_data,
            "momentum_strength": {
                "adx_14": {
                    "value": None if adx_last is None else round(adx_last, 2),
                    "slope": None if adx_slope is None else round(adx_slope, 2),
                    "slope_horizon_bars": 14,
                    "regime": mom_regime,
                    "trend_quality": "improving" if (adx_slope or 0) > 0 else "decaying",
                    "confidence": self._score_confidence(
                        data_quality=self._data_quality_score(adx, 14),
                        trend_quality=adx_r2,
                        stability=0.85 if adx_last is not None else 0.0,
                    ),
                }
            },
            "ichimoku_structure": {
                "parameters": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
                "features": {
                    "price_vs_cloud_pct": price_vs_cloud_pct,
                    "cloud_thickness_pct": cloud_thickness_pct,
                    "cloud_slope_atr_norm": cloud_slope_atr_norm,
                    "cloud_slope_horizon_bars": 26,
                },
                "regime": ichi_regime,
                "stability": "stable" if cloud_thickness_pct is not None and cloud_thickness_pct > 0.5 else "volatile",
                "confidence": self._score_confidence(
                    data_quality=min(self._data_quality_score(senkou_a, 26), self._data_quality_score(senkou_b, 26)),
                    agreement=1.0 if ichi_regime in {"bullish", "bearish"} else 0.5,
                ),
            },
            "market_geometry": {
                "levels": {k: geo.get(k) for k in ["hh", "hl", "lh", "ll"]},
                "regime": geo["regime"],
                "integrity": "intact" if geo["regime"] in ["uptrend", "downtrend"] else "fragile",
                "bars_since_last_structure_break": geo["bars_since"],
                "calculation_logic": {"swing_threshold_atr": 0.75, "confirmed_pivots_only": True},
                "confidence": geo["confidence"],
            },
            "volatility_risk": {
                "atr_14": {
                    "value": None if atr_last is None else round(float(atr_last), 2),
                    "percent": None if atr_last is None else round((atr_last / close.iloc[-1]) * 100, 2),
                    "slope_atr_norm": None if atr_slope is None else round(float(atr_slope), 2),
                    "regime": "high" if atr_last is not None and atr_last > atr.dropna().mean() else "low",
                    "validity_horizon_bars": 7,
                }
            },
            "trend_score": {
                "score": trend_score,
                "bias": trend_bias,
                "confidence": self._score_confidence(
                    data_quality=min(1.0, len(self.df) / 100),
                    agreement=max(ema_stack_score, geometry_score),
                    stability=adx_score,
                ),
            },
        }
        return result
