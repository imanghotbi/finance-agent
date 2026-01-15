from typing import Any, Dict, TypedDict, Annotated
import operator

from src.schema.technical import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
    TechnicalConsensus,
)
from src.schema.fundamental import (
    BalanceSheetOutput,
    EarningsQualityOutput,
    ValuationOutput,
    FundamentalAnalysisOutput,
)

def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**a, **b}

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

class FundamentalState(TypedDict):
    symbol: str
    fundamental_data: Dict[str, Any]
    
    # Outputs
    balance_sheet_report: BalanceSheetOutput
    earnings_quality_report: EarningsQualityOutput
    valuation_report: ValuationOutput
    fundamental_consensus_report: FundamentalAnalysisOutput

class AgentState(TypedDict):
    
    symbol: str
    
    # Inputs
    visual_data: Dict[str, Any]
    technical_data: Dict[str, Any]
    fundamental_data: Dict[str, Any]
    
    # Technical Outputs
    trend_report: TrendAgentOutput
    oscillator_report: OscillatorAgentOutput
    volatility_report: VolatilityAgentOutput
    volume_report: VolumeAgentOutput
    sr_report: SupportResistanceAgentOutput
    technical_consensus_report: TechnicalConsensus
    
    # Fundamental Outputs
    balance_sheet_report: BalanceSheetOutput
    earnings_quality_report: EarningsQualityOutput
    valuation_report: ValuationOutput
    fundamental_consensus_report: FundamentalAnalysisOutput
    
    # Final Output
    final_report: str
