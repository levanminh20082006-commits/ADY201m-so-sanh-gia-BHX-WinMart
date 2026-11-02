"""Step 5 - Reconcile record counts: raw JSON -> CSV -> SQL Server.

Checks for one run:
  raw rows in JSON  == rows in raw_products_flat.csv
  raw rows          == clean rows + rejected rows       (nothing lost silently)
  clean rows (CSV)  == PriceObservations rows in SQL
  matched pairs CSV == ProductMatches MATCHED rows in SQL (+ NEEDS_REVIEW)

Usage: python -m report2.reconcile [--run RUN_ID]
"""
import argparse
import json

import pandas as pd

from report2 import settings, storage
from report2.clean import flatten_page


def reconcile(run_id: str | None = None) -> dict:
    flat = pd.read_csv(settings.PROCESSED_DIR / "raw_products_flat.csv", usecols=["run_id", "store"])
    clean = pd.read_csv(settings.PROCESSED_DIR / "clean_observations.csv", usecols=["run_id", "store"])
    rejected = pd.read_csv(settings.PROCESSED_DIR / "rejected_rows.csv", usecols=["run_id", "store", "reject_reason"])
    results = pd.read_csv(settings.PROCESSED_DIR / "match_results.csv", usecols=["run_id", "status"])
    run_id = run_id or sorted(clean["run_id"].unique())[-1]

    json_rows = {"bhx": 0, "winmart": 0}
    for path in sorted((settings.RAW_DIR / run_id).glob("*__*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        json_rows[page["store"]] += len(flatten_page(page, path.name))

    def by_store(df):
        part = df[df["run_id"] == run_id]
        return {s: int((part["store"] == s).sum()) for s in ("bhx", "winmart")}

    csv_flat, csv_clean, csv_rejected = by_store(flat), by_store(clean), by_store(rejected)
    run_results = results[results["run_id"] == run_id]["status"].value_counts().to_dict()

    conn = storage.connect()
    try:
        sql_obs = dict(conn.execute("""
            SELECT p.store_code, COUNT(*) FROM dbo.PriceObservations o
            JOIN dbo.Products p ON p.product_key = o.product_key WHERE o.run_id = ? GROUP BY p.store_code""", run_id).fetchall())
        sql_matches = dict(conn.execute(
            "SELECT status, COUNT(*) FROM dbo.ProductMatches WHERE run_id = ? GROUP BY status", run_id).fetchall())
        sql_dup = conn.execute("""SELECT COUNT(*) FROM (SELECT run_id, product_key FROM dbo.PriceObservations
                                  GROUP BY run_id, product_key HAVING COUNT(*) > 1) d""").fetchone()[0]
        sql_db = conn.execute("SELECT DB_NAME()").fetchone()[0]
    finally:
        conn.close()

    checks = {
        "json_rows == flat_csv_rows": json_rows == csv_flat,
        "raw_rows == clean + rejected": all(csv_flat[s] == csv_clean[s] + csv_rejected[s] for s in csv_flat),
        "clean_csv_rows == sql_observations": all(csv_clean[s] == sql_obs.get(s, 0) for s in csv_clean),
        "matched_csv == sql_matched": run_results.get("MATCHED", 0) == sql_matches.get("MATCHED", 0),
        "needs_review_csv == sql_needs_review": run_results.get("NEEDS_REVIEW", 0) == sql_matches.get("NEEDS_REVIEW", 0),
        "no_duplicate_observations_in_sql": sql_dup == 0,
    }
    report = {"run_id": run_id, "database": sql_db, "checked_at": settings.now_vn().isoformat(timespec="seconds"),
              "raw_json_rows": json_rows, "raw_flat_csv_rows": csv_flat, "clean_csv_rows": csv_clean,
              "rejected_csv_rows": csv_rejected,
              "rejected_by_reason": rejected[rejected["run_id"] == run_id]["reject_reason"].value_counts().to_dict(),
              "sql_price_observations": sql_obs, "csv_match_status": run_results, "sql_match_status": sql_matches,
              "checks": checks, "all_checks_passed": all(checks.values())}
    out = settings.REPORTS_DIR / f"reconciliation_{run_id}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=int), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1, default=int))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile JSON, CSV and SQL Server counts")
    parser.add_argument("--run", help="run id (default: latest)")
    reconcile(parser.parse_args().run)


if __name__ == "__main__":
    main()
