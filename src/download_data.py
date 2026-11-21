"""Download 24 months of BTS on-time performance data and the airport coordinates into data/raw/.

Sources (public, no account needed):
* Bureau of Transportation Statistics, Reporting Carrier On-Time Performance (1987-present), monthly
  zip files, October 2024 to September 2026: one row per scheduled domestic flight of the reporting carriers.
* OurAirports airport list (public domain): coordinates for the airport map.

Usage:
    python -m src.download_data
"""
from __future__ import annotations

from src import config
from src._fetch import fetch, sha256, write_manifest
from src.data import zip_path


def main() -> None:
    entries = []
    for year, month in config.MONTHS:
        url = config.BTS_URL.format(year=year, month=month)
        path = fetch(url, zip_path(year, month))
        print(f"ok  {path.name:80s} {path.stat().st_size / 1e6:7.1f} MB", flush=True)
        entries.append({"file": f"bts/{path.name}", "bytes": path.stat().st_size, "sha256": sha256(path), "url": url})
    path = fetch(config.AIRPORTS_URL, config.AIRPORTS_CSV)
    entries.append({"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path), "url": config.AIRPORTS_URL})
    write_manifest(config.RAW_DIR, entries)


if __name__ == "__main__":
    main()
