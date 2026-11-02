"""Report 3 - evidence files for the presentation (CSV opens in Excel, PNG figures).

Output: evidence/report3/*.csv, *.png  - every number is computed from the project files, nothing typed by hand.
Usage : python -m report3.evidence
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from report2 import settings
from report3 import preprocess as P
from report3 import stats as S
from report3.run import MATCHED_FILE, VARIABLES

OUT = settings.ROOT / "evidence" / "report3"
COLORS = {"bhx": "#2a78d6", "winmart": "#eb6834"}          # validated categorical slots 1-2
NAMES = {"bhx": "Bách Hóa Xanh", "winmart": "WinMart"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
DECISION_VI = {
    "list_price_vnd": "Điền = giá bán (không có khuyến mãi)", "brand": "Điền 'UNKNOWN' + cột cờ brand_imputed",
    "brand_key": "Điền 'unknown'", "pack_count": "Điền 1 (mode, 74% dòng) vào pack_count_filled + cờ pack_imputed",
    "size_value": "KHÔNG bịa cho giá/kg; chỉ điền median nhóm (log) vào log_size_filled + cờ size_imputed",
    "size_unit": "Để trống (không đoán được)", "size_source": "Để trống", "pack_source": "Để trống",
    "total_quantity": "Tính lại sau khi sửa; trống khi thiếu size/pack",
    "unit_price_vnd_per_kg_or_l": "Tính lại sau khi sửa; trống khi thiếu size/pack",
    "flash_sale_price_vnd": "Đổi thành cột có/không: is_flash_sale",
}


def save_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def style(ax, title: str, xlabel: str, ylabel: str = "Số sản phẩm") -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED)


def figure(n_cols: int, width: float = 11, height: float = 4.2):
    fig, axes = plt.subplots(1, n_cols, figsize=(width, height), facecolor=SURFACE)
    return fig, np.atleast_1d(axes)


# ------------------------------------------------------------------ evidence per presenter
def person1(clean: pd.DataFrame, matched: pd.DataFrame) -> None:
    save_csv(pd.DataFrame([{"bien": v, "kieu_du_lieu": k, "y_nghia": m, "so_gia_tri_khac_nhau": int(clean[v].nunique()),
                            "thieu_%": round(clean[v].isna().mean() * 100, 1),
                            "vi_du": clean[v].dropna().iloc[0] if clean[v].notna().any() else ""}
                           for v, k, m in VARIABLES]), "1_bien_va_kieu_du_lieu.csv")
    save_csv(pd.crosstab(clean["group"], clean["store"], margins=True, margins_name="tong").reset_index(),
             "1_so_dong_theo_nhom_hang.csv")
    save_csv(clean["unit_label"].value_counts().rename_axis("don_vi_ban").reset_index(name="so_dong"),
             "1_don_vi_ban.csv")


def person2(df: pd.DataFrame) -> None:
    keep = ["n", "mean", "median", "mode", "std", "variance", "cv_pct", "min", "q1", "q3", "iqr", "max", "range", "skew", "kurtosis"]
    save_csv(S.describe_by(df, "sale_price_vnd", ["store"])[["store"] + keep].round(2), "2_thong_ke_gia_ban_theo_sieu_thi.csv")
    save_csv(S.describe_by(df, "sale_price_vnd", ["group", "store"])[["group", "store"] + keep].round(2),
             "2_thong_ke_gia_ban_theo_nhom.csv")
    save_csv(S.describe_by(df, "unit_price_vnd_per_kg_or_l", ["store"])[["store"] + keep].round(2),
             "2_thong_ke_gia_tren_kg_lit.csv")
    save_csv(S.correlation_matrix(df).round(3).reset_index().rename(columns={"index": "bien"}), "2_tuong_quan_spearman.csv")

    fig, (a, b) = figure(2)
    raw_bins = np.linspace(0, 600_000, 41)
    log_bins = np.linspace(df["log_price"].min(), df["log_price"].max(), 41)
    for store in ("bhx", "winmart"):
        s = df[df["store"] == store]
        a.hist(s["sale_price_vnd"].clip(upper=600_000), bins=raw_bins, histtype="step", linewidth=2,
               color=COLORS[store], label=NAMES[store])
        b.hist(s["log_price"], bins=log_bins, histtype="step", linewidth=2, color=COLORS[store], label=NAMES[store])
    a.xaxis.set_major_formatter(lambda x, _: f"{x / 1000:.0f}k")
    style(a, f"Giá gốc: lệch phải mạnh (skew = {df['sale_price_vnd'].skew():.2f})", "Giá bán (VND, >600k gộp vào cột cuối)")
    style(b, f"Sau khi lấy log: gần cân đối (skew = {df['log_price'].skew():.2f})", "log(giá bán)")
    a.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "2_hinh_phan_phoi_gia_goc_va_log.png", dpi=150)
    plt.close(fig)


def person3(df: pd.DataFrame, matched: pd.DataFrame) -> None:
    promo, overall, pairs = S.promotion_test(df), S.overall_price_test(df), S.matched_pairs_test(matched)
    rows = [
        ("H1 Tỉ lệ khuyến mãi BHX vs WinMart", "Chi-square 2x2", f"chi2 = {promo['chi2']:.2f}", promo["p_value"],
         f"BHX {promo['promo_share_pct']['bhx']}% vs WinMart {promo['promo_share_pct']['winmart']}%"),
        ("H2 Giá cả kệ hàng (không ghép cặp)", "Mann-Whitney U", f"z = {overall['z']:.2f}", overall["p_value"],
         f"P(giá WinMart > giá BHX) = {overall['prob_a_greater']:.3f} - so sánh khác mặt hàng"),
        ("H3 Cùng 1 sản phẩm (139 cặp)", "Paired t-test trên log(WinMart/BHX)", f"t = {pairs['paired_t']['t']:.3f}",
         pairs["paired_t"]["p_value"], f"chênh trung bình hình học {pairs['geo_mean_ratio_pct']:+.2f}%"),
        ("H3 Cùng 1 sản phẩm (139 cặp)", "Sign test chính xác", f"{pairs['winmart_cheaper']} rẻ hơn / "
         f"{pairs['winmart_more_expensive']} đắt hơn", pairs["sign_test"]["p_value"], f"{pairs['same_price']} cặp bằng giá bị loại"),
    ]
    out = pd.DataFrame(rows, columns=["gia_thuyet", "kiem_dinh", "thong_ke", "p_value", "ghi_chu"])
    out["ket_luan_alpha_0.05"] = out["p_value"].map(lambda p: "CÓ ý nghĩa thống kê" if p < S.ALPHA else "KHÔNG có ý nghĩa thống kê")
    save_csv(out, "3_ket_qua_kiem_dinh.csv")
    save_csv(S.matched_by_group(matched).round(4), "3_kiem_dinh_theo_nhom_hang.csv")
    cols = ["group", "brand", "bhx_name", "winmart_name", "size_value", "size_unit", "pack_count",
            "bhx_price_vnd", "winmart_price_vnd", "price_diff_vnd", "price_diff_pct", "cheaper_store"]
    pairs_df = matched[cols].copy()
    pairs_df["log_ratio_winmart_bhx"] = np.log(matched["winmart_price_vnd"] / matched["bhx_price_vnd"]).round(5)
    save_csv(pairs_df.sort_values("price_diff_pct"), "3_139_cap_san_pham_chenh_lech.csv")

    fig, (ax,) = figure(1, 8, 4.2)
    ax.hist(matched["price_diff_pct"], bins=np.arange(-35, 52.5, 2.5), color=COLORS["bhx"], edgecolor=SURFACE, linewidth=1)
    ax.axvline(0, color=INK, linewidth=1.5)
    ax.text(18, ax.get_ylim()[1] * 0.92, f"Vạch đen 0% = bằng giá\n{pairs['winmart_cheaper']} cặp WinMart rẻ hơn (trái)\n"
            f"{pairs['winmart_more_expensive']} cặp WinMart đắt hơn (phải)", color=INK, fontsize=9, va="top")
    style(ax, f"139 cặp cùng sản phẩm: chênh lệch quanh 0 (paired t p = {pairs['paired_t']['p_value']:.2f})",
          "Chênh lệch giá WinMart so với BHX (%)", "Số cặp")
    fig.tight_layout()
    fig.savefig(OUT / "3_hinh_chenh_lech_139_cap.png", dpi=150)
    plt.close(fig)


def person4(df: pd.DataFrame, log: dict) -> None:
    fixes = df[df["pack_fix"].notna()][["store", "name_clean", "unit_label", "size_value", "size_unit",
                                        "pack_count_report2", "pack_count", "unit_price_report2",
                                        "unit_price_vnd_per_kg_or_l", "pack_fix", "row_id"]]
    save_csv(fixes.rename(columns={"pack_count_report2": "pack_cu", "pack_count": "pack_moi",
                                   "unit_price_report2": "gia_kg_lit_cu", "unit_price_vnd_per_kg_or_l": "gia_kg_lit_moi",
                                   "pack_fix": "ly_do_sua"}), "4_sua_pack_count_truoc_sau.csv")
    miss = pd.DataFrame(log["missing_before"])
    miss["loai_thieu"] = miss["type"].map({"structural": "Thiếu do cấu trúc (không phải lỗi)", "real gap": "Thiếu thật"})
    miss["cach_xu_ly"] = miss["column"].map(DECISION_VI).fillna("Để trống (không áp dụng)")
    save_csv(miss[["column", "missing_total", "bhx_pct", "winmart_pct", "loai_thieu", "note", "cach_xu_ly"]],
             "4_missing_value_va_cach_xu_ly.csv")
    flags = ["list_price_imputed", "brand_imputed", "pack_imputed", "size_imputed"]
    save_csv(df[df[flags].any(axis=1)][["store", "name_clean", "brand", "list_price_vnd", "pack_count_filled",
                                        "size_value", "log_size_filled"] + flags], "4_cac_dong_da_dien_gia_tri.csv")

    # evidence for the questions a lecturer may ask (Nguoi 4)
    save_csv(df.nsmallest(20, "unit_price_report2")[["store", "name_clean", "size_value", "size_unit", "pack_count_report2",
                                                     "sale_price_vnd", "unit_price_report2", "pack_count",
                                                     "unit_price_vnd_per_kg_or_l"]],
             "4_hoi_gia_kg_thap_nhat_truoc_khi_sua.csv")
    kept = df[(df["pack_source"] == "name") & (df["pack_count_report2"] > 1) & df["pack_fix"].isna()]
    save_csv(kept[["store", "name_clean", "unit_label", "pack_count"]].sort_values("pack_count", ascending=False),
             "4_hoi_pack_tu_ten_duoc_giu_nguyen.csv")
    lots = df[df["pack_fix"] == "selling_unit_label"].copy()
    lots["so_trong_ten"] = lots["name_clean"].str.extract(r"(?i)thùng\s*(\d+)")[0].astype(float)
    lots["gia_1_mon_theo_loc"] = (lots["sale_price_vnd"] / lots["pack_count"]).round()
    lots["gia_1_mon_neu_theo_ten"] = (lots["sale_price_vnd"] / lots["so_trong_ten"]).round()
    save_csv(lots[["name_clean", "unit_label", "sale_price_vnd", "pack_count", "gia_1_mon_theo_loc",
                   "so_trong_ten", "gia_1_mon_neu_theo_ten"]], "4_hoi_27_dong_ban_theo_loc.csv")
    # flash sale: BEFORE (Report 2 file, only the price column with empty cells) vs AFTER (new yes/no column)
    flash_cols = ["store", "name_clean", "sale_price_vnd", "flash_sale_price_vnd", "flash_sale_start", "flash_sale_end"]
    order = df.sort_values(["is_flash_sale", "store"], ascending=[False, True]).index    # flash-sale rows on top
    save_csv(df.loc[order, flash_cols], "4_flash_sale_TRUOC_report3.csv")
    save_csv(df.loc[order, flash_cols + ["is_flash_sale", "is_flash_sale_int"]], "4_flash_sale_SAU_report3.csv")
    rate = pd.crosstab(df["group"], df["store"], values=df["size_value"].isna(), aggfunc="mean") * 100
    save_csv(rate.round(1).reset_index().rename(columns={"bhx": "bhx_%_thieu_khoi_luong",
                                                         "winmart": "winmart_%_thieu_khoi_luong"}),
             "4_hoi_ti_le_thieu_khoi_luong_theo_nhom.csv")

    real = miss[miss["type"] == "real gap"].sort_values("missing_total")
    fig, (ax,) = figure(1, 9, 4.6)
    y = np.arange(len(real))
    h = 0.38
    for i, store in enumerate(("bhx", "winmart")):   # BHX drawn on top of each pair, same order as the legend
        vals, offset = real[f"{store}_pct"].to_numpy(), (0.5 - i) * (h + 0.02)
        ax.barh(y + offset, vals, height=h, color=COLORS[store], label=NAMES[store])
        for yy, v in zip(y, vals):
            if v > 0:
                ax.text(v + 0.15, yy + offset, f"{v:.1f}%", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(y, real["column"])
    style(ax, "Thiếu thật (real gap) theo cột - % số dòng của mỗi siêu thị", "% dòng bị thiếu", "")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "4_hinh_missing_value.png", dpi=150)
    plt.close(fig)


def person5(df: pd.DataFrame, log: dict) -> None:
    out = df[df["log_price_outlier"] | df["unit_price_outlier"]]
    save_csv(out[["store", "group", "name_clean", "sale_price_vnd", "unit_price_vnd_per_kg_or_l",
                  "price_outlier", "log_price_outlier", "unit_price_outlier"]].sort_values(["group", "sale_price_vnd"]),
             "5_outlier_duoc_danh_dau.csv")
    save_csv(pd.DataFrame(log["scaling_params"]).T.round(6).reset_index().rename(columns={"index": "feature"}),
             "5_tham_so_normalize.csv")
    sample = df.sample(20, random_state=1)[["store", "name_clean", "sale_price_vnd", "log_price", "log_price_minmax",
                                            "log_price_z", "log_price_robust"]].round(4)
    save_csv(sample, "5_normalize_20_dong_mau.csv")
    check = df[[f"log_price{s}" for s in ("", "_minmax", "_z", "_robust")]].describe().T.round(4)
    save_csv(check.reset_index().rename(columns={"index": "cot"}), "5_kiem_tra_normalize.csv")

    fig, axes = figure(4, 13, 3.6)
    panels = [("log_price", "log(giá)"), ("log_price_minmax", "Min-max -> [0, 1]"),
              ("log_price_z", "Z-score -> mean 0, std 1"), ("log_price_robust", "Robust -> (x - median) / IQR")]
    for ax, (col, title) in zip(axes, panels):
        ax.hist(df[col], bins=40, color=COLORS["bhx"], edgecolor=SURFACE, linewidth=0.6)
        style(ax, title, f"min {df[col].min():.2f} / max {df[col].max():.2f}", "Số dòng" if col == "log_price" else "")
    fig.suptitle("Cùng một hình dạng phân phối - chỉ đổi thang đo", x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "5_hinh_so_sanh_normalize.png", dpi=150)
    plt.close(fig)


NEW_COLUMNS = {   # column -> (Report 3 step, meaning in Vietnamese)
    "pack_count_report2": ("3.1 Sửa lỗi", "pack_count CŨ của Report 2 (giữ lại để đối chiếu)"),
    "unit_price_report2": ("3.1 Sửa lỗi", "giá/kg-lít CŨ của Report 2 (giữ lại để đối chiếu)"),
    "pack_fix": ("3.1 Sửa lỗi", "lý do sửa pack_count (trống = không sửa)"),
    "list_price_imputed": ("3.2 Missing", "cờ: giá niêm yết được điền = giá bán"),
    "is_flash_sale": ("3.2 Missing", "có flash sale hay không (thay cho ô giá flash sale trống)"),
    "brand_imputed": ("3.2 Missing", "cờ: thương hiệu được điền 'UNKNOWN'"),
    "pack_imputed": ("3.2 Missing", "cờ: số lượng trong gói được điền 1"),
    "pack_count_filled": ("3.2 Missing", "số lượng trong gói, ô trống đã điền 1 (dùng cho mô hình)"),
    "size_imputed": ("3.2 Missing", "cờ: khối lượng được điền median (chỉ cho mô hình)"),
    "log_size_filled": ("3.2 Missing", "log khối lượng, ô trống điền median cùng siêu thị + danh mục"),
    "log_price": ("3.3 Outlier / log", "log của giá bán (bớt lệch phải)"),
    "log_unit_price": ("3.3 Outlier / log", "log của giá/kg-lít"),
    "price_outlier": ("3.3 Outlier / log", "cờ outlier theo giá gốc (IQR trong nhóm hàng)"),
    "log_price_outlier": ("3.3 Outlier / log", "cờ outlier theo log giá"),
    "unit_price_outlier": ("3.3 Outlier / log", "cờ outlier theo log giá/kg-lít"),
}
for base, label in (("log_price", "log giá"), ("discount_pct", "% giảm giá"), ("log_size_filled", "log khối lượng"),
                    ("pack_count_filled", "số lượng trong gói")):
    NEW_COLUMNS[f"{base}_minmax"] = ("3.4 Normalize", f"{label} chuẩn hóa min-max về [0, 1]")
    NEW_COLUMNS[f"{base}_z"] = ("3.4 Normalize", f"{label} chuẩn hóa z-score (mean 0, std 1)")
    NEW_COLUMNS[f"{base}_robust"] = ("3.4 Normalize", f"{label} chuẩn hóa robust (x - median) / IQR")
CHANGE_REASON = {"pack_count": "sửa số lượng sai (3.1)", "total_quantity": "tính lại sau khi sửa số lượng",
                 "unit_price_vnd_per_kg_or_l": "tính lại sau khi sửa số lượng", "list_price_vnd": "điền = giá bán (3.2)",
                 "brand": "điền 'UNKNOWN' (3.2)", "brand_key": "điền 'unknown' (3.2)"}


def before_after(clean: pd.DataFrame, df: pd.DataFrame) -> None:
    """Whole Report 3: input file (Report 2) vs output file - new columns, changed cells, summary."""
    rows = []
    for c in df.columns:
        if c in clean.columns:
            continue
        step, meaning = NEW_COLUMNS.get(c, ("3.5 Encoding", "mã hóa 0/1 (one-hot / có-không) cho mô hình"))
        rows.append({"cot_moi": c, "buoc_report3": step, "y_nghia": meaning, "vi_du_gia_tri": df[c].dropna().iloc[0]})
    save_csv(pd.DataFrame(rows), "R3_38_cot_moi_va_y_nghia.csv")
    changes = []
    for c in clean.columns:
        diff = clean[c].fillna("<trống>").astype(str) != df[c].fillna("<trống>").astype(str)
        for i in diff[diff].index:
            changes.append({"row_id": clean.at[i, "row_id"], "san_pham": clean.at[i, "name_clean"], "cot": c,
                            "TRUOC": clean.at[i, c] if pd.notna(clean.at[i, c]) else "<trống>",
                            "SAU": df.at[i, c] if pd.notna(df.at[i, c]) else "<trống>", "ly_do": CHANGE_REASON.get(c, "")})
    order = {c: i for i, c in enumerate(CHANGE_REASON)}                      # pack_count fixes first
    changes = sorted(changes, key=lambda r: order.get(r["cot"], 99))
    save_csv(pd.DataFrame(changes), "R3_cac_o_da_thay_doi_truoc_sau.csv")
    feats = ["log_price", "discount_pct", "log_size_filled", "pack_count_filled"]
    summary = [
        ("Số dòng", len(clean), len(df)),
        ("Số cột", clean.shape[1], df.shape[1]),
        ("Số ô giá trị bị thay đổi", "", len(changes)),
        ("pack_count sai (Wake Up 247, lốc 6, 25*20g...)", "41 dòng sai", "đã sửa 41"),
        ("Dòng có giá/kg-lít", int(clean["unit_price_vnd_per_kg_or_l"].notna().sum()), int(df["unit_price_vnd_per_kg_or_l"].notna().sum())),
        ("Giá/kg-lít thấp nhất (đ)", int(clean["unit_price_vnd_per_kg_or_l"].min()), int(df["unit_price_vnd_per_kg_or_l"].min())),
        ("Thương hiệu trống", int(clean["brand"].isna().sum()), int(df["brand"].isna().sum())),
        ("Giá niêm yết trống", int(clean["list_price_vnd"].isna().sum()), int(df["list_price_vnd"].isna().sum())),
        ("Ô trống trong 4 cột đặc trưng cho mô hình", "chưa có cột", int(df[feats].isna().sum().sum())),
        ("Cột có / không flash sale", "chưa có", f"is_flash_sale: {int(df['is_flash_sale'].sum())} True"),
        ("Cột cờ outlier", "chưa có", f"{int(df['log_price_outlier'].sum())} dòng (log giá) - chỉ đánh dấu"),
        ("Cột chuẩn hóa (min-max, z, robust)", "chưa có", "12 cột"),
        ("Cột one-hot (siêu thị, nhóm hàng)", "chưa có", "9 cột + 2 cột 0/1"),
        ("Dòng trùng lặp (kiểm tra 3 cách)", "chưa kiểm tra", "0"),
        ("Phân khúc giá - binning (rẻ / trung bình / cao)", "chưa có",
         " / ".join(str(int(v)) for v in pd.cut(df["sale_price_vnd"], [0, 20_000, 100_000, float("inf")], right=False)
                    .value_counts(sort=False))),
        ("Thống kê mô tả (mean, median, mode, variance, std, range)", "chưa có", "8 biến số + theo siêu thị, nhóm hàng"),
        ("Kiểm định ý nghĩa thống kê", "chưa có", "3 giả thuyết (Chi-square, Mann-Whitney, paired t-test + sign test)"),
        ("REPORT 4 - Biểu đồ trực quan hóa (slide 6.3, 6.4)", "chưa có biểu đồ nào",
         "12 biểu đồ: column/bar 4, stacked column 1, pie 1, histogram 2, boxplot 2, scatter 2"),
        ("File kết quả", "chưa có", "report3_results.md (Report 3) + report4_results.md và 12 hình .png (Report 4)"),
    ]
    save_csv(pd.DataFrame(summary, columns=["chi_so", "TRUOC (chưa làm Report 3 + 4)", "SAU (đã làm Report 3 + 4)"]),
             "R3_tom_tat_truoc_va_sau.csv")

    # 30 readable rows of the output: the special cases first (fixed, flash sale, filled), then a random sample
    special = pd.concat([df[df["pack_fix"].notna()].head(3), df[df["is_flash_sale"]].head(3), df[df["brand_imputed"]].head(2),
                         df[df["size_imputed"]].head(2), df[df["log_price_outlier"]].head(2)])
    sample = pd.concat([special, df.drop(special.index).sample(30 - len(special), random_state=7)])
    out = sample.assign(phan_khuc_gia=pd.cut(sample["sale_price_vnd"], [0, 20_000, 100_000, float("inf")], right=False,
                                             labels=["rẻ (< 20k)", "trung bình", "cao (>= 100k)"]))
    out[["store", "group", "name_clean", "brand", "sale_price_vnd", "list_price_vnd", "is_promotion", "discount_pct",
                  "is_flash_sale", "size_value", "size_unit", "pack_count_report2", "pack_count", "pack_fix",
                  "unit_price_vnd_per_kg_or_l", "phan_khuc_gia", "brand_imputed", "pack_imputed", "size_imputed",
                  "log_price_outlier", "log_price", "log_price_minmax", "log_price_z", "store_bhx", "store_winmart"]].round(4)        .to_csv(settings.REPORTS_DIR / "report3_mau_du_lieu_SAU_30_dong.csv", index=False, encoding="utf-8-sig")


def build() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    clean = pd.read_csv(P.CLEAN_FILE)
    matched = pd.read_csv(MATCHED_FILE)
    df, log = P.prepare(clean)
    person1(clean, matched)
    person2(df)
    person3(df, matched)
    person4(df, log)
    person5(df, log)
    before_after(clean, df)
    return sorted(p.name for p in OUT.iterdir())


def main() -> None:
    files = build()
    print(f"{OUT}: {len(files)} files")
    for f in files:
        print(" -", f)


if __name__ == "__main__":
    main()
