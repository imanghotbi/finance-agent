import pandas as pd
from base_analyzer import BaseTechnicalAnalyzer

class SupportResistanceAnalyzer(BaseTechnicalAnalyzer):
    """
    Requires 'raw_pivots_data' in constructor or analyze method.
    Preserves exact logic of rsubagent.py
    """
    def __init__(self, data_source, raw_pivots_data=None, symbol="UNKNOWN"):
        super().__init__(data_source, symbol)
        self.raw_pivots_data = raw_pivots_data or []
        self.current_price = self.df['close'].iloc[-1]
    
    def _get_moving_averages(self):
        levels = []
        # rsubagent used pandas ewm, preserving exact logic
        ema_20 = self.df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        levels.append({
            "source": "EMA_20", "price": ema_20, 
            "type": "SUPPORT" if ema_20 < self.current_price else "RESISTANCE"
        })
        if len(self.df) >= 50:
            sma_50 = self.df['close'].rolling(window=50).mean().iloc[-1]
            levels.append({
                "source": "SMA_50", "price": sma_50, 
                "type": "SUPPORT" if sma_50 < self.current_price else "RESISTANCE"
            })
        return levels

    def _get_vwap(self):
        v = self.df['volume'].values
        tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        vwap_series = (tp * v).cumsum() / v.cumsum()
        current_vwap = vwap_series.iloc[-1]
        return [{
            "source": "VWAP_Session", "price": current_vwap,
            "type": "SUPPORT" if current_vwap < self.current_price else "RESISTANCE"
        }]

    def _get_fractals(self, window=5):
        levels = []
        recent_df = self.df.iloc[-50:].reset_index(drop=True)
        for i in range(window, len(recent_df) - window):
            # Swing High
            if all(recent_df['high'][i] > recent_df['high'][i-x] for x in range(1, window+1)) and \
               all(recent_df['high'][i] > recent_df['high'][i+x] for x in range(1, window+1)):
                levels.append({"source": "Fractal_High", "price": recent_df['high'][i], "type": "RESISTANCE"})
            # Swing Low
            if all(recent_df['low'][i] < recent_df['low'][i-x] for x in range(1, window+1)) and \
               all(recent_df['low'][i] < recent_df['low'][i+x] for x in range(1, window+1)):
                levels.append({"source": "Fractal_Low", "price": recent_df['low'][i], "type": "SUPPORT"})
        return levels[-3:]

    def _get_vpvr_zones(self, bins=30):
        price_range = self.df['high'].max() - self.df['low'].min()
        if price_range == 0: return []
        
        # Creating a copy to avoid SettingWithCopy warning on the main DF
        temp_df = self.df.copy()
        temp_df['bin'] = pd.cut(temp_df['close'], bins=bins)
        vp = temp_df.groupby('bin', observed=False)['volume'].sum()
        poc_price = vp.idxmax().mid
        return [{
            "source": "VPVR_POC", "price": poc_price,
            "type": "SUPPORT" if poc_price < self.current_price else "RESISTANCE"
        }]

    def _parse_raw_pivots(self):
        pivot_types = ['PivotPointClassic(30)', 'PivotPointFibonacci(30)']
        parsed_levels = []
        for i, p_list in enumerate(self.raw_pivots_data):
            p_name_prefix = pivot_types[i] if i < len(pivot_types) else f"Pivot_{i}"
            for item in self.raw_pivots_data[p_list]:
                raw_name = item['name']
                std_name = "PIVOT" if raw_name == "pivot" else raw_name.upper()
                val = item['value']
                parsed_levels.append({
                    "source": f"{p_name_prefix}_{std_name}", "price": val,
                    "type": "RESISTANCE" if val > self.current_price else "SUPPORT"
                })
        return parsed_levels

    def _create_zone_object(self, cluster):
        prices = [x['price'] for x in cluster]
        sources = [x['source'] for x in cluster]
        avg_price = sum(prices) / len(prices)
        z_type = "RESISTANCE" if avg_price > self.current_price else "SUPPORT"
        strength = min(len(set(sources)) * 0.25, 1.0)
        
        return {
            "type": z_type, 
            "price_range": [float(min(prices)), float(max(prices))], 
            "avg_price": float(round(avg_price, 2)), 
            "strength_score": float(strength),
            "contributors": list(set(sources))
        }

    def analyze(self, current_price=None):
        # Update current price if passed explicitly, else use last close
        if current_price: self.current_price = current_price
        
        all_levels = self._parse_raw_pivots() + self._get_moving_averages() + \
                     self._get_vwap() + self._get_fractals() + self._get_vpvr_zones()
        
        all_levels.sort(key=lambda x: x['price'])
        
        zones = []
        if all_levels:
            threshold_pct = 0.005
            current_cluster = [all_levels[0]]
            for i in range(1, len(all_levels)):
                prev_price = current_cluster[-1]['price']
                curr_price = all_levels[i]['price']
                if (curr_price - prev_price) / prev_price <= threshold_pct:
                    current_cluster.append(all_levels[i])
                else:
                    zones.append(self._create_zone_object(current_cluster))
                    current_cluster = [all_levels[i]]
            zones.append(self._create_zone_object(current_cluster))

        supports = sorted([z for z in zones if z['avg_price'] < self.current_price], key=lambda x: x['avg_price'], reverse=True)
        resistances = sorted([z for z in zones if z['avg_price'] > self.current_price], key=lambda x: x['avg_price'])

        payload = {
            "agent_id": "SR_SubAgent_01",
            "current_price": self.current_price,
            "signal_summary": {
                "status": "NEUTRAL",
                "nearest_support": supports[0] if supports else None,
                "nearest_resistance": resistances[0] if resistances else None
            },
            "confluence_zones": zones,
            "raw_pivots_debug": self.raw_pivots_data
        }
        return payload
