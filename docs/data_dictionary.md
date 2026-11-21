# Data dictionary

## `flights` (DuckDB, one row per scheduled flight; `sql/01_flights.sql`)

| Column | Type | BTS field | Meaning |
|---|---|---|---|
| flight_id | integer | | surrogate key |
| flight_date | date | FlightDate | scheduled date of departure (local) |
| carrier | text | Reporting_Airline | reporting carrier code (names in `src/config.py`) |
| tail | text | Tail_Number | aircraft registration (NULL when missing) |
| flight_number | text | Flight_Number_Reporting_Airline | |
| origin, dest | text | Origin, Dest | IATA airport codes |
| origin_city, origin_state, dest_city, dest_state | text | city and state fields | |
| crs_dep_min, crs_arr_min | integer | CRSDepTime, CRSArrTime | scheduled local time in minutes after midnight (2400 = 0) |
| dep_hour, arr_hour | integer | | scheduled local hour |
| dow, year, month, year_month | | | calendar fields (dow: 0 = Sunday) |
| day_num | integer | | days since 1 Oct 2024 |
| sched_dep_abs, sched_arr_abs | integer | | minutes since 1 Oct 2024 on the local clock of the departure / arrival airport |
| crs_elapsed, actual_elapsed, air_time, distance, taxi_out, taxi_in | double | same | minutes, miles |
| cancelled, diverted | boolean | Cancelled, Diverted | |
| cancel_code | text | CancellationCode | A carrier, B weather, C National Aviation System, D security |
| operated | boolean | | not cancelled, not diverted, arrival time present |
| dep_delay, arr_delay | double | DepDelay, ArrDelay | minutes, negative when early |
| dep_delay_min, arr_delay_min | double | | delay floored at zero |
| dep_del15, arr_del15 | double | DepDel15, ArrDel15 | 1 when 15+ minutes late |
| carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay | double | cause fields | minutes by cause on flights arriving 15+ minutes late (0 otherwise) |

## Derived tables
| Table | Grain | Contents |
|---|---|---|
| `airports` | airport | OurAirports name, city, coordinates |
| `tail_legs` | operated flight with a tail number | previous flight of the same aircraft (LAG), leg of the day |
| `turns` | linked pair | scheduled and actual ground time between consecutive flights of one aircraft at one airport |
| `min_turn` | carrier | 5th percentile of actual ground time on forced quick turns |
| `propagation` | linked pair | slack, propagated delay and own departure delay |

## Report tables (`reports/tables/`)
| File | Grain | Notes |
|---|---|---|
| carrier_scorecard.csv | carrier | flights, on-time rate with bootstrap interval, cancellations, cause minutes, late-aircraft share, delay multiplier |
| carrier_turns.csv | carrier | median scheduled turn, minimum turn, slack share, propagated and own departure minutes |
| turn_profile.csv | 5-minute scheduled-turn bin | late-departure shares with the inbound late or on time, pass-through |
| buffer_scenarios.csv | carrier x window x threshold x buffer | turns buffered, propagated minutes before and after, minutes avoided |
| airports.csv | airport (20,000+ departures) | coordinates, departure delay rates, NAS minutes, late-aircraft share |
| hourly.csv, daily.csv, monthly_causes.csv | hour, day, month | network totals |
| shutdown_effects.csv | sample x metric x period | year-over-year effect with Newey-West interval |
| shutdown_period_means.csv, shutdown_weekly.csv, shutdown_airports.csv | period, week, airport | shutdown comparison |
| model_deciles.csv, model_calibration.csv, model_importance.csv | | risk model evaluation on Apr - Sep 2026 |
| routes_top50.csv | route | routes with the most arrival delay minutes |

## Tableau extracts (`dashboards/tableau/data/`)
`airports.csv`, `carriers.csv` (carriers reporting all 24 months), `hourly.csv`, `causes.csv` (minutes per scheduled
flight by month and cause), `turn_profile.csv`, `buffer.csv` (network, all-day turns), `shutdown_weekly.csv`,
`carrier_turns.csv`.
