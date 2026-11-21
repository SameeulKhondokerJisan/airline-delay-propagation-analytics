-- First-order effect of adding buffer minutes to short scheduled turns: propagated delay avoided on the next
-- departure, by carrier ('All' = network), departure window, threshold and buffer size. New slack =
-- max(0, scheduled turn + buffer - carrier minimum turn); the inbound delay is the one that actually happened.
WITH grid AS (
    SELECT t.threshold, b.buffer
    FROM (SELECT unnest([{thresholds}]) AS threshold) t, (SELECT unnest([{buffers}]) AS buffer) b
),
pairs AS (
    SELECT carrier, sched_turn, prev_arr_delay, min_turn, propagated, w.time_window
    FROM propagation,
         LATERAL (SELECT unnest(CASE WHEN dep_hour >= 15 THEN ['All day', 'Departures from 15:00']
                                     ELSE ['All day'] END) AS time_window) w
)
SELECT COALESCE(p.carrier, 'All') AS carrier, p.time_window, g.threshold, g.buffer,
       COUNT(*) AS turns_buffered,
       SUM(p.propagated) AS propagated_now,
       SUM(LEAST(GREATEST(p.prev_arr_delay - GREATEST(p.sched_turn + g.buffer - p.min_turn, 0), 0), p.propagated))
           AS propagated_after,
       SUM(p.propagated)
           - SUM(LEAST(GREATEST(p.prev_arr_delay - GREATEST(p.sched_turn + g.buffer - p.min_turn, 0), 0), p.propagated))
           AS minutes_avoided
FROM pairs p JOIN grid g ON p.sched_turn <= g.threshold
GROUP BY GROUPING SETS ((p.carrier, p.time_window, g.threshold, g.buffer), (p.time_window, g.threshold, g.buffer))
ORDER BY carrier, time_window, threshold, buffer
