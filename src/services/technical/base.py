import io
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from scipy import stats

from src.core.logger import logger


class BaseTechnicalAnalyzer(ABC):
    """
    Parent class for all technical analysis agents.
    Handles data ingestion, standardization, and common math operations.
    """

    REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]

    def __init__(self, data_source, symbol="UNKNOWN"):
        self.symbol = symbol
        self.logger = logger
        self.data_quality = {}
        self.df = self._load_data(data_source)
        self._validate_data()

    def _load_data(self, source):
        """Unified data loader for CSV string, file path, or DataFrame."""
        if isinstance(source, pd.DataFrame):
            df = source.copy()
        elif isinstance(source, str):
            try:
                if source.endswith(".csv"):
                    df = pd.read_csv(source)
                else:
                    df = pd.read_csv(io.StringIO(source))
            except Exception:
                df = pd.read_csv(io.StringIO(source))
        else:
            raise ValueError("Unsupported data source format.")

        df.columns = [c.lower().strip() for c in df.columns]

        rename_map = {
            "date_time": "date",
            "timestamp": "date",
            "real_close_price": "close",
            "real_close": "close",
            "high_price": "high",
            "low_price": "low",
            "open_price": "open",
            "vol": "volume",
        }
        df.rename(columns=rename_map, inplace=True)

        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df.set_index("date", inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            parsed_index = pd.to_datetime(df.index, errors="coerce")
            if parsed_index.notna().any():
                df.index = parsed_index
                df = df[~df.index.isna()]

        if df.index.has_duplicates:
            duplicate_count = int(df.index.duplicated().sum())
            logger.warning(
                "Dropping %s duplicate timestamps for %s technical input.",
                duplicate_count,
                self.symbol,
            )
            df = df[~df.index.duplicated(keep="last")]

        if all(col in df.columns for col in self.REQUIRED_COLUMNS):
            before_drop = len(df)
            df = df.dropna(subset=self.REQUIRED_COLUMNS, how="any")
            dropped = before_drop - len(df)
            if dropped:
                logger.warning(
                    "Dropped %s OHLCV rows with missing numeric values for %s.",
                    dropped,
                    self.symbol,
                )

        df.sort_index(inplace=True)
        return df

    def _validate_data(self):
        missing = [c for c in self.REQUIRED_COLUMNS if c not in self.df.columns]
        if missing:
            raise ValueError(f"Data missing required columns: {missing}")
        if self.df.empty:
            raise ValueError("No valid OHLCV rows available after cleaning.")

        self.data_quality["row_count"] = len(self.df)
        self.data_quality["has_datetime_index"] = isinstance(self.df.index, pd.DatetimeIndex)
        self.data_quality["is_monotonic_increasing"] = bool(self.df.index.is_monotonic_increasing)
        if not self.data_quality["has_datetime_index"]:
            logger.warning("Technical input index is not DatetimeIndex for %s.", self.symbol)

    def _coerce_series(self, series):
        if series is None:
            return pd.Series(dtype=float)
        if isinstance(series, pd.Series):
            coerced = pd.to_numeric(series, errors="coerce")
        else:
            coerced = pd.to_numeric(pd.Series(series), errors="coerce")
        return coerced

    def _tail_valid(self, series, horizon):
        coerced = self._coerce_series(series)
        valid = coerced.dropna()
        if horizon <= 0 or len(valid) < horizon:
            return None
        return valid.iloc[-horizon:]

    def _calc_slope(self, series, horizon):
        """
        Returns (slope, r_squared) using linear regression.
        Returns (None, None) when data is insufficient after NaN filtering.
        """
        prepared = self._tail_valid(series, horizon)
        if prepared is None:
            return None, None

        y = prepared.values.astype(float)
        x = np.arange(len(y), dtype=float)
        slope, _, r_value, _, _ = stats.linregress(x, y)
        if np.isnan(slope) or np.isnan(r_value):
            return None, None
        return float(slope), float(r_value**2)

    def _get_strength_r2(self, r2):
        """Standardized R2 strength labeling."""
        if r2 is None:
            return "insufficient_data"
        if r2 > 0.8:
            return "very_strong"
        if r2 > 0.5:
            return "strong"
        if r2 > 0.2:
            return "moderate"
        return "weak"

    def _calc_percentile(self, series, window=200):
        """Calculates percentile rank of the last valid value against a valid recent window."""
        valid = self._coerce_series(series).dropna()
        if valid.empty:
            return None
        recent = valid.iloc[-window:]
        current = recent.iloc[-1]
        return float(stats.percentileofscore(recent, current))

    def _score_confidence(
        self,
        *,
        data_quality=1.0,
        trend_quality=None,
        agreement=None,
        stability=None,
    ):
        components = [float(np.clip(data_quality, 0.0, 1.0))]
        if trend_quality is not None:
            components.append(float(np.clip(trend_quality, 0.0, 1.0)))
        if agreement is not None:
            components.append(float(np.clip(agreement, 0.0, 1.0)))
        if stability is not None:
            components.append(float(np.clip(stability, 0.0, 1.0)))

        score = float(np.mean(components)) if components else 0.0
        if score >= 0.75:
            label = "high"
        elif score >= 0.45:
            label = "medium"
        else:
            label = "low"
        return {"score": round(score, 2), "label": label}

    def _data_quality_score(self, series, horizon):
        coerced = self._coerce_series(series)
        if coerced.empty or horizon <= 0:
            return 0.0
        recent = coerced.iloc[-horizon:]
        return float(recent.notna().mean())

    def _safe_pct_distance(self, base_value, current_value):
        if base_value in (None, 0) or current_value is None:
            return None
        return round(((current_value - base_value) / base_value) * 100, 2)

    def _build_meta(self, current_price=None):
        """Standardized meta header generation."""
        last_close = self.df["close"].iloc[-1]
        cur_price = current_price if current_price is not None else last_close
        last_index = self.df.index[-1]
        timestamp = last_index.strftime("%Y-%m-%d") if hasattr(last_index, "strftime") else str(last_index)
        return {
            "symbol": self.symbol,
            "timestamp": timestamp,
            "timeframe": "1D",
            "price": {
                "close": round(float(last_close), 2),
                "current_price": round(float(cur_price), 2),
            },
            "data_quality": self.data_quality,
        }

    @abstractmethod
    def analyze(self, current_price=None):
        pass
