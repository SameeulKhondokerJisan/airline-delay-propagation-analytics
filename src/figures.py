"""Static figures for the README, memo and notebook (reports/figures/*.png)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import config  # noqa: E402
from src.delays import CAUSES  # noqa: E402

BLUE, ORANGE, GREY, GREEN, RED, PURPLE = "#1f5aa6", "#e07b39", "#9aa5b1", "#2e8b57", "#c0392b", "#7b5ea7"
CAUSE_COLORS = [BLUE, GREEN, ORANGE, PURPLE, RED]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 11, "axes.titleweight": "bold", "figure.dpi": 110})


def _save(fig, name: str) -> str:
    fig.tight_layout()
    fig.savefig(config.FIGURES / name, dpi=130)
    plt.close(fig)
    return f"reports/figures/{name}"


def _shade(ax):
    ax.axvspan(pd.Timestamp(config.SHUTDOWN_START), pd.Timestamp(config.SHUTDOWN_END), color=GREY, alpha=0.25, lw=0)


def monthly(monthly_df: pd.DataFrame) -> str:
    m = monthly_df.copy()
    m["month"] = pd.to_datetime(m.year_month + "-15")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(m.month, m.on_time_rate * 100, color=BLUE, marker="o", ms=3, label="On-time arrivals (%)")
    ax.set_ylabel("On-time arrival rate (%)")
    ax2 = ax.twinx()
    ax2.bar(m.month, m.cancel_rate * 100, width=20, color=ORANGE, alpha=0.5, label="Cancelled (%)")
    ax2.set_ylabel("Cancelled (%)")
    ax2.spines["right"].set_visible(True)
    _shade(ax)
    ax.text(pd.Timestamp(config.SHUTDOWN_START), ax.get_ylim()[0] + 0.5, " shutdown", fontsize=8, color="#555")
    ax.set_title("On-time arrivals and cancellations by month, Oct 2024 - Sep 2026")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="lower left", fontsize=8)
    return _save(fig, "01_monthly_on_time.png")


def causes(monthly_df: pd.DataFrame) -> str:
    m = monthly_df.copy()
    m["month"] = pd.to_datetime(m.year_month + "-15")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bottom = np.zeros(len(m))
    for (col, label), color in zip(CAUSES.items(), CAUSE_COLORS):
        v = m[col] / m.scheduled
        ax.bar(m.month, v, width=22, bottom=bottom, color=color, label=label)
        bottom += v
    ax.set_ylabel("Delay minutes per scheduled flight")
    ax.set_title("Arrival delay minutes by cause (flights 15+ minutes late, carrier-reported causes)")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    _shade(ax)
    return _save(fig, "02_delay_causes.png")


def hourly(h: pd.DataFrame) -> str:
    d = h[h.dep_hour.between(5, 23)]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    ax.plot(d.dep_hour, d.dep_delay15_rate * 100, color=BLUE, marker="o", label="Departures 15+ min late (%)")
    ax.plot(d.dep_hour, d.late_aircraft_share * 100, color=ORANGE, marker="s",
            label="Share of delay minutes from late-arriving aircraft (%)")
    ax.set_xlabel("Scheduled departure hour (local time)")
    ax.set_ylabel("%")
    ax.set_title("Delays build through the day as late aircraft carry them forward")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, "03_delay_by_hour.png")


def turn_profile(tp: pd.DataFrame, min_turns: pd.DataFrame) -> str:
    d = tp[(tp.sched_turn_bin >= 25) & (tp.sched_turn_bin <= 150)]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.plot(d.sched_turn_bin, d.share_departs_late_if_inbound_late * 100, color=RED, label="Inbound arrived 15+ min late")
    ax.plot(d.sched_turn_bin, d.share_departs_late_if_inbound_on_time * 100, color=BLUE, label="Inbound on time")
    med = float(np.median(min_turns.min_turn))
    ax.axvline(med, color="black", ls="--", lw=0.8)
    ax.text(med + 1, 90, f"median carrier\nminimum turn\n{med:.0f} min", fontsize=8, va="top")
    ax.set_xlabel("Scheduled ground time between flights (minutes)")
    ax.set_ylabel("Next departure 15+ min late (%)")
    ax.set_title("Short turns pass inbound delays straight to the next flight")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, "04_turn_propagation.png")


def carriers(sc: pd.DataFrame) -> str:
    d = sc[sc.full_window].sort_values("on_time_rate")
    fig, ax = plt.subplots(figsize=(8.5, 0.32 * len(d) + 1.2))
    y = np.arange(len(d))
    ax.barh(y, d.on_time_rate * 100, color=BLUE)
    ax.errorbar(d.on_time_rate * 100, y, xerr=[(d.on_time_rate - d.on_time_ci_low) * 100,
                                              (d.on_time_ci_high - d.on_time_rate) * 100],
                fmt="none", ecolor="black", capsize=2, lw=0.8)
    for yi, (r, s) in enumerate(zip(d.on_time_rate, d.late_aircraft_share)):
        ax.text(r * 100 + 0.6, yi, f"{r * 100:.1f}%  late-aircraft share {s * 100:.0f}%", va="center", fontsize=8)
    ax.set_yticks(y, d.carrier_name)
    ax.set_xlim(60, 100)
    ax.set_xlabel("On-time arrival rate, 24 months (95% interval from resampling days)")
    ax.set_title("Carrier on-time performance")
    return _save(fig, "05_carrier_on_time.png")


def shutdown_weekly(weekly: pd.DataFrame) -> str:
    w = weekly.copy()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, (a, b, label) in zip(axes, (("nas_2025", "nas_2024", "NAS delay minutes per scheduled flight"),
                                        ("cancel_2025", "cancel_2024", "Cancellation rate (%)"))):
        scale = 100 if "cancel" in a else 1
        ax.plot(w.week_start, w[a] * scale, color=RED, marker="o", ms=3, label="Oct-Dec 2025")
        ax.plot(w.week_start, w[b] * scale, color=GREY, marker="o", ms=3, label="Same weeks a year earlier")
        _shade(ax)
        ax.axvspan(pd.Timestamp(config.CUTS_START), pd.Timestamp(config.CUTS_END), color=RED, alpha=0.12, lw=0)
        ax.set_title(label, fontsize=10)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("The 2025 shutdown: weekly averages against the same weeks of 2024 (grey band: shutdown, red: "
                 "FAA flight cuts)", fontsize=10, fontweight="bold")
    return _save(fig, "06_shutdown_weekly.png")


def airport_map(ap: pd.DataFrame) -> str:
    d = ap[ap.lon.between(-130, -60) & ap.lat.between(23, 50)]
    fig, ax = plt.subplots(figsize=(9, 5))
    sc = ax.scatter(d.lon, d.lat, s=d.departures / d.departures.max() * 600, c=d.dep_delay15_rate * 100,
                    cmap="OrRd", edgecolor="black", linewidth=0.3, alpha=0.85)
    for r in d.nlargest(12, "departures").itertuples():
        ax.annotate(r.airport, (r.lon, r.lat), fontsize=7, xytext=(3, 3), textcoords="offset points")
    fig.colorbar(sc, ax=ax, label="Departures 15+ min late (%)")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Airports (lower 48) by departures (size) and late departures (colour)")
    return _save(fig, "07_airport_map.png")


def model_lift(dec: pd.DataFrame, cal: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    axes[0].bar(dec.decile, dec.disruption_rate * 100, color=BLUE)
    axes[0].axhline(dec.disruption_rate.mean() * 100, color="black", ls="--", lw=0.8)
    axes[0].set_xlabel("Predicted risk decile (10 = highest)")
    axes[0].set_ylabel("Disrupted flights (%)")
    axes[0].set_title("Test period: disruption rate by risk decile", fontsize=10)
    c = cal[cal.flights >= 500]
    axes[1].plot([0, 1], [0, 1], color=GREY, ls="--")
    axes[1].plot(c.predicted, c.observed, marker="o", color=ORANGE)
    axes[1].set_xlabel("Predicted probability")
    axes[1].set_ylabel("Observed share")
    axes[1].set_title("Calibration on the test period", fontsize=10)
    return _save(fig, "08_model_lift_calibration.png")


def buffer(buf: pd.DataFrame, total_propagated: float) -> str:
    d = buf[(buf.carrier == "All") & (buf.time_window == "All day")]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for t, color in zip(config.TURN_THRESHOLDS, [RED, ORANGE, BLUE, GREEN]):
        s = d[d.threshold == t].sort_values("buffer")
        ax.plot(s.buffer, s.minutes_avoided / total_propagated * 100, marker="o", color=color,
                label=f"turns scheduled <= {t} min")
    ax.set_xlabel("Minutes added to each scheduled turn")
    ax.set_ylabel("Propagated delay avoided (% of total)")
    ax.set_title("What extra turn time buys: propagated delay avoided on the next departure")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, "09_buffer_scenarios.png")
