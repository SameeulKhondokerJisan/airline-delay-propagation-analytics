-- One row per scheduled flight with features known when the schedule is published, for the disruption-risk
-- model. Target: cancelled, diverted or arriving 15+ minutes late. The planned turn uses the previous scheduled
-- flight of the same tail (cancelled flights included, because the plan is what is known in advance).
WITH planned AS (
    SELECT flight_id,
           sched_dep_abs - LAG(sched_arr_abs) OVER w AS planned_turn,
           LAG(dest) OVER w = origin AS planned_link,
           row_number() OVER (PARTITION BY carrier, tail, flight_date ORDER BY sched_dep_abs) AS planned_leg
    FROM flights
    WHERE tail IS NOT NULL
    WINDOW w AS (PARTITION BY carrier, tail ORDER BY sched_dep_abs, flight_id)
)
SELECT f.flight_id, f.flight_date, f.carrier, f.origin, f.dest, f.dep_hour, f.arr_hour, f.dow, f.month,
       f.distance, f.crs_elapsed,
       CASE WHEN p.planned_link AND p.planned_turn BETWEEN 10 AND 240 THEN p.planned_turn END AS planned_turn,
       COALESCE(p.planned_leg, 1) AS planned_leg,
       (f.cancelled OR f.diverted OR f.arr_del15 = 1)::INT AS disrupted
FROM flights f LEFT JOIN planned p USING (flight_id)
WHERE f.cancelled OR f.diverted OR f.arr_del15 IS NOT NULL
