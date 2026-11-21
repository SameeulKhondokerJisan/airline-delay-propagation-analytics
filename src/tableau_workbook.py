"""Generate the Tableau workbook (dashboards/tableau/airline_delay_propagation.twbx).

Writes small CSV extracts to dashboards/tableau/data/ and packages them as Hyper extracts in a .twbx with two
dashboards: "Network delays" (airport map, carrier on-time rates, delay by hour, causes by month) and
"Propagation and the 2025 shutdown" (turn profile, buffer scenarios, weekly shutdown comparison, carrier turns).
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.delays import CAUSES
from src.twb import Dashboard, DataSource, Field, Worksheet, Zone, save


def _extracts(airports, sc, hourly, monthly, tp, buffers, weekly, carrier_turns) -> None:
    d = config.TABLEAU_DATA
    d.mkdir(parents=True, exist_ok=True)
    airports[["airport", "airport_name", "municipality", "state", "lat", "lon", "departures", "dep_delay15_rate",
              "dep_delay_min_per_flight", "cancel_rate", "late_aircraft_share"]].dropna(subset=["lat", "lon"]).to_csv(
        d / "airports.csv", index=False)
    c = sc[sc.full_window].copy()
    c[["carrier_name", "scheduled", "on_time_rate", "on_time_ci_low", "on_time_ci_high", "cancel_rate",
       "arr_delay_min_per_flight", "late_aircraft_share"]].to_csv(d / "carriers.csv", index=False)
    h = hourly[hourly.dep_hour.between(5, 23)].copy()
    rows = [{"dep_hour": int(r.dep_hour), "measure": label, "value": float(getattr(r, col))}
            for r in h.itertuples() for col, label in (("dep_delay15_rate", "Leaving 15+ min late"),
                                                       ("late_aircraft_share", "Late-aircraft share"))]
    pd.DataFrame(rows).to_csv(d / "hourly.csv", index=False)
    rows = [{"month": r.year_month, "cause": label, "minutes_per_flight": float(getattr(r, col)) / r.scheduled}
            for r in monthly.itertuples() for col, label in CAUSES.items()]
    pd.DataFrame(rows).to_csv(d / "causes.csv", index=False)
    t = tp[(tp.sched_turn_bin >= 25) & (tp.sched_turn_bin <= 150)]
    rows = [{"sched_turn": int(r.sched_turn_bin), "inbound": label, "share_departs_late": float(getattr(r, col))}
            for r in t.itertuples() for col, label in (("share_departs_late_if_inbound_late", "Inbound late"),
                                                       ("share_departs_late_if_inbound_on_time", "Inbound on time"))]
    pd.DataFrame(rows).to_csv(d / "turn_profile.csv", index=False)
    b = buffers[(buffers.carrier == "All") & (buffers.time_window == "All day")].copy()
    b["threshold"] = "<= " + b.threshold.astype(str) + " min"
    b[["threshold", "buffer", "minutes_avoided", "turns_buffered"]].to_csv(d / "buffer.csv", index=False)
    rows = []
    for r in weekly.itertuples():
        for season, col in (("2025", "nas_2025"), ("A year earlier", "nas_2024")):
            rows.append({"week_start": pd.Timestamp(r.week_start).strftime("%Y-%m-%d"), "season": season,
                         "nas_minutes_per_flight": float(getattr(r, col))})
    pd.DataFrame(rows).to_csv(d / "shutdown_weekly.csv", index=False)
    ct = carrier_turns.copy()
    ct["carrier_name"] = ct.carrier.map(config.CARRIERS).fillna(ct.carrier)
    ct["propagated_share"] = ct.propagated_minutes / (ct.propagated_minutes + ct.own_departure_minutes)
    ct[["carrier_name", "median_sched_turn", "min_turn", "share_slack_15_or_less", "propagated_share"]].to_csv(
        d / "carrier_turns.csv", index=False)


def build(airports, sc, hourly, monthly, tp, buffers, weekly, carrier_turns) -> dict:
    _extracts(airports, sc, hourly, monthly, tp, buffers, weekly, carrier_turns)
    d = config.TABLEAU_DATA
    ap = DataSource.from_csv("airports", "Airports", d / "airports.csv", dims=("airport",),
                             captions={"lat": "Latitude", "lon": "Longitude", "departures": "Departures",
                                       "dep_delay15_rate": "Departures 15+ min late",
                                       "dep_delay_min_per_flight": "Departure delay minutes per flight",
                                       "late_aircraft_share": "Late-aircraft share of delay"},
                             formats={"dep_delay15_rate": "p0.0%", "departures": "n#,##0", "late_aircraft_share": "p0%",
                                      "cancel_rate": "p0.0%", "dep_delay_min_per_flight": "n0.0"},
                             roles={"lat": "[Geographical].[Latitude]", "lon": "[Geographical].[Longitude]"})
    ca = DataSource.from_csv("carriers", "Carriers", d / "carriers.csv",
                             captions={"carrier_name": "Carrier", "on_time_rate": "On-time arrival rate",
                                       "on_time_ci_low": "95% interval low", "on_time_ci_high": "95% interval high",
                                       "late_aircraft_share": "Late-aircraft share of delay"},
                             formats={"on_time_rate": "p0.0%", "on_time_ci_low": "p0.0%", "on_time_ci_high": "p0.0%",
                                      "cancel_rate": "p0.0%", "late_aircraft_share": "p0%"})
    hr = DataSource.from_csv("hourly", "Delay by hour", d / "hourly.csv", dims=("dep_hour",),
                             captions={"dep_hour": "Scheduled departure hour", "value": "Share", "measure": "Measure"},
                             formats={"value": "p0%"})
    cz = DataSource.from_csv("causes", "Delay causes", d / "causes.csv",
                             captions={"month": "Month", "cause": "Cause",
                                       "minutes_per_flight": "Delay minutes per scheduled flight"},
                             formats={"minutes_per_flight": "n0.0"})
    tpd = DataSource.from_csv("turns", "Turn profile", d / "turn_profile.csv",
                              captions={"sched_turn": "Scheduled ground time (min)", "inbound": "Inbound flight",
                                        "share_departs_late": "Next departure 15+ min late"},
                              formats={"share_departs_late": "p0%"})
    tpd.column("sched_turn").role, tpd.column("sched_turn").type = "dimension", "quantitative"
    bf = DataSource.from_csv("buffer", "Buffer scenarios", d / "buffer.csv",
                             captions={"buffer": "Minutes added per turn", "minutes_avoided": "Propagated minutes avoided",
                                       "threshold": "Turns buffered"}, formats={"minutes_avoided": "n#,##0"})
    bf.column("buffer").role, bf.column("buffer").type = "dimension", "quantitative"
    sw = DataSource.from_csv("shutdown", "Shutdown weekly", d / "shutdown_weekly.csv",
                             captions={"week_start": "Week starting", "season": "Season",
                                       "nas_minutes_per_flight": "NAS delay minutes per scheduled flight"},
                             formats={"nas_minutes_per_flight": "n0.0"})
    ctd = DataSource.from_csv("carrier_turns", "Carrier turns", d / "carrier_turns.csv",
                              captions={"carrier_name": "Carrier", "median_sched_turn": "Median scheduled turn (min)",
                                        "propagated_share": "Propagated share of departure delay",
                                        "share_slack_15_or_less": "Turns with 15 min slack or less"},
                              formats={"propagated_share": "p0%", "share_slack_15_or_less": "p0%"})
    sources = [ap, ca, hr, cz, tpd, bf, sw, ctd]
    sheets = [
        Worksheet("Airport map", ap, rows=[Field("lat", "avg")], cols=[Field("lon", "avg")], mark="Circle",
                  detail=[Field("airport"), Field("airport_name")], color=Field("dep_delay15_rate", "avg"),
                  size=Field("departures", "sum"), tooltip=[Field("late_aircraft_share", "avg")],
                  title="Airports by departures (size) and share of departures 15+ minutes late (colour)"),
        Worksheet("Carrier on-time", ca, rows=[Field("carrier_name")], cols=[Field("on_time_rate", "avg")], mark="Bar",
                  text=Field("on_time_rate", "avg"), show_labels=True, tooltip=[Field("on_time_ci_low", "avg"),
                                                                                Field("on_time_ci_high", "avg")],
                  title="On-time arrival rate by carrier, Oct 2024 - Sep 2026"),
        Worksheet("Delay by hour", hr, rows=[Field("value", "avg")], cols=[Field("dep_hour")], mark="Line",
                  color=Field("measure"), title="Delays build through the day"),
        Worksheet("Delay causes", cz, rows=[Field("minutes_per_flight", "sum")], cols=[Field("month")], mark="Bar",
                  color=Field("cause"), title="Delay minutes per scheduled flight by cause"),
        Worksheet("Turn profile", tpd, rows=[Field("share_departs_late", "avg")], cols=[Field("sched_turn", kind="qk")],
                  mark="Line", color=Field("inbound"),
                  title="Short turns pass inbound delays to the next departure"),
        Worksheet("Buffer scenarios", bf, rows=[Field("minutes_avoided", "sum")], cols=[Field("buffer", kind="qk")],
                  mark="Line", color=Field("threshold"),
                  title="Propagated delay minutes avoided by adding minutes to short turns (24 months)"),
        Worksheet("Shutdown weekly", sw, rows=[Field("nas_minutes_per_flight", "avg")], cols=[Field("week_start")],
                  mark="Line", color=Field("season"),
                  title="NAS delay minutes per flight, Oct-Dec 2025 against a year earlier (shutdown: 1 Oct - 12 Nov)"),
        Worksheet("Carrier turns", ctd, rows=[Field("carrier_name")], cols=[Field("propagated_share", "avg")],
                  mark="Bar", color=Field("median_sched_turn", "avg"), text=Field("propagated_share", "avg"),
                  show_labels=True, title="Share of departure delay propagated from the inbound flight"),
    ]
    head = lambda title, sub: [Zone(16, 6, 1300, 34, text=title, font_size=18, bold=True),  # noqa: E731
                               Zone(16, 40, 1360, 22, text=sub, font_size=10)]
    sub = ("BTS Reporting Carrier On-Time Performance, Oct 2024 - Sep 2026. Causes as reported by carriers; "
           "propagation from linked aircraft rotations.")
    db1 = Dashboard("Network delays", 1400, 900, head("Where US flight delays happen", sub) + [
        Zone(16, 66, 700, 420, sheet="Airport map"),
        Zone(16, 488, 700, 50, legend_sheet="Airport map", legend_field=f"[{ap.name}].[avg:dep_delay15_rate:qk]"),
        Zone(730, 66, 654, 420, sheet="Carrier on-time"),
        Zone(16, 546, 560, 346, sheet="Delay by hour"),
        Zone(580, 556, 150, 80, legend_sheet="Delay by hour", legend_field=f"[{hr.name}].[none:measure:nk]"),
        Zone(740, 546, 490, 346, sheet="Delay causes"),
        Zone(1234, 556, 160, 130, legend_sheet="Delay causes", legend_field=f"[{cz.name}].[none:cause:nk]"),
    ])
    db2 = Dashboard("Propagation and shutdown", 1400, 900, head("How delays spread, and what the 2025 shutdown did",
                                                                sub) + [
        Zone(16, 66, 560, 400, sheet="Turn profile"),
        Zone(580, 76, 120, 60, legend_sheet="Turn profile", legend_field=f"[{tpd.name}].[none:inbound:nk]"),
        Zone(704, 66, 560, 400, sheet="Buffer scenarios"),
        Zone(1268, 76, 120, 100, legend_sheet="Buffer scenarios", legend_field=f"[{bf.name}].[none:threshold:nk]"),
        Zone(16, 476, 560, 416, sheet="Shutdown weekly"),
        Zone(580, 486, 120, 60, legend_sheet="Shutdown weekly", legend_field=f"[{sw.name}].[none:season:nk]"),
        Zone(704, 476, 680, 416, sheet="Carrier turns"),
    ])
    twbx = save(config.TABLEAU_DIR / "airline_delay_propagation.twbx", sources, sheets, [db1, db2])
    return {"twbx": str(twbx.relative_to(config.ROOT)), "sheets": len(sheets), "sources": len(sources),
            "dashboards": 2}
