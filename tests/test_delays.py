"""Shutdown comparison and carrier bootstrap on constructed daily data with a planted effect."""
import numpy as np
import pandas as pd
import pytest

from src import config, delays


def _daily(effect: float) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    dates = pd.date_range("2024-09-01", "2025-12-31")
    sched = rng.integers(20000, 22000, len(dates))
    nas = rng.normal(2.0, 0.3, len(dates))
    in_shutdown = (dates >= config.SHUTDOWN_START) & (dates < config.CUTS_START)
    nas = nas + effect * in_shutdown
    return pd.DataFrame({"flight_date": dates.strftime("%Y-%m-%d"), "dow": dates.dayofweek, "scheduled": sched,
                         "cancelled": (sched * 0.01).astype(int), "cancelled_nas": (sched * 0.002).astype(int),
                         "operated": (sched * 0.99).astype(int), "delayed15": (sched * 0.2).astype(int),
                         "arr_delay_minutes": sched * 12.0, "carrier_minutes": 0.0, "weather_minutes": 0.0,
                         "nas_minutes": nas * sched, "security_minutes": 0.0, "late_aircraft_minutes": 0.0})


def test_shutdown_effect_is_recovered():
    out = delays.shutdown(_daily(1.5))
    row = out["effects"].query("metric == 'nas_min_per_flight' and period == 'Shutdown, before flight cuts'").iloc[0]
    assert row.ci_low < 1.5 < row.ci_high
    none = delays.shutdown(_daily(0.0))["effects"]
    row0 = none.query("metric == 'nas_min_per_flight' and period == 'Shutdown, before flight cuts'").iloc[0]
    assert row0.ci_low < 0 < row0.ci_high


def test_carrier_bootstrap_interval_contains_rate():
    days = pd.date_range("2025-01-01", periods=200).strftime("%Y-%m-%d")
    rng = np.random.default_rng(0)
    cd = pd.DataFrame({"carrier": "XX", "flight_date": days, "scheduled": 1000, "cancelled": 10, "operated": 990,
                       "on_time": rng.binomial(990, 0.8, len(days))})
    carriers = pd.DataFrame({"carrier": ["XX"], "scheduled": [200000], "on_time_rate": [cd.on_time.sum() / cd.operated.sum()],
                             "months_reported": [len(config.MONTHS)], "carrier_minutes": [1.0], "weather_minutes": [0.0],
                             "nas_minutes": [1.0], "security_minutes": [0.0], "late_aircraft_minutes": [1.0]})
    sc = delays.carrier_scorecard(carriers, cd, reps=300).iloc[0]
    assert sc.on_time_ci_low < sc.on_time_rate < sc.on_time_ci_high
    assert sc.delay_multiplier == pytest.approx(1.5)
