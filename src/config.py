"""Paths, study windows and cost assumptions."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# AIR_RAW_DIR / AIR_DB_PATH / AIR_MONTHS let the test suite run the pipeline on synthetic data.
RAW_DIR = Path(os.environ.get("AIR_RAW_DIR", ROOT / "data" / "raw"))
BTS_DIR = RAW_DIR / "bts"
AIRPORTS_CSV = RAW_DIR / "airports.csv"
PARQUET_DIR = Path(os.environ.get("AIR_PARQUET_DIR", ROOT / "data" / "processed" / "flights"))
DB_PATH = Path(os.environ.get("AIR_DB_PATH", ROOT / "data" / "processed" / "flights.duckdb"))
SQL_DIR = ROOT / "sql"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
RESULTS_JSON = REPORTS / "results.json"
TABLEAU_DIR = ROOT / "dashboards" / "tableau"
TABLEAU_DATA = TABLEAU_DIR / "data"
EXCEL_PATH = ROOT / "excel" / "delay_cost_turn_buffer_model.xlsx"

# Study window: 24 months of BTS Reporting Carrier On-Time Performance data.
MONTHS = [(2024, m) for m in (10, 11, 12)] + [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 10)]
if os.environ.get("AIR_MONTHS"):
    MONTHS = [tuple(int(x) for x in ym.split("_")) for ym in os.environ["AIR_MONTHS"].split(",")]
START = "2024-10-01"
END = "2026-09-30"
BTS_URL = ("https://transtats.bts.gov/PREZIP/"
           "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# The October-November 2025 federal government shutdown (43 days, ended 12 November 2025) and the FAA order
# that cut flights at 40 high-traffic airports from 7 November until 6 am on 17 November 2025.
SHUTDOWN_START, SHUTDOWN_END = "2025-10-01", "2025-11-12"
CUTS_START, CUTS_END = "2025-11-07", "2025-11-16"
SHUTDOWN_COMPARE_END = "2025-12-31"   # shutdown analysis window: 1 Oct - 31 Dec 2025 against a year earlier
# Hurricane Milton made landfall in Florida on 9 October 2024 and cancelled many flights in the comparison year;
# the main shutdown estimate drops 2025 days whose comparison day falls in this week (both versions are reported).
MILTON_WEEK = ("2024-10-07", "2024-10-13")

# Model: trained on the first 18 months, tested on the last 6.
MODEL_TEST_START = "2026-04-01"
SEED = 42

# Delay cost assumptions (editable in the Excel model).
# Airlines for America, "U.S. Passenger Carrier Delay Costs": 2025 direct aircraft operating cost per block
# minute, from DOT Form 41 (https://airlines.org/dataset/u-s-passenger-carrier-delay-costs/, read 2026-11-20).
COST_PER_BLOCK_MINUTE = {"Crew labor": 37.01, "Fuel": 29.34, "Maintenance": 18.35, "Aircraft ownership": 9.76,
                         "Other": 3.95}
# Components assumed to accrue while an aircraft waits at the gate (no fuel burn or engine wear).
GATE_COMPONENTS = ("Crew labor", "Aircraft ownership", "Other")
PASSENGER_VALUE_OF_TIME = 47.0          # $ per hour, FAA-recommended value quoted by A4A
# BTS TranStats national summary, 12 months ending January 2026: 840 million enplaned passengers on
# 8,759 thousand departures (https://www.transtats.bts.gov/, read 2026-11-20).
PASSENGERS_PER_DEPARTURE = 840_000 / 8_759

BUFFER_MINUTES = (5, 10, 15, 20, 30)    # extra scheduled turn time tested in the buffer scenario
TURN_THRESHOLDS = (45, 60, 75, 90)      # buffer added to turns scheduled at or below this many minutes

CARRIERS = {
    "AA": "American Airlines", "AS": "Alaska Airlines", "B6": "JetBlue", "DL": "Delta Air Lines",
    "F9": "Frontier Airlines", "G4": "Allegiant Air", "HA": "Hawaiian Airlines", "MQ": "Envoy Air",
    "NK": "Spirit Airlines", "OH": "PSA Airlines", "OO": "SkyWest Airlines", "UA": "United Airlines",
    "WN": "Southwest Airlines", "YX": "Republic Airways", "9E": "Endeavor Air", "QX": "Horizon Air",
    "ZW": "Air Wisconsin", "C5": "CommuteAir", "G7": "GoJet Airlines", "YV": "Mesa Airlines", "PT": "Piedmont Airlines",
}
