-- One row per scheduled flight, with clock times turned into minutes. Scheduled times are local to each
-- airport; sched_*_abs count minutes from 1 Oct 2024 on the local clock of the airport concerned, so a
-- departure and the previous arrival of the same aircraft at that airport can be subtracted directly.
CREATE OR REPLACE TABLE flights AS
WITH t AS (
    SELECT *,
           -- 2400 (midnight) becomes minute 0
           ((TRY_CAST(crs_dep_time AS INTEGER) // 100) * 60 + TRY_CAST(crs_dep_time AS INTEGER) % 100) % 1440 AS crs_dep_min,
           ((TRY_CAST(crs_arr_time AS INTEGER) // 100) * 60 + TRY_CAST(crs_arr_time AS INTEGER) % 100) % 1440 AS crs_arr_min,
           date_diff('day', DATE '{start}', flight_date) AS day_num
    FROM read_parquet('{parquet_glob}')
)
SELECT
    row_number() OVER (ORDER BY flight_date, carrier, flight_number, origin) AS flight_id,
    flight_date, carrier, tail, flight_number, origin, origin_city, origin_state, dest, dest_city, dest_state,
    crs_dep_min, crs_arr_min, crs_dep_min // 60 AS dep_hour, crs_arr_min // 60 AS arr_hour,
    dayofweek(flight_date) AS dow, year(flight_date) AS year, month(flight_date) AS month,
    strftime(flight_date, '%Y-%m') AS year_month, day_num,
    day_num * 1440 + crs_dep_min AS sched_dep_abs,
    day_num * 1440 + crs_arr_min + 1440 * round((crs_dep_min + crs_elapsed - crs_arr_min) / 1440) AS sched_arr_abs,
    crs_elapsed, actual_elapsed, air_time, distance, taxi_out, taxi_in,
    cancelled, cancel_code, diverted, NOT cancelled AND NOT diverted AND arr_delay IS NOT NULL AS operated,
    dep_delay, arr_delay,
    GREATEST(dep_delay, 0) AS dep_delay_min, GREATEST(arr_delay, 0) AS arr_delay_min,
    dep_del15, arr_del15,
    COALESCE(carrier_delay, 0) AS carrier_delay, COALESCE(weather_delay, 0) AS weather_delay,
    COALESCE(nas_delay, 0) AS nas_delay, COALESCE(security_delay, 0) AS security_delay,
    COALESCE(late_aircraft_delay, 0) AS late_aircraft_delay
FROM t;

CREATE OR REPLACE TABLE airports AS
SELECT iata_code AS airport, name AS airport_name, municipality, iso_region, latitude_deg AS lat,
       longitude_deg AS lon, type AS airport_type
FROM read_csv('{airports_csv}', header = true)
WHERE iata_code IS NOT NULL AND iata_code <> ''
QUALIFY row_number() OVER (PARTITION BY iata_code ORDER BY scheduled_service DESC, type) = 1;
