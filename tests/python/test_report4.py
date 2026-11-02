"""Report 4 helpers on SYNTHETIC values (binning, labels) + Report 3 descriptive measures of slide 6.2."""
import pandas as pd

from report3.run import price_band
from report3.stats import describe
from report4.visualize import vn, vnd


def test_binning_turns_price_into_ordered_bands():
    bands = price_band(pd.Series([5_000, 19_999, 20_000, 99_999, 100_000, 1_500_000]))
    assert list(bands.astype(str)) == ["low (< 20k)", "low (< 20k)", "medium (20k - 100k)", "medium (20k - 100k)",
                                       "high (>= 100k)", "high (>= 100k)"]
    assert bands.cat.ordered is False or list(bands.cat.categories)[0] == "low (< 20k)"


def test_slide_6_2_measures():
    d = describe(pd.Series([10, 20, 20, 30, 120]))
    assert d["mean"] == 40 and d["median"] == 20 and d["mode"] == 20
    assert d["range"] == 110
    assert d["variance"] == pd.Series([10, 20, 20, 30, 120]).var() and round(d["std"] ** 2, 6) == round(d["variance"], 6)


def test_labels_are_rounded_and_vietnamese():
    assert [vnd(x) for x in (84_945.5, 377_500, 1_521_000)] == ["84.9k", "378k", "1.5 tr"]
    assert vn("2,095 sản phẩm, 24.6%, r = 0.994 (slide 6.3)") == "2.095 sản phẩm, 24,6%, r = 0,994 (slide 6.3)"
