"""Stage the monthly BTS zips as Parquet, build the DuckDB warehouse and expose query helpers."""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

from src import config


class DataQualityError(RuntimeError):
    """Raised when a hard data-quality rule fails."""


def split_statements(sql: str) -> list[str]:
    no_comments = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(config.DB_PATH), read_only=read_only)


def fill(sql: str, **params) -> str:
    base = {"start": config.START, "end": config.END, "n_months": len(config.MONTHS),
            "parquet_glob": (config.PARQUET_DIR / "flights_*.parquet").as_posix(),
            "airports_csv": config.AIRPORTS_CSV.as_posix(), "min_airport_flights": 20000,
            "shutdown_start": config.SHUTDOWN_START, "shutdown_end": config.SHUTDOWN_END,
            "thresholds": ", ".join(map(str, config.TURN_THRESHOLDS)),
            "buffers": ", ".join(map(str, config.BUFFER_MINUTES))}
    for key, value in {**base, **params}.items():
        sql = sql.replace("{" + key + "}", str(value))
    return sql


def run_sql(con, filename: str, **params) -> pd.DataFrame | None:
    result = None
    for statement in split_statements(fill((config.SQL_DIR / filename).read_text(), **params)):
        result = con.execute(statement)
    try:
        return result.df() if result is not None else None
    except duckdb.Error:
        return None


def zip_path(year: int, month: int) -> Path:
    return config.BTS_DIR / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"


def stage_parquet() -> list[Path]:
    """Convert each monthly zip to typed Parquet (skipped when the Parquet file is newer than the zip)."""
    config.PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    out_files = []
    for year, month in config.MONTHS:
        src = zip_path(year, month)
        out = config.PARQUET_DIR / f"flights_{year}_{month:02d}.parquet"
        out_files.append(out)
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            continue
        if not src.exists():
            raise FileNotFoundError(f"{src} is missing. Run `python -m src.download_data` first.")
        tmp = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(src) as zf:
                member = next(m for m in zf.namelist() if m.lower().endswith(".csv"))
                csv = Path(zf.extract(member, tmp))
            with duckdb.connect() as con:
                run_sql(con, "00_stage_month.sql", csv=csv.as_posix(), out=out.as_posix())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"staged {out.name}", flush=True)
    return out_files


def build_warehouse() -> pd.DataFrame:
    stage_parquet()
    if not config.AIRPORTS_CSV.exists():
        raise FileNotFoundError(f"{config.AIRPORTS_CSV} is missing. Run `python -m src.download_data` first.")
    with connect() as con:
        con.execute("SET preserve_insertion_order = false")
        run_sql(con, "01_flights.sql")
        checks = run_sql(con, "02_quality_checks.sql")
        failed = checks[(checks.severity == "hard") & (checks.failures > 0)]
        if not failed.empty:
            raise DataQualityError("Hard data-quality rules failed:\n" + failed.to_string(index=False))
        run_sql(con, "03_rotations.sql")
    return checks


def query(filename_or_sql: str, **params) -> pd.DataFrame:
    with connect(read_only=True) as con:
        if filename_or_sql.endswith(".sql"):
            return run_sql(con, filename_or_sql, **params)
        return con.execute(fill(filename_or_sql, **params)).df()


def row_counts() -> dict[str, int]:
    with connect(read_only=True) as con:
        return {n: int(con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0])
                for n in ("flights", "tail_legs", "turns", "propagation", "airports")}
