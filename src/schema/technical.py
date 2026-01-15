from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


# ----------------------------
# Shared building blocks
# ----------------------------

Confidence = Literal["low", "medium", "high"]


class _BaseOut(BaseModel):
    """Forgiving base: ignores unexpected fields to reduce pipeline breakage."""
    model_config = ConfigDict(extra="ignore")


# ----------------------------
# Trend Agent
# ----------------------------

TrendDirection = Literal["bullish", "bearish", "neutral"]
TrendStrength = Literal["weak", "moderate", "strong", "very_strong"]
TrendPhase = Literal["early", "developing", "mature", "extended"]


class TrendSummary(_BaseOut):
    direction: TrendDirection
    strength: TrendStrength
    phase: TrendPhase
    confidence: Confidence


class TrendKeyMetrics(_BaseOut):
    ema_stack: Optional[str] = None
    ema10_slope_atr_norm: Optional[float] = None
    ema50_slope_atr_norm: Optional[float] = None
    ema100_slope_atr_norm: Optional[float] = None
    adx14: Optional[float] = None
    ichimoku_regime: Optional[Literal["bullish", "bearish", "neutral"]] = None
    price_vs_cloud_pct: Optional[float] = None
    atr14_percent: Optional[float] = None
    doji_ratio: Optional[float] = None


class TrendAgentOutput(_BaseOut):
    trend_summary: TrendSummary
    primary_causes: List[str] = Field(default_factory=list)
    trend_health_flags: List[str] = Field(default_factory=list)
    key_metrics: TrendKeyMetrics = Field(default_factory=TrendKeyMetrics)


# ----------------------------
# Oscillator Agent
# ----------------------------

MomentumState = Literal["accelerating", "steady", "fading", "mixed"]
OBOS = Literal["overbought", "oversold", "neutral"]
OscRegime = Literal["trend_following", "mean_reversion_risk", "climax"]


class OscillatorSummary(_BaseOut):
    momentum_state: MomentumState
    overbought_oversold: OBOS
    regime: OscRegime
    confidence: Confidence


class OscillatorKeyMetrics(_BaseOut):
    rsi14: Optional[float] = None
    rsi_slope: Optional[float] = None
    macd_hist: Optional[float] = None
    macd_hist_slope: Optional[float] = None
    adx14: Optional[float] = None
    market_regime_state: Optional[str] = None
    doji_ratio: Optional[float] = None


class OscillatorAgentOutput(_BaseOut):
    oscillator_summary: OscillatorSummary
    primary_causes: List[str] = Field(default_factory=list)
    divergence_and_exhaustion_flags: List[str] = Field(default_factory=list)
    key_metrics: OscillatorKeyMetrics = Field(default_factory=OscillatorKeyMetrics)


# ----------------------------
# Volatility Agent
# ----------------------------

VolRegime = Literal["EXPANSION", "CONTRACTION", "COOLING_OFF", "RISING_VOL", "MIXED"]


class VolatilitySummary(_BaseOut):
    regime: VolRegime
    squeeze: bool
    confidence: Confidence


class VolatilityKeyMetrics(_BaseOut):
    keltner_regime: Optional[str] = None
    keltner_position_pct: Optional[float] = None
    bollinger_regime: Optional[str] = None
    bollinger_position_pct: Optional[float] = None
    bollinger_band_width: Optional[float] = None
    log_return_std: Optional[float] = None
    historical_volatility: Optional[float] = None
    synthesis_regime: Optional[str] = None
    main_driver: Optional[str] = None
    doji_ratio: Optional[float] = None


class VolatilityAgentOutput(_BaseOut):
    volatility_summary: VolatilitySummary
    primary_causes: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    key_metrics: VolatilityKeyMetrics = Field(default_factory=VolatilityKeyMetrics)


# ----------------------------
# Volume Agent
# ----------------------------

