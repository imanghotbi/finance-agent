from datetime import datetime
from typing import List, Dict, Union, Optional


class SmartMoneyAnalyzer:
    """
    Analyzes trade history details to identify Smart Money movements,
    Buy/Sell Power Ratios, and Net Flow of real (retail) vs legal (institutional) money.
    """
    def __init__(self, data: List[Dict[str, Union[str, int]]], window_size: Optional[int] = None):
        """
        :param data: List of dictionaries containing trade detail history.
                     Expected keys: date_time, person_buy_volume, person_buyer_count, 
                     person_sell_volume, person_seller_count, person_owner_change, company_owner_change
        :param window_size: Number of recent records to process. If None, processes all data.
        """
        self.raw_data = data
        if window_size is not None and window_size > 0:
            # Assuming data is sorted descending (newest first), this takes the most recent 'window_size' items.
            self.data = self.raw_data[:window_size]
        else:
            self.data = self.raw_data

    def _determine_volume_status(self, ratio: float, net_flow: float) -> str:
        """
        Determines the status string based on power ratio and net flow.
        Logic derived from standard indicators and provided examples.
        """
        if ratio >= 1.2 and net_flow > 0:
            return "Smart Money Entry"
        elif ratio < 0.1: # Heuristic for extreme divergence based on example
            return "Abnormal Divergence"
        elif ratio < 1.0 and net_flow < 0:
            return "High Selling Pressure"
        elif ratio < 1.0 and net_flow > 0:
            return "Divergence (Retail Buying)"
        else:
            return "Normal"

    def analyze(self) -> Dict:
        symbol_data = []

        for row in self.data:
            # 1. Date Conversion (Gregorian -> Jalali or just standardized format)
            # The input provided used datetime.fromisoformat which handles the ISO string
            try:
                dt = datetime.fromisoformat(row.get('date_time', ''))
                date_str = dt.strftime("%Y/%m/%d")
            except (ValueError, TypeError):
                date_str = row.get('date_time', 'UNKNOWN')

            # 2. Extract and Scale Values (Scaling by 1,000,000 as per example)
            scale_factor = 1_000_000
            
            # Volumes and Counts
            p_buy_vol = float(row.get('person_buy_volume', 0))
            p_buy_count = float(row.get('person_buyer_count', 0))
            p_sell_vol = float(row.get('person_sell_volume', 0))
            p_sell_count = float(row.get('person_seller_count', 0))
            
            # Per Capita Calculations (Volume per person / 1M)
            # Avoid division by zero
            per_capita_buy = (p_buy_vol / p_buy_count) / scale_factor if p_buy_count > 0 else 0
            per_capita_sell = (p_sell_vol / p_sell_count) / scale_factor if p_sell_count > 0 else 0
            
            # Power Ratio
            if per_capita_sell != 0:
                real_buy_power_ratio = per_capita_buy / per_capita_sell
            else:
                real_buy_power_ratio = 0
                
            # Net Flows (Change / 1M)
            real_net_flow = float(row.get('person_owner_change', 0)) / scale_factor
            legal_net_flow = float(row.get('company_owner_change', 0)) / scale_factor

            # 3. Determine Status
            status = self._determine_volume_status(real_buy_power_ratio, real_net_flow)

            # 4. Construct Output Dictionary
            output_row = {
                "date": date_str,
                "real_buy_power_ratio": round(real_buy_power_ratio, 2),
                "real_net_flow": round(real_net_flow, 2),
                "per_capita_buy": round(per_capita_buy, 4), # Increased precision to match small values
                "per_capita_sell": round(per_capita_sell, 4), # Increased precision
                "legal_net_flow": round(legal_net_flow, 2),
                "volume_status": status
            }
            
            symbol_data.append(output_row)

        
        return symbol_data
