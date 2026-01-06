from typing import Any, Dict, TypedDict, Union

from src.core.schema import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
    TechnicalConsensus,
)



SubAgentOutput = Union[
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
]


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
