"""Report 5 - Mô hình dự đoán chênh lệch giá giữa hai siêu thị (slide 2.4 xây dựng và đánh giá mô hình, slide 6.8 hồi quy).

Input : data/processed_py/matched_products.csv   139 cặp: cùng một sản phẩm ở Bách Hóa Xanh và WinMart
Output: data/processed_py/report5_predictions.csv  giá trị thật và giá trị dự đoán (ngoài mẫu) của từng cặp
        reports_py/report5/*.png                    2 hình
        reports_py/report5_results.md               mô hình, cách đánh giá, kết quả, hạn chế

Biến cần dự đoán: y = ln(giá WinMart / giá BHX), cùng thang đo với kiểm định cặp của Report 3.
Mô hình: hồi quy tuyến tính bình phương nhỏ nhất (OLS), tự viết bằng numpy (không dùng scikit-learn) để thấy rõ công thức.
Đánh giá: kiểm định chéo 5 lần (5-fold cross-validation, seed 42): mỗi cặp được dự đoán bởi mô hình KHÔNG nhìn thấy cặp đó.
So sánh 3 mô hình:
  M0  mốc so sánh: luôn đoán bằng chênh lệch trung bình của tập huấn luyện
  M1  hồi quy theo đặc điểm sản phẩm: nhóm hàng, log khối lượng/dung tích, số lượng trong gói
  M2  M1 + tình trạng khuyến mãi ở từng siêu thị (giá bán < giá niêm yết)
Không đưa giá bán, giá niêm yết hay đơn giá vào biến đầu vào: chúng chứa sẵn đáp án (rò rỉ dữ liệu).
Usage: python -m report5.model
"""
import math

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from report2 import settings
from report3.run import fmt, md_table, vn
from report4.visualize import GRID, GROUP_VI, INK, MUTED, SURFACE, style

MATCHED = settings.PROCESSED_DIR / "matched_products.csv"
PREDICTIONS = settings.PROCESSED_DIR / "report5_predictions.csv"
OUT = settings.REPORTS_DIR / "report5"
RESULTS = settings.REPORTS_DIR / "report5_results.md"

SEED = 42
K = 5
REPEATS = 20                 # lặp lại 5-fold với 20 cách chia khác nhau để xem kết quả có ổn định không
MIN_GROUP_PAIRS = 10         # nhóm hàng ít hơn 10 cặp gộp thành "nhóm nhỏ" để hệ số không quá bất ổn
SMALL = "small_groups"
MODELS = {"M0": "Mốc so sánh (đoán bằng trung bình)", "M1": "Hồi quy: nhóm hàng + kích thước",
          "M2": "Hồi quy: + khuyến mãi ở hai nơi"}
FEATURE_VI = {"intercept": "Hệ số chặn (nhóm Đồ uống, không khuyến mãi)", "log_size": "log khối lượng / dung tích",
              "pack_count": "số lượng trong gói", "promo_bhx": "BHX đang khuyến mãi", "promo_winmart": "WinMart đang khuyến mãi"}
COLOR = {"M1": "#2a78d6", "M2": "#eb6834"}


# ------------------------------------------------------------------ data and features
def target(m: pd.DataFrame) -> np.ndarray:
    return np.log(m["winmart_price_vnd"] / m["bhx_price_vnd"]).to_numpy(float)


def features(m: pd.DataFrame, with_promo: bool) -> pd.DataFrame:
    """Design matrix (without intercept). Only product attributes and promotion flags: no price columns."""
    counts = m["group"].value_counts()
    group = m["group"].where(m["group"].map(counts) >= MIN_GROUP_PAIRS, SMALL)
    levels = sorted(group.unique())
    x = pd.DataFrame(index=m.index)
    for g in levels[1:]:                                   # first level (alphabetical) is the reference
        x[f"group_{g}"] = (group == g).astype(float)
    x["log_size"] = np.log(m["size_value"].astype(float))
    x["pack_count"] = m["pack_count"].astype(float)
    if with_promo:
        x["promo_bhx"] = (m["bhx_price_vnd"] < m["bhx_list_price_vnd"]).astype(float)
        x["promo_winmart"] = (m["winmart_price_vnd"] < m["winmart_list_price_vnd"]).astype(float)
    return x


# ------------------------------------------------------------------ model and metrics (numpy only)
def add_intercept(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x])


