from src.services.fundamental.base import BaseFundamentalAgent

class ValuationAgent(BaseFundamentalAgent):
    def process(self):
        keys_map = {
            "revenue": "درآمد حاصل از خدمات و فروش",
            "st_debt": "تسهیلات جاری مالی دریافتی",
            "lt_debt": "تسهیلات مالی دریافتی بلند مدت",
            "cash": "وجوه نقد و موجودی‌های نزد بانک",
            "st_inv": "سرمایه گذاری‌های کوتاه مدت"
        }

        # --- 1. Market Raw Data ---
        market_raw = {}

        # Market Cap
        market_cap = None
        if 'last_value' in self.gs and 'value' in self.gs['last_value']:
            market_cap = self.gs['last_value']['value']
        else:
            pass
        market_raw['market_cap'] = market_cap

        # Current Price
        current_price = self.md.get('current_price')

        # Shares Outstanding
        shares_outstanding = None
        if market_cap is not None and current_price:
            shares_outstanding = market_cap / current_price

        # Free Float
        ff_data = self.gs.get('last_free_float', {})
        ff_percent_raw = ff_data.get('percent')
        market_raw['free_float_pct'] = ff_percent_raw * 100 if ff_percent_raw is not None else None

        # Free Float Shares
        market_raw['free_float_shares'] = None
        if shares_outstanding is not None and ff_percent_raw is not None:
            market_raw['free_float_shares'] = shares_outstanding * ff_percent_raw

        # Reported Ratios
        market_raw['pb_reported'] = self.gs.get('last_pb', {}).get('value')
        market_raw['pe_ttm_reported'] = self.gs.get('eps', {}).get('pe_ttm')
        market_raw['pe_at_agm_reported'] = self.gs.get('dps', {}).get('pe')
        market_raw['eps_ttm_reported'] = self.gs.get('eps', {}).get('pure_ttm')

        # --- 2. Enterprise Value Block ---
        ev_block = {}

        # Net Debt Calculation
        st_debt = self.get_latest_value(self.bs.get(keys_map['st_debt'])) or 0
        lt_debt = self.get_latest_value(self.bs.get(keys_map['lt_debt'])) or 0
        total_debt = st_debt + lt_debt

        cash = self.get_latest_value(self.bs.get(keys_map['cash'])) or 0
        st_inv = self.get_latest_value(self.bs.get(keys_map['st_inv'])) or 0

        net_debt = total_debt - cash - st_inv
        ev_block['net_debt'] = net_debt

        # Enterprise Value
        enterprise_value = None
        if market_cap is not None:
            enterprise_value = market_cap + net_debt
        ev_block['enterprise_value'] = enterprise_value

        # --- 3. Multiples and Yields ---
        mult = {}

        mult['pe_ttm'] = market_raw['pe_ttm_reported']
        mult['pb'] = market_raw['pb_reported']

        # PS TTM
        rev_series = self.pl.get(keys_map['revenue'])
        revenue_ttm = self.get_latest_value(rev_series)

        mult['ps_ttm'] = None
        if market_cap is not None and revenue_ttm:
            mult['ps_ttm'] = market_cap / revenue_ttm

        # EV to Sales
        mult['ev_to_sales'] = None
        if enterprise_value is not None and revenue_ttm:
            mult['ev_to_sales'] = enterprise_value / revenue_ttm

        return {
            "agent_name": "Valuation & Market Microstructure Sub-Agent",
            "market_raw": market_raw,
            "enterprise_value_block": ev_block,
            "multiples_and_yields": mult,
        }
