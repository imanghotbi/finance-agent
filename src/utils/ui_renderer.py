from typing import Any
import pandas as pd
from src.schema.technical import TechnicalConsensus
from src.schema.fundamental import FundamentalAnalysisOutput
from src.schema.social_news import NewsSocialFusionOutput


TRANSLATIONS = {
    "STRONG_BUY": "خرید قوی",
    "BUY": "خرید",
    "NEUTRAL": "خنثی",
    "SELL": "فروش",
    "STRONG_SELL": "فروش قوی",
    "Strong Buy": "خرید قوی",
    "Buy": "خرید",
    "Hold": "نگهداری",
    "Sell": "فروش",
    "Strong Sell": "فروش قوی",
    "Bullish": "صعودی",
    "Bearish": "نزولی",
    "Aligned": "همسو",
    "Overheated": "بیش‌ازحد داغ",
    "Fragile": "شکننده",
    "Panic": "هراس",
    "Conflicted": "متعارض",
    "Primary": "سناریوی اصلی",
    "Alternative": "سناریوی جایگزین",
}


def tr(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value)
    return TRANSLATIONS.get(text, text)

def render_technical_report(report: TechnicalConsensus) -> str:
    md = (
        f"### 📈 گزارش اجماع تکنیکال\n"
        f"**سیگنال نهایی:** {tr(report.signal_bias)} (میزان اطمینان: {report.confidence_score:.2f})\n\n"
        f"**خلاصه اجرایی:**\n"
        f"{report.executive_summary}\n\n"
        f"**روایت تحلیلی:**\n"
        f"{report.technical_narrative}\n\n"
        f"**سطوح کلیدی:**\n"
        f"{', '.join([str(l) for l in report.key_levels_to_watch])}\n\n"
        f"**هم‌راستایی پول هوشمند:** {report.institutional_alignment}\n"
        f"**واگرایی پول هوشمند:** {'⚠️ بله' if report.smart_money_divergence else '✅ خیر'}\n\n"
        f"**ریسک اصلی:**\n"
        f"{report.primary_risk}\n\n"
        f"#### سناریوها\n"
    )
    for s in report.scenarios:
        md += f"- **{tr(s.scenario_type)}** ({s.probability}): {s.description} (ابطال سناریو: {s.invalidation_condition})\n"
    
    return md

def render_fundamental_report(report: FundamentalAnalysisOutput) -> str:
    md = (
        f"### 📊 گزارش اجماع بنیادی\n"
        f"**جهت‌گیری سرمایه‌گذاری:** {tr(report.investment_bias.value)} (میزان اطمینان: {report.confidence_score:.2f})\n\n"
        f"**خلاصه اجرایی:**\n"
        f"{report.executive_summary}\n\n"
        f"**ارکان تحلیل:**\n"
        f"- **تاب‌آوری مالی:** {report.financial_resilience}\n"
        f"- **کیفیت کسب‌وکار:** {report.business_quality}\n"
        f"- **ارزش‌گذاری:** {report.valuation_context}\n"
        f"- **چشم‌انداز راهبردی:** {report.strategic_outlook}\n\n"
        f"#### محرک‌های اصلی\n"
    )
    for d in report.key_drivers:
        md += f"- ✅ {d}\n"
        
    md += "\n#### ریسک‌ها\n"
    for r in report.thesis_risks:
        md += f"- ⚠️ {r}\n"
        
    return md

def render_social_report(report: NewsSocialFusionOutput) -> str:
    md = (
        f"### 🐦 گزارش اخبار و شبکه‌های اجتماعی\n"
        f"**جهت‌گیری:** {tr(report.information_bias)} (میزان اطمینان: {report.confidence_score:.2f})\n\n"
        f"**خلاصه اجرایی:**\n"
        f"{report.executive_summary}\n\n"
        f"**ارزیابی روایت بازار:**\n"
        f"**{tr(report.narrative_assessment.state)}**: {report.narrative_assessment.explanation}\n\n"
        f"**عوامل کلیدی:**\n"
    )
    for d in report.key_drivers:
        md += f"- {d}\n"

    if report.scenarios:
        md += "\n**سناریوهای روایی:**\n"
        for scenario in report.scenarios:
            md += f"- **{tr(scenario.scenario_type)}:** {scenario.description}\n"

    md += f"\n**نقطه ابطال روایت:** {report.narrative_kill_switch}\n"
    
    return md

def render_final_report(text: str) -> str:
    return (
        f"# 📝 گزارش نهایی دستیار مالی\n\n"
        f"{text}\n"
    )


def build_candlestick_chart(price_history: list[dict], symbol: str, short_name: str | None = None):
    if not price_history:
        return None

    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    df = pd.DataFrame(price_history)
    required_columns = {"date_time", "open_price", "high_price", "low_price", "real_close_price"}
    if not required_columns.issubset(df.columns):
        return None

    df = df[list(required_columns | {"volume"} & set(df.columns))].copy()
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df.dropna(subset=["date_time", "open_price", "high_price", "low_price", "real_close_price"], inplace=True)
    if df.empty:
        return None

    df.sort_values("date_time", inplace=True)

    figure = go.Figure(
        data=[
            go.Candlestick(
                x=df["date_time"],
                open=df["open_price"],
                high=df["high_price"],
                low=df["low_price"],
                close=df["real_close_price"],
                name=symbol,
            )
        ]
    )
    display_name = f"{symbol} - {short_name}" if short_name else symbol
    figure.update_layout(
        title=f"Candlestick Chart: {display_name}",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=500,
    )
    return figure
