from typing import Any, Dict, TypedDict

from src.schema.technical import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
    TechnicalConsensus,
)

class TechnicalState(TypedDict):
    symbol: str
    visual_data: Dict[str, Any]
    technical_data: Dict[str, Any]
    
    # Outputs (The Aggregated Report)
    trend_report: TrendAgentOutput
    oscillator_report: OscillatorAgentOutput
    volatility_report: VolatilityAgentOutput
    volume_report: VolumeAgentOutput
    sr_report: SupportResistanceAgentOutput
    technical_consensus_report: TechnicalConsensus
