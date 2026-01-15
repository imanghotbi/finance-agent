class BaseFundamentalAgent:
    def __init__(self, fundamental_data):
        self.data = fundamental_data
        
        # Common Access Points
        self.fa = self.data.get('fundamental_analysis', {})
        self.bs = self.fa.get('balance_sheet', {})
        self.pl = self.fa.get('profit_loss', {})
        self.cf = self.fa.get('cash_flow', {})
        self.fr = self.fa.get('financial_ratios', {})
        
        self.md = self.data.get('market_data', {})
        self.gs = self.md.get('general_snapshot', {})

    def get_data(self, source, key):
        """Helper to safely get data from source dict."""
        return source.get(key)

    def get_latest_value(self, data_dict):
        """Helper to find the latest value based on date keys."""
        if not data_dict:
            return None
        sorted_dates = sorted(data_dict.keys(), reverse=True)
        return data_dict[sorted_dates[0]]

    def get_latest_item(self, data_dict):
        """Helper to get latest value and its date."""
        if not data_dict:
            return None, None
        sorted_dates = sorted(data_dict.keys(), reverse=True)
        latest_date = sorted_dates[0]
        return latest_date, data_dict[latest_date]

    def get_current_and_prev_items(self, data_dict):
        """Helper to find current and previous year items for YoY calculations."""
        if not data_dict:
            return None, None, None, None
        sorted_dates = sorted(data_dict.keys(), reverse=True)
        if len(sorted_dates) < 1:
            return None, None, None, None
        
        curr_date = sorted_dates[0]
        curr_val = data_dict[curr_date]
        
        prev_date = None
        prev_val = None
        
        if len(sorted_dates) >= 2:
            prev_date = sorted_dates[1]
            prev_val = data_dict[prev_date]
            
        return curr_date, curr_val, prev_date, prev_val

