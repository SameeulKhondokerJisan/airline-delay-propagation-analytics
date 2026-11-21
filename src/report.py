"""Render README.md and reports/memo.md from reports/results.json (numbers never typed by hand)."""
from __future__ import annotations

from src import config


def _p(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def _usd(x: float) -> str:
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e9:
        return f"{sign}${x / 1e9:,.2f} billion"
    if x >= 1e6:
        return f"{sign}${x / 1e6:,.0f} million"
    return f"{sign}${x:,.0f}"


def _m(x: float) -> str:
    return f"{x / 1e6:,.1f} million"


def buffer_economics(row: dict, months: int) -> dict:
    cost = config.COST_PER_BLOCK_MINUTE
    gate = sum(v for k, v in cost.items() if k in config.GATE_COMPONENTS)
    ground = cost["Aircraft ownership"] + cost["Other"]
    pax = config.PASSENGERS_PER_DEPARTURE * config.PASSENGER_VALUE_OF_TIME / 60
    minutes_used = row["turns_buffered"] * row["buffer"]
    k = 12 / months
    airline = row["minutes_avoided"] * gate * k
    passengers = row["minutes_avoided"] * pax * k
    buffer_cost = minutes_used * ground * k
    return {"airline_saving": airline, "passenger_saving": passengers, "buffer_cost": buffer_cost,
            "net_airline": airline - buffer_cost, "net_total": airline + passengers - buffer_cost,
            "break_even": row["minutes_avoided"] * gate / minutes_used, "ground": ground, "gate": gate}


def render(results: dict) -> None:
    n, c, h, pr = results["network"], results["causes"], results["hourly"], results["propagation"]
    tp, chk = pr["turn_profile"], pr["check"]
    months = len(results["settings"]["months"])
    full = [x for x in results["carriers"] if x["months_reported"] == months]
    best = max(full, key=lambda x: x["on_time_rate"])
    worst = min(full, key=lambda x: x["on_time_rate"])
    mult_hi = max(full, key=lambda x: x["delay_multiplier"])
    mult_lo = min(full, key=lambda x: x["delay_multiplier"])
    turns = {t["carrier"]: t for t in results["carrier_turns"]}
    s = results["shutdown"]["main"]
    nas_pre, nas_cut = s["nas_min_per_flight|Shutdown, before flight cuts"], s["nas_min_per_flight|Shutdown with flight cuts"]
    can_pre, can_cut = s["cancel_rate|Shutdown, before flight cuts"], s["cancel_rate|Shutdown with flight cuts"]
    ot_cut = s["on_time_rate|Shutdown with flight cuts"]
    nas_after = s["nas_min_per_flight|Flight cuts after shutdown"]
    alld = results["shutdown"]["all_days"]["cancel_rate|Shutdown, before flight cuts"]
    m = results["model"]
    imp = m["importance"]
    b60, b45, bpm = results["buffer"]["all_60_15"], results["buffer"]["all_45_10"], results["buffer"]["pm_60_15"]
    e60, e45, epm = (buffer_economics(x, months) for x in (b60, b45, bpm))
    total_prop = results["buffer"]["total_propagated_minutes"]
    sh = {x["carrier"]: x for x in results["carriers"]}
    top_airports = results["shutdown"]["airports"][:3]

    def poss(name: str) -> str:
        return name + ("'" if name.endswith("s") else "'s")

    def sig(r: dict) -> bool:
        return r["ci_low"] > 0 or r["ci_high"] < 0

    def ci(r: dict, scale: float = 1, unit: str = "", d: int = 1) -> str:
        return f"95% CI {r['ci_low'] * scale:.{d}f} to {r['ci_high'] * scale:.{d}f}{unit}"

    pre_txt = (f"In the five weeks before the cuts, the year-over-year change in NAS delay was {nas_pre['effect']:+.1f} "
               f"minutes per flight above its post-shutdown level ({ci(nas_pre)}), "
               + ("too small to tell apart from zero" if not sig(nas_pre) else "a measurable rise")
               + f", and the cancellation rate moved by {can_pre['effect'] * 100:+.2f} points ({ci(can_pre, 100, d=2)}).")
    findings = [
        (f"**{n['scheduled']:,} scheduled flights from {n['first_date']} to {n['last_date']}:** {_p(n['on_time_rate'])} "
         f"arrived on time (less than 15 minutes late), {_p(n['cancel_rate'])} were cancelled, and operated flights "
         f"arrived {n['arr_delay_min_per_flight']:.1f} minutes late on average, {_m(n['arr_delay_minutes'])} minutes "
         f"in total."),
        (f"**Late-arriving aircraft is the largest cause of delay: {_p(c['shares']['Late-arriving aircraft'])} of delay "
         f"minutes,** ahead of carrier causes ({_p(c['shares']['Carrier'])}), the National Aviation System "
         f"({_p(c['shares']['National Aviation System'])}) and extreme weather ({_p(c['shares']['Extreme weather'])}). "
         f"Each minute of original delay grows to {c['delay_multiplier']:.2f} minutes as it moves through aircraft "
         f"rotations."),
        (f"**Delay builds through the day.** {_p(h['dep_delay15_6am'])} of 6 am departures leave 15+ minutes late; by "
         f"{h['peak_hour']}:00 it is {_p(h['dep_delay15_peak'])}. The late-aircraft share of delay minutes rises from "
         f"{_p(h['late_aircraft_share_6am'], 0)} to {_p(h['late_aircraft_share_peak'], 0)}."),
        (f"**Scheduled turn time decides whether a delay spreads.** When the inbound flight arrived 15+ minutes late, "
         f"{_p(tp['late_if_inbound_late_30_40'], 0)} of departures after a 30-40 minute turn also left late, against "
         f"{_p(tp['late_if_inbound_late_90_120'], 0)} after a 90-120 minute turn (and "
         f"{_p(tp['late_if_inbound_on_time_30_40'], 0)} when the inbound was on time). Across {pr['turns'] / 1e6:,.1f} "
         f"million linked aircraft turns, {_p(pr['propagated_share_of_departure_delay'], 0)} of departure delay minutes "
         f"were carried in from the inbound flight; turns of 45 minutes or less are {_p(pr['share_turns_45_or_less'], 0)} "
         f"of turns and carry {_p(pr['propagated_share_from_turns_45_or_less'], 0)} of propagated minutes. The estimate "
         f"agrees with the carriers' own late-aircraft coding on {_p(chk['agreement_share'], 0)} of delayed flights "
         f"(correlation {chk['correlation']:.2f})."),
        (f"**{best['carrier_name']} has the highest on-time rate of the {len(full)} carriers that reported all 24 months** "
         f"({_p(best['on_time_rate'])}, 95% interval {_p(best['on_time_ci_low'])} to {_p(best['on_time_ci_high'])}) and "
         f"{worst['carrier_name']} the lowest ({_p(worst['on_time_rate'])}). {mult_hi['carrier_name']} turns delay over "
         f"most: {_p(mult_hi['late_aircraft_share'], 0)} of its delay minutes come from late aircraft (multiplier "
         f"{mult_hi['delay_multiplier']:.2f}, median scheduled turn {turns[mult_hi['carrier']]['median_sched_turn']:.0f} "
         f"minutes) against {_p(mult_lo['late_aircraft_share'], 0)} at {mult_lo['carrier_name']} "
         f"({mult_lo['delay_multiplier']:.2f})."),
        (f"**A blanket schedule buffer does not pay for itself at the airline level.** Adding 15 minutes to every turn "
         f"scheduled at 60 minutes or less would avoid {_p(b60['minutes_avoided'] / total_prop, 0)} of propagated delay "
         f"({_m(b60['minutes_avoided'])} minutes over 24 months) but use {_m(b60['turns_buffered'] * b60['buffer'])} "
         f"aircraft minutes. Priced at A4A's 2025 cost rates, the airline saves {_usd(e60['airline_saving'])} a year in "
         f"gate time and spends {_usd(e60['buffer_cost'])} on aircraft time (net {_usd(e60['net_airline'])}); it breaks "
         f"even only if extra ground time costs less than ${e60['break_even']:.2f} a minute. Passengers would save "
         f"{_usd(e60['passenger_saving'])} a year in time. The same buffer on afternoon turns only (departures from "
         f"15:00) breaks even at ${epm['break_even']:.2f} a minute."),
        (f"**The 2025 shutdown hit hardest once the FAA cut flights.** "
         + pre_txt
         + f" During the shutdown days with flight cuts (7-12 November), NAS delay rose by {nas_cut['effect']:+.1f} "
           f"minutes per flight ({ci(nas_cut)}), cancellations by {can_cut['effect'] * 100:+.1f} points "
           f"({ci(can_cut, 100, d=2)}) and the on-time rate fell by {abs(ot_cut['effect']) * 100:.1f} points. After the "
           f"shutdown ended, NAS delay was back near normal ({nas_after['effect']:+.1f} minutes, {ci(nas_after)}). "
           f"The largest NAS increases were at {', '.join(a['airport'] for a in top_airports)}."),
        (f"**Schedule data alone flags the riskiest flights.** A LightGBM model trained on October 2024 - March 2026 "
         f"and tested on {m['test_rows']:,} flights from April to September 2026 scores an AUC of {m['auc']:.3f} "
         f"(baseline on carrier, hour and month: {m['auc_baseline']:.3f}). The top risk decile was disrupted "
         f"{_p(m['top_decile_rate'], 0)} of the time against {_p(m['base_rate_test'], 0)} on average "
         f"({m['top_decile_lift']:.1f}x) and the bottom decile {_p(m['bottom_decile_rate'], 0)}. The planned turn "
         f"before the flight is the {['first', 'second', 'third', 'fourth'][[x['feature'] for x in imp].index('planned_turn')]} "
         f"most useful feature ({_p(next(x['share'] for x in imp if x['feature'] == 'planned_turn'), 0)} of gain)."),
    ]
    if abs(alld["effect"] - can_pre["effect"]) > 0.003:
        findings[6] += (f" Hurricane Milton (landfall 9 October 2024) cancelled many flights in the comparison year; "
                        f"with those days kept, the pre-cut cancellation change is {alld['effect'] * 100:+.2f} points.")
    recs = [
        "Protect the first wave: departures before 8 am are rarely late, and every minute they lose is carried "
        "through the day. Track first-departure on-time rate by hub as a daily operating KPI.",
        f"Add turn time where inbound delays are common, not across the board. A blanket 15-minute buffer on turns of "
        f"60 minutes or less breaks even only below ${e60['break_even']:.2f} a ground minute; limited to afternoon turns "
        f"the break-even rises to ${epm['break_even']:.2f}. Test the targeted version first at the airports with the "
        f"most propagated delay, and confirm the true cost of an aircraft ground minute (the model's default is "
        f"${e60['ground']:.2f}).",
        "Use the risk model at schedule-build time: flights in the top risk decile are worth a longer planned turn, "
        "a spare aircraft or crew at the hub, or a swap with a lower-risk rotation.",
        f"Review {poss(mult_hi['carrier_name'])} turn standards against {poss(mult_lo['carrier_name'])}: the gap in delay "
        f"multiplier ({mult_hi['delay_multiplier']:.2f} against {mult_lo['delay_multiplier']:.2f}) is mostly scheduled "
        f"slack, which the airline controls.",
        "Keep a playbook for air traffic control staffing events: during the FAA flight cuts, NAS delay and "
        "cancellations rose sharply within days. Early, planned cancellations on thin routes protect the hub banks.",
    ]
    tab = results.get("tableau", {})
    readme = f"""# US Airline Delays: Where They Start, How They Spread, What They Cost

**Which flights, airports and carriers lose the most time, how much of it is delay passed from one flight to the
next by the same aircraft, and would more scheduled turn time pay for itself?** This project analyses
{n['scheduled']:,} scheduled US domestic flights (BTS on-time data, October 2024 to September 2026), links each
flight to the aircraft's previous flight to measure delay propagation, prices delays with airline cost data,
measures what the 2025 federal shutdown did to air traffic delays, and builds a model that flags high-risk flights
from the schedule alone.

**Tools:** SQL (DuckDB over 24 monthly Parquet files: window functions for aircraft rotations, grouping sets,
lateral unnest, quantiles) · Python (pandas, NumPy, statsmodels, LightGBM, scikit-learn) · Statistics (day-level
bootstrap, year-over-year comparison with Newey-West errors, calibration and lift) · Excel (delay cost model and
turn-buffer business case with formulas and data validation) · Tableau (two dashboards, Hyper extracts, map)

![Turn time and propagation](reports/figures/04_turn_propagation.png)

## Findings

""" + "\n".join(f"{i}. {t}" for i, t in enumerate(findings, 1)) + """

![Delay by hour](reports/figures/03_delay_by_hour.png)

![Shutdown weekly](reports/figures/06_shutdown_weekly.png)

## Recommendations for an airline operations planning team

""" + "\n".join(f"{i}. {t}" for i, t in enumerate(recs, 1)) + f"""

## Deliverables

| Deliverable | Where |
|---|---|
| Tableau workbook: 2 dashboards, {tab.get('sheets', 8)} sheets, {tab.get('sources', 8)} Hyper extracts | `dashboards/tableau/airline_delay_propagation.twbx` |
| CSV extracts used by Tableau | `dashboards/tableau/data/` |
| Excel delay cost model and turn-buffer business case | `excel/delay_cost_turn_buffer_model.xlsx` |
| Analysis notebook with outputs | `notebooks/airline_delay_propagation.ipynb` |
| One-page memo | `reports/memo.md` |
| SQL: staging, flights, {results['quality']['rules']} quality rules, rotations and propagation, buffer scenarios, scorecards, shutdown, model frame | `sql/` |
| Result tables and figures | `reports/tables/`, `reports/figures/` |

![Tableau dashboard](dashboards/tableau/dashboard_preview.png)

## How it works

1. **Staging** (`sql/00`, `src/data.py`): each monthly BTS zip is unpacked and written as typed Parquet (32 of 109
   columns).
2. **Warehouse** (`sql/01-02`): one table of {n['scheduled']:,} flights with clock times turned into minutes on each
   airport's local clock; {results['quality']['rules']} quality rules ([`docs/data_quality_log.md`](docs/data_quality_log.md)).
3. **Rotations** (`sql/03`): a window function over carrier and tail number links {pr['turns']:,.0f} turns; carrier
   minimum turn times; propagated and own departure delay for every turn.
4. **Analysis** (`sql/04-17`, `src/delays.py`): turn profile, buffer scenarios computed flight by flight, carrier and
   airport scorecards with a day-level bootstrap, hourly and monthly views, shutdown comparison against the same
   weekdays a year earlier.
5. **Risk model** (`src/model.py`): LightGBM on features known at schedule time, tested on the last six months.
6. **Business tools**: Excel cost model and buffer business case (`src/excel_model.py`); Tableau workbook
   (`src/tableau_workbook.py`).

Details: [`docs/methodology.md`](docs/methodology.md) · data dictionary: [`docs/data_dictionary.md`](docs/data_dictionary.md)

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all        # download (about 730 MB), stage, warehouse, analysis, model, notebook, tests (about 10 minutes)
```

## Project structure

```
├── data/                 raw/ and processed/ (git-ignored); README with sources
├── sql/                  DuckDB SQL: staging, flights, quality rules, rotations, propagation, scorecards, model frame
├── src/                  pipeline: data, delays, model, figures, Excel, Tableau, report
├── notebooks/            executed analysis notebook
├── excel/                delay cost model and turn-buffer business case
├── dashboards/tableau/   .twbx workbook, CSV extracts, preview
├── reports/              results.json, memo, figures, tables
├── docs/                 methodology, data dictionary, data quality log
└── tests/                pytest suite
```

## Data

Bureau of Transportation Statistics, Reporting Carrier On-Time Performance (1987-present), monthly files for
October 2024 to September 2026 from [transtats.bts.gov/PREZIP](https://transtats.bts.gov/PREZIP/). Airport
coordinates from [OurAirports](https://ourairports.com/data/) (public domain). Cost per block minute from Airlines
for America, [U.S. Passenger Carrier Delay Costs](https://airlines.org/dataset/u-s-passenger-carrier-delay-costs/)
(2025, DOT Form 41). No account is needed. Raw files are not stored in this repository.

## Assumptions and limits

* Delay costs use industry averages: ${sum(config.COST_PER_BLOCK_MINUTE.values()):.2f} per block minute (A4A, 2025),
  of which ${e60['gate']:.2f} (crew, ownership, other) is assumed to accrue at the gate; passenger time at
  ${config.PASSENGER_VALUE_OF_TIME:.0f} an hour and {config.PASSENGERS_PER_DEPARTURE:.1f} passengers per departure
  (BTS). All are inputs in the Excel model.
* The cost of extra scheduled ground time (default ${e60['ground']:.2f} a minute, ownership plus other) is the
  assumption the buffer decision turns on; the Excel model shows the break-even value.
* Propagation uses one minimum turn per carrier. Buffer benefits count the next departure only, so they are a
  lower bound.
* Causes are coded by carriers. The shutdown comparison controls for season and weekday but not for weather
  differences between years.
* {n['carriers'] - n['carriers_full_window']} carriers reported for fewer than 24 months; they are in the tables but
  not in the carrier ranking.
"""
    (config.ROOT / "README.md").write_text(readme)
    memo = ("# Memo: where US flight delays start and what extra turn time is worth\n\n**To:** VP Operations Planning · "
            f"**Data:** BTS on-time performance, {n['scheduled']:,} flights, {n['first_date']} to {n['last_date']}\n\n"
            "**What we found**\n\n" + "\n".join(f"- {t}" for t in findings) + "\n\n**What to do**\n\n"
            + "\n".join(f"{i}. {t}" for i, t in enumerate(recs, 1))
            + "\n\n**Caveats:** industry-average cost rates; carrier-coded causes; first-order buffer benefits.\n")
    (config.REPORTS / "memo.md").write_text(memo)
