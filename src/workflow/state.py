from typing import Any, Dict, TypedDict, Annotated
import operator

from src.schema.technical import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
    TechnicalConsensus,
    SmartMoneyAnalysis
)
from src.schema.fundamental import (
    BalanceSheetAgentState,
    BalanceSheetOutput,
    EarningsQualityAgentState,
    EarningsQualityOutput,
    ValuationAgentState,
    ValuationOutput,
    FundamentalAnalysisOutput,
    CodalAgentState,
    CodalAnalysisOutput
)
from src.schema.social_news import (
    SocialSentimentOutput,
    RetailPulseAnalysis,
    FundamentalNewsAnalysis,
    NewsSocialFusionOutput
)

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**a, **b}

def update_latest(old, new):
    return new

class TechnicalState(TypedDict):
    symbol: str
    visual_data: Dict[str, Any]
    technical_data: Dict[str, Any]
    
    trend_report: TrendAgentOutput
    oscillator_report: OscillatorAgentOutput
    volatility_report: VolatilityAgentOutput
    volume_report: VolumeAgentOutput
    sr_report: SupportResistanceAgentOutput
    technical_consensus_report: TechnicalConsensus
    smart_money_report:SmartMoneyAnalysis

class FundamentalState(TypedDict):
    symbol: str
    fundamental_data: Dict[str, Any]
    
    # Outputs
    balance_sheet_report: BalanceSheetAgentState
    balance_sheet_analysis_report: BalanceSheetOutput
    earnings_quality_report: EarningsQualityAgentState
    earnings_quality_analysis_report: EarningsQualityOutput
    valuation_report: ValuationAgentState
    valuation_analysis_report: ValuationOutput
    codal_report: CodalAgentState
    codal_analysis_report: CodalAnalysisOutput
    fundamental_consensus_report: FundamentalAnalysisOutput

class NewsSocialState(TypedDict):
    symbol: str
    news_social_data: Dict[str, Any]
    
    # Outputs
    twitter_report: SocialSentimentOutput
    sahamyab_report: RetailPulseAnalysis
    news_report: FundamentalNewsAnalysis
    social_news_consensus_report: NewsSocialFusionOutput

class AgentState(TypedDict):
    
    symbol: Annotated[str, update_latest]
    short_name: str
    analysis_started_at: str
    analysis_completed_at: str
    time_consumption_seconds: float
    time_consumption_display: str
    messages: list[Any]
    price_history: list[Dict[str, Any]]
    
    # Inputs
    technical_data: Dict[str, Any]
    fundamental_data: Dict[str, Any]
    news_social_data: Dict[str, Any]
    
    # Technical Outputs
    trend_report: TrendAgentOutput
    oscillator_report: OscillatorAgentOutput
    volatility_report: VolatilityAgentOutput
    volume_report: VolumeAgentOutput
    sr_report: SupportResistanceAgentOutput
    technical_consensus_report: TechnicalConsensus
    
    # Fundamental Outputs
    balance_sheet_report: BalanceSheetAgentState
    balance_sheet_analysis_report: BalanceSheetOutput
    earnings_quality_report: EarningsQualityAgentState
    earnings_quality_analysis_report: EarningsQualityOutput
    valuation_report: ValuationAgentState
    valuation_analysis_report: ValuationOutput
    codal_report: CodalAgentState
    codal_analysis_report: CodalAnalysisOutput
    fundamental_consensus_report: FundamentalAnalysisOutput
    
    # News & Social Outputs
    twitter_report: SocialSentimentOutput
    sahamyab_report: RetailPulseAnalysis
    news_report: FundamentalNewsAnalysis
    social_news_consensus_report: NewsSocialFusionOutput
    
    # Final Output
    final_report: str
