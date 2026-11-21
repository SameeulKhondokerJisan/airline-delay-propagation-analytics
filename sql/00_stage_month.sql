-- Stage one month of BTS on-time records: keep the 32 columns used downstream, with types, as Parquet.
-- {csv} is the CSV extracted from the monthly zip; {out} is the Parquet file written.
COPY (
    SELECT CAST(FlightDate AS DATE) AS flight_date,
           Reporting_Airline AS carrier,
           NULLIF(trim(Tail_Number), '') AS tail,
           Flight_Number_Reporting_Airline AS flight_number,
           Origin AS origin, OriginCityName AS origin_city, OriginState AS origin_state,
           Dest AS dest, DestCityName AS dest_city, DestState AS dest_state,
           CRSDepTime AS crs_dep_time, DepTime AS dep_time,
           TRY_CAST(DepDelay AS DOUBLE) AS dep_delay,
           TRY_CAST(DepDel15 AS DOUBLE) AS dep_del15,
           TRY_CAST(TaxiOut AS DOUBLE) AS taxi_out,
           TRY_CAST(TaxiIn AS DOUBLE) AS taxi_in,
           CRSArrTime AS crs_arr_time, ArrTime AS arr_time,
           TRY_CAST(ArrDelay AS DOUBLE) AS arr_delay,
           TRY_CAST(ArrDel15 AS DOUBLE) AS arr_del15,
           TRY_CAST(Cancelled AS DOUBLE) = 1 AS cancelled,
           NULLIF(CancellationCode, '') AS cancel_code,
           TRY_CAST(Diverted AS DOUBLE) = 1 AS diverted,
           TRY_CAST(CRSElapsedTime AS DOUBLE) AS crs_elapsed,
           TRY_CAST(ActualElapsedTime AS DOUBLE) AS actual_elapsed,
           TRY_CAST(AirTime AS DOUBLE) AS air_time,
           TRY_CAST(Distance AS DOUBLE) AS distance,
           TRY_CAST(CarrierDelay AS DOUBLE) AS carrier_delay,
           TRY_CAST(WeatherDelay AS DOUBLE) AS weather_delay,
           TRY_CAST(NASDelay AS DOUBLE) AS nas_delay,
           TRY_CAST(SecurityDelay AS DOUBLE) AS security_delay,
           TRY_CAST(LateAircraftDelay AS DOUBLE) AS late_aircraft_delay
    FROM read_csv('{csv}', header = true, all_varchar = true)
) TO '{out}' (FORMAT parquet, COMPRESSION zstd);
