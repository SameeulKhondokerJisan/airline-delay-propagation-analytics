-- Data-quality rules. Hard rules stop the pipeline; soft rules are known features of the BTS file.
SELECT * FROM (
    SELECT 'Every study month is present' AS rule, 'hard' AS severity,
           {n_months} - COUNT(DISTINCT year_month) AS failures FROM flights
    UNION ALL
    SELECT 'Flight dates inside the study window', 'hard',
           COUNT(*) FILTER (WHERE flight_date NOT BETWEEN DATE '{start}' AND DATE '{end}') FROM flights
    UNION ALL
    SELECT 'Scheduled times parse to minutes 0-1439', 'hard',
           COUNT(*) FILTER (WHERE crs_dep_min NOT BETWEEN 0 AND 1439 OR crs_arr_min NOT BETWEEN 0 AND 1439
                             OR crs_dep_min IS NULL OR crs_arr_min IS NULL) FROM flights
    UNION ALL
    SELECT 'Not cancelled or diverted but no arrival time (treated as not operated)', 'soft',
           COUNT(*) FILTER (WHERE NOT cancelled AND NOT diverted AND arr_delay IS NULL) FROM flights
    UNION ALL
    SELECT 'Arrival delay flag matches arrival delay of 15+ minutes', 'hard',
           COUNT(*) FILTER (WHERE operated AND (arr_del15 = 1) <> (arr_delay >= 15)) FROM flights
    UNION ALL
    SELECT 'Cancelled flights have a cancellation code', 'hard',
           COUNT(*) FILTER (WHERE cancelled AND cancel_code IS NULL) FROM flights
    UNION ALL
    SELECT 'Delay causes add up to the arrival delay (delayed flights)', 'soft',
           COUNT(*) FILTER (WHERE arr_del15 = 1
                             AND abs(carrier_delay + weather_delay + nas_delay + security_delay
                                     + late_aircraft_delay - arr_delay) > 1) FROM flights
    UNION ALL
    SELECT 'Tail number missing', 'soft', COUNT(*) FILTER (WHERE tail IS NULL) FROM flights
    UNION ALL
    SELECT 'Scheduled arrival day offset outside 0-1 (time zones)', 'soft',
           COUNT(*) FILTER (WHERE (sched_arr_abs - day_num * 1440 - crs_arr_min) / 1440 NOT IN (0, 1)) FROM flights
    UNION ALL
    SELECT 'Same carrier, flight number, date and origin twice', 'soft',
           COUNT(*) - COUNT(DISTINCT (carrier, flight_number, flight_date, origin)) FROM flights
    UNION ALL
    SELECT 'Origin airport without coordinates', 'soft',
           COUNT(*) FILTER (WHERE origin NOT IN (SELECT airport FROM airports)) FROM flights
)
