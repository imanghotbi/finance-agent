import numpy as np
import talib
import pandas as pd
from src.services.analysis.base import BaseTechnicalAnalyzer

class VolumeAnalyzer(BaseTechnicalAnalyzer):
    
    def analyze(self, current_price=None):
        c = self.df['close'].values.astype(float)
        h = self.df['high'].values.astype(float)
        l = self.df['low'].values.astype(float)
        o = self.df['open'].values.astype(float)
        v = self.df['volume'].values.astype(float)
        cur_price = current_price if current_price else c[-1]

        # Indicators
        vma_20 = talib.SMA(v, timeperiod=20)
        vma_50 = talib.SMA(v, timeperiod=50)
        vma_ratio_series = pd.Series(vma_20 / (vma_50 + 1e-9))
        rvol_series = pd.Series(v / (vma_20 + 1e-9))
        
        obv = talib.OBV(c, v)
        buy_vol = np.where(c >= o, v, 0)
        sell_vol = np.where(c < o, v, 0)
        cvd = np.cumsum(buy_vol - sell_vol)

        log_ret = np.log(c[1:] / c[:-1])
        log_ret = np.insert(log_ret, 0, 0)
        log_ret_series = pd.Series(log_ret)
        rv_30 = log_ret_series.rolling(30).std() * np.sqrt(252) * 100
        rv_90 = log_ret_series.rolling(90).std() * np.sqrt(252) * 100

        mfi = talib.MFI(h, l, c, v, timeperiod=14)
        vol_weighted_ret = (log_ret_series * v) / (vma_20 + 1e-9)
        
        # VWAP
        typical = (h + l + c) / 3
        pv = pd.Series(typical * v)
        v_s = pd.Series(v)
        vwap = pv.rolling(20).sum() / v_s.rolling(20).sum()

        def get_slope_data(series, horizon, name):
            slope, r2 = self._calc_slope(pd.Series(series), horizon)
            val = float(series.iloc[-1]) if hasattr(series, 'iloc') else float(series[-1])
            
            regime = "neutral"
            if name == "vma_ratio": regime = "expanding_participation" if slope > 0 else "contracting_interest"
            elif name == "rvol": regime = "liquidity_surge" if val > 2.0 else "normal_turnover"
            elif name == "obv": regime = "strong_accumulation" if slope > 0 else "distribution"
            elif name == "cvd": regime = "aggressive_buying" if slope > 0 else "aggressive_selling"
            elif name == "rv": regime = "volatility_expansion" if slope > 0 else "volatility_compression"
            elif name == "mfi": regime = "overbought" if val > 80 else "oversold" if val < 20 else "bullish_flow" if slope > 0 else "bearish_flow"
            elif name == "vwap":
                 dist = (float(cur_price) - val) / val
                 regime = "premium_markup" if dist > 0 else "discount_markdown"

            return {
                "value": round(val, 4),
                "slope": round(slope, 4),
                "slope_horizon_bars": horizon,
                "trend_quality_r2": round(r2, 2),
                "strength": self._get_strength_r2(r2),
                "regime": regime
            }

        final_json = {
            "meta": self._build_meta(current_price),
            "volume_participation": {
                "vma_ratio": get_slope_data(vma_ratio_series, 15, "vma_ratio"),
                "rvol": get_slope_data(rvol_series, 10, "rvol")
            },
            "directional_flow": {
                "obv_20": get_slope_data(pd.Series(obv), 20, "obv"),
                "cvd": get_slope_data(pd.Series(cvd), 15, "cvd")
            },
            "relative_volume_regime": {
                "rv_30": get_slope_data(rv_30, 20, "rv"),
                "rv_90": get_slope_data(rv_90, 20, "rv")
            },
            "price_volume_efficiency": {
                "mfi_14": get_slope_data(pd.Series(mfi), 10, "mfi"),
                "volume_weighted_return": get_slope_data(vol_weighted_ret, 14, "neutral")
            },
            "institutional_reference": {
                "vwap": {
                    "distance_percent": round(((float(cur_price) - vwap.iloc[-1])/vwap.iloc[-1])*100, 2),
                    **get_slope_data(vwap, 15, "vwap")
                }
            }
        }
        del final_json["institutional_reference"]["vwap"]["value"]
        return final_json
    

if __name__ == '__main__':
    import json
    import pandas as pd
    data_source = pd.read_csv(r'C:\Users\Iman\Desktop\fin-agen\data.csv')
    trand_analyzer = VolumeAnalyzer(data_source=data_source , symbol='فملی')
    result = trand_analyzer.analyze('1000')
    print(json.dumps(result,indent=2,ensure_ascii=False))