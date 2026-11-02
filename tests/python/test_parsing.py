"""Unit tests for text/price/size parsing. All inputs are hand-written TEST strings."""
from report2.parsing import (card_prices, exclusive_attributes, jaccard, name_tokens, normalize_text,
                             parse_pack_count, parse_percent, parse_price, parse_size, variant_words)


def test_parse_price_vietnamese_formats():
    assert parse_price("345.000đ") == 345000
    assert parse_price("16.500\xa0₫") == 16500
    assert parse_price("1.250.000 VND") == 1250000
    assert parse_price(92000.0) == 92000
    assert parse_price(4300) == 4300


def test_parse_price_invalid_values_return_none():
    assert parse_price(None) is None
    assert parse_price("") is None
    assert parse_price("Liên hệ") is None
    assert parse_price(float("nan")) is None


def test_parse_percent():
    assert parse_percent("-9%") == 9
    assert parse_percent("giảm 25 %") == 25
    assert parse_percent("no discount") is None


def test_card_prices_ignores_promo_lines():
    text = "Combo\nVỉ 4 hộp váng sữa\nMua 2 gói (lốc) 4 với giá 120.600\xa0₫\n76.000\xa0₫\nThêm vào giỏ"
    assert card_prices(text) == [76000]
    assert card_prices("270.000đ\n/48 bịch\n-24%\n353.000đ") == [270000, 353000]


def test_normalize_text_removes_accents_and_symbols():
    assert normalize_text("  Sữa tươi  TH true MILK 1,5L ") == "sua tuoi th true milk 1.5l"
    assert normalize_text("Đường") == "duong"


def test_parse_size_converts_units():
    assert parse_size("Dầu ăn Simply 1,5L")["size_value"] == 1500.0
    assert parse_size("Dầu ăn Simply 1,5L")["size_unit"] == "ml"
    assert parse_size("Gạo 5kg")["size_value"] == 5000.0
    assert parse_size("Mì 75g")["size_unit"] == "g"
    assert parse_size("Sữa 1 lít")["size_value"] == 1000.0
    assert parse_size("Khăn giấy hộp")["size_value"] is None


def test_parse_pack_count():
    assert parse_pack_count("Thùng 48 hộp sữa tươi 180ml") == 48
    assert parse_pack_count("Sữa lốc 4 hộp x 180ml") == 4
    assert parse_pack_count("Nước ngọt lon 320ml x 24") == 24
    assert parse_pack_count("Gói (Lốc) 3") == 3
    assert parse_pack_count("Sữa tươi Vinamilk 1 lít") == 1        # single item
    assert parse_pack_count("Thùng sữa tươi 180ml") is None          # multipack but count unknown


def test_same_name_different_packaging_is_different():
    single, pack4, carton = "Sữa tươi Vinamilk 180ml", "Lốc 4 hộp sữa tươi Vinamilk 180ml", "Thùng 48 hộp sữa tươi Vinamilk 180ml"
    assert parse_size(single) == parse_size(pack4) == parse_size(carton)
    assert {parse_pack_count(single), parse_pack_count(pack4), parse_pack_count(carton)} == {1, 4, 48}


def test_variant_words_keep_accents_apart():
    assert variant_words("Sữa chua dâu") == {"sữa chua", "dâu"}
    assert variant_words("Dầu ăn đậu nành") == {"đậu nành"}           # 'dầu' is oil, not strawberry
    assert variant_words("Sữa sô cô la") == {"socola"}                 # synonym
    assert "ít đường" not in variant_words("Sữa rất ít đường")         # longest phrase wins


def test_exclusive_attributes():
    assert exclusive_attributes("Sữa tươi tiệt trùng") == {"process": "tiệt trùng"}
    assert exclusive_attributes("Sữa tươi") == {}


def test_name_tokens_and_jaccard():
    a = name_tokens("Lốc 4 hộp sữa tươi Vinamilk ít đường 180ml", "Vinamilk")
    b = name_tokens("Sữa tươi tiệt trùng Vinamilk ít đường lốc 4 hộp x 180ml", "VINAMILK")
    assert a == {"sua", "tuoi", "it", "duong"}
    assert jaccard(a, b) == 4 / 6
    assert jaccard(set(), set()) == 0.0
