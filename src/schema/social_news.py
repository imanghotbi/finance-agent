from pydantic import BaseModel, Field 
from typing import List , Literal , Optional

# ----------------------------
# Tweet Agent
# ----------------------------

class SentimentDistribution(BaseModel):
    very_bullish: float = Field(...,description="Proportion of social messages expressing strong positive sentiment and aggressive optimism.")
    bullish: float = Field(...,description="Proportion of messages with moderate positive sentiment.")
    neutral: float = Field(...,description="Proportion of messages that are informational or emotionally neutral.")
    bearish: float = Field(...,description="Proportion of messages with moderate negative sentiment.")
    very_bearish: float = Field(...,description="Proportion of messages expressing strong negative sentiment, fear, or accusations.")

class EmotionVector(BaseModel):
    optimism: float = Field(...,description="Degree of positive expectations about future performance, growth, or price increase.")
    fear: float = Field(...,description="Degree of concern related to losses, debt, regulation, or financial instability.")
    anger: float = Field(...,description="Degree of frustration or outrage, often linked to corruption, mismanagement, or rent-seeking claims.")
    trust: float = Field(...,description="Degree of confidence in management decisions, macro conditions, or official policies.")
    speculation: float = Field(...,description="Degree of short-term trading behavior, hype, or tactical buy/sell calls.")

class SocialSentimentOutput(BaseModel):

    sentiment_distribution: SentimentDistribution = Field(...,description="Normalized distribution of sentiment polarity across analyzed social media messages.")
    emotion_vector: EmotionVector = Field(...,description="Aggregated emotional profile extracted from social discussions.")
    weighted_sentiment_score: float = Field(...,description=(
            "Engagement-weighted sentiment score in range [-1, +1]. "
            "Negative values indicate bearish pressure; positive values indicate bullish pressure."
        )
    )
    dominant_bias: str = Field(...,
        description=(
            "Human-readable interpretation of the dominant market sentiment "
            "(e.g. 'bullish', 'slightly bearish', 'mixed', 'highly bearish')."
        )
    )
    social_summary: str = Field(...,
        description=(
            "Short factual summary of key events, concerns, and discussions observed in recent tweets "
            "and forum posts, without prediction or investment advice."
        )
    )

# ----------------------------
# Sahamyab tweet Agent
# ----------------------------

class RetailPulseAnalysis(BaseModel):
    retail_sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="A floating point number between -1.0 (Extremely Negative) and 1.0 (Extremely Positive) representing the aggregate sentiment.")
    market_structure_signal: str = Field(..., description="A short string describing the market state, e.g., 'Bullish Reversal', 'Sell Queue', 'Buy Queue', 'Range Bound'.")
    macro_drivers: List[str] = Field(..., description="A list of external economic factors mentioned by users influencing the stock (e.g., Dollar rate, political news).")
    actionable_insight: str = Field(..., description="A synthesized conclusion explaining what retail traders are actually doing (e.g., shifting to buy side).")
    panic_level: Literal["Low", "Medium", "High", "Extreme"] = Field(..., description="The observed level of fear or irrational behavior in the comments.")

# ----------------------------
# News Agent
# ----------------------------

class CorporateEvent(BaseModel):
    category: Literal["Dividend", "Capital Increase", "Regulatory Warning", "General Impact"] = Field(...,description="The specific category of the event based on the prompt's focus areas.")
    details: str = Field(...,description="A concise summary of the hard fact (e.g., '370 Rials DPS distributed', 'License issued for 35% capital increase').")
    impact_type: Literal["Monetary", "Governance"] = Field(...,description="Classifies if the impact is on direct cash flow/valuation (Monetary) or management quality/risk (Governance).")
    sentiment: Literal["Positive", "Negative", "Neutral"] = Field(...,description="The distinct sentiment of this specific event.")

class FundamentalNewsAnalysis(BaseModel):
    news_sentiment_score: float = Field(...,ge=-1.0,le=1.0,description="Aggregate sentiment score derived from all news items (-1.0 to 1.0).")
    corporate_events: List[CorporateEvent] = Field(...,description="List of extracted hard corporate events.")
    summary: str = Field(...,description="A high-level executive summary of the fundamental news landscape for the period.")

# ----------------------------
# Social and News Agent
# ----------------------------

class NarrativeAssessment(BaseModel):
    state: Literal["Aligned","Overheated","Fragile","Panic","Conflicted"] = Field(...,description="Describes whether sentiment, behavior, and facts are coherent or diverging.")
    explanation: str = Field(...,description="Concise explanation of why the narrative is classified in this state.")

class InformationScenario(BaseModel):
    scenario_type: Literal["Primary", "Alternative"] = Field(...)
    description: str = Field(...,description="Expected behavioral or narrative evolution under this scenario.")

class NewsSocialFusionOutput(BaseModel):
    information_bias: Literal["Bullish", "Neutral", "Bearish"] = Field(...,description="Final bias derived from weighted information and behavioral evidence.")
    confidence_score: float = Field(...,ge=0.0,le=1.0,description="Confidence in the information bias after resolving conflicts.")
    narrative_assessment: NarrativeAssessment = Field(...,description="High-level diagnosis of the information environment.")
    key_drivers: List[str] = Field(...,description="Bullet list of dominant forces shaping sentiment and behavior.")
    executive_summary: str = Field(...,
        description=(
            "Institutional-grade summary explaining whether news and social dynamics "
            "support, distort, or threaten price stability."
        )
    )
    scenarios: List[InformationScenario] = Field(...,description="Primary and alternative narrative-driven market paths.")
    narrative_kill_switch: str = Field(...,
        description=(
            "Specific event or shift that would invalidate the current information bias "
            "(e.g., regulatory denial, sentiment collapse, retail capitulation)."
        )
    )
