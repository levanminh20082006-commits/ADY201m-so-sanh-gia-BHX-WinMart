"""Step 4 - Data Storage in SQL Server with pyodbc.

Safety rules built into the code:
- Windows Authentication only: no password is stored anywhere.
- The database name MUST start with 'ADY201m_Report2' - any other database is refused,
  so the original project database or other databases can never be written by mistake.
- The database is only created when you pass --create-database explicitly.
- Everything for one run is written in ONE transaction: all rows or nothing.
- Re-running is safe: existing rows are skipped (idempotent), so no unwanted duplicates.

Settings come from environment variables (see .env.example):
    ADY_SQL_SERVER    default localhost\\SQLEXPRESS
    ADY_SQL_DATABASE  default ADY201m_Report2
    ADY_SQL_DRIVER    default ODBC Driver 18 for SQL Server

Usage:
    python -m report2.storage --create-database   # first time only
    python -m report2.storage                     # load latest run (clean + matches)
    python -m report2.storage --run run_20261012_1612
"""
import argparse
import json
import os
import re
import struct
from datetime import datetime, timedelta, timezone

import pandas as pd
import pyodbc

from report2 import settings

ALLOWED_DB_PREFIX = "ADY201m_Report2"
SCHEMA_FILE = settings.ROOT / "sql" / "01_schema.sql"
STORES = [("bhx", "Bach Hoa Xanh", "https://www.bachhoaxanh.com"), ("winmart", "WinMart", "https://winmart.vn")]


def db_settings() -> dict:
    return {"server": os.environ.get("ADY_SQL_SERVER", r"localhost\SQLEXPRESS"),
            "database": os.environ.get("ADY_SQL_DATABASE", "ADY201m_Report2"),
            "driver": os.environ.get("ADY_SQL_DRIVER", "ODBC Driver 18 for SQL Server")}


def check_database_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name) or not name.startswith(ALLOWED_DB_PREFIX):
        raise ValueError(f"Refusing database '{name}': only databases named {ALLOWED_DB_PREFIX}* are allowed")
    return name


