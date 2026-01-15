from src.services.fundamental.base import BaseFundamentalAgent

class EarningsQualityAgent(BaseFundamentalAgent):
    def process(self):
        keys_map = {
            "revenue": "درآمد حاصل از خدمات و فروش",
            "cogs": "بهای تمام شده کالای فروش رفته",
            "gross_profit": "سود ناویژه",
            "operating_profit": "سود (زیان عملیاتی",
            "net_income": "سود (زیان ویژه پس از کسر مالیات",
            "ocf": "جریان خالص ورود (خروج نقد حاصل از فعالیت های عملیاتی",
            "capex_ppe": "پرداخت های نقدی برای خرید دارایی های ثابت مشهود",
            "capex_intangibles": "پرداخت های نقدی برای خرید دارایی های نامشهود",
            "total_assets": "جمع کل دارایی‌ها",
            "net_margin_pct": "سود خالص به فروش",
            "gross_margin_pct": "سود ناخالص به فروش",
            "operating_margin_pct": "حاشیه سود عملیاتی"
        }

        # --- 1. Raw Metrics ---
        raw_metrics = {}

        # Revenue
        rev_series = self.get_data(self.pl, keys_map['revenue'])
        curr_date, rev_curr, prev_date, rev_prev = self.get_current_and_prev_items(rev_series)
        raw_metrics['revenue_ttm'] = rev_curr

        # COGS
        cogs_series = self.get_data(self.pl, keys_map['cogs'])
        _, cogs_curr, _, _ = self.get_current_and_prev_items(cogs_series)
        raw_metrics['cogs_ttm'] = cogs_curr

        # Gross Profit
        gp_series = self.get_data(self.pl, keys_map['gross_profit'])
        _, gp_curr, _, _ = self.get_current_and_prev_items(gp_series)
        raw_metrics['gross_profit_ttm'] = gp_curr

        # Operating Profit
        op_series = self.get_data(self.pl, keys_map['operating_profit'])
        _, op_curr, _, _ = self.get_current_and_prev_items(op_series)
        raw_metrics['operating_profit_ttm'] = op_curr

        # Net Income
        ni_series = self.get_data(self.pl, keys_map['net_income'])
        _, ni_curr, _, ni_prev = self.get_current_and_prev_items(ni_series)
        raw_metrics['net_income_ttm'] = ni_curr

        # Operating Cash Flow
        ocf_series = self.get_data(self.cf, keys_map['ocf'])
        _, ocf_curr, _, ocf_prev = self.get_current_and_prev_items(ocf_series)
        raw_metrics['operating_cash_flow_ttm'] = ocf_curr

        # CapEx (PPE & Intangibles)
        capex_ppe_series = self.get_data(self.cf, keys_map['capex_ppe'])
        _, capex_ppe_curr, _, capex_ppe_prev = self.get_current_and_prev_items(capex_ppe_series)
        raw_metrics['capex_ppe_ttm'] = abs(capex_ppe_curr) if capex_ppe_curr is not None else 0

        capex_int_series = self.get_data(self.cf, keys_map['capex_intangibles'])
        _, capex_int_curr, _, capex_int_prev = self.get_current_and_prev_items(capex_int_series)
        raw_metrics['capex_intangibles_ttm'] = abs(capex_int_curr) if capex_int_curr is not None else 0

        raw_metrics['total_capex_ttm'] = raw_metrics['capex_ppe_ttm'] + raw_metrics['capex_intangibles_ttm']

        # Free Cash Flow
        if raw_metrics['operating_cash_flow_ttm'] is not None:
            raw_metrics['free_cash_flow_ttm'] = raw_metrics['operating_cash_flow_ttm'] - raw_metrics['total_capex_ttm']
        else:
            raw_metrics['free_cash_flow_ttm'] = None
            
        # Calculate Previous FCF for Growth Metric
        total_capex_prev = (abs(capex_ppe_prev) if capex_ppe_prev is not None else 0) + \
                           (abs(capex_int_prev) if capex_int_prev is not None else 0)

        fcf_prev = None
        if ocf_prev is not None:
            fcf_prev = ocf_prev - total_capex_prev

        # Total Assets
        ta_series = self.get_data(self.bs, keys_map['total_assets'])
        _, ta_curr, _, ta_prev = self.get_current_and_prev_items(ta_series)
        raw_metrics['total_assets'] = ta_curr

        if ta_curr is not None and ta_prev is not None:
            raw_metrics['avg_total_assets'] = (ta_curr + ta_prev) / 2
        else:
            raw_metrics['avg_total_assets'] = ta_curr if ta_curr is not None else None

        # --- 2. Delta Metrics (YoY Growth) ---
        delta_metrics = {}

        def calc_growth(curr, prev):
            if prev is not None and prev != 0 and curr is not None:
                return ((curr - prev) / abs(prev)) * 100
            return None

        delta_metrics['revenue_growth_yoy_pct'] = calc_growth(rev_curr, rev_prev)
        delta_metrics['net_income_growth_yoy_pct'] = calc_growth(ni_curr, ni_prev)
        delta_metrics['operating_cash_flow_growth_yoy_pct'] = calc_growth(ocf_curr, ocf_prev)
        delta_metrics['free_cash_flow_growth_yoy_pct'] = calc_growth(raw_metrics['free_cash_flow_ttm'], fcf_prev)

        # --- 3. Quality Ratios ---
        quality_ratios = {}

        nm_series = self.get_data(self.fr, keys_map['net_margin_pct'])
        _, nm_val, _, _ = self.get_current_and_prev_items(nm_series)

        gm_series = self.get_data(self.fr, keys_map['gross_margin_pct'])
        _, gm_val, _, _ = self.get_current_and_prev_items(gm_series)

        om_series = self.get_data(self.fr, keys_map['operating_margin_pct'])
        _, om_val, _, _ = self.get_current_and_prev_items(om_series)

        quality_ratios['net_margin_pct'] = nm_val if nm_val is not None else (ni_curr / rev_curr * 100 if rev_curr else None)
        quality_ratios['gross_margin_pct'] = gm_val if gm_val is not None else (gp_curr / rev_curr * 100 if rev_curr else None)
        quality_ratios['operating_margin_pct'] = om_val if om_val is not None else (op_curr / rev_curr * 100 if rev_curr else None)

        if ocf_curr is not None and ni_curr is not None and ni_curr != 0:
            quality_ratios['ocf_to_net_income'] = ocf_curr / ni_curr
        else:
            quality_ratios['ocf_to_net_income'] = None

        if raw_metrics['free_cash_flow_ttm'] is not None and ni_curr is not None and ni_curr != 0:
            quality_ratios['fcf_to_net_income'] = raw_metrics['free_cash_flow_ttm'] / ni_curr
        else:
            quality_ratios['fcf_to_net_income'] = None

        # --- 4. Flags ---
        flags = {}
        if quality_ratios['ocf_to_net_income'] is not None:
            flags['flag_ocf_below_net_income'] = quality_ratios['ocf_to_net_income'] < 1
        else:
            flags['flag_ocf_below_net_income'] = None

        return {
            "agent_name": "Earnings & Cash Quality Sub-Agent",
            "raw_metrics": raw_metrics,
            "delta_metrics": delta_metrics,
            "quality_ratios": quality_ratios,
            "flags": flags
        }
