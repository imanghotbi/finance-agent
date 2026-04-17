import numpy as np
import pandas as pd
import talib

from src.services.technical.base import BaseTechnicalAnalyzer


class VolumeAnalyzer(BaseTechnicalAnalyzer):
    def _series_payload(self, series, horizon, name, current_price=None):
        coerced = self._coerce_series(series)
        latest_value = coerced.dropna().iloc[-1] if not coerced.dropna().empty else None
        slope, r2 = self._calc_slope(coerced, horizon)
        data_quality = self._data_quality_score(coerced, horizon)

        if latest_value is None:
            confidence = self._score_confidence(data_quality=data_quality, trend_quality=0.0)
            return {
                "value": None,
                "slope": None,
                "slope_horizon_bars": horizon,
                "trend_quality_r2": None,
                "strength": "insufficient_data",
                "regime": "insufficient_data",
                "confidence": confidence,
            }

        regime = "neutral"
        if name == "vma_ratio":
            regime = "expanding_participation" if (slope or 0) > 0 else "contracting_interest"
        elif name == "rvol":
            regime = "volume_anomaly" if latest_value > 2.0 else "normal_turnover"
        elif name == "obv":
            regime = "accumulation_bias" if (slope or 0) > 0 else "distribution_bias"
        elif name == "proxy_cvd":
            regime = "buyer_dominant_candle_flow" if (slope or 0) > 0 else "seller_dominant_candle_flow"
        elif name == "rv":
            regime = "volatility_expansion" if (slope or 0) > 0 else "volatility_compression"
        elif name == "mfi":
            if latest_value > 80:
                regime = "overbought"
            elif latest_value < 20:
                regime = "oversold"
            else:
                regime = "positive_flow" if (slope or 0) > 0 else "negative_flow"
        elif name == "volume_efficiency":
            regime = "positive_volume_efficiency" if (slope or 0) > 0 else "negative_volume_efficiency"
        elif name == "vwap":
            if current_price is not None and latest_value not in (None, 0):
                regime = "premium_markup" if current_price > latest_value else "discount_markdown"

        confidence = self._score_confidence(
            data_quality=data_quality,
            trend_quality=r2,
            stability=1.0 if latest_value == 0 else 0.8,
        )
        return {
            "value": round(float(latest_value), 4),
            "slope": None if slope is None else round(float(slope), 4),
            "slope_horizon_bars": horizon,
            "trend_quality_r2": None if r2 is None else round(float(r2), 2),
            "strength": self._get_strength_r2(r2),
            "regime": regime,
            "confidence": confidence,
        }

    def analyze(self, current_price=None):
        c = self.df["close"].values.astype(float)
        h = self.df["high"].values.astype(float)
        l = self.df["low"].values.astype(float)
        o = self.df["open"].values.astype(float)
        v = self.df["volume"].values.astype(float)
        cur_price = float(current_price) if current_price is not None else float(c[-1])

        vma_20 = talib.SMA(v, timeperiod=20)
        vma_50 = talib.SMA(v, timeperiod=50)
        vma_ratio_series = pd.Series(vma_20 / (vma_50 + 1e-9))
        rvol_series = pd.Series(v / (vma_20 + 1e-9))

        obv = pd.Series(talib.OBV(c, v))
        buy_vol = np.where(c >= o, v, 0)
        sell_vol = np.where(c < o, v, 0)
        candle_direction_cvd = pd.Series(np.cumsum(buy_vol - sell_vol))

        log_ret = np.log(c[1:] / c[:-1])
        log_ret = np.insert(log_ret, 0, 0)
        log_ret_series = pd.Series(log_ret)
        rv_30 = log_ret_series.rolling(30, min_periods=20).std() * np.sqrt(252) * 100
        rv_90 = log_ret_series.rolling(90, min_periods=60).std() * np.sqrt(252) * 100

        mfi = pd.Series(talib.MFI(h, l, c, v, timeperiod=14))
        vol_weighted_ret = pd.Series((log_ret_series * v) / (pd.Series(vma_20) + 1e-9))

        typical = (h + l + c) / 3
        pv = pd.Series(typical * v)
        v_s = pd.Series(v)
        vwap = pv.rolling(20, min_periods=10).sum() / v_s.rolling(20, min_periods=10).sum()

        obv_slope, _ = self._calc_slope(obv, 20)
        proxy_cvd_slope, _ = self._calc_slope(candle_direction_cvd, 15)
        mfi_slope, _ = self._calc_slope(mfi, 10)

        directional_votes = [
            1 if (obv_slope or 0) > 0 else -1 if (obv_slope or 0) < 0 else 0,
            1 if (proxy_cvd_slope or 0) > 0 else -1 if (proxy_cvd_slope or 0) < 0 else 0,
            1 if (mfi_slope or 0) > 0 else -1 if (mfi_slope or 0) < 0 else 0,
        ]
        non_zero_votes = [vote for vote in directional_votes if vote != 0]
        agreement_score = abs(sum(directional_votes)) / len(directional_votes)
        internal_conflict = len(set(non_zero_votes)) > 1 if non_zero_votes else False

        volume_percentile_60 = self._calc_percentile(pd.Series(v), window=60)
        anomaly_regime = (
            "extreme_volume"
            if volume_percentile_60 is not None and volume_percentile_60 >= 95
            else "elevated_volume"
            if volume_percentile_60 is not None and volume_percentile_60 >= 80
            else "normal_volume"
        )

        consistency_confidence = self._score_confidence(
            data_quality=min(1.0, len(self.df) / 90),
            agreement=agreement_score,
            stability=0.3 if internal_conflict else 0.9,
        )

        vwap_payload = self._series_payload(vwap, 15, "vwap", current_price=cur_price)
        distance_percent = None
        if vwap_payload["value"] not in (None, 0):
            distance_percent = round(((cur_price - vwap_payload["value"]) / vwap_payload["value"]) * 100, 2)

        final_json = {
            "meta": self._build_meta(current_price),
            "volume_participation": {
                "vma_ratio": self._series_payload(vma_ratio_series, 15, "vma_ratio"),
                "rvol": self._series_payload(rvol_series, 10, "rvol"),
                "volume_anomaly": {
                    "rolling_percentile_60": None if volume_percentile_60 is None else round(volume_percentile_60, 1),
                    "regime": anomaly_regime,
                },
            },
            "directional_flow": {
                "obv_20": self._series_payload(obv, 20, "obv"),
                "candle_direction_cvd": self._series_payload(candle_direction_cvd, 15, "proxy_cvd"),
            },
            "relative_volume_regime": {
                "rv_30": self._series_payload(rv_30, 20, "rv"),
                "rv_90": self._series_payload(rv_90, 20, "rv"),
            },
            "price_volume_efficiency": {
                "mfi_14": self._series_payload(mfi, 10, "mfi"),
                "volume_weighted_return": self._series_payload(vol_weighted_ret, 14, "volume_efficiency"),
            },
            "institutional_reference": {
                "vwap_20": {
                    "distance_percent": distance_percent,
                    **vwap_payload,
                }
            },
            "consistency_checks": {
                "obv_cvd_mfi_agreement_score": round(agreement_score, 2),
                "internal_conflict": internal_conflict,
                "confidence": consistency_confidence,
            },
        }
        return final_json
