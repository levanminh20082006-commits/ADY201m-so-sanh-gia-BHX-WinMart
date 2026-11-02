"""Cleaning & validation rules on SYNTHETIC test pages."""
import pandas as pd

from report2.clean import derive_fields, flatten_page, validate


def run_pipeline(pages):
    rows = []
    for page in pages:
        rows += flatten_page(page, "test.json")
    df = derive_fields(pd.DataFrame(rows))
    return validate(df)


def test_valid_rows_are_kept_and_fields_parsed(helpers):
    page = helpers["page_record"]("bhx", [helpers["bhx_product"]("1000000000001", "Thùng 48 hộp sữa test ít đường 180ml",
                                                                 345000, 380000)])
    clean, rejected = run_pipeline([page])
    assert len(clean) == 1 and rejected.empty
    row = clean.iloc[0]
    assert row["sale_price_vnd"] == 345000 and row["list_price_vnd"] == 380000
    assert row["size_value"] == 180 and row["size_unit"] == "ml" and row["pack_count"] == 48
    assert row["unit_price_vnd_per_kg_or_l"] == round(345000 / (180 * 48) * 1000)
    assert bool(row["is_promotion"]) and row["discount_pct"] == 9.2
    assert row["row_id"] == "test_run|bhx|test-cat|r0|i0"     # traceable to raw JSON position


def test_missing_name_or_price_is_rejected(helpers):
    p = helpers["bhx_product"]
    page = helpers["page_record"]("bhx", [p("1000000000001", "", 10000), p("1000000000002", "Sữa test 1L", None)])
    clean, rejected = run_pipeline([page])
    assert clean.empty
    assert sorted(rejected["reject_reason"]) == ["missing_name", "missing_or_unparseable_price"]


def test_invalid_prices_are_rejected(helpers):
    p = helpers["winmart_item"]
    page = helpers["page_record"]("winmart", [p("1", "Zero price 1L", 0), p("2", "Negative 1L", -5000),
                                              p("3", "Too cheap 1L", 500), p("4", "Too expensive 1L", 99_000_000)])
    clean, rejected = run_pipeline([page])
    assert clean.empty
    assert rejected["reject_reason"].tolist() == ["price_not_positive", "price_not_positive",
                                                  "price_out_of_range", "price_out_of_range"]


def test_duplicate_in_same_run_is_removed_but_other_runs_are_kept(helpers):
    item = helpers["winmart_item"]("10", "Sữa test 1L", 30000)
    same_run_a = helpers["page_record"]("winmart", [item], slug="cat-a")
    same_run_b = helpers["page_record"]("winmart", [item], slug="cat-b")            # same product, 2nd category
    later_run = helpers["page_record"]("winmart", [dict(item, salePrice=32000)], run_id="test_run_2",
                                       collected_at="2026-01-02T10:00:00+07:00")
    clean, rejected = run_pipeline([same_run_a, same_run_b, later_run])
    assert len(clean) == 2                                   # one per run = price history
    assert rejected["reject_reason"].tolist() == ["duplicate_in_run"]
    assert sorted(clean["sale_price_vnd"]) == [30000, 32000]
    assert clean["observation_id"].nunique() == 2


def test_timestamp_must_have_vietnam_offset(helpers):
    item = helpers["winmart_item"]("11", "Sữa test 1L", 30000)
    clean, rejected = run_pipeline([helpers["page_record"]("winmart", [item], collected_at="2026-01-01 10:00:00"),
                                    helpers["page_record"]("winmart", [item], collected_at="not a date", run_id="r2")])
    assert clean.empty
    assert set(rejected["reject_reason"]) == {"invalid_or_naive_timestamp"}


def test_list_price_below_sale_price_is_dropped_not_guessed(helpers):
    item = helpers["winmart_item"]("12", "Sữa test 1L", sale=36700, price=34200)
    clean, _ = run_pipeline([helpers["page_record"]("winmart", [item])])
    row = clean.iloc[0]
    assert pd.isna(row["list_price_vnd"]) and "list_price_below_sale_price" in row["warnings"]


def test_flash_sale_price_kept_separately_and_dom_check(helpers):
    product = helpers["bhx_product"]("1000000000003", "Sữa test 1L", 353000, flash=270000)
    card = {"product_code": "1000000000003", "card_text": "270.000đ\n-24%\n353.000đ"}
    clean, _ = run_pipeline([helpers["page_record"]("bhx", [product], dom_cards=[card])])
    row = clean.iloc[0]
    assert row["sale_price_vnd"] == 353000 and row["flash_sale_price_vnd"] == 270000
    assert row["dom_price_check"] == "match_flash_sale"


def test_missing_fields_stay_missing(helpers):
    item = helpers["winmart_item"]("13", "Khăn giấy test", 20000, brand=None)
    clean, _ = run_pipeline([helpers["page_record"]("winmart", [item])])
    row = clean.iloc[0]
    assert row["brand"] is None and pd.isna(row["size_value"]) and pd.isna(row["unit_price_vnd_per_kg_or_l"])
    assert "brand_missing" in row["warnings"] and "size_not_found" in row["warnings"]


def test_winmart_selling_units_get_their_own_pack_count(helpers):
    """Same WinMart product sold as 'Thùng' (30) and 'Gói' (1): the shared name says 'Thùng 30 gói'."""
    item = helpers["winmart_item"]("20", "Thùng 30 gói mì test 75g", 135700)
    item["uom"] = "T"
    item["uoms"] = [{"uom": "T", "uomName": "Thùng", "sku": "20T", "quantityPerUnit": 30.0, "salePrice": 135700, "price": 135700},
                    {"uom": "G1", "uomName": "Gói", "sku": "20G1", "quantityPerUnit": 1.0, "salePrice": 4700, "price": 4700}]
    clean, _ = run_pipeline([helpers["page_record"]("winmart", [item])])
    by_code = clean.set_index("product_code")
    assert by_code.loc["20T", "pack_count"] == 30 and by_code.loc["20T", "sale_price_vnd"] == 135700
    assert by_code.loc["20G1", "pack_count"] == 1 and by_code.loc["20G1", "sale_price_vnd"] == 4700
    assert bool(by_code.loc["20T", "uom_is_primary"]) and not bool(by_code.loc["20G1", "uom_is_primary"])


def test_ambiguous_size_is_left_empty(helpers):
    item = helpers["winmart_item"]("21", "Nước ngọt test chai 1.5L/1.75L", 16600)
    clean, _ = run_pipeline([helpers["page_record"]("winmart", [item])])
    assert pd.isna(clean.iloc[0]["size_value"])
