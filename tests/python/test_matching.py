"""Product matching rules on SYNTHETIC test products."""
import pandas as pd

from report2.clean import derive_fields, flatten_page, validate
from report2.matching import match


def build(helpers, bhx_items, wm_items):
    rows = []
    rows += flatten_page(helpers["page_record"]("bhx", bhx_items), "t.json")
    rows += flatten_page(helpers["page_record"]("winmart", wm_items, collected_at="2026-01-01T10:30:00+07:00"), "t.json")
    clean, _ = validate(derive_fields(pd.DataFrame(rows)))
    return match(clean, "test_run")


def status_of(results, bhx_name):
    return results.set_index("bhx_name").loc[bhx_name, "status"]


def test_identical_product_is_matched_with_price_difference(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, matched = build(helpers, [b("1000000000001", "Lốc 4 hộp sữa tươi TestBrand ít đường 180ml", 36500)],
                             [w("1", "Sữa tươi tiệt trùng TestBrand ít đường lốc 4 hộp x 180ml", 33900)])
    assert results["status"].tolist() == ["MATCHED"]
    row = matched.iloc[0]
    assert row["price_diff_vnd"] == 33900 - 36500                     # WinMart - BHX, negative = WinMart cheaper
    assert row["price_diff_pct"] == round((33900 - 36500) / 36500 * 100, 2)
    assert row["cheaper_store"] == "winmart" and bool(row["price_comparable"])
    assert row["time_gap_minutes"] == 30


def test_same_name_different_pack_is_not_matched(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, matched = build(helpers, [b("1000000000001", "Thùng 48 hộp sữa tươi TestBrand ít đường 180ml", 395000)],
                             [w("1", "Lốc 4 hộp sữa tươi TestBrand ít đường 180ml", 33900)])
    assert results["status"].tolist() == ["NOT_MATCHED"] and matched.empty
    assert results["reason"].iloc[0] == "no_winmart_product_with_same_brand_size_and_pack"


def test_different_brand_or_size_is_not_matched(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Sữa tươi TestBrand 1L", 40000),
                                 b("1000000000002", "Sữa tươi OtherBrand 1L", 40000, brand="OtherBrand")],
                       [w("1", "Sữa tươi TestBrand 180ml", 9000)])
    assert set(results["status"]) == {"NOT_MATCHED"}


def test_flavour_conflict_is_not_matched(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Sữa chua uống TestBrand dâu 170ml", 8000)],
                       [w("1", "Sữa chua uống TestBrand cam 170ml", 8000)])
    assert results["status"].tolist() == ["NOT_MATCHED"]
    assert results["reason"].iloc[0].startswith("variant_conflict")


def test_variant_missing_on_one_side_needs_review(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, matched = build(helpers, [b("1000000000001", "Sữa đặc TestBrand hộp 380g", 27500)],
                             [w("1", "Sữa đặc có đường TestBrand hộp 380g", 30000)])
    assert results["status"].tolist() == ["NEEDS_REVIEW"] and matched.empty   # not in comparison table


def test_ambiguous_candidates_need_review(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Nước giặt TestBrand 2kg", 100000)],
                       [w("1", "Nước giặt TestBrand túi 2kg", 99000), w("2", "Nước giặt TestBrand chai 2kg", 98000)])
    assert results["status"].tolist() == ["NEEDS_REVIEW"]
    assert results["reason"].iloc[0].startswith("ambiguous")


def test_one_winmart_product_is_used_only_once(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Dầu ăn TestBrand 1L", 50000),
                                 b("1000000000002", "Dầu ăn TestBrand chai 1L", 51000)],
                       [w("1", "Dầu ăn TestBrand 1L", 52000)])
    assert results["winmart_observation_id"].notna().sum() == 1


def test_brand_written_in_other_name_counts_as_brand_evidence(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Mì Hảo Hảo tôm chua cay gói 75g", 4500, brand="Hảo Hảo")],
                       [w("1", "Mì Hảo Hảo tôm chua cay 75g", 4400, brand="ACECOOK")])
    assert results["status"].tolist() == ["MATCHED"]
    assert results["reason"].iloc[0].startswith("bhx_brand_in_winmart_name")


def test_different_descriptors_need_review(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Dầu gội TestBrand Classic tóc chắc khoẻ 650g", 200000)],
                       [w("1", "Dầu gội TestBrand Gentleman tóc chắc khoẻ 650g", 201000)])
    assert results["status"].tolist() == ["NEEDS_REVIEW"]
    assert results["reason"].iloc[0].startswith("different_descriptors")


def test_two_extra_words_on_one_side_need_review(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Snack truyền thống TestBrand 6g", 12000)],
                       [w("1", "Snack truyền thống TestBrand Big Bang 6g", 12500)])
    assert results["status"].tolist() == ["NEEDS_REVIEW"]
    assert results["reason"].iloc[0].startswith("extra_descriptors_one_side")


def test_word_that_is_another_brand_needs_review(helpers):
    b, w = helpers["bhx_product"], helpers["winmart_item"]
    results, _ = build(helpers, [b("1000000000001", "Mì TestBrand tôm chua cay gói 65g", 3700),
                                 b("1000000000002", "Mì Reeva lẩu nấm gói 85g", 10200, brand="Reeva")],
                       [w("1", "Mì tôm chua cay TestBrand Reeva gói 65g", 3500)])
    row = results.set_index("bhx_name").loc["Mì TestBrand tôm chua cay gói 65g"]
    assert row["status"] == "NEEDS_REVIEW" and row["reason"].startswith("other_brand_word")
