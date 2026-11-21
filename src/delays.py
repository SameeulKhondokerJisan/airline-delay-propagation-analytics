"""Delay statistics: carrier scorecard with day-level bootstrap intervals, cause shares, the delay multiplier,
and the 2025 shutdown comparison against the same days a year earlier.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src import config

CAUSES = {"carrier_minutes": "Carrier", "weather_minutes": "Extreme weather", "nas_minutes": "National Aviation System",
          "security_minutes": "Security", "late_aircraft_minutes": "Late-arriving aircraft"}


def carrier_scorecard(carriers: pd.DataFrame, carrier_days: pd.DataFrame, reps: int = 1000) -> pd.DataFrame:
    """On-time arrival rate per carrier with 95% intervals from resampling whole days (flights on the same day share
    weather and congestion, so they are not independent). The same resampled days are used for every carrier."""
    days = np.sort(carrier_days.flight_date.unique())
    rng = np.random.default_rng(config.SEED)
    idx = rng.integers(0, len(days), size=(reps, len(days)))
    day_pos = {d: i for i, d in enumerate(days)}
    out = []
    for carrier, d in carrier_days.groupby("carrier"):
        ops = np.zeros(len(days))
        ont = np.zeros(len(days))
        pos = d.flight_date.map(day_pos).to_numpy()
        ops[pos] = d.operated.to_numpy()
        ont[pos] = d.on_time.fillna(0).to_numpy()
        draws = ont[idx].sum(axis=1) / np.maximum(ops[idx].sum(axis=1), 1)
        out.append({"carrier": carrier, "on_time_ci_low": float(np.percentile(draws, 2.5)),
                    "on_time_ci_high": float(np.percentile(draws, 97.5))})
    sc = carriers.merge(pd.DataFrame(out), on="carrier")
    sc["carrier_name"] = sc.carrier.map(config.CARRIERS).fillna(sc.carrier)
    total = sc[[c for c in CAUSES]].sum(axis=1)
    sc["late_aircraft_share"] = sc.late_aircraft_minutes / total
    sc["delay_multiplier"] = total / (total - sc.late_aircraft_minutes)
    sc["full_window"] = sc.months_reported == len(config.MONTHS)
    return sc.sort_values("scheduled", ascending=False).reset_index(drop=True)


def cause_summary(monthly: pd.DataFrame) -> dict:
    totals = {label: float(monthly[col].sum()) for col, label in CAUSES.items()}
    all_minutes = sum(totals.values())
    root = all_minutes - totals["Late-arriving aircraft"]
    return {"minutes": totals, "shares": {k: v / all_minutes for k, v in totals.items()},
            "total_minutes": all_minutes, "delay_multiplier": all_minutes / root}


def _aligned(daily: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Each day of [start, end] next to the same weekday 364 days earlier."""
    d = daily.copy()
    d["flight_date"] = pd.to_datetime(d.flight_date)
    d["cancel_rate"] = d.cancelled / d.scheduled
    d["nas_cancel_rate"] = d.cancelled_nas / d.scheduled
    d["on_time_rate"] = 1 - d.delayed15 / d.operated
    d["nas_min_per_flight"] = d.nas_minutes / d.scheduled
    d["delay_min_per_flight"] = d.arr_delay_minutes / d.operated
    cur = d[(d.flight_date >= start) & (d.flight_date <= end)].copy()
    prev = d.set_index("flight_date")
    cur["prior_date"] = cur.flight_date - pd.to_timedelta(364, unit="D")
    metrics = ["scheduled", "cancel_rate", "nas_cancel_rate", "on_time_rate", "nas_min_per_flight",
               "delay_min_per_flight"]
    prior = prev.reindex(cur.prior_date)[metrics].reset_index(drop=True)
    prior.columns = [f"{m}_prior" for m in metrics]
    return pd.concat([cur.reset_index(drop=True), prior], axis=1)


def _effects(a: pd.DataFrame, periods: list[str], label: str) -> list[dict]:
    X = sm.add_constant(pd.DataFrame({p: (a.period == p).astype(float) for p in periods}, index=a.index))
    rows = []
    for metric in ("nas_min_per_flight", "cancel_rate", "nas_cancel_rate", "on_time_rate", "delay_min_per_flight"):
        y = a[metric] - a[f"{metric}_prior"]
        ok = y.notna()
        fit = sm.OLS(y[ok], X[ok]).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
        ci = fit.conf_int()
        for p in periods:
            rows.append({"sample": label, "metric": metric, "period": p, "effect": float(fit.params[p]),
                         "ci_low": float(ci.loc[p, 0]), "ci_high": float(ci.loc[p, 1]), "p": float(fit.pvalues[p]),
                         "baseline_yoy": float(fit.params["const"]), "days": int(ok.sum())})
    return rows


def shutdown(daily: pd.DataFrame) -> dict:
    """Year-over-year differences, 1 Oct - 31 Dec 2025 against the same weekdays of 2024, regressed on the
    shutdown and flight-cut periods (baseline: 17 Nov - 31 Dec). Newey-West errors (7 lags). The main sample
    drops days compared with the Hurricane Milton week of 2024; the full sample is reported alongside."""
    a = _aligned(daily, config.SHUTDOWN_START, config.SHUTDOWN_COMPARE_END)
    s0, s1 = pd.Timestamp(config.SHUTDOWN_START), pd.Timestamp(config.SHUTDOWN_END)
    c0, c1 = pd.Timestamp(config.CUTS_START), pd.Timestamp(config.CUTS_END)
    a["period"] = np.select(
        [(a.flight_date >= s0) & (a.flight_date < c0), (a.flight_date >= c0) & (a.flight_date <= s1),
         (a.flight_date > s1) & (a.flight_date <= c1)],
        ["Shutdown, before flight cuts", "Shutdown with flight cuts", "Flight cuts after shutdown"], "After")
    periods = ["Shutdown, before flight cuts", "Shutdown with flight cuts", "Flight cuts after shutdown"]
    m0, m1 = pd.Timestamp(config.MILTON_WEEK[0]), pd.Timestamp(config.MILTON_WEEK[1])
    a["milton_comparison"] = a.prior_date.between(m0, m1)
    rows = _effects(a[~a.milton_comparison], periods, "Excluding Hurricane Milton week") + \
        _effects(a, periods, "All days")
    means = (a[~a.milton_comparison].groupby("period")[["nas_min_per_flight", "nas_min_per_flight_prior", "cancel_rate", "cancel_rate_prior",
                                  "on_time_rate", "on_time_rate_prior", "scheduled", "scheduled_prior"]].mean()
             .reindex(periods + ["After"]).reset_index())
    a["week"] = ((a.flight_date - s0).dt.days // 7).astype(int)
    weekly = a.groupby("week").agg(week_start=("flight_date", "min"), nas_2025=("nas_min_per_flight", "mean"),
                                   nas_2024=("nas_min_per_flight_prior", "mean"), cancel_2025=("cancel_rate", "mean"),
                                   cancel_2024=("cancel_rate_prior", "mean"), on_time_2025=("on_time_rate", "mean"),
                                   on_time_2024=("on_time_rate_prior", "mean")).reset_index()
    return {"effects": pd.DataFrame(rows), "means": means, "weekly": weekly, "daily": a}