def _read_datetimeoffset(raw: bytes) -> datetime:
    """pyodbc cannot read SQL Server datetimeoffset (ODBC type -155) by itself; convert the raw bytes."""
    y, mo, d, h, mi, sec, ns, off_h, off_m = struct.unpack("<6hI2h", raw)
    return datetime(y, mo, d, h, mi, sec, ns // 1000, tzinfo=timezone(timedelta(hours=off_h, minutes=off_m)))


def connect(database: str | None = None, autocommit: bool = False) -> pyodbc.Connection:
    cfg = db_settings()
    db = check_database_name(database or cfg["database"])
    conn_str = (f"DRIVER={{{cfg['driver']}}};SERVER={cfg['server']};DATABASE={db};"
                "Trusted_Connection=yes;TrustServerCertificate=yes")
    conn = pyodbc.connect(conn_str, timeout=10, autocommit=autocommit)
    conn.add_output_converter(-155, _read_datetimeoffset)
    return conn


def create_database(database: str | None = None) -> None:
    cfg = db_settings()
    db = check_database_name(database or cfg["database"])
    conn = pyodbc.connect(f"DRIVER={{{cfg['driver']}}};SERVER={cfg['server']};DATABASE=master;"
                          "Trusted_Connection=yes;TrustServerCertificate=yes", timeout=10, autocommit=True)
    try:
        if conn.execute("SELECT DB_ID(?)", db).fetchone()[0] is not None:
            # Agreed rule: an existing database is never reset or overwritten - stop and ask the owner.
            raise RuntimeError(f"Database {db} already exists - not creating it again. Ask the owner before any change.")
        conn.execute(f"CREATE DATABASE [{db}]")
    finally:
        conn.close()


def apply_schema(conn: pyodbc.Connection) -> None:
    for batch in re.split(r"^\s*GO\s*$", SCHEMA_FILE.read_text(encoding="utf-8"), flags=re.M | re.I):
        if batch.strip():
            conn.execute(batch)
    conn.commit()


def _none(value):
    """pandas NaN / NA -> None for SQL NULL; numpy numbers -> plain Python numbers for pyodbc."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def save_run(conn: pyodbc.Connection, run_id: str, clean: pd.DataFrame, matches: pd.DataFrame) -> dict:
    """Insert one run in a single transaction. Returns inserted / skipped counts."""
    manifest = json.loads((settings.RAW_DIR / run_id / "manifest.json").read_text(encoding="utf-8"))
    rows = clean[clean["run_id"] == run_id]
    counts = {"products_inserted": 0, "products_updated": 0, "observations_inserted": 0,
              "observations_skipped_existing": 0, "matches_inserted": 0, "matches_skipped_existing": 0}
    cur = conn.cursor()
    try:
        for code, name, site in STORES:
            cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.Stores WHERE store_code = ?) "
                        "INSERT INTO dbo.Stores (store_code, store_name, website) VALUES (?, ?, ?)", code, code, name, site)
        cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.CollectionRuns WHERE run_id = ?) "
                    "INSERT INTO dbo.CollectionRuns (run_id, started_at, finished_at, pages_total, pages_ok, raw_folder) "
                    "VALUES (?, ?, ?, ?, ?, ?)", run_id, run_id, manifest["started_at"], manifest.get("finished_at"),
                    len(manifest["pages"]), sum(p["status"] == "ok" for p in manifest["pages"]),
                    f"data/raw_py/{run_id}")

        for r in rows.itertuples(index=False):
            cur.execute("SELECT product_key FROM dbo.Products WHERE store_code = ? AND store_product_code = ?",
                        r.store, r.product_code)
            found = cur.fetchone()
            values = (r.name_clean, _none(r.brand), _none(r.barcode), _none(r.size_value), _none(r.size_unit),
                      _none(r.pack_count), _none(r.unit_label), r.product_url)
            if found:
                product_key = found[0]
                cur.execute("UPDATE dbo.Products SET name = ?, brand = ?, barcode = ?, size_value = ?, size_unit = ?, "
                            "pack_count = ?, unit_label = ?, product_url = ?, last_seen_run = ? "
                            "WHERE product_key = ? AND last_seen_run <= ?", *values, run_id, product_key, run_id)
                counts["products_updated"] += cur.rowcount
            else:
                cur.execute("INSERT INTO dbo.Products (name, brand, barcode, size_value, size_unit, pack_count, unit_label, "
                            "product_url, store_code, store_product_code, first_seen_run, last_seen_run) "
                            "OUTPUT INSERTED.product_key VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            *values, r.store, r.product_code, run_id, run_id)
                product_key = cur.fetchone()[0]
                counts["products_inserted"] += 1

            cur.execute("""
                INSERT INTO dbo.PriceObservations (observation_id, run_id, product_key, collected_at, category_slug,
                    sale_price_vnd, list_price_vnd, is_promotion, flash_sale_price_vnd, price_store_id, price_area,
                    dom_price_check, source_url, raw_file, row_id)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM dbo.PriceObservations WHERE observation_id = ?)""",
                        r.observation_id, run_id, product_key, r.collected_at, r.category_slug,
                        int(r.sale_price_vnd), _none(r.list_price_vnd), bool(r.is_promotion),
                        _none(r.flash_sale_price_vnd), _none(r.price_store_id), _none(r.price_area),
                        r.dom_price_check, r.source_url, r.raw_file, r.row_id, r.observation_id)
            key = "observations_inserted" if cur.rowcount == 1 else "observations_skipped_existing"
            counts[key] += 1

        for m in matches.itertuples(index=False):
            cur.execute("""
                INSERT INTO dbo.ProductMatches (run_id, status, reason, name_similarity, bhx_observation_id,
                    winmart_observation_id, price_diff_vnd, price_diff_pct, price_comparable)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM dbo.ProductMatches WHERE run_id = ? AND bhx_observation_id = ?)""",
                        run_id, m.status, m.reason[:300], float(m.name_similarity), m.bhx_observation_id,
                        m.winmart_observation_id, _none(m.price_diff_vnd), _none(m.price_diff_pct),
                        bool(m.price_comparable), run_id, m.bhx_observation_id)
            key = "matches_inserted" if cur.rowcount == 1 else "matches_skipped_existing"
            counts[key] += 1
        conn.commit()
    except Exception:
        conn.rollback()  # nothing from this run is kept if any statement fails
        raise
    return counts


def load_frames(run_id: str | None) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    clean = pd.read_csv(settings.PROCESSED_DIR / "clean_observations.csv",
                        dtype={"product_code": str, "barcode": str, "price_store_id": str})
    clean["pack_count"] = clean["pack_count"].astype("Int64").astype(object)
    run_id = run_id or sorted(clean["run_id"].unique())[-1]
    results = pd.read_csv(settings.PROCESSED_DIR / "match_results.csv")
    matched = pd.read_csv(settings.PROCESSED_DIR / "matched_products.csv")
    review = results[results["status"] == "NEEDS_REVIEW"].assign(price_diff_vnd=float("nan"), price_diff_pct=float("nan"),
                                                                   price_comparable=False)
    cols = ["status", "reason", "name_similarity", "bhx_observation_id", "winmart_observation_id",
            "price_diff_vnd", "price_diff_pct", "price_comparable", "run_id"]
    matches = pd.concat([matched[cols], review[cols]], ignore_index=True)
    matches = matches[matches["run_id"] == run_id]
    return run_id, clean, matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Store clean data and matches in SQL Server")
    parser.add_argument("--run", help="run id (default: latest)")
    parser.add_argument("--create-database", action="store_true", help="create the database if missing")
    args = parser.parse_args()
    if args.create_database:
        create_database()
    run_id, clean, matches = load_frames(args.run)
    conn = connect()
    try:
        apply_schema(conn)
        counts = save_run(conn, run_id, clean, matches)
    finally:
        conn.close()
    print(json.dumps({"run_id": run_id, **counts}, indent=1))


if __name__ == "__main__":
    main()
