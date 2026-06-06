"""Darts-based time series forecasting (optional upgrade).

Falls back to numpy forecaster when u8darts is not installed.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def forecast_with_darts(
    daily_spends_paise: list[int],
    budget_remaining_paise: int,
    forecast_days: int = 30,
) -> dict[str, Any] | None:
    """Run Darts ExponentialSmoothing forecast. Returns None if darts unavailable."""
    try:
        from darts import TimeSeries
        from darts.models import ExponentialSmoothing
    except ImportError:
        return None

    if len(daily_spends_paise) < 7:
        return None

    try:
        import numpy as np

        values = np.array(daily_spends_paise, dtype=np.float64) / 100.0  # rupees
        series = TimeSeries.from_values(values)
        model = ExponentialSmoothing()
        model.fit(series)
        pred = model.predict(forecast_days)
        pred_values = pred.values().flatten()

        avg_daily = float(values.mean()) * 100
        trend_daily = float(pred_values[0]) * 100 if len(pred_values) else avg_daily
        runway_days = int(budget_remaining_paise / trend_daily) if trend_daily > 0 else None

        forecast = []
        remaining = budget_remaining_paise
        import datetime as _dt
        for day, val in enumerate(pred_values[:7], start=1):
            projected = int(val * 100)
            remaining = max(0, remaining - projected)
            forecast.append({
                "day": day,
                "date": (_dt.date.today() + _dt.timedelta(days=day)).isoformat(),
                "projected_spend_paise": projected,
                "budget_remaining_paise": remaining,
            })

        if runway_days is not None and runway_days <= 7:
            severity = "critical"
        elif runway_days is not None and runway_days <= 14:
            severity = "warning"
        elif runway_days is not None and runway_days <= 30:
            severity = "monitor"
        else:
            severity = "healthy"

        return {
            "engine": "darts",
            "avg_daily_spend_paise": int(avg_daily),
            "trend_daily_spend_paise": int(trend_daily),
            "budget_remaining_paise": budget_remaining_paise,
            "runway_days": runway_days,
            "severity": severity,
            "forecast": forecast,
            "data_points": len(daily_spends_paise),
        }
    except Exception as exc:
        logger.warning("Darts forecast failed, using numpy fallback: %s", exc)
        return None
