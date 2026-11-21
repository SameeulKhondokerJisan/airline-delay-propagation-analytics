# Data

`make data` downloads 25 public files into `raw/` (no account needed) and writes `raw/MANIFEST.json` with each
file's size, SHA-256 checksum and URL. `make pipeline` stages each month as Parquet in `processed/flights/` and
builds `processed/flights.duckdb`. Both folders are git-ignored; the files are not redistributed here.

| File | Source | Size | Grain |
|---|---|---|---|
| bts/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_YYYY_M.zip (24 files, Oct 2024 - Sep 2026) | Bureau of Transportation Statistics, Reporting Carrier On-Time Performance (1987-present), https://transtats.bts.gov/PREZIP/ | about 30 MB zipped and 250 MB unzipped per month; about 14 million rows in total | one scheduled domestic flight of a reporting carrier |
| airports.csv | OurAirports (public domain), https://davidmegginson.github.io/ourairports-data/airports.csv | 13 MB | airport, with IATA code and coordinates |

The BTS field definitions are in the `readme.html` inside each zip and on the TranStats table page for
"Reporting Carrier On-Time Performance (1987-present)". Times are local to each airport (hhmm); delay cause
fields are filled only for flights arriving 15 or more minutes late. The staging step keeps 32 of the 109
columns (`sql/00_stage_month.sql`).
