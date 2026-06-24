"""Configuration values for time-series trend adjustments."""

from enum import Enum

from config.settings import INVESTMENT_PROFILE


class InvestmentProfile(Enum):
    """User risk appetite for trend adjustments."""

    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


def parse_investment_profile(profile: str) -> InvestmentProfile:
    """Validate and return an investment-profile configuration value."""

    try:
        return InvestmentProfile(profile.upper())
    except ValueError as error:
        raise ValueError(
            f"Invalid INVESTMENT_PROFILE: {profile}. "
            "Must be CONSERVATIVE, MODERATE, or AGGRESSIVE."
        ) from error


# Exponential smoothing alphas per metric smoothing category.
# Higher alpha = more weight on recent observations (ranges 0.0-1.0).
# Used when a time series has at most 10 observations.
EMA_ALPHA_BY_CATEGORY = {
    "high": 0.50,      # Margins (gross, operating, net, EBITDA, FCF, OCF)
    "medium": 0.35,    # Returns (ROA, ROE), cash flow to ratios
    "low": 0.25,       # Leverage and debt ratios, liquidity ratios
}

# Mapping of each metric to its smoothing category for EMA selection.
METRIC_EMA_CATEGORY = {
    # High volatility: margins are sensitive to one-time items, revenue shifts
    "gross_margin": "high",
    "operating_margin": "high",
    "net_margin": "high",
    "ebitda_margin": "high",
    "free_cash_flow_margin": "high",
    "operating_cash_flow_margin": "high",
    # Medium volatility: returns and cash flow conversion ratios
    "return_on_assets": "medium",
    "return_on_equity": "medium",
    "operating_cash_flow_to_net_income": "medium",
    "free_cash_flow_to_debt": "medium",
    # Low volatility: leverage and liquidity are more stable
    "cash_ratio": "low",
    "quick_ratio": "low",
    "current_ratio": "low",
    "equity_ratio": "low",
    "debt_to_assets": "low",
    "debt_to_equity": "low",
    "liabilities_to_assets": "low",
    "interest_coverage": "low",
    "net_debt_to_ebitda": "low",
    "working_capital_to_assets": "low",
    "retained_earnings_to_assets": "low",
}

TREND_CLIPPING_RANGE = (-1.0, 1.0)  # Trend normalized to [-1, +1]

# Three or fewer observations leave the latest row unchanged.
MINIMUM_TREND_PERIODS = 3
NO_TREND_ADJUSTMENT_MAX_PERIODS = 3
MAX_STALE_BALANCE_SHEET_PERIODS = 1

# Time series length threshold for switching calculation method.
# 4-10 observations: exponential smoothing.
# More than 10 observations: timestamp-aware linear regression.
TIMESERIES_LENGTH_THRESHOLD = 10

PERIOD_MONTHS_BY_FREQUENCY = {
    "quarterly": 3,
    "annual": 12,
}

ALIGNMENT_TOLERANCE_DAYS_BY_FREQUENCY = {
    "quarterly": 45,
    "annual": 60,
}

# Trend sensitivity multipliers by investment profile.
# Determines the maximum adjustment relative to the metric scale.
# adjusted = current + scale * normalized_trend * sensitivity
TREND_SENSITIVITY = {
    InvestmentProfile.CONSERVATIVE: 0.10,  # ±10% adjustment
    InvestmentProfile.MODERATE: 0.15,      # ±15% adjustment
    InvestmentProfile.AGGRESSIVE: 0.20,    # ±20% adjustment
}

TREND_ADJUSTMENT_LIMIT = TREND_SENSITIVITY[
    parse_investment_profile(INVESTMENT_PROFILE)
]
MIN_TREND_ADJUSTMENT = -TREND_ADJUSTMENT_LIMIT
MAX_TREND_ADJUSTMENT = TREND_ADJUSTMENT_LIMIT


def get_trend_sensitivity(profile: str) -> float:
    """Return the configured adjustment ceiling for an investment profile."""

    return TREND_SENSITIVITY[parse_investment_profile(profile)]
