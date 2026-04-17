import pandas as pd
import talib

from src.services.technical.base import BaseTechnicalAnalyzer


class OscillatorAnalyzer(BaseTechnicalAnalyzer):
    def _find_divergence(self, price_series, indicator_series, lookback=10):
        price_slope, _ = self._calc_slope(price_series, lookback)
        indicator_slope, _ = self._calc_slope(indicator_series, lookback)
        if price_slope is None or indicator_slope is None:
            return "insufficient_data"
        if price_slope > 0 and indicator_slope < 0:
            return "bearish_divergence"
        if price_slope < 0 and indicator_slope > 0:
            return "bullish_divergence"
        return "none"

    def analyze(self, current_price=None):
        c = self.df["close"].values.astype(float)
        h = self.df["high"].values.astype(float)
        l = self.df["low"].values.astype(float)

        rsi = pd.Series(talib.RSI(c, timeperiod=14))
        adx = pd.Series(talib.ADX(h, l, c, timeperiod=14))
        _, _, macd_hist = talib.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)
        macd_hist = pd.Series(macd_hist)
        price_series = self.df["close"].reset_index(drop=True)

        last_rsi = rsi.dropna().iloc[-1] if not rsi.dropna().empty else None
        last_adx = adx.dropna().iloc[-1] if not adx.dropna().empty else None
        last_hist = macd_hist.dropna().iloc[-1] if not macd_hist.dropna().empty else None

        rsi_slope, rsi_r2 = self._calc_slope(rsi, 5)
        adx_slope, adx_r2 = self._calc_slope(adx, 7)
        hist_slope, hist_r2 = self._calc_slope(macd_hist, 4)

        state = "insufficient_data"
        direction = "neutral"
        if last_hist is not None:
            direction = "bullish" if last_hist > 0 else "bearish"
        if last_rsi is not None and last_adx is not None and last_hist is not None:
            state = "indeterminate_transition"
            if last_adx < 20 and 40 <= last_rsi <= 60:
                state = "choppy_noise"
            elif last_adx > 40 and last_hist > 0 and last_rsi > 75:
                state = "bullish_climax"
            elif last_adx > 40 and last_hist < 0 and last_rsi < 25:
                state = "bearish_capitulation"
            elif last_adx > 25 and last_hist > 0 and 55 <= last_rsi <= 75:
                state = "strong_bull_trend"
            elif last_adx > 25 and last_hist < 0 and 25 <= last_rsi <= 45:
                state = "strong_bear_trend"
            elif last_adx < 25 and last_hist > 0 and last_rsi > 55:
                state = "weak_bullish"
            elif last_adx < 25 and last_hist < 0 and last_rsi < 45:
                state = "weak_bearish"

        regime_factors = {
            "trend_strength": "high" if last_adx is not None and last_adx > 25 else "low",
            "direction_bias": direction,
            "extension_risk": "high" if last_rsi is not None and (last_rsi > 70 or last_rsi < 30) else "moderate",
        }

        def get_rsi_state(val, slope):
            if val is None:
                return "insufficient_data"
            if val > 70:
                return "overbought"
            if val < 30:
                return "oversold"
            if val >= 50 and (slope or 0) > 0:
                return "bullish_accelerating"
            if val < 50 and (slope or 0) > 0:
                return "recovering_below_midline"
            if val <= 50 and (slope or 0) < 0:
                return "bearish_weakening"
            return "softening_above_midline"

        def get_macd_state(hist, slope):
            if hist is None:
                return "insufficient_data"
            if hist > 0 and (slope or 0) > 0:
                return "positive_momentum_expanding"
            if hist > 0 and (slope or 0) < 0:
                return "positive_momentum_waning"
            if hist < 0 and (slope or 0) < 0:
                return "negative_momentum_expanding"
            return "negative_momentum_waning"

        rsi_divergence = self._find_divergence(price_series, rsi, lookback=10)
        macd_divergence = self._find_divergence(price_series, macd_hist, lookback=10)
        has_meaningful_divergence = any(
            signal in {"bullish_divergence", "bearish_divergence"}
            for signal in [rsi_divergence, macd_divergence]
        )

        bullish_votes = 0
        bearish_votes = 0
        if last_rsi is not None:
            bullish_votes += 1 if last_rsi > 55 else 0
            bearish_votes += 1 if last_rsi < 45 else 0
        if last_hist is not None:
            bullish_votes += 1 if last_hist > 0 else 0
            bearish_votes += 1 if last_hist < 0 else 0
        if last_adx is not None and last_adx > 25:
            bullish_votes += 0.5 if direction == "bullish" else 0
            bearish_votes += 0.5 if direction == "bearish" else 0

        oscillator_score_raw = (bullish_votes - bearish_votes + 3) / 6
        oscillator_score = round(max(0.0, min(1.0, oscillator_score_raw)), 2)

        result = {
            "meta": self._build_meta(current_price),
            "indicators": {
                "rsi_14": {
                    "value": None if last_rsi is None else round(float(last_rsi), 1),
                    "slope_horizon_bars": 5,
                    "slope": None if rsi_slope is None else round(float(rsi_slope), 2),
                    "trend_quality_r2": None if rsi_r2 is None else round(float(rsi_r2), 2),
                    "strength_r2": self._get_strength_r2(rsi_r2),
                    "regime": get_rsi_state(last_rsi, rsi_slope),
                    "confidence": self._score_confidence(
                        data_quality=self._data_quality_score(rsi, 5),
                        trend_quality=rsi_r2,
                    ),
                },
                "adx_14": {
                    "value": None if last_adx is None else round(float(last_adx), 1),
                    "slope_horizon_bars": 7,
                    "slope": None if adx_slope is None else round(float(adx_slope), 2),
                    "trend_quality_r2": None if adx_r2 is None else round(float(adx_r2), 2),
                    "strength_r2": self._get_strength_r2(adx_r2),
                    "state": "trending" if last_adx is not None and last_adx > 25 else "ranging",
                    "confidence": self._score_confidence(
                        data_quality=self._data_quality_score(adx, 7),
                        trend_quality=adx_r2,
                    ),
                },
                "macd_26": {
                    "histogram_value": None if last_hist is None else round(float(last_hist), 2),
                    "slope_horizon_bars": 4,
                    "histogram_slope": None if hist_slope is None else round(float(hist_slope), 2),
                    "trend_quality_r2": None if hist_r2 is None else round(float(hist_r2), 2),
                    "strength_r2": self._get_strength_r2(hist_r2),
                    "state": get_macd_state(last_hist, hist_slope),
                    "confidence": self._score_confidence(
                        data_quality=self._data_quality_score(macd_hist, 4),
                        trend_quality=hist_r2,
                    ),
                },
            },
            "divergence_checks": {
                "price_vs_rsi": rsi_divergence,
                "price_vs_macd_histogram": macd_divergence,
            },
            "market_regime": {
                "state": state,
                "factors": regime_factors,
            },
            "oscillator_score": {
                "score": oscillator_score,
                "bias": "bullish" if oscillator_score >= 0.6 else "bearish" if oscillator_score <= 0.4 else "neutral",
                "confidence": self._score_confidence(
                    data_quality=min(1.0, len(self.df) / 50),
                    agreement=1 - (0.35 if has_meaningful_divergence else 0.0),
                    stability=max(filter(lambda x: x is not None, [rsi_r2, adx_r2, hist_r2]), default=0.0),
                ),
            },
        }
        return result
