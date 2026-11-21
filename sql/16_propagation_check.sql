-- Check the propagated-delay estimate against the carriers' own cause coding: on outbound flights that arrived
-- 15+ minutes late, compare estimated propagated minutes with the late-aircraft minutes the carrier reported.
SELECT COUNT(*) AS delayed_outbound_turns,
       corr(propagated, late_aircraft_delay) AS correlation,
       AVG(((propagated > 0) = (late_aircraft_delay > 0))::INT) AS agreement_share,
       AVG((late_aircraft_delay > 0)::INT) FILTER (WHERE propagated > 0) AS reported_given_estimated,
       AVG((propagated > 0)::INT) FILTER (WHERE late_aircraft_delay > 0) AS estimated_given_reported,
       SUM(propagated) AS propagated_minutes,
       SUM(late_aircraft_delay) AS late_aircraft_minutes
FROM propagation
WHERE arr_del15 = 1
