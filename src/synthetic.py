"""Synthetic BTS-shaped monthly zips for the test suite (never used for results).

Each aircraft flies four legs a day between three airports in one time zone with a fixed scheduled turn. The next
departure delay is max(0, inbound arrival delay - (turn - 25)) plus its own delay, so the true minimum turn is
25 minutes and tests can check the rotation linking and the propagation arithmetic.
"""
from __future__ import annotations

import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

TRUE_MIN_TURN = 25
COLUMNS = ["FlightDate", "Reporting_Airline", "Tail_Number", "Flight_Number_Reporting_Airline", "Origin",
           "OriginCityName", "OriginState", "Dest", "DestCityName", "DestState", "CRSDepTime", "DepTime", "DepDelay",
           "DepDel15", "TaxiOut", "TaxiIn", "CRSArrTime", "ArrTime", "ArrDelay", "ArrDel15", "Cancelled",
           "CancellationCode", "Diverted", "CRSElapsedTime", "ActualElapsedTime", "AirTime", "Distance",
           "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]


def _hhmm(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}{minutes % 60:02d}"


def flights(start: date, days: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tails = [("XX", f"N{i:03d}XX", t) for i, t in enumerate([30, 45, 60, 90] * 5)] + \
            [("YY", f"N{i:03d}YY", t) for i, t in enumerate([40, 75] * 5)]
    route = ["ATL", "ORD", "DFW", "ATL", "ORD"]
    rows, fn = [], 1000
    for d in range(days):
        day = start + timedelta(days=d)
        for carrier, tail, turn in tails:
            dep = 360 + int(rng.integers(0, 60))
            inbound = None
            for leg in range(4):
                elapsed = 120
                own = float(rng.exponential(8)) if rng.random() < 0.4 else 0.0
                prop = max(0.0, inbound - (turn - TRUE_MIN_TURN)) if inbound is not None else 0.0
                dep_delay = round(prop + own - 3)
                arr_delay = round(dep_delay + rng.normal(0, 4))
                cancelled = rng.random() < 0.01
                fn += 1
                rec = {"FlightDate": day.isoformat(), "Reporting_Airline": carrier, "Tail_Number": tail,
                       "Flight_Number_Reporting_Airline": str(fn), "Origin": route[leg], "OriginCityName": "City, ST",
                       "OriginState": "GA", "Dest": route[leg + 1], "DestCityName": "City, ST", "DestState": "IL",
                       "CRSDepTime": _hhmm(dep), "CRSArrTime": _hhmm(dep + elapsed), "CRSElapsedTime": f"{elapsed}.00",
                       "Distance": "600.00", "Cancelled": "1.00" if cancelled else "0.00",
                       "CancellationCode": "A" if cancelled else "", "Diverted": "0.00"}
                if cancelled:
                    rec.update({"DepTime": "", "DepDelay": "", "DepDel15": "", "ArrTime": "", "ArrDelay": "",
                                "ArrDel15": "", "TaxiOut": "", "TaxiIn": "", "ActualElapsedTime": "", "AirTime": ""})
                    inbound = None
                else:
                    late = arr_delay >= 15
                    lateac = min(prop, max(arr_delay, 0)) if late else None
                    rec.update({"DepTime": _hhmm(dep + dep_delay), "DepDelay": f"{dep_delay}.00",
                                "DepDel15": "1.00" if dep_delay >= 15 else "0.00", "ArrTime": _hhmm(dep + elapsed + arr_delay),
                                "ArrDelay": f"{arr_delay}.00", "ArrDel15": "1.00" if late else "0.00",
                                "TaxiOut": "15.00", "TaxiIn": "7.00", "ActualElapsedTime": f"{elapsed}.00",
                                "AirTime": "98.00",
                                "CarrierDelay": f"{arr_delay - lateac:.2f}" if late else "",
                                "WeatherDelay": "0.00" if late else "", "NASDelay": "0.00" if late else "",
                                "SecurityDelay": "0.00" if late else "", "LateAircraftDelay": f"{lateac:.2f}" if late else ""})
                    inbound = arr_delay
                rows.append(rec)
                dep += elapsed + turn
    return pd.DataFrame(rows).reindex(columns=COLUMNS).fillna("")


def write(raw_dir: Path, months: list[tuple[int, int]], days: int = 10) -> None:
    bts = raw_dir / "bts"
    bts.mkdir(parents=True, exist_ok=True)
    for i, (y, m) in enumerate(months):
        df = flights(date(y, m, 1), days, seed=i)
        name = f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{y}_{m}"
        csv = df.to_csv(index=False)
        with zipfile.ZipFile(bts / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{y}_{m}.csv", csv)
            zf.writestr("readme.html", "<html></html>")
    pd.DataFrame({"id": [1, 2, 3], "ident": ["KATL", "KORD", "KDFW"], "type": "large_airport",
                  "name": ["Atlanta", "Chicago O'Hare", "Dallas Fort Worth"], "latitude_deg": [33.6, 41.9, 32.9],
                  "longitude_deg": [-84.4, -87.9, -97.0], "iso_region": ["US-GA", "US-IL", "US-TX"],
                  "municipality": ["Atlanta", "Chicago", "Dallas"], "scheduled_service": "yes",
                  "iata_code": ["ATL", "ORD", "DFW"]}).to_csv(raw_dir / "airports.csv", index=False)
