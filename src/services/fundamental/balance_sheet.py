from src.services.fundamental.base import BaseFundamentalAgent


class BalanceSheetAgent(BaseFundamentalAgent):
    def process(self):
        keys_map = {
            "cash_and_banks": "وجوه نقد و موجودی‌های نزد بانک",
            "short_term_investments": "سرمایه گذاری‌های کوتاه مدت",
            "current_assets": "جمع دارایی‌های جاری",
            "total_assets": "جمع کل دارایی‌ها",
            "current_liabilities": "جمع بدهی‌های جاری",
            "short_term_debt": "تسهیلات جاری مالی دریافتی",
            "long_term_debt": "تسهیلات مالی دریافتی بلند مدت",
            "current_ratio": "نسبت جاری",
            "quick_ratio": "نسبت آنی",
            "cash_ratio": "نسبت نقدینگی",
            "debt_to_equity": "نسبت بدهی به ارزش ویژه",
            "dividends": "سود سهام مصوب سال جاری",
            "net_income": "سود (زیان ویژه پس از کسر مالیات"
        }

        # 1. Fill Raw Metrics
        raw_metrics = {}
        raw_metrics['cash_and_banks'] = self.get_latest_value(self.get_data(self.bs, keys_map['cash_and_banks']))
        raw_metrics['short_term_investments'] = self.get_latest_value(self.get_data(self.bs, keys_map['short_term_investments']))
        raw_metrics['current_assets'] = self.get_latest_value(self.get_data(self.bs, keys_map['current_assets']))
        raw_metrics['total_assets'] = self.get_latest_value(self.get_data(self.bs, keys_map['total_assets']))
        raw_metrics['current_liabilities'] = self.get_latest_value(self.get_data(self.bs, keys_map['current_liabilities']))

        st_debt_val = self.get_latest_value(self.get_data(self.bs, keys_map['short_term_debt']))
        lt_debt_val = self.get_latest_value(self.get_data(self.bs, keys_map['long_term_debt']))

        raw_metrics['short_term_debt'] = st_debt_val
        raw_metrics['long_term_debt'] = lt_debt_val

        # Calculate Total Debt
        if st_debt_val is not None and lt_debt_val is not None:
            raw_metrics['total_debt'] = st_debt_val + lt_debt_val
        else:
            raw_metrics['total_debt'] = (st_debt_val or 0) + (lt_debt_val or 0)

        # 2. Fill Liquidity and Solvency Ratios
        l_s_ratios = {}
        l_s_ratios['current_ratio'] = self.get_latest_value(self.get_data(self.fr, keys_map['current_ratio']))
        l_s_ratios['quick_ratio'] = self.get_latest_value(self.get_data(self.fr, keys_map['quick_ratio']))
        l_s_ratios['cash_ratio'] = self.get_latest_value(self.get_data(self.fr, keys_map['cash_ratio']))
        l_s_ratios['debt_to_equity'] = self.get_latest_value(self.get_data(self.fr, keys_map['debt_to_equity']))

        # 3. Fill Payout and Capital Allocation
        payout_alloc = {}

        # Calculate Dividend Payout Ratio
        div_series = self.get_data(self.pl, keys_map['dividends'])
        ni_series = self.get_data(self.pl, keys_map['net_income'])

        latest_div_date, latest_div_val = self.get_latest_item(div_series)
        if latest_div_date and latest_div_val is not None:
            ni_val = ni_series.get(latest_div_date)
            if ni_val:
                payout_alloc['dividend_payout_ratio_pct'] = (latest_div_val / ni_val) * 100
            else:
                payout_alloc['dividend_payout_ratio_pct'] = None
        else:
            payout_alloc['dividend_payout_ratio_pct'] = None

        return {
            "agent_name": "Balance Sheet & Capital Allocation Sub-Agent",
            "raw_metrics": raw_metrics,
            "liquidity_and_solvency_ratios": l_s_ratios,
            "payout_and_capital_allocation": payout_alloc
        }
