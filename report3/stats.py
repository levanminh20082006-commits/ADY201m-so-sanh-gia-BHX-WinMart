"""Report 3 - Part 2: descriptive statistics and statistical significance tests.

Only numpy / pandas / math are used (no scipy), so every formula is visible here:
- chi-square 2x2 (df = 1): p = erfc(sqrt(chi2 / 2))                    exact for df = 1
- exact sign test: two-sided binomial(n, 0.5)                          exact
- paired t-test / Mann-Whitney U / correlation: normal approximation    fine for n > 100 (here n >= 139)
- bootstrap 95% confidence interval (10 000 resamples, fixed seed)
"""
import math

import numpy as np
import pandas as pd

ALPHA = 0.05
SEED = 42


# ------------------------------------------------------------------ descriptive statistics
def describe(s: pd.Series) -> dict:
    s = s.dropna().astype(float)
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    mean = s.mean()
    return {"n": int(s.size), "mean": mean, "median": s.median(), "mode": s.mode().iloc[0], "std": s.std(), "variance": s.var(),
            "cv_pct": s.std() / mean * 100, "min": s.min(), "q1": q1, "q3": q3, "iqr": q3 - q1, "max": s.max(),
            "range": s.max() - s.min(), "skew": s.skew(), "kurtosis": s.kurt()}   # slide 6.2: mean/median/mode, variance, std


def describe_by(df: pd.DataFrame, col: str, by: list[str]) -> pd.DataFrame:
    out = pd.DataFrame({k if isinstance(k, tuple) else (k,): describe(g[col]) for k, g in df.groupby(by)}).T \
        .rename_axis(by).reset_index()
    return out.astype({"n": int})


def shape_meaning(d: dict) -> str:
    """Plain-language meaning of skewness / kurtosis / mean vs median."""
    if d["skew"] > 1:
        shape = f"strongly right-skewed (skew {d['skew']:.2f}): a few expensive items pull the mean above the median"
    elif d["skew"] > 0.5:
        shape = f"moderately right-skewed (skew {d['skew']:.2f})"
    elif d["skew"] < -0.5:
        shape = f"left-skewed (skew {d['skew']:.2f})"
    else:
        shape = f"roughly symmetric (skew {d['skew']:.2f})"
    tails = "heavy tails / many extreme values" if d["kurtosis"] > 3 else "tails close to a normal curve"
    centre = "median" if abs(d["skew"]) > 0.5 else "mean"
    return f"{shape}; {tails} (excess kurtosis {d['kurtosis']:.2f}); the {centre} is the better 'typical' value."


