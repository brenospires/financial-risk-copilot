# Trend Analysis Configuration Guide

## Purpose

Company risk scoring uses metrics from the final snapshot after adjusting each
present value for its historical trajectory. The trend layer returns a flat
dictionary containing one adjusted value per metric. If a metric is missing
from the final snapshot, its adjusted value is `None`, even when older values
exist. Only this final adjusted metric set is passed to company risk scoring.

The calculation remains separate from risk interpretation. A rising debt ratio
is adjusted upward and a rising interest-coverage ratio is also adjusted
upward; the risk scorer is responsible for knowing that the first is adverse
and the second is favorable.

## Investment profile

Select the investment profile in the local `.env` file:

```dotenv
INVESTMENT_PROFILE=CONSERVATIVE
```

Supported values and maximum trajectory sensitivities are:

| Profile | Maximum adjustment |
|---|---:|
| `CONSERVATIVE` | 10% |
| `MODERATE` | 15% |
| `AGGRESSIVE` | 20% |

The application validates the configured value. An unsupported profile raises
a configuration error rather than silently selecting a different profile.

## Adjustment formula

Every calculated trajectory is normalized and clipped to `[-1, 1]`. The
adjustment uses:

```text
adjusted = current + scale * normalized_trend * profile_sensitivity
```

For an ordinary nonzero metric, `scale` is the absolute current value. Near
zero, the calculation falls back to the median absolute historical magnitude.
This prevents negative values from reversing the intended adjustment and keeps
the adjustment bounded by the selected profile.

For example, debt/equity of `1.50` with a maximum upward trajectory becomes:

| Profile | Adjusted debt/equity |
|---|---:|
| `CONSERVATIVE` | 1.65 |
| `MODERATE` | 1.725 |
| `AGGRESSIVE` | 1.80 |

## Trend method selection

A metric needs at least three real observations before its trajectory can
adjust the latest value. With fewer observations, the latest available value
is returned unchanged.

- Between 3 and 20 real observations, the calculation measures the latest QoQ
  or YoY movement of EMA-smoothed metric levels.
- Above 20 real observations, it uses timestamp-aware linear-regression pace per
  reporting interval.
- A constant series has a normalized trajectory of zero.
- Missing and carried-forward values do not count as new observations.

EMA alphas are grouped by smoothing category. These categories are fixed
configuration choices, not estimates of realized metric volatility:

| Category | Alpha | Examples |
|---|---:|---|
| High | 0.50 | Profitability and cash-flow margins |
| Medium | 0.35 | Returns and cash-conversion ratios |
| Low | 0.25 | Liquidity, leverage, and capital structure |

## Period comparisons

The shared time-series utilities support calendar-aligned day-over-day,
month-over-month, quarter-over-quarter, and year-over-year comparisons. Company
adjustment selects one comparison from the statement frequency: annual
statements use YoY and quarterly statements use QoQ.

When a period lacks an observation, the latest known value can be carried
forward for trajectory context. Expected reporting grids are anchored to the
latest statement and tolerate ordinary fiscal-date drift. The carried value
retains its source timestamp and is marked as carried. It can participate in the
trajectory calculation but does not increase the count of real observations.
Carry-forward never fills a missing metric in the final snapshot used for risk
scoring.

## Negative and contextual values

Absolute change is always `current - previous`. Relative change uses the
absolute previous value as its denominator. Relative change is unavailable
when the previous value is zero, and sign crossings are identified explicitly.
CAGR is available only with sufficient positive endpoints spanning at least
one year.

Some ratios require additional interpretation:

- ROE and debt/equity are unavailable when equity is non-positive.
- Net debt/EBITDA is unavailable when EBITDA is non-positive.
- Operating cash flow/net income is unavailable when net income is
  non-positive.
- Margin ratios are unavailable when revenue is non-positive.
- Negative working capital, retained earnings, equity ratio, coverage, and
  cash-flow margins remain meaningful risk observations.

Missing or conditionally invalid metrics remain `None` in the adjusted metric
dictionary so downstream scoring can report reduced coverage instead of
inventing a value.
