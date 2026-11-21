-- Aircraft rotations. For each operated flight with a tail number, the previous operated flight of the same
-- aircraft (window function over carrier and tail in scheduled order). A pair counts as a turn when the previous
-- flight landed where this one departs and the scheduled ground time is 10 to 240 minutes.
CREATE OR REPLACE TABLE tail_legs AS
SELECT flight_id, carrier, tail, flight_date, origin, dest, dep_hour, sched_dep_abs, sched_arr_abs,
       dep_delay, arr_delay, arr_del15, late_aircraft_delay,
       LAG(flight_id) OVER w AS prev_flight_id,
       LAG(dest) OVER w AS prev_dest,
       LAG(sched_arr_abs) OVER w AS prev_sched_arr_abs,
       LAG(arr_delay) OVER w AS prev_arr_delay,
       row_number() OVER (PARTITION BY carrier, tail, flight_date ORDER BY sched_dep_abs) AS leg_of_day
FROM flights
WHERE operated AND tail IS NOT NULL
WINDOW w AS (PARTITION BY carrier, tail ORDER BY sched_dep_abs, flight_id);

CREATE OR REPLACE TABLE turns AS
SELECT *,
       sched_dep_abs - prev_sched_arr_abs AS sched_turn,
       (sched_dep_abs + dep_delay) - (prev_sched_arr_abs + prev_arr_delay) AS actual_turn
FROM tail_legs
WHERE prev_dest = origin AND sched_dep_abs - prev_sched_arr_abs BETWEEN 10 AND 240;

-- Minimum turn time each carrier achieves: the 5th percentile of actual ground time when the inbound flight
-- arrived 15+ minutes late and the outbound still left 15+ minutes late (the crew turned it as fast as possible).
CREATE OR REPLACE TABLE min_turn AS
SELECT carrier, quantile_cont(actual_turn, 0.05) AS min_turn, COUNT(*) AS forced_turns
FROM turns
WHERE prev_arr_delay >= 15 AND dep_delay >= 15 AND actual_turn > 0
GROUP BY carrier;

-- Propagated delay: the part of the inbound delay that the scheduled slack could not absorb, capped at the
-- outbound departure delay. slack = scheduled turn - carrier minimum turn, floored at zero (some aircraft types
-- turn faster than the carrier-wide minimum).
CREATE OR REPLACE TABLE propagation AS
WITH s AS (
    SELECT t.*, m.min_turn, GREATEST(t.sched_turn - m.min_turn, 0) AS slack
    FROM turns t JOIN min_turn m USING (carrier)
)
SELECT *,
       LEAST(GREATEST(prev_arr_delay - slack, 0), GREATEST(dep_delay, 0)) AS propagated,
       GREATEST(dep_delay, 0) - LEAST(GREATEST(prev_arr_delay - slack, 0), GREATEST(dep_delay, 0))
           AS own_departure_delay
FROM s;