# ------------------------------------------------------------------ significance tests
def normal_p_two_sided(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def chi_square_2x2(table: pd.DataFrame) -> dict:
    """Test of independence for a 2x2 contingency table (no continuity correction)."""
    obs = table.to_numpy(dtype=float)
    expected = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()
    chi2 = float(((obs - expected) ** 2 / expected).sum())
    return {"chi2": chi2, "df": 1, "p_value": math.erfc(math.sqrt(chi2 / 2)),
            "min_expected": float(expected.min())}


def sign_test(n_pos: int, n_neg: int) -> dict:
    """Exact two-sided sign test; ties are left out before calling."""
    n, k = n_pos + n_neg, min(n_pos, n_neg)
    if n == 0:
        return {"n": 0, "p_value": 1.0}
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return {"n": n, "positive": n_pos, "negative": n_neg, "p_value": min(1.0, p)}


def bootstrap_ci(values, stat=np.mean, n_boot: int = 10_000, level: float = 0.95, seed: int = SEED) -> tuple:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = stat(rng.choice(values, size=(n_boot, values.size), replace=True), axis=1)
    lo, hi = np.quantile(samples, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def paired_t(diffs) -> dict:
    d = np.asarray(diffs, dtype=float)
    se = d.std(ddof=1) / math.sqrt(d.size)
    t = d.mean() / se if se else 0.0
    return {"n": int(d.size), "mean_diff": float(d.mean()), "t": float(t), "p_value": normal_p_two_sided(t)}


def mann_whitney(a: pd.Series, b: pd.Series) -> dict:
    """U test with normal approximation and tie correction. Returns also P(A > B) (common-language effect)."""
    a, b = a.dropna().to_numpy(float), b.dropna().to_numpy(float)
    n1, n2 = a.size, b.size
    ranks = pd.Series(np.concatenate([a, b])).rank().to_numpy()
    u1 = ranks[:n1].sum() - n1 * (n1 + 1) / 2
    n = n1 + n2
    ties = pd.Series(np.concatenate([a, b])).value_counts().to_numpy(float)
    var = n1 * n2 / 12 * ((n + 1) - (ties ** 3 - ties).sum() / (n * (n - 1)))
    z = (u1 - n1 * n2 / 2) / math.sqrt(var)
    return {"n_a": int(n1), "n_b": int(n2), "U": float(u1), "z": float(z), "p_value": normal_p_two_sided(z),
            "prob_a_greater": float(u1 / (n1 * n2))}


def correlation_test(x: pd.Series, y: pd.Series, method: str = "pearson") -> dict:
    """Spearman = Pearson on ranks (computed here because pandas needs scipy for it)."""
    pair = pd.concat([x, y], axis=1).dropna()
    if method == "spearman":
        pair = pair.rank()
    r = pair.iloc[:, 0].corr(pair.iloc[:, 1])
    n = len(pair)
    t = r * math.sqrt((n - 2) / (1 - r ** 2)) if abs(r) < 1 else float("inf")
    return {"method": method, "n": n, "r": float(r), "p_value": normal_p_two_sided(t)}


def verdict(p: float) -> str:
    return "significant (p < 0.05)" if p < ALPHA else "not significant (p ≥ 0.05)"


def strength(r: float) -> str:
    a = abs(r)
    return "very weak" if a < 0.2 else "weak" if a < 0.4 else "moderate" if a < 0.6 else "strong" if a < 0.8 else "very strong"


# ------------------------------------------------------------------ analyses used by the report
def promotion_test(df: pd.DataFrame) -> dict:
    table = pd.crosstab(df["store"], df["is_promotion"])
    result = chi_square_2x2(table)
    result["promo_share_pct"] = (df.groupby("store")["is_promotion"].mean() * 100).round(1).to_dict()
    result["mean_discount_when_promo"] = df[df["is_promotion"]].groupby("store")["discount_pct"].mean().round(1).to_dict()
    return result


def overall_price_test(df: pd.DataFrame) -> dict:
    """All products, NOT matched: different assortments, so this compares the shelves, not the same product."""
    return mann_whitney(df.loc[df["store"] == "winmart", "sale_price_vnd"], df.loc[df["store"] == "bhx", "sale_price_vnd"])


def matched_pairs_test(m: pd.DataFrame) -> dict:
    """The fair comparison: the same product (brand + size + pack + variant) in both stores."""
    log_ratio = np.log(m["winmart_price_vnd"] / m["bhx_price_vnd"])
    diff_pct = m["price_diff_pct"]
    t = paired_t(log_ratio)
    sign = sign_test(int((diff_pct > 0).sum()), int((diff_pct < 0).sum()))
    ci = bootstrap_ci(log_ratio)
    return {"n_pairs": len(m), "winmart_more_expensive": sign["positive"], "winmart_cheaper": sign["negative"],
            "same_price": int((diff_pct == 0).sum()),
            "mean_diff_pct": float(diff_pct.mean()), "median_diff_pct": float(diff_pct.median()),
            "geo_mean_ratio_pct": float((math.exp(t["mean_diff"]) - 1) * 100),
            "geo_mean_ratio_ci95_pct": [(math.exp(v) - 1) * 100 for v in ci],
            "paired_t": t, "sign_test": sign}


def matched_by_group(m: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, g in m.groupby("group"):
        s = sign_test(int((g["price_diff_pct"] > 0).sum()), int((g["price_diff_pct"] < 0).sum()))
        rows.append({"group": group, "pairs": len(g), "winmart_cheaper": s["negative"], "winmart_more_expensive": s["positive"],
                     "median_diff_pct": g["price_diff_pct"].median(), "mean_diff_pct": g["price_diff_pct"].mean(),
                     "sign_test_p": s["p_value"]})
    return pd.DataFrame(rows).sort_values("pairs", ascending=False, ignore_index=True)


def size_price_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Bigger total quantity -> higher price? Measured on log scale (prices are skewed)."""
    rows = []
    for store, g in df.groupby("store"):
        x = np.log(g["total_quantity"])
        for method in ("pearson", "spearman"):
            rows.append({"store": store, **correlation_test(x, g["log_price"], method)})
    return pd.DataFrame(rows)


CORR_COLUMNS = {"log_price": "log price", "log_list_price": "log list price", "discount_pct": "discount %",
                "log_size": "log size", "pack_count": "pack count", "log_total_quantity": "log total qty",
                "log_unit_price": "log unit price"}


def correlation_matrix(df: pd.DataFrame, method: str = "spearman") -> pd.DataFrame:
    x = pd.DataFrame({"log_price": df["log_price"], "log_list_price": np.log(df["list_price_vnd"]),
                      "discount_pct": df["discount_pct"], "log_size": np.log(df["size_value"]),
                      "pack_count": df["pack_count"], "log_total_quantity": np.log(df["total_quantity"]),
                      "log_unit_price": df["log_unit_price"]})
    if method == "spearman":   # pairwise: rank each pair of columns on the rows where both exist
        cols = list(x.columns)
        r = pd.DataFrame({a: [correlation_test(x[a], x[b], "spearman")["r"] for b in cols] for a in cols}, index=cols)
    else:
        r = x.corr()
    return r.rename(index=CORR_COLUMNS, columns=CORR_COLUMNS)


# ------------------------------------------------------------------ Vietnamese wording for the results file
def shape_meaning_vi(d: dict) -> str:
    """Vietnamese reading of skewness / kurtosis (same rules as shape_meaning)."""
    if d["skew"] > 1:
        shape = f"lệch phải mạnh (skew {d['skew']:.2f}): vài sản phẩm rất đắt kéo mean lên trên median"
    elif d["skew"] > 0.5:
        shape = f"lệch phải vừa (skew {d['skew']:.2f})"
    elif d["skew"] < -0.5:
        shape = f"lệch trái (skew {d['skew']:.2f})"
    else:
        shape = f"gần đối xứng (skew {d['skew']:.2f})"
    tails = "đuôi dày, nhiều giá trị cực đoan" if d["kurtosis"] > 3 else "đuôi gần giống phân phối chuẩn"
    centre = "median" if abs(d["skew"]) > 0.5 else "mean"
    return f"{shape}; {tails} (excess kurtosis {d['kurtosis']:.2f}); dùng {centre} làm giá trị điển hình."


def verdict_vi(p: float) -> str:
    return "CÓ ý nghĩa thống kê (p < 0,05)" if p < ALPHA else "KHÔNG có ý nghĩa thống kê (p ≥ 0,05)"


def strength_vi(r: float) -> str:
    return {"very weak": "rất yếu", "weak": "yếu", "moderate": "trung bình", "strong": "mạnh",
            "very strong": "rất mạnh"}[strength(r)]
