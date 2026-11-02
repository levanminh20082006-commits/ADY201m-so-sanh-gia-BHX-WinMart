"""SQL Server storage tests. They ONLY use the test database ADY201m_Report2_Test (synthetic data).

Run them with:  $env:ADY_RUN_DB_TESTS = "1"; python -m pytest tests/python/test_storage.py
"""
import json
import os

import pandas as pd
import pyodbc
import pytest

from report2 import settings, storage
from report2.clean import derive_fields, flatten_page, validate
from report2.matching import match

TEST_DB = "ADY201m_Report2_Test"
pytestmark = pytest.mark.skipif(os.environ.get("ADY_RUN_DB_TESTS") != "1", reason="set ADY_RUN_DB_TESTS=1 to run")


@pytest.fixture
def conn():
    connection = storage.connect(TEST_DB)
    assert connection.execute("SELECT DB_NAME()").fetchone()[0] == TEST_DB   # never another database
    storage.apply_schema(connection)
    for table in ("ProductMatches", "PriceObservations", "Products", "CollectionRuns", "Stores"):
        connection.execute(f"DELETE FROM dbo.{table}")                        # test DB only
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def test_run(helpers, tmp_path, monkeypatch):
    """A synthetic run: 2 BHX + 2 WinMart products, one matching pair, plus a manifest file."""
    monkeypatch.setattr(settings, "RAW_DIR", tmp_path)
    (tmp_path / "test_run").mkdir()
    (tmp_path / "test_run" / "manifest.json").write_text(json.dumps(
        {"run_id": "test_run", "started_at": "2026-01-01T10:00:00+07:00", "finished_at": "2026-01-01T11:00:00+07:00",
         "pages": [{"status": "ok"}, {"status": "ok"}]}), encoding="utf-8")
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    rows = flatten_page(helpers["page_record"]("bhx", [b("1000000000001", "Sữa tươi TestBrand ít đường 1 lít", 41000),
                                                       b("1000000000002", "Nước mắm TestBrand 500ml", 30000)]), "t.json")
    rows += flatten_page(helpers["page_record"]("winmart", [w("1", "Sữa tươi tiệt trùng TestBrand ít đường hộp 1 lít", 38300),
                                                            w("2", "Dầu ăn TestBrand 1L", 50000)]), "t.json")
    clean, _ = validate(derive_fields(pd.DataFrame(rows)))
    results, matched = match(clean, "test_run")
    clean["pack_count"] = clean["pack_count"].astype(object)
    return clean, matched.assign(run_id="test_run")


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM dbo.{table}").fetchone()[0]


def test_connect_to_test_database(conn):
    assert conn.execute("SELECT DB_NAME()").fetchone()[0] == TEST_DB


def test_save_run_inserts_rows(conn, test_run):
    clean, matched = test_run
    counts = storage.save_run(conn, "test_run", clean, matched)
    assert counts["observations_inserted"] == 4 and counts["products_inserted"] == 4
    assert counts["matches_inserted"] == 1
    assert count(conn, "PriceObservations") == 4 and count(conn, "Products") == 4
    diff = conn.execute("SELECT price_diff_vnd FROM dbo.vw_PriceComparison").fetchone()[0]
    assert diff == 38300 - 41000


def test_rerun_does_not_create_duplicates(conn, test_run):
    clean, matched = test_run
    storage.save_run(conn, "test_run", clean, matched)
    again = storage.save_run(conn, "test_run", clean, matched)
    assert again["observations_inserted"] == 0 and again["observations_skipped_existing"] == 4
    assert again["matches_inserted"] == 0 and again["products_inserted"] == 0
    assert count(conn, "PriceObservations") == 4 and count(conn, "ProductMatches") == 1


def test_invalid_row_rolls_back_whole_run(conn, test_run):
    clean, matched = test_run
    broken = clean.copy()
    broken.loc[broken.index[-1], "sale_price_vnd"] = 0          # violates CHECK (sale_price_vnd > 0)
    with pytest.raises(pyodbc.IntegrityError):
        storage.save_run(conn, "test_run", broken, matched)
    assert count(conn, "PriceObservations") == 0 and count(conn, "Products") == 0   # transaction rolled back


def test_unique_constraint_blocks_duplicate_product(conn, test_run):
    clean, matched = test_run
    storage.save_run(conn, "test_run", clean, matched)
    with pytest.raises(pyodbc.IntegrityError):
        conn.execute("INSERT INTO dbo.Products (store_code, store_product_code, name, product_url, first_seen_run, "
                     "last_seen_run) VALUES ('bhx', '1000000000001', N'dup', 'x', 'test_run', 'test_run')")
    conn.rollback()


def test_other_databases_are_refused():
    for name in ("SupermarketPrices", "master", "ADY201m", "x; DROP DATABASE y"):
        with pytest.raises(ValueError):
            storage.connect(name)


def test_database_connection_error_is_raised(monkeypatch):
    monkeypatch.setenv("ADY_SQL_SERVER", r"127.0.0.1,1")   # nothing listens on port 1
    with pytest.raises(pyodbc.Error):
        storage.connect(TEST_DB)
