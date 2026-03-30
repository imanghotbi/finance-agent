from typing import Any
import pandas as pd
from src.schema.technical import TechnicalConsensus
from src.schema.fundamental import FundamentalAnalysisOutput
from src.schema.social_news import NewsSocialFusionOutput

def render_technical_report(report: TechnicalConsensus) -> str:
    md = (
        f"### 📈 Technical Consensus Report\n"
        f"**Signal:** {report.signal_bias} (Confidence: {report.confidence_score:.2f})\n\n"
        f"**Executive Summary:**\n"
        f"{report.executive_summary}\n\n"
        f"**Narrative:**\n"
        f"{report.technical_narrative}\n\n"
        f"**Key Levels:**\n"
        f"{', '.join([str(l) for l in report.key_levels_to_watch])}\n\n"
        f"**Institutional Alignment:** {report.institutional_alignment}\n"
        f"**Smart Money Divergence:** {'⚠️ Yes' if report.smart_money_divergence else '✅ No'}\n\n"
        f"**Primary Risk:**\n"
        f"{report.primary_risk}\n\n"
        f"#### Scenarios\n"
    )
    for s in report.scenarios:
        md += f"- **{s.scenario_type}** ({s.probability}): {s.description} (Invalidation: {s.invalidation_condition})\n"
    
    return md

def render_fundamental_report(report: FundamentalAnalysisOutput) -> str:
    md = (
        f"### 📊 Fundamental Consensus Report\n"
        f"**Investment Bias:** {report.investment_bias.value} (Confidence: {report.confidence_score:.2f})\n\n"
        f"**Executive Summary:**\n"
        f"{report.executive_summary}\n\n"
        f"**Pillars:**\n"
        f"- **Financial Resilience:** {report.financial_resilience}\n"
        f"- **Business Quality:** {report.business_quality}\n"
        f"- **Valuation:** {report.valuation_context}\n"
        f"- **Strategic Outlook:** {report.strategic_outlook}\n\n"
        f"#### Key Drivers\n"
    )
    for d in report.key_drivers:
        md += f"- ✅ {d}\n"
        
    md += "\n#### Risks\n"
    for r in report.thesis_risks:
        md += f"- ⚠️ {r}\n"
        
    return md

def render_social_report(report: NewsSocialFusionOutput) -> str:
    md = (
        f"### 🐦 Social & News Consensus Report\n"
        f"**Bias:** {report.information_bias} (Confidence: {report.confidence_score:.2f})\n\n"
        f"**Executive Summary:**\n"
        f"{report.executive_summary}\n\n"
        f"**Narrative Assessment:**\n"
        f"**{report.narrative_assessment.state}**: {report.narrative_assessment.explanation}\n\n"
        f"**Key Drivers:**\n"
    )
    for d in report.key_drivers:
        md += f"- {d}\n"

    md += f"\n**Kill Switch:** {report.narrative_kill_switch}\n"
    
    return md

def render_final_report(text: str) -> str:
    return (
        f"# 📝 Final Finance Agent Report\n\n"
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
