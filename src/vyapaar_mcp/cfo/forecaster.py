"""Cash Flow Forecasting using time series analysis.

Provides budget burn-rate estimation, runway prediction, and
spending trend analysis using exponential smoothing and linear
regression — no heavy ML framework required at baseline.
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any

import numpy as np


def forecast_burn_rate(
    daily_spends_paise: list[int],
    budget_remaining_paise: int,
    forecast_days: int = 30,
) -> dict[str, Any]:
    """Estimate budget runway and forecast future spending.

    Uses exponential weighted moving average for trend detection
    and linear projection for runway estimation.

    Args:
        daily_spends_paise: Historical daily spend in paise (most recent last).
        budget_remaining_paise: Current remaining budget in paise.
        forecast_days: Number of days to project forward.
    """
    if not daily_spends_paise:
        return {
            "error": "No spending data provided",
            "runway_days": None,
        }

    spends = np.array(daily_spends_paise, dtype=np.float64)
    n = len(spends)

    # Simple moving average
    avg_daily = float(np.mean(spends))

    # Exponentially weighted moving average (recent days have more weight)
    alpha = 0.3
    ewma = float(spends[0])
    for val in spends[1:]:
        ewma = alpha * val + (1 - alpha) * ewma
    trend_daily = ewma

    # Linear trend (slope)
    if n >= 3:
        x = np.arange(n, dtype=np.float64)
        coeffs = np.polyfit(x, spends, 1)
        slope = float(coeffs[0])
        intercept = float(coeffs[1])
    else:
        slope = 0.0
        intercept = avg_daily

    # Runway estimation
    if trend_daily > 0:
        runway_days = int(budget_remaining_paise / trend_daily)
    else:
        runway_days = None  # Not spending

    # Forecast
    forecast: list[dict[str, Any]] = []
    remaining = budget_remaining_paise
    for day in range(1, forecast_days + 1):
        projected = max(0, intercept + slope * (n + day))
        remaining = max(0, remaining - int(projected))
        forecast.append({
            "day": day,
            "date": (_dt.date.today() + _dt.timedelta(days=day)).isoformat(),
            "projected_spend_paise": int(projected),
            "budget_remaining_paise": remaining,
        })

    # Severity assessment
    if runway_days is not None and runway_days <= 7:
        severity = "critical"
    elif runway_days is not None and runway_days <= 14:
        severity = "warning"
    elif runway_days is not None and runway_days <= 30:
        severity = "monitor"
    else:
        severity = "healthy"

    # Trend direction
    if slope > 0 and abs(slope) > avg_daily * 0.05:
        trend = "increasing"
    elif slope < 0 and abs(slope) > avg_daily * 0.05:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "avg_daily_spend_paise": int(avg_daily),
        "trend_daily_spend_paise": int(trend_daily),
        "trend_direction": trend,
        "slope_per_day_paise": int(slope),
        "budget_remaining_paise": budget_remaining_paise,
        "runway_days": runway_days,
        "runway_date": (
            (_dt.date.today() + _dt.timedelta(days=runway_days)).isoformat()
            if runway_days
            else None
        ),
        "severity": severity,
        "forecast": forecast[:7],  # Return first 7 days
        "data_points": n,
    }


def detect_spending_anomaly(
    daily_spends_paise: list[int],
    current_spend_paise: int,
    sigma_threshold: float = 2.0,
) -> dict[str, Any]:
    """Detect if today's spend is anomalous relative to history.

    Uses z-score analysis (how many standard deviations from mean).
    """
    if len(daily_spends_paise) < 5:
        return {
            "anomalous": False,
            "reason": "Insufficient data (need 5+ days)",
            "current_spend_paise": current_spend_paise,
        }

    spends = np.array(daily_spends_paise, dtype=np.float64)
    mean = float(np.mean(spends))
    std = float(np.std(spends))

    if std == 0:
        z_score = 0.0 if current_spend_paise == mean else float("inf")
    else:
        z_score = (current_spend_paise - mean) / std

    is_anomalous = abs(z_score) > sigma_threshold

    return {
        "anomalous": is_anomalous,
        "z_score": round(z_score, 2),
        "threshold": sigma_threshold,
        "current_spend_paise": current_spend_paise,
        "historical_mean_paise": int(mean),
        "historical_std_paise": int(std),
        "reason": (
            f"Spend is {abs(z_score):.1f}σ from mean"
            if is_anomalous
            else "Within normal range"
        ),
    }
