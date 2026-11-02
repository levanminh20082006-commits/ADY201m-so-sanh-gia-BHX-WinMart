"""Report 3 preprocessing rules on SYNTHETIC rows (fix pack count, missing values, normalisation)."""
import numpy as np
import pandas as pd

from report3.preprocess import fix_values, handle_missing, normalize, pack_written_in_name


def row(name, pack, unit="Gói", size=100.0, price=10000, source="name", list_price=None, brand="B"):
    return {"store": "winmart", "category_slug": "c", "group": "g", "name_clean": name, "unit_label": unit,
            "pack_count": pack, "pack_source": source, "size_value": size, "sale_price_vnd": price,
            "list_price_vnd": list_price if list_price is not None else price, "brand": brand, "brand_key": brand,
            "flash_sale_price_vnd": np.nan, "unit_price_vnd_per_kg_or_l": np.nan}


def test_number_is_a_count_only_with_a_count_word():
    assert pack_written_in_name("Thùng 24 lon nước ngọt 330ml", 24)
    assert pack_written_in_name("Lốc 4 hộp sữa 180ml", 4)
    assert pack_written_in_name("Sữa chua 4 x 100g", 4)
    assert pack_written_in_name("Thùng 100 gói mì 75g", 100)
    assert not pack_written_in_name("Nước tăng lực Wake Up 247 vị cà phê 330ml", 247)
    assert not pack_written_in_name("Sữa tươi Meiji 4.3% hộp 946ml", 3)
    assert not pack_written_in_name("Dầu gội Thái Dương 7+ chai 250ml", 7)
    assert not pack_written_in_name("Khăn giấy Fairy 280 tờ 200 x 195mm", 200)   # a dimension, not a count


def test_three_pack_rules_and_unit_price_recomputed():
    df = fix_values(pd.DataFrame([
        row("Nước tăng lực Wake Up 247 vị cà phê 330ml", 247, "Chai", 330, 11500),   # c) number is part of name
        row("Thùng 24 lon nước ngọt 7UP 330ml", np.nan, "Gói (Lốc) 6", 330, 42900, "conflict"),  # a) selling unit
        row("Café sữa đá Nescafe 25*20g", 1, "Gói", 20, 135400),                       # b) 25 x 20 g
        row("Thùng 100 gói mì Miliket 75g", 100, "Thùng", 75, 390000),                 # kept
    ]))
    assert df["pack_count"].tolist() == [1, 6, 25, 100]
    assert df["pack_fix"].tolist()[:3] == ["number_is_part_of_name", "selling_unit_label", "n_x_size_in_name"]
    assert pd.isna(df["pack_fix"].iloc[3])
    assert df["pack_count_report2"].iloc[0] == 247                      # old value kept as evidence
    assert df["unit_price_vnd_per_kg_or_l"].iloc[0] == round(11500 / 330 * 1000)


def test_missing_values_filled_with_flags_and_size_never_invented_for_unit_price():
    df = handle_missing(fix_values(pd.DataFrame([
        row("Bánh A 100g", 1, size=100.0, list_price=np.nan),
        row("Bánh B", np.nan, size=np.nan, brand=np.nan),
        row("Bánh C 300g", 1, size=300.0),
    ])))
    assert df["list_price_vnd"].iloc[0] == df["sale_price_vnd"].iloc[0] and df["list_price_imputed"].iloc[0]
    assert df["brand"].iloc[1] == "UNKNOWN" and df["brand_imputed"].iloc[1]
    assert df["pack_count_filled"].iloc[1] == 1 and df["pack_imputed"].iloc[1]
    assert df["size_imputed"].iloc[1] and np.isclose(df["log_size_filled"].iloc[1], np.log(np.sqrt(100 * 300)))
    assert pd.isna(df["unit_price_vnd_per_kg_or_l"].iloc[1])            # no unit price from a guessed size
    assert not df[["log_size_filled", "pack_count_filled"]].isna().any().any()


def test_normalisation_ranges():
    df, params = normalize(pd.DataFrame({"x": [1.0, 2.0, 3.0, 10.0]}), columns=["x"])
    assert df["x_minmax"].min() == 0 and df["x_minmax"].max() == 1
    assert np.isclose(df["x_z"].mean(), 0) and np.isclose(df["x_z"].std(ddof=0), 1)
    assert params["x"]["median"] == 2.5
