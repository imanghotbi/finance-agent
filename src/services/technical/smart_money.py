from datetime import datetime
from typing import Dict, List, Optional, Union

import pandas as pd


class SmartMoneyAnalyzer:
    """
    Analyzes real/legal trade history and separates retail flow from legal flow.
    The output avoids calling retail activity "institutional" unless legal flow supports it.
    """

    def __init__(self, data: Optional[List[Dict[str, Union[str, int, float]]]], window_size: Optional[int] = None):
        self.raw_data = data or []
        self.window_size = window_size

    def _normalize_rows(self) -> pd.DataFrame:
        rows = []
        for row in self.raw_data:
            raw_date = row.get("date_time")
            try:
                dt = datetime.fromisoformat(str(raw_date))
            except (ValueError, TypeError):
                dt = None

            rows.append(
                {
                    "date_time": raw_date,
                    "parsed_date": dt,
                    "person_buy_volume": float(row.get("person_buy_volume", 0) or 0),
                    "person_buyer_count": float(row.get("person_buyer_count", 0) or 0),
                    "person_sell_volume": float(row.get("person_sell_volume", 0) or 0),
                    "person_seller_count": float(row.get("person_seller_count", 0) or 0),
                    "person_owner_change": float(row.get("person_owner_change", 0) or 0),
                    "company_owner_change": float(row.get("company_owner_change", 0) or 0),
                }
            )

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        if df["parsed_date"].notna().any():
            dated = df[df["parsed_date"].notna()].sort_values("parsed_date")
            undated = df[df["parsed_date"].isna()]
            df = pd.concat([dated, undated], ignore_index=True)

        if self.window_size is not None and self.window_size > 0:
            df = df.tail(self.window_size).reset_index(drop=True)
        return df

    @staticmethod
    def _safe_ratio(buy_value: float, sell_value: float) -> Optional[float]:
        if sell_value > 0:
            return buy_value / sell_value
        if buy_value > 0:
            return None
        return 1.0

    @staticmethod
    def _real_flow_signal(ratio_3d: Optional[float], net_flow_3d: float) -> str:
        if ratio_3d is None and net_flow_3d > 0:
            return "real_buying"
        if ratio_3d is None and net_flow_3d <= 0:
            return "conflicted_real_flow"
        if ratio_3d >= 1.2 and net_flow_3d > 0:
            return "real_buying"
        if ratio_3d <= 0.85 and net_flow_3d < 0:
            return "real_selling"
        if ratio_3d >= 1.2 and net_flow_3d <= 0:
            return "conflicted_real_flow"
        if ratio_3d <= 0.85 and net_flow_3d > 0:
            return "retail_accumulation_divergence"
        return "neutral_real_flow"

    @staticmethod
    def _legal_flow_signal(legal_net_flow_3d: float) -> str:
        if legal_net_flow_3d > 0:
            return "legal_buying"
        if legal_net_flow_3d < 0:
            return "legal_selling"
        return "neutral_legal_flow"

    @staticmethod
    def _combined_classification(real_signal: str, legal_signal: str) -> str:
        if real_signal == "real_buying" and legal_signal == "legal_buying":
            return "broad_accumulation"
        if real_signal == "real_selling" and legal_signal == "legal_selling":
            return "broad_distribution"
        if real_signal == "real_buying" and legal_signal != "legal_buying":
            return "real_buying"
        if legal_signal == "legal_buying" and real_signal != "real_buying":
            return "legal_buying"
        if real_signal in {"conflicted_real_flow", "retail_accumulation_divergence"} or (
            real_signal == "real_buying" and legal_signal == "legal_selling"
        ):
            return "conflicted_flow"
        return "neutral_flow"

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    def analyze(self) -> List[Dict]:
        df = self._normalize_rows()
        if df.empty:
            return []

        scale_factor = 1_000_000
        df["per_capita_buy"] = df.apply(
            lambda row: (row["person_buy_volume"] / row["person_buyer_count"]) / scale_factor
            if row["person_buyer_count"] > 0
            else 0.0,
            axis=1,
        )
        df["per_capita_sell"] = df.apply(
            lambda row: (row["person_sell_volume"] / row["person_seller_count"]) / scale_factor
            if row["person_seller_count"] > 0
            else 0.0,
            axis=1,
        )
        df["real_buy_power_ratio"] = df.apply(
            lambda row: self._safe_ratio(row["per_capita_buy"], row["per_capita_sell"]),
            axis=1,
        )
        df["real_net_flow"] = df["person_owner_change"] / scale_factor
        df["legal_net_flow"] = df["company_owner_change"] / scale_factor

        ratio_proxy = df["real_buy_power_ratio"].fillna(df["per_capita_buy"].where(df["per_capita_buy"] > 0, 1.0) * 2.0)
        df["real_buy_power_ratio_3d_avg"] = ratio_proxy.rolling(3, min_periods=1).mean()
        df["real_buy_power_ratio_5d_avg"] = ratio_proxy.rolling(5, min_periods=1).mean()
        df["real_net_flow_3d_avg"] = df["real_net_flow"].rolling(3, min_periods=1).mean()
        df["real_net_flow_5d_avg"] = df["real_net_flow"].rolling(5, min_periods=1).mean()
        df["legal_net_flow_3d_avg"] = df["legal_net_flow"].rolling(3, min_periods=1).mean()
        df["legal_net_flow_5d_avg"] = df["legal_net_flow"].rolling(5, min_periods=1).mean()

        real_signals = []
        legal_signals = []
        combined_labels = []
        output_rows = []

        for idx, row in df.iterrows():
            ratio_3d = row["real_buy_power_ratio_3d_avg"]
            real_signal = self._real_flow_signal(ratio_3d, row["real_net_flow_3d_avg"])
            legal_signal = self._legal_flow_signal(row["legal_net_flow_3d_avg"])
            combined = self._combined_classification(real_signal, legal_signal)

            real_signals.append(real_signal)
            legal_signals.append(legal_signal)
            combined_labels.append(combined)

            recent_window = combined_labels[max(0, idx - 2) : idx + 1]
            real_alignment = float(
                (
                    real_signal == "real_buying" and row["real_net_flow_3d_avg"] > 0
                )
                or (
                    real_signal == "real_selling" and row["real_net_flow_3d_avg"] < 0
                )
                or real_signal in {"neutral_real_flow", "conflicted_real_flow", "retail_accumulation_divergence"}
            )
            persistence = recent_window.count(combined) / len(recent_window)
            stability = 1.0 if abs(row["real_net_flow"] - row["real_net_flow_3d_avg"]) <= max(abs(row["real_net_flow_3d_avg"]) * 0.5, 0.15) else 0.35
            agreement = 1.0 if combined in {"broad_accumulation", "broad_distribution"} else 0.6 if combined in {"real_buying", "legal_buying"} else 0.3
            confidence_score = round((0.3 * real_alignment) + (0.35 * persistence) + (0.2 * stability) + (0.15 * agreement), 2)
            confidence = {
                "score": confidence_score,
                "label": self._confidence_label(confidence_score),
                "drivers": {
                    "persistence_3d": round(persistence, 2),
                    "stability_vs_3d_avg": round(stability, 2),
                    "signal_agreement": round(agreement, 2),
                },
            }

            if row["parsed_date"] is not None:
                date_str = row["parsed_date"].strftime("%Y/%m/%d")
            else:
                date_str = str(row["date_time"] or "UNKNOWN")

            output_rows.append(
                {
                    "date": date_str,
                    "real_buy_power_ratio": None if row["real_buy_power_ratio"] is None else round(float(row["real_buy_power_ratio"]), 2),
                    "real_net_flow": round(float(row["real_net_flow"]), 2),
                    "legal_net_flow": round(float(row["legal_net_flow"]), 2),
                    "per_capita_buy": round(float(row["per_capita_buy"]), 4),
                    "per_capita_sell": round(float(row["per_capita_sell"]), 4),
                    "smoothed_metrics": {
                        "real_buy_power_ratio_3d_avg": round(float(row["real_buy_power_ratio_3d_avg"]), 2),
                        "real_buy_power_ratio_5d_avg": round(float(row["real_buy_power_ratio_5d_avg"]), 2),
                        "real_net_flow_3d_avg": round(float(row["real_net_flow_3d_avg"]), 2),
                        "real_net_flow_5d_avg": round(float(row["real_net_flow_5d_avg"]), 2),
                        "legal_net_flow_3d_avg": round(float(row["legal_net_flow_3d_avg"]), 2),
                        "legal_net_flow_5d_avg": round(float(row["legal_net_flow_5d_avg"]), 2),
                    },
                    "flow_signals": {
                        "real_flow_signal": real_signal,
                        "legal_flow_signal": legal_signal,
                        "combined_classification": combined,
                    },
                    "confidence": confidence,
                }
            )

        return output_rows