def ols_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Least squares: b minimises sum (y - Xb)^2. lstsq is the stable way to solve (X'X) b = X'y."""
    return np.linalg.lstsq(add_intercept(x), y, rcond=None)[0]


def ols_predict(b: np.ndarray, x: np.ndarray) -> np.ndarray:
    return add_intercept(x) @ b


def r2(y, pred) -> float:
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    return float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def mae(y, pred) -> float:
    return float(np.mean(np.abs(np.asarray(y, float) - np.asarray(pred, float))))


def sign_accuracy(y, pred) -> float:
    """Share of pairs with a price gap where the model guesses the cheaper store right."""
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    keep = y != 0
    return float(np.mean(np.sign(pred[keep]) == np.sign(y[keep])))


def kfold_indices(n: int, k: int = K, seed: int = SEED) -> list[np.ndarray]:
    return np.array_split(np.random.default_rng(seed).permutation(n), k)


def cross_val_predict(x: np.ndarray | None, y: np.ndarray, k: int = K, seed: int = SEED) -> np.ndarray:
    """Out-of-fold predictions. x=None means the baseline: predict the training mean."""
    pred = np.empty_like(y, dtype=float)
    idx = np.arange(len(y))
    for test in kfold_indices(len(y), k, seed):
        train = np.setdiff1d(idx, test)
        pred[test] = y[train].mean() if x is None else ols_predict(ols_fit(x[train], y[train]), x[test])
    return pred


# ------------------------------------------------------------------ analysis
def evaluate(m: pd.DataFrame) -> dict:
    y = target(m)
    xs = {"M0": None, "M1": features(m, False), "M2": features(m, True)}
    preds, rows = {}, []
    for name, x in xs.items():
        arr = None if x is None else x.to_numpy(float)
        preds[name] = cross_val_predict(arr, y)
        rep = [cross_val_predict(arr, y, seed=SEED + i) for i in range(REPEATS)]
        r2s = [r2(y, p) for p in rep]
        rows.append({"model": name, "mo_ta": MODELS[name], "so_bien": 0 if x is None else x.shape[1],
                     "r2_cv": r2(y, preds[name]), "mae_cv_pct": mae(y, preds[name]) * 100,
                     "dung_noi_re_hon_pct": sign_accuracy(y, preds[name]) * 100 if name != "M0" else float("nan"),
                     "r2_cv_20_lan_min": min(r2s), "r2_cv_20_lan_max": max(r2s)})
    x2 = xs["M2"]
    b = ols_fit(x2.to_numpy(float), y)
    coef = pd.DataFrame({"bien": ["intercept"] + list(x2.columns), "he_so": b})
    coef["anh_huong_pct"] = (np.exp(coef["he_so"]) - 1) * 100
    coef["y_nghia"] = coef["bien"].map(lambda c: FEATURE_VI.get(c) or "nhóm " + GROUP_VI.get(c[6:], "nhỏ (Tẩy rửa + Chăm sóc cá nhân)"))
    pred_df = pd.DataFrame({"group": m["group"], "bhx_name": m["bhx_name"], "bhx_price_vnd": m["bhx_price_vnd"],
                            "winmart_price_vnd": m["winmart_price_vnd"], "y_log_ratio": y,
                            "pred_M1": preds["M1"], "pred_M2": preds["M2"]})
    return {"y": y, "preds": preds, "table": pd.DataFrame(rows), "coef": coef, "pred_df": pred_df,
            "in_sample_r2_m2": r2(y, ols_predict(b, x2.to_numpy(float))),
            "promo": {"bhx": int(x2["promo_bhx"].sum()), "winmart": int(x2["promo_winmart"].sum())},
            "n": len(y), "small_groups": sorted(set(m["group"]) - set(m["group"].value_counts()[lambda s: s >= MIN_GROUP_PAIRS].index))}


# ------------------------------------------------------------------ figures
def fig_pred_vs_actual(res: dict) -> str:
    y = res["y"] * 100
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharex=True, sharey=True)
    lim = max(abs(y).max(), 45)
    for ax, name in zip(axes, ["M1", "M2"]):
        p = res["preds"][name] * 100
        row = res["table"].set_index("model").loc[name]
        ax.plot([-lim, lim], [-lim, lim], color=MUTED, linewidth=1, linestyle="--")
        ax.axhline(0, color=GRID, linewidth=1)
        ax.axvline(0, color=GRID, linewidth=1)
        ax.scatter(y, p, s=22, color=COLOR[name], alpha=0.75, edgecolor="white", linewidth=0.5)
        style(ax, f"{name}: {MODELS[name][9:]}\nR² = {fmt(row.r2_cv, 2)} · sai trung bình {fmt(row.mae_cv_pct, 1)} điểm %",
              "Chênh lệch thật (log %, dương = WinMart đắt hơn)", "Chênh lệch dự đoán (log %)" if name == "M1" else "", grid=None)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
    fig.suptitle("Dự đoán ngoài mẫu (5-fold) so với thực tế, 139 cặp · càng gần đường chéo càng đúng", x=0.01, ha="left", color=INK)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / "01_du_doan_so_voi_thuc_te.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return "01_du_doan_so_voi_thuc_te.png"


def fig_compare(res: dict) -> str:
    t = res["table"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    colors = ["#c3c2b7", COLOR["M1"], COLOR["M2"]]
    labels = ["M0\nđoán bằng\ntrung bình", "M1\nnhóm hàng\n+ kích thước", "M2\n+ khuyến mãi\nở hai nơi"]
    for ax, col, title, f in [(axes[0], "mae_cv_pct", "Sai trung bình (điểm %) – càng thấp càng tốt", 1),
                              (axes[1], "r2_cv", "R² ngoài mẫu – càng cao càng tốt", 2)]:
        bars = ax.bar(labels, t[col], color=colors, width=0.6)
        for bar, v in zip(bars, t[col]):
            ax.text(bar.get_x() + bar.get_width() / 2, v, fmt(v, f), ha="center", va="bottom", color=INK, fontsize=10)
        style(ax, title)
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, 2 if f == 2 else 0)))
    fig.tight_layout()
    fig.savefig(OUT / "02_so_sanh_3_mo_hinh.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return "02_so_sanh_3_mo_hinh.png"


# ------------------------------------------------------------------ report
def report(res: dict, figs: list[str]) -> str:
    t = res["table"].set_index("model")
    m0, m1, m2 = t.loc["M0"], t.loc["M1"], t.loc["M2"]
    coef = res["coef"].copy()
    coef_show = coef[["y_nghia", "he_so", "anh_huong_pct"]].rename(
        columns={"y_nghia": "biến", "he_so": "hệ số (log)", "anh_huong_pct": "ảnh hưởng lên giá WinMart so với BHX (%)"})
    show = res["table"].drop(columns=["model"]).rename(columns={
        "mo_ta": "mô hình", "so_bien": "số biến", "r2_cv": "R² (5-fold)", "mae_cv_pct": "sai trung bình (điểm %)",
        "dung_noi_re_hon_pct": "đoán đúng nơi rẻ hơn (%)", "r2_cv_20_lan_min": "R² thấp nhất (20 lần chia)",
        "r2_cv_20_lan_max": "R² cao nhất (20 lần chia)"})
    pw = coef.set_index("bien")["anh_huong_pct"]
    text = f"""# Report 5 – Mô hình dự đoán chênh lệch giá

**Câu hỏi:** từ đặc điểm của một sản phẩm, có dự đoán được nó ở WinMart đắt hơn hay rẻ hơn Bách Hóa Xanh bao nhiêu không?

## 1. Dữ liệu và biến (slide 2.4)
- {res['n']} cặp sản phẩm giống hệt nhau ở hai siêu thị (Report 2–3), giá lấy ngày 12/10/2026.
- **Biến cần dự đoán:** y = ln(giá WinMart / giá BHX). y > 0 là WinMart đắt hơn; e^y − 1 là phần trăm chênh lệch.
- **Biến đầu vào:** nhóm hàng (biến giả; nhóm dưới {MIN_GROUP_PAIRS} cặp gộp thành "nhóm nhỏ": {', '.join(GROUP_VI[g] for g in res['small_groups'])}), log khối lượng/dung tích, số lượng trong gói, và ở M2 thêm cờ khuyến mãi ở từng nơi (BHX {res['promo']['bhx']} cặp, WinMart {res['promo']['winmart']} cặp).
- **Không dùng** giá bán, giá niêm yết hay đơn giá làm biến đầu vào vì chúng chứa sẵn đáp án.

## 2. Mô hình và cách đánh giá
- **Hồi quy tuyến tính (slide 6.8)**, ước lượng bằng bình phương nhỏ nhất, tự viết bằng numpy (`report5/model.py`).
- **Mốc so sánh M0:** luôn đoán bằng chênh lệch trung bình. Mô hình chỉ có giá trị khi tốt hơn mốc này.
- **Kiểm định chéo 5 lần (seed {SEED}):** chia 139 cặp thành 5 phần; mỗi lần học trên 4 phần, dự đoán phần còn lại. Mọi con số dưới đây là dự đoán **ngoài mẫu**. Lặp lại với {REPEATS} cách chia khác nhau để kiểm tra độ ổn định.
- **Thước đo:** R² (tỉ lệ biến động của chênh lệch được mô hình giải thích), sai trung bình tuyệt đối (điểm %), tỉ lệ đoán đúng nơi rẻ hơn (bỏ {int((res['y'] == 0).sum())} cặp bằng giá).

## 3. Kết quả

{md_table(show, 2)}

![So sánh 3 mô hình](report5/{figs[1]})

![Dự đoán so với thực tế](report5/{figs[0]})

**Đọc kết quả:**
- **M1 (chỉ đặc điểm sản phẩm)** gần như không tốt hơn mốc so sánh: R² = {fmt(m1.r2_cv, 2)}, sai trung bình {fmt(m1.mae_cv_pct, 1)} điểm % so với {fmt(m0.mae_cv_pct, 1)} điểm % của M0, đoán đúng nơi rẻ hơn {fmt(m1.dung_noi_re_hon_pct, 0)}%, gần như tung đồng xu. Biết loại hàng và kích thước không đoán được nơi nào rẻ hơn, khớp với kết luận kiểm định cặp (p = 0,51) ở Report 3.
- **M2 (thêm khuyến mãi)** giải thích được khoảng {fmt(m2.r2_cv * 100, 0)}% biến động của chênh lệch (R² ngoài mẫu {fmt(m2.r2_cv, 2)}, dao động {fmt(m2.r2_cv_20_lan_min, 2)}–{fmt(m2.r2_cv_20_lan_max, 2)} qua {REPEATS} cách chia), sai trung bình giảm còn {fmt(m2.mae_cv_pct, 1)} điểm %. Chênh lệch giá gắn chủ yếu với khuyến mãi tạm thời, không phải với loại hàng.
- R² trên chính dữ liệu huấn luyện của M2 là {fmt(res['in_sample_r2_m2'], 2)}, cao hơn R² ngoài mẫu: đây là lý do phải đánh giá ngoài mẫu.

## 4. Hệ số của M2 (học trên cả 139 cặp)

{md_table(coef_show, 2)}

- Khi **WinMart đang khuyến mãi**, giá WinMart so với BHX thấp hơn khoảng {fmt(-pw['promo_winmart'], 0)}%; khi **BHX đang khuyến mãi**, giá WinMart so với BHX cao hơn khoảng {fmt(pw['promo_bhx'], 0)}% (các yếu tố khác giữ nguyên).
- Hệ số cho biết mối liên hệ trong dữ liệu, không chứng minh quan hệ nhân quả.

## 5. Hạn chế
- Chỉ {res['n']} cặp và giá lấy một lần: mô hình **giải thích** chênh lệch tại một thời điểm, chưa dự đoán được giá trong tương lai.
- Cờ khuyến mãi được ghi nhận cùng lúc với giá, nên M2 chỉ dùng được khi đã biết sản phẩm đang khuyến mãi ở đâu.
- Chưa so sánh với mô hình phi tuyến (Random Forest); với 139 cặp, mô hình phức tạp dễ học thuộc dữ liệu huấn luyện.
"""
    return vn(text).replace("| nan |", "| — |")


def run() -> dict:
    m = pd.read_csv(MATCHED)
    res = evaluate(m)
    figs = [fig_pred_vs_actual(res), fig_compare(res)]
    res["pred_df"].to_csv(PREDICTIONS, index=False, encoding="utf-8-sig")
    RESULTS.write_text(report(res, figs), encoding="utf-8")
    return res


def main() -> None:
    res = run()
    print(res["table"].round(3).to_string(index=False))
    print(res["coef"].round(3).to_string(index=False))
    print("wrote", RESULTS, PREDICTIONS, OUT)


if __name__ == "__main__":
    main()
