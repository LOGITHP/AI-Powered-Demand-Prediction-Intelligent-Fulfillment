"""
Deterministic volume forecasting.

Baselines first, per the plan:
  - seasonal-naive (weekly seasonality) is the primary workhorse
  - rolling-origin backtesting with WAPE/MAPE per horizon
  - forecast is converted to task-hours via LaborStandard (workforce.py)

No LLM in this module. Upgrade path: LightGBM on engineered features
(demand lags, rolling means, calendar/seasonality) once enough history exists.
"""
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.db.models import VolumeHistory, LaborStandard

SEASON_DAYS = 7  # weekly seasonality
DEFAULT_DAILY_BASELINE = 500.0


def get_history(db: Session, warehouse_id: str, process_type: str) -> List[Tuple[datetime, float]]:
    rows = (
        db.query(VolumeHistory)
        .filter(
            VolumeHistory.warehouse_id == warehouse_id,
            VolumeHistory.process_type == process_type,
        )
        .order_by(VolumeHistory.date.asc())
        .all()
    )
    return [(r.date, r.volume) for r in rows]


def seasonal_naive(history: List[float], horizon: int, season: int = SEASON_DAYS) -> List[float]:
    """Predict each horizon step with the value from the same weekday last week."""
    preds = []
    for _ in range(horizon):
        if len(history) >= season:
            preds.append(float(history[-season]))
        elif history:
            preds.append(float(history[-1]))  # naive fallback: last observed
        else:
            preds.append(DEFAULT_DAILY_BASELINE)
        # advance the pseudo-history so multi-step forecasts keep cycling the season
        history = history + [preds[-1]]
    return preds


def moving_average(history: List[float], horizon: int, window: int = 7) -> List[float]:
    """Simple 7-day moving-average challenger model."""
    if not history:
        return [DEFAULT_DAILY_BASELINE] * horizon
    recent = history[-window:]
    mean = sum(recent) / len(recent)
    return [float(mean)] * horizon


def backtest(
    history: List[Tuple[datetime, float]],
    horizon: int = 7,
    season: int = SEASON_DAYS,
) -> dict:
    """
    Rolling-origin evaluation of the seasonal-naive baseline.

    Returns WAPE/MAPE mean per origin. WAPE is preferred for warehouse volume,
    since a zero-volume day would explode MAPE.
    """
    values = [v for _, v in history]
    if len(values) < season + horizon:
        return {
            "model": "seasonal_naive",
            "horizon_days": horizon,
            "origins": 0,
            "wape": None,
            "mape": None,
            "note": "Not enough history to backtest; need at least season + horizon points.",
        }

    origins = []
    # last 3 origins (rolling windows)
    n_origins = min(3, len(values) - season - horizon + 1)
    for k in range(n_origins):
        cut = len(values) - horizon - k
        train, actual = values[:cut], values[cut:cut + horizon]
        preds = seasonal_naive(list(train), horizon, season)
        total_actual = sum(actual)
        wape = sum(abs(a - p) for a, p in zip(actual, preds)) / total_actual if total_actual > 0 else None
        mape_list = [abs(a - p) / a for a, p in zip(actual, preds) if a > 0]
        mape = sum(mape_list) / len(mape_list) if mape_list else None
        origins.append({
            "origin_end": history[cut - 1][0].date().isoformat() if cut > 0 else None,
            "wape": round(wape, 4) if wape is not None else None,
            "mape": round(mape, 4) if mape is not None else None,
        })

    valid_wapes = [o["wape"] for o in origins if o["wape"] is not None]
    valid_mapes = [o["mape"] for o in origins if o["mape"] is not None]
    return {
        "model": "seasonal_naive",
        "horizon_days": horizon,
        "origins": len(origins),
        "wape": round(sum(valid_wapes) / len(valid_wapes), 4) if valid_wapes else None,
        "mape": round(sum(valid_mapes) / len(valid_mapes), 4) if valid_mapes else None,
        "detail": origins,
    }


def forecast(
    db: Session,
    warehouse_id: str,
    process_type: str,
    horizon_days: int = 7,
    model: str = "seasonal_naive",
) -> dict:
    history = get_history(db, warehouse_id, process_type)
    values = [v for _, v in history]
    start = history[-1][0] if history else datetime.utcnow()

    if model == "moving_average":
        preds = moving_average(values, horizon_days)
    else:
        preds = seasonal_naive(list(values), horizon_days)

    # Convert volume -> task-hours via the labor standard
    standard = (
        db.query(LaborStandard)
        .filter(LaborStandard.warehouse_id == warehouse_id, LaborStandard.process_type == process_type)
        .first()
    )
    uph = standard.units_per_hour if standard else 50.0

    points = [{
        "date": (start + timedelta(days=i + 1)).date().isoformat(),
        "forecast_volume": round(p, 1),
        "forecast_task_hours": round(p / uph, 2),
    } for i, p in enumerate(preds)]

    low_confidence = len(values) < 2 * SEASON_DAYS
    return {
        "process_type": process_type,
        "warehouse_id": warehouse_id,
        "model": model,
        "horizon_days": horizon_days,
        "labor_standard_units_per_hour": uph,
        "confidence": "LOW" if low_confidence else "NORMAL",
        "note": "Low-confidence: under 2 weeks of history." if low_confidence else None,
        "history_points": len(values),
        "forecast": points,
    }
