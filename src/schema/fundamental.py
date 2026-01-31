from typing import List
from enum import Enum
from pydantic import BaseModel, Field

# ----------------------------
# Balance Sheet Agent
# ----------------------------

class BalanceSheetSignal(str, Enum):
    ROBUST = "Robust"
    STABLE = "Stable"
    STRAINED = "Strained"
    DISTRESSED = "Distressed"

class FinancialStability(BaseModel):
    liquidity_strength: str = Field(..., description="Assessment of short-term liquidity (e.g., 'Strong with Current Ratio > 1.5')")
    debt_pressure: str = Field(..., description="Assessment of leverage (e.g., 'Low risk, Debt/Equity < 0.5')")
    capital_buffer: str = Field(..., description="Assessment of cash reserves (e.g., 'High cash reserves covering 20% of liabilities')")

class CapitalAllocation(BaseModel):
    dividend_sustainability: str = Field(..., description="Is the payout ratio sustainable? (e.g., 'Sustainable at 40% payout')")
    balance_sheet_impact: str = Field(..., description="How allocation affects the sheet (e.g., 'Retained earnings strengthening equity')")

class BalanceSheetOutput(BaseModel):
    balance_sheet_signal: BalanceSheetSignal = Field(..., description="Overall financial health status")
    
    financial_stability: FinancialStability
    capital_allocation: CapitalAllocation
    
    core_causes: List[str] = Field(..., description="List of 3 distinct reasons for the signal", min_items=1, max_items=3)
    risk_flags: List[str] = Field(..., description="Specific risks identified", min_items=0)

# ----------------------------
# Earning Quality Agent
# ----------------------------

class EarningsSignal(str, Enum):
    HIGH_QUALITY = "High Quality"
    GROWING_BUT_CAPITAL_INTENSIVE = "Growing but Capital Intensive"
    MIXED = "Mixed"
    LOW_QUALITY = "Low Quality"

class ProfitabilityProfile(BaseModel):
    margin_health: str = Field(..., description="Status of margins (e.g., 'Healthy Net Margin at 43%')")
    growth_trend: str = Field(..., description="Status of growth (e.g., 'Accelerating revenue growth (+40% YoY)')")

class CashReality(BaseModel):
    conversion_quality: str = Field(..., description="Relationship between Profit and Cash (e.g., 'High quality, OCF > Net Income')")
    capex_intensity: str = Field(..., description="Impact of reinvestment on free cash (e.g., 'Heavy Capex reducing FCF')")

class EarningsQualityOutput(BaseModel):
    earnings_signal: EarningsSignal = Field(..., description="Overall quality status of earnings")
    
    profitability_profile: ProfitabilityProfile
    cash_reality: CashReality
    
    core_causes: List[str] = Field(..., description="List of 3 distinct reasons for the signal", min_items=1, max_items=3)
    risk_flags: List[str] = Field(..., description="Specific quality risks (e.g., paper profits)", min_items=0)

# ----------------------------
# Valuation Agent
# ----------------------------

class ValuationSignal(str, Enum):
    UNDERVALUED = "Undervalued"
    FAIRLY_VALUED = "Fairly Valued"
    PREMIUM_PRICING = "Premium Pricing"
    OVERVALUED = "Overvalued"

class ValuationMultiples(BaseModel):
    pe_context: str = Field(..., description="P/E relative to market norms (e.g., 'Attractive P/E of 5.5 vs Sector 7.0')")
    asset_backing: str = Field(..., description="P/B or Asset value context (e.g., 'High P/B justified by ROE')")

class MarketStructure(BaseModel):
    liquidity_status: str = Field(..., description="Float and tradeability (e.g., 'Highly liquid with 30% float')")
    market_weight: str = Field(..., description="Influence on the index (e.g., 'Market Leader / Big Cap')")

class ValuationOutput(BaseModel):
    valuation_signal: ValuationSignal = Field(..., description="Overall valuation attractiveness")
    
    valuation_multiples: ValuationMultiples
    market_structure: MarketStructure
    
    core_causes: List[str] = Field(..., description="List of 3 distinct reasons for the signal", min_items=1, max_items=3)
    risk_flags: List[str] = Field(..., description="Specific valuation risks (e.g., Value Trap)", min_items=0)

# ----------------------------
# Codal Agent
# ----------------------------

class CodalReportSelection(BaseModel):
    selected_ids: List = Field(..., description="List of IDs of the most important financial codal reports like [codal_1 , ...]")

class CodalAnalysisOutput(BaseModel):
    key_findings: List[str] = Field(..., description="List of key points extracted from the reports")
    summary: str = Field(..., description="Concise summary of the analysis")

# ----------------------------
# Fundamental Agent
# ----------------------------   

class InvestmentBias(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"

class FundamentalAnalysisOutput(BaseModel):

    financial_resilience: str = Field(
        ..., 
        description="Synthesis of Balance Sheet data. Assessment of survival capability and downside protection. (e.g., 'Fortress-like', 'Vulnerable to rate hikes')"
    )
    business_quality: str = Field(
        ..., 
        description="Synthesis of Earnings Quality. Assessment of the business model's ability to compound capital. (e.g., 'High-margin Compounder', 'Capital-intensive Cyclical')"
    )
    valuation_context: str = Field(
        ..., 
        description="Synthesis of Valuation. Assessment of the price relative to the quality identified above. (e.g., 'Premium price justified by quality', 'Value Trap')"
    )
    strategic_outlook: str = Field(
        ...,
        description="Synthesis of Codal/Corporate Reports. Assessment of catalysts, management sentiment, and material events found in the reports. (e.g., 'Positive Capital Increase Pending', 'Management warning on supply chain')"
    )

    investment_bias: InvestmentBias = Field(..., description="The final recommendation based on the synthesis of the 3 pillars")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence level in the thesis (0.0 to 1.0)")
    
    executive_summary: str = Field(..., description="Institutional-grade thesis summary (2-3 sentences) linking Quality, Resilience, and Price.")
    
    key_drivers: List[str] = Field(..., description="Top 3 positive factors driving the decision", min_items=1, max_items=3)
    thesis_risks: List[str] = Field(..., description="Top 3 negative risks that could invalidate the thesis", min_items=1, max_items=3)