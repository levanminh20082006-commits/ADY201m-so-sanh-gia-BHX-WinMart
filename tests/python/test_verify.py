"""Price readers used by the live spot-check (verify_samples.py), on hand-written TEST page text."""
from report2.verify_samples import page_prices, winmart_main_price


def test_winmart_main_price_prefers_promotion_price():
    text = "SKU: 1\nGiá niêm yết\n21.900\xa0₫\nGiá khuyến mại\n16.500\xa0₫\nTình trạng"
    assert winmart_main_price(text) == 16500


def test_winmart_main_price_without_promotion():
    assert winmart_main_price("Giá bán lẻ\n135.700\xa0₫\nGiá sản phẩm đã gồm VAT") == 135700
    assert winmart_main_price("Hết hàng") is None


def test_page_prices_reads_inline_prices():
    assert page_prices("Kẹo 18.000₫ (2.000đ/viên) và 37.000 ₫") == [18000, 2000, 37000]
