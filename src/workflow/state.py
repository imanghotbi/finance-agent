from typing import Annotated, TypedDict, List, Literal, Dict, Any
from schema import SubAgentOutput



class TechnicalState(TypedDict):
    symbol: str
    visual_data: Dict[str, Any]
    technical_data: Dict[str, Any]
    
    # Outputs (The Aggregated Report)
    trend_report: SubAgentOutput
    oscillator_report: SubAgentOutput
    volatility_report: SubAgentOutput
    volume_report: SubAgentOutput
    sr_report: SubAgentOutput