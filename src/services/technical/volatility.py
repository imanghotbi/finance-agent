import numpy as np
import talib

from src.services.technical.base import BaseTechnicalAnalyzer


class VolatilityAnalyzer(BaseTechnicalAnalyzer):
    def _determine_regime(self, slope, position_pct):
        if slope is None or position_pct is None:
            return "INSUFFICIENT_DATA"
        if slope > 0.05 and position_pct > 70:
            return "EXPANSION"
        if slope < -0.05 and position_pct < 30:
            return "COMPRESSION"
        if slope > 0:
            return "RISING_VOL"
        if slope < 0:
            return "COOLING_OFF"
        return "NEUTRAL"

    def _metric_payload(self, series, horizon, name, upper=None, middle=None, lower=None):
        latest = series.dropna().iloc[-1] if not series.dropna().empty else None
        slope, r2 = self._calc_slope(series, horizon)
        pct = self._calc_percentile(series, 120)
        regime = self._determine_regime(slope, pct)
        confidence = self._score_confidence(
            data_quality=self._data_quality_score(series, horizon),
            trend_quality=r2,
            stability=0.8 if latest is not None else 0.0,
        )

        payload = {
            "final": None if latest is None else round(float(latest), 4),
            "slope": None if slope is None else round(float(slope), 4),
            "slope_horizon_bars": horizon,
            "trend_quality_r2": None if r2 is None else round(float(r2), 2),
            "position_pct": None if pct is None else round(float(pct), 1),
            "regime": regime,
            "confidence": confidence,
            "risk_interpretation": (
                "absolute_volatility"
                if name in {"log_return_std", "historical_volatility"}
                else "envelope_width"
            ),
        }
        if upper is not None:
            payload["upper_band"] = round(float(upper), 2)
        if middle is not None:
            payload["middle_band"] = round(float(middle), 2)
        if lower is not None:
            payload["lower_band"] = round(float(lower), 2)
        return payload

    def analyze(self, current_price=None):
        if len(self.df) < 50:
            raise ValueError("Insufficient data points")

        close = self.df["close"]
        high = self.df["high"]
        low = self.df["low"]

        keltner_mult = 2.0
        ema_16 = talib.EMA(close, timeperiod=16)
        atr_16 = talib.ATR(high, low, close, timeperiod=16)
        k_upper = ema_16 + (atr_16 * keltner_mult)
        k_lower = ema_16 - (atr_16 * keltner_mult)
        keltner_width = k_upper - k_lower

        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        bb_upper = close.__class__(bb_upper, index=close.index)
        bb_middle = close.__class__(bb_middle, index=close.index)
        bb_lower = close.__class__(bb_lower, index=close.index)
        bb_width = bb_upper - bb_lower

        log_returns = np.log(close / close.shift(1))
        log_ret_std = log_returns.rolling(window=20, min_periods=15).std()
        hist_vol = log_returns.rolling(window=30, min_periods=20).std() * np.sqrt(252)

        k_payload = self._metric_payload(keltner_width, 15, "keltner_16")
        b_payload = self._metric_payload(
            bb_width,
            15,
            "bollinger_20",
            upper=bb_upper.dropna().iloc[-1] if not bb_upper.dropna().empty else None,
            middle=bb_middle.dropna().iloc[-1] if not bb_middle.dropna().empty else None,
            lower=bb_lower.dropna().iloc[-1] if not bb_lower.dropna().empty else None,
        )
        l_payload = self._metric_payload(log_ret_std, 10, "log_return_std")
        h_payload = self._metric_payload(hist_vol, 10, "historical_volatility")

        if not bb_upper.dropna().empty and not k_upper.dropna().empty and not bb_lower.dropna().empty and not k_lower.dropna().empty:
            is_squeeze = (bb_upper.dropna().iloc[-1] < k_upper.dropna().iloc[-1]) and (bb_lower.dropna().iloc[-1] > k_lower.dropna().iloc[-1])
        else:
            is_squeeze = False

        bb_position = b_payload["position_pct"]
        hv_position = h_payload["position_pct"]
        main_driver = "bollinger_20" if (b_payload["trend_quality_r2"] or 0) >= (k_payload["trend_quality_r2"] or 0) else "keltner_16"
        breakout_readiness = 0.0
        if is_squeeze:
            breakout_readiness = 0.7
            if bb_position is not None and bb_position < 25:
                breakout_readiness += 0.2
            if k_payload["slope"] is not None and k_payload["slope"] > 0:
                breakout_readiness += 0.1
        breakout_readiness = round(min(breakout_readiness, 1.0), 2)

        low_quality_penalty = 0.0
        if (b_payload["trend_quality_r2"] or 0) < 0.2 and (bb_position is not None and 30 <= bb_position <= 70):
            low_quality_penalty += 0.15
        if (h_payload["trend_quality_r2"] or 0) < 0.2 and (hv_position is not None and 30 <= hv_position <= 70):
            low_quality_penalty += 0.15

        synthesis_confidence = self._score_confidence(
            data_quality=min(1.0, len(self.df) / 120),
            agreement=1.0 if ((bb_position is not None and hv_position is not None and abs(bb_position - hv_position) <= 20)) else 0.5,
            stability=max(0.0, 1 - low_quality_penalty),
        )

        result = {
            "meta": self._build_meta(current_price),
            "volatility_signals": {
                "keltner_16": {
                    "value": k_payload.pop("final"),
                    **k_payload,
                },
                "bollinger_20": {
                    "band_width": b_payload.pop("final"),
                    **b_payload,
                },
                "log_return_std": l_payload,
                "historical_volatility": h_payload,
            },
            "signal_synthesis": {
                "is_squeeze": bool(is_squeeze),
                "regime": "COMPRESSION" if is_squeeze else "EXPANSION",
                "main_driver": main_driver,
                "breakout_readiness_score": breakout_readiness,
                "low_quality_penalty": round(low_quality_penalty, 2),
                "confidence": synthesis_confidence,
            },
        }
        return result
