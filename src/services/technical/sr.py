import pandas as pd

from src.services.technical.base import BaseTechnicalAnalyzer


class SupportResistanceAnalyzer(BaseTechnicalAnalyzer):
    """
    Builds support/resistance zones from pivots, moving averages, fractals,
    cumulative VWAP, and volume profile, then scores each zone by confluence,
    recency, distance, and touch count.
    """

    def __init__(self, data_source, raw_pivots_data=None, symbol="UNKNOWN"):
        super().__init__(data_source, symbol)
        self.raw_pivots_data = raw_pivots_data or {}
        self.current_price = float(self.df["close"].iloc[-1])

    def _make_level(self, source, price, level_type, category, bars_ago=None, touches=1):
        return {
            "source": source,
            "price": float(price),
            "type": level_type,
            "category": category,
            "bars_ago": bars_ago,
            "touches": touches,
        }

    def _get_moving_averages(self):
        levels = []
        ema_20 = self.df["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        levels.append(
            self._make_level(
                "EMA_20",
                ema_20,
                "SUPPORT" if ema_20 < self.current_price else "RESISTANCE",
                "dynamic_levels",
                bars_ago=0,
            )
        )
        if len(self.df) >= 50:
            sma_50 = self.df["close"].rolling(window=50).mean().iloc[-1]
            levels.append(
                self._make_level(
                    "SMA_50",
                    sma_50,
                    "SUPPORT" if sma_50 < self.current_price else "RESISTANCE",
                    "dynamic_levels",
                    bars_ago=0,
                )
            )
        return levels

    def _get_vwap(self):
        v = self.df["volume"].values
        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        vwap_series = (tp * v).cumsum() / v.cumsum()
        current_vwap = float(vwap_series.iloc[-1])
        return [
            self._make_level(
                "VWAP_Cumulative",
                current_vwap,
                "SUPPORT" if current_vwap < self.current_price else "RESISTANCE",
                "dynamic_levels",
                bars_ago=0,
            )
        ]

    def _get_fractals(self, window=5):
        levels = []
        recent_df = self.df.iloc[-80:].reset_index(drop=True)
        for i in range(window, len(recent_df) - window):
            if all(recent_df["high"][i] > recent_df["high"][i - x] for x in range(1, window + 1)) and all(
                recent_df["high"][i] > recent_df["high"][i + x] for x in range(1, window + 1)
            ):
                levels.append(
                    self._make_level(
                        "Fractal_High",
                        recent_df["high"][i],
                        "RESISTANCE",
                        "static_levels",
                        bars_ago=len(recent_df) - 1 - i,
                    )
                )
            if all(recent_df["low"][i] < recent_df["low"][i - x] for x in range(1, window + 1)) and all(
                recent_df["low"][i] < recent_df["low"][i + x] for x in range(1, window + 1)
            ):
                levels.append(
                    self._make_level(
                        "Fractal_Low",
                        recent_df["low"][i],
                        "SUPPORT",
                        "static_levels",
                        bars_ago=len(recent_df) - 1 - i,
                    )
                )
        return levels[-6:]

    def _get_vpvr_zones(self, bins=30):
        price_range = self.df["high"].max() - self.df["low"].min()
        if price_range == 0:
            return []

        temp_df = self.df.copy()
        temp_df["bin"] = pd.cut(temp_df["close"], bins=bins)
        vp = temp_df.groupby("bin", observed=False)["volume"].sum()
        poc_bin = vp.idxmax()
        poc_price = float(poc_bin.mid)
        touch_count = int(temp_df[temp_df["bin"] == poc_bin].shape[0])
        return [
            self._make_level(
                "VPVR_POC",
                poc_price,
                "SUPPORT" if poc_price < self.current_price else "RESISTANCE",
                "volume_profile",
                bars_ago=None,
                touches=max(touch_count, 1),
            )
        ]

    def _parse_raw_pivots(self):
        parsed_levels = []
        if not isinstance(self.raw_pivots_data, dict):
            return parsed_levels

        for pivot_name, items in self.raw_pivots_data.items():
            for item in items or []:
                raw_name = item["name"]
                std_name = "PIVOT" if raw_name == "pivot" else raw_name.upper()
                val = item["value"]
                parsed_levels.append(
                    self._make_level(
                        f"{pivot_name}_{std_name}",
                        val,
                        "RESISTANCE" if val > self.current_price else "SUPPORT",
                        "pivot_levels",
                        bars_ago=0,
                    )
                )
        return parsed_levels

    def _zone_strength(self, cluster):
        sources = {level["source"] for level in cluster}
        source_score = min(len(sources) / 4, 1.0)

        recency_values = []
        for level in cluster:
            bars_ago = level.get("bars_ago")
            if bars_ago is None:
                recency_values.append(0.65)
            else:
                recency_values.append(max(0.2, 1 - (bars_ago / 60)))
        recency_score = sum(recency_values) / len(recency_values)

        avg_price = sum(level["price"] for level in cluster) / len(cluster)
        distance_pct = abs(avg_price - self.current_price) / max(abs(self.current_price), 1e-9)
        distance_score = max(0.2, 1 - min(distance_pct / 0.12, 1.0))

        touch_count = sum(level.get("touches", 1) for level in cluster)
        touch_score = min(touch_count / 6, 1.0)

        strength = (0.35 * source_score) + (0.25 * recency_score) + (0.2 * distance_score) + (0.2 * touch_score)
        return round(strength, 2), {
            "source_score": round(source_score, 2),
            "recency_score": round(recency_score, 2),
            "distance_score": round(distance_score, 2),
            "touch_score": round(touch_score, 2),
            "touch_count": touch_count,
        }

    def _create_zone_object(self, cluster):
        prices = [x["price"] for x in cluster]
        avg_price = sum(prices) / len(prices)
        z_type = "RESISTANCE" if avg_price > self.current_price else "SUPPORT"
        strength, drivers = self._zone_strength(cluster)

        return {
            "type": z_type,
            "price_range": [float(min(prices)), float(max(prices))],
            "avg_price": float(round(avg_price, 2)),
            "strength_score": float(strength),
            "strength_drivers": drivers,
            "contributors": sorted({x["source"] for x in cluster}),
            "categories": sorted({x["category"] for x in cluster}),
        }

    def _nearest_zone_confidence(self, zone):
        if not zone:
            return {"score": 0.0, "label": "low"}
        contributor_bonus = min(len(zone.get("contributors", [])) / 4, 1.0)
        distance_pct = abs(zone["avg_price"] - self.current_price) / max(abs(self.current_price), 1e-9)
        distance_score = max(0.2, 1 - min(distance_pct / 0.08, 1.0))
        score = round((0.55 * zone["strength_score"]) + (0.25 * contributor_bonus) + (0.2 * distance_score), 2)
        label = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"
        return {"score": score, "label": label}

    def analyze(self, current_price=None):
        if current_price is not None:
            self.current_price = float(current_price)

        static_levels = self._parse_raw_pivots() + self._get_fractals() + self._get_vpvr_zones()
        dynamic_levels = self._get_moving_averages() + self._get_vwap()
        all_levels = static_levels + dynamic_levels
        all_levels.sort(key=lambda x: x["price"])

        zones = []
        if all_levels:
            threshold_pct = 0.005
            current_cluster = [all_levels[0]]
            for level in all_levels[1:]:
                prev_price = current_cluster[-1]["price"]
                relative_gap = abs(level["price"] - prev_price) / max(abs(prev_price), 1e-9)
                if relative_gap <= threshold_pct:
                    current_cluster.append(level)
                else:
                    zones.append(self._create_zone_object(current_cluster))
                    current_cluster = [level]
            zones.append(self._create_zone_object(current_cluster))

        supports = sorted([z for z in zones if z["avg_price"] < self.current_price], key=lambda x: x["avg_price"], reverse=True)
        resistances = sorted([z for z in zones if z["avg_price"] > self.current_price], key=lambda x: x["avg_price"])
        nearest_support = supports[0] if supports else None
        nearest_resistance = resistances[0] if resistances else None

        if nearest_support and nearest_resistance:
            status = "NEUTRAL"
            if nearest_support["strength_score"] > nearest_resistance["strength_score"] + 0.15:
                status = "BULLISH_BIAS"
            elif nearest_resistance["strength_score"] > nearest_support["strength_score"] + 0.15:
                status = "BEARISH_BIAS"
        elif nearest_support:
            status = "BULLISH_BIAS"
        elif nearest_resistance:
            status = "BEARISH_BIAS"
        else:
            status = "NEUTRAL"

        payload = {
            "agent_id": "SR_SubAgent_01",
            "current_price": self.current_price,
            "signal_summary": {
                "status": status,
                "nearest_support": nearest_support,
                "nearest_support_confidence": self._nearest_zone_confidence(nearest_support),
                "nearest_resistance": nearest_resistance,
                "nearest_resistance_confidence": self._nearest_zone_confidence(nearest_resistance),
            },
            "level_buckets": {
                "static_levels": static_levels,
                "dynamic_levels": dynamic_levels,
            },
            "confluence_zones": zones,
            "raw_pivots_debug": self.raw_pivots_data,
        }
        return payload