Participation = Literal["expanding", "normal", "fading", "mixed"]
FlowBias = Literal["accumulation", "distribution", "neutral", "mixed"]
Efficiency = Literal["high", "moderate", "low", "mixed"]


class VolumeSummary(_BaseOut):
    participation: Participation
    flow_bias: FlowBias
    efficiency: Efficiency
    confidence: Confidence


class VolumeKeyMetrics(_BaseOut):
    vma_ratio: Optional[float] = None
    rvol: Optional[float] = None
    obv_slope: Optional[float] = None
    cvd_slope: Optional[float] = None
    mfi14: Optional[float] = None
    vwap_distance_pct: Optional[float] = None
    rv_30: Optional[float] = None
    rv_90: Optional[float] = None
    doji_ratio: Optional[float] = None


class VolumeAgentOutput(_BaseOut):
    volume_summary: VolumeSummary
    primary_causes: List[str] = Field(default_factory=list)
    conflict_and_risk_flags: List[str] = Field(default_factory=list)
    key_metrics: VolumeKeyMetrics = Field(default_factory=VolumeKeyMetrics)


# ----------------------------
# Support / Resistance Agent
# ----------------------------

SRStatus = Literal["BULLISH_BIAS", "BEARISH_BIAS", "NEUTRAL"]
NearestBias = Literal["near_support", "near_resistance", "between_levels", "no_overhead_resistance"]
ZoneType = Literal["SUPPORT", "RESISTANCE"]


class SRLevel(_BaseOut):
    price: float
    strength_score: Optional[float] = None
    contributors: List[str] = Field(default_factory=list)


class SRZone(_BaseOut):
    type: ZoneType
    price_range: List[float] = Field(default_factory=list)  # e.g., [low, high]
    avg_price: float
    strength_score: Optional[float] = None
    contributors: List[str] = Field(default_factory=list)


class SRKeyZones(_BaseOut):
    nearest_support: SRLevel
    nearest_resistance: Optional[SRLevel] = None
    top_confluence_zones: List[SRZone] = Field(default_factory=list)


class SRKeyMetrics(_BaseOut):
    current_price: Optional[float] = None
    doji_ratio: Optional[float] = None
    nearest_support_distance_pct: Optional[float] = None


class SRSummary(_BaseOut):
    status: SRStatus
    nearest_level_bias: NearestBias
    confidence: Confidence


class SupportResistanceAgentOutput(_BaseOut):
    sr_summary: SRSummary
    primary_causes: List[str] = Field(default_factory=list)
    key_zones: SRKeyZones
    risk_flags: List[str] = Field(default_factory=list)
    key_metrics: SRKeyMetrics = Field(default_factory=SRKeyMetrics)


# ----------------------------
# Aggregator Output Models
# ----------------------------

SignalBias = Literal["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]

class ConflictAlert(BaseModel):
    agent_a: str
    agent_b: str
    description: str
    severity: Literal["low", "medium", "high"]

class TradeScenario(BaseModel):
    scenario_type: Literal["continuation", "reversal", "breakout", "range_bound"]
    probability: Literal["low", "medium", "high"]
    description: str
    invalidation_condition: str

class TechnicalConsensus(BaseModel):
    """Final output structure for the Technical Analysis Aggregator."""
    signal_bias: SignalBias
    confidence_score: float = Field(description="Confidence from 0.0 to 1.0")
    
    executive_summary: str = Field(description="A concise 3-sentence summary for the Portfolio Manager.")
    technical_narrative: str = Field(description="Detailed synthesis of how the factors interact.")
    
    confluence_factors: List[str] = Field(description="List of factors where agents agree.")
    conflicts: List[ConflictAlert] = Field(description="Disagreements between agents.")
    
    key_levels_to_watch: List[float] = Field(description="Price levels strictly filtered by confluence.")
    scenarios: List[TradeScenario]
    
    primary_risk: str = Field(description="The single biggest technical threat to the thesis.")