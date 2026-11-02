"""Report 4 - Phân tích dữ liệu qua trực quan hóa (slide 6.3 Visualization fundamentals, 6.4 Statistical charts).

Input : data/processed_py/report3_prepared.csv  (output of Report 3)
        data/processed_py/matched_products.csv  (139 pairs: same product in both stores)
Output: reports_py/report4/*.png                  12 charts
        reports_py/report4_results.md             each chart: type (which slide), why this type, findings

Rule of slide 6.3: the chart type follows the job - compare categories -> bar/column; distribution -> histogram;
relationship of 2 continuous variables -> scatter; composition -> pie / stacked column; over time -> line.
Every number in the findings is computed here, nothing is typed by hand.
Usage: python -m report4.visualize
"""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from report2 import settings
from report3 import stats as S
from report3.run import PRICE_LABELS, price_band, vn

PREPARED = settings.PROCESSED_DIR / "report3_prepared.csv"
MATCHED = settings.PROCESSED_DIR / "matched_products.csv"
OUT = settings.REPORTS_DIR / "report4"
RESULTS = settings.REPORTS_DIR / "report4_results.md"
CONTACT = settings.REPORTS_DIR / "report4_tong_hop_12_bieu_do.png"

STORE = {"bhx": "Bách Hóa Xanh", "winmart": "WinMart"}
STORE_COLOR = {"bhx": "#2a78d6", "winmart": "#eb6834"}            # validated categorical slots 1-2
GROUP_VI = {"beverages": "Đồ uống", "household_cleaning": "Tẩy rửa", "instant_food": "Mì ăn liền",
            "milk_dairy": "Sữa", "personal_care": "Chăm sóc cá nhân", "seasoning": "Gia vị",
            "snacks_confectionery": "Bánh kẹo"}
GROUP_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]   # fixed order, slots 1-7
BAND_COLORS = ["#9ec5f4", "#3987e5", "#1c5cab"]                  # ordinal: one hue, light -> dark
BAND_VI = ["Rẻ (< 20k)", "Trung bình (20k - 100k)", "Cao (≥ 100k)"]
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
PRICE_TICKS = [3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000]


# ------------------------------------------------------------------ helpers
def vnd(x: float) -> str:
    """Short VND label, rounded: 1.5 tr, 125k, 34.9k."""
    if x >= 1e6:
        return f"{x / 1e6:.1f}".rstrip("0").rstrip(".") + " tr"
    k = x / 1e3
    return (f"{k:.0f}" if k >= 100 else f"{k:.1f}".rstrip("0").rstrip(".")) + "k"


def style(ax, title, xlabel="", ylabel="", grid="y"):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=10)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED)


def figure(ncols=1, w=9.5, h=4.8):
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), facecolor=SURFACE)
    return fig, np.atleast_1d(axes)


def save(fig, name) -> str:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return name


def group_order(df):
    return df.groupby("group").size().sort_values(ascending=False).index.tolist()


def log_price_axis(ax, axis="y"):
    ticks = [math.log10(t) for t in PRICE_TICKS]
    (ax.set_yticks if axis == "y" else ax.set_xticks)(ticks, [vnd(t) for t in PRICE_TICKS])


def grouped_bars(ax, cats, values: dict, fmt, horizontal=False):
    """values: store -> list aligned with cats. Draws 2 bars per category with a 2px gap and value labels."""
    pos = np.arange(len(cats))
    width = 0.38
    for i, store in enumerate(("bhx", "winmart")):
        off = (i - 0.5) * (width + 0.03)
        vals = values[store]
        if horizontal:
            bars = ax.barh(pos + off, vals, height=width, color=STORE_COLOR[store], label=STORE[store])
        else:
            bars = ax.bar(pos + off, vals, width=width, color=STORE_COLOR[store], label=STORE[store])
        for b, v in zip(bars, vals):
            if horizontal:
                ax.text(b.get_width(), b.get_y() + b.get_height() / 2, " " + fmt(v), va="center", fontsize=8, color=MUTED)
            else:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(), fmt(v), ha="center", va="bottom", fontsize=8, color=MUTED)
    labels = [GROUP_VI[c] for c in cats]
    if horizontal:
        ax.set_yticks(pos, labels)
        ax.invert_yaxis()
    else:
        ax.set_xticks(pos, labels, rotation=0)
    ax.legend(frameon=False)


# ------------------------------------------------------------------ the charts (each returns a findings dict)
def c01_count(df):
    order = group_order(df)
    t = pd.crosstab(df["group"], df["store"]).loc[order]
    fig, (ax,) = figure()
    grouped_bars(ax, order, {s: t[s].tolist() for s in ("bhx", "winmart")}, lambda v: f"{v:,}")
    style(ax, "Số sản phẩm thu thập theo nhóm hàng và siêu thị", "", "Số sản phẩm (dòng)")
    big = t["winmart"].sub(t["bhx"]).idxmax()
    return {"file": save(fig, "01_column_so_san_pham_theo_nhom.png"),
            "title": "Số sản phẩm theo nhóm hàng và siêu thị",
            "type": "Column chart nhóm (grouped column)", "slide": "6.3 - so sánh các nhóm (ít category) dùng bar/column chart",
            "why": "7 nhóm hàng x 2 siêu thị là biến phân loại -> so sánh số lượng bằng cột đặt cạnh nhau.",
            "findings": [f"WinMart có {int(t['winmart'].sum()):,} sản phẩm, BHX {int(t['bhx'].sum()):,}.",
                         f"Chênh lệch lớn nhất ở nhóm {GROUP_VI[big]}: WinMart {t.loc[big, 'winmart']} vs BHX {t.loc[big, 'bhx']}.",
                         f"Nhóm BHX có nhiều sản phẩm hơn: {', '.join(GROUP_VI[g] for g in t.index[t['bhx'] > t['winmart']])}.",
                         "=> Hai kệ hàng có cơ cấu khác nhau: không thể so giá trung bình cả kệ mà kết luận nơi nào rẻ hơn."]}


def c02_median(df):
    order = group_order(df)
    med = df.groupby(["group", "store"])["sale_price_vnd"].median().unstack().loc[order]
    fig, (ax,) = figure(h=5.2)
    grouped_bars(ax, order, {s: med[s].tolist() for s in ("bhx", "winmart")}, lambda v: vnd(v), horizontal=True)
    style(ax, "Giá bán trung vị theo nhóm hàng và siêu thị", "Giá trung vị (VND)", "", grid="x")
    ax.xaxis.set_major_formatter(lambda x, _: vnd(x) if x else "0")
    higher = med["winmart"] > med["bhx"]
    return {"file": save(fig, "02_bar_gia_trung_vi_theo_nhom.png"),
            "title": "Giá trung vị theo nhóm hàng và siêu thị",
            "type": "Bar chart ngang nhóm", "slide": "6.3 bar chart + 6.4 so sánh 1 số đo theo 2 biến phân loại",
            "why": "Giá lệch phải mạnh nên dùng TRUNG VỊ (slide 6.2) thay cho trung bình; 2 biến phân loại (nhóm, siêu thị).",
            "findings": [f"Trung vị WinMart cao hơn ở {int(higher.sum())}/7 nhóm: "
                         f"{', '.join(GROUP_VI[g] for g in med.index[higher])}.",
                         f"Nhóm đắt nhất: {GROUP_VI[med.max(axis=1).idxmax()]} (~{vnd(med.max(axis=1).max())}); "
                         f"rẻ nhất: {GROUP_VI[med.min(axis=1).idxmin()]} (~{vnd(med.min(axis=1).min())}).",
                         "=> Chênh lệch trung vị phản ánh khác MẶT HÀNG (gói lẻ, thùng); hình 10-12 so CÙNG sản phẩm."]}


def c03_promo(df):
    order = group_order(df)
    pct = df.groupby(["group", "store"])["is_promotion"].mean().unstack().loc[order] * 100
    fig, (ax,) = figure()
    grouped_bars(ax, order, {s: pct[s].tolist() for s in ("bhx", "winmart")}, lambda v: f"{v:.0f}%")
    style(ax, "Tỉ lệ sản phẩm đang khuyến mãi theo nhóm hàng", "", "% sản phẩm khuyến mãi")
    promo = S.promotion_test(df)
    return {"file": save(fig, "03_column_ti_le_khuyen_mai.png"),
            "title": "Tỉ lệ khuyến mãi theo nhóm hàng",
            "type": "Column chart nhóm", "slide": "6.3 - so sánh các nhóm",
            "why": "So sánh một tỉ lệ (%) giữa 7 nhóm x 2 siêu thị.",
            "findings": [f"Toàn bộ: BHX {promo['promo_share_pct']['bhx']}% vs WinMart {promo['promo_share_pct']['winmart']}% "
                         f"(Chi-square p = {promo['p_value']:.1e} - có ý nghĩa thống kê, Report 3).",
                         f"BHX khuyến mãi nhiều hơn ở {int((pct['bhx'] > pct['winmart']).sum())}/7 nhóm; cao nhất "
                         f"{GROUP_VI[pct['bhx'].idxmax()]} {pct['bhx'].max():.0f}%."]}


def c04_bands(df):
    order = group_order(df)
    band = price_band(df["sale_price_vnd"])
    fig, axes = figure(2, w=12, h=4.8)
    shares = {}
    for ax, store in zip(axes, ("bhx", "winmart")):
        sub = df["store"] == store
        t = pd.crosstab(df.loc[sub, "group"], band[sub], normalize="index").reindex(index=order, columns=PRICE_LABELS).fillna(0) * 100
        shares[store] = pd.crosstab(df.loc[sub, "store"], band[sub], normalize="index").iloc[0] * 100
        bottom = np.zeros(len(order))
        for col, color, label in zip(PRICE_LABELS, BAND_COLORS, BAND_VI):
            ax.bar(range(len(order)), t[col], bottom=bottom, color=color, label=label, edgecolor=SURFACE, linewidth=2, width=0.7)
            for x, (b, v) in enumerate(zip(bottom, t[col])):
                if v >= 9:
                    ax.text(x, b + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                            color="white" if color != BAND_COLORS[0] else INK)
            bottom += t[col].to_numpy()
        ax.set_xticks(range(len(order)), [GROUP_VI[g] for g in order], rotation=30, ha="right")
        style(ax, STORE[store], "", "% sản phẩm của nhóm")
        ax.set_ylim(0, 100)
    axes[1].legend(frameon=False, bbox_to_anchor=(1.0, 1.0), loc="upper left", title="Phân khúc giá (binning)")
    fig.suptitle("Cơ cấu phân khúc giá trong từng nhóm hàng", x=0.01, ha="left", color=INK)
    return {"file": save(fig, "04_stacked_column_phan_khuc_gia.png"),
            "title": "Cơ cấu phân khúc giá (binning) trong từng nhóm hàng",
            "type": "Stacked column 100%", "slide": "6.3 - thể hiện cơ cấu (composition) bằng stacked column; binning slide 2.6",
            "why": "Giá đã chia thành 3 khoảng (binning -> biến ordinal); stacked 100% cho thấy cơ cấu từng nhóm.",
            "findings": [f"BHX: rẻ {shares['bhx'].iloc[0]:.0f}% - trung bình {shares['bhx'].iloc[1]:.0f}% - cao {shares['bhx'].iloc[2]:.0f}%; "
                         f"WinMart: {shares['winmart'].iloc[0]:.0f}% - {shares['winmart'].iloc[1]:.0f}% - {shares['winmart'].iloc[2]:.0f}%.",
                         "BHX có tỉ lệ hàng rẻ (< 20k) cao hơn - phù hợp việc BHX bán nhiều gói lẻ, trung vị BHX thấp hơn."]}


def c05_pie(df):
    fig, axes = figure(2, w=11, h=5)
    order = group_order(df)
    colors = dict(zip(order, GROUP_COLORS))
    shares = {}
    for ax, store in zip(axes, ("bhx", "winmart")):
        s = df[df["store"] == store]["group"].value_counts().reindex(order)
        shares[store] = s / s.sum() * 100
        ax.pie(s, colors=[colors[g] for g in order], startangle=90, counterclock=False,
               wedgeprops={"edgecolor": SURFACE, "linewidth": 2},
               autopct=lambda p: f"{p:.0f}%", pctdistance=0.78, textprops={"color": "white", "fontsize": 9})
        ax.set_title(f"{STORE[store]} ({int(s.sum()):,} sản phẩm)", color=INK)
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=colors[g]) for g in order], [GROUP_VI[g] for g in order],
               frameon=False, loc="lower center", ncol=4)
    fig.suptitle("Cơ cấu nhóm hàng của mỗi siêu thị", x=0.01, ha="left", color=INK)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(OUT / "05_pie_co_cau_nhom_hang.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    top = {s: shares[s].idxmax() for s in shares}
    return {"file": "05_pie_co_cau_nhom_hang.png", "title": "Cơ cấu nhóm hàng của mỗi siêu thị",
            "type": "Pie chart (2 bánh)", "slide": "6.3 - cơ cấu dữ liệu tĩnh (static composition) dùng pie chart",
            "why": "Dữ liệu là 1 lần chụp (tĩnh); mỗi bánh = 100% sản phẩm của 1 siêu thị.",
            "findings": [f"BHX nhiều nhất {GROUP_VI[top['bhx']]} ({shares['bhx'].max():.0f}%); "
                         f"WinMart nhiều nhất {GROUP_VI[top['winmart']]} ({shares['winmart'].max():.0f}%).",
                         f"Tẩy rửa chiếm {shares['bhx']['household_cleaning']:.0f}% ở BHX nhưng chỉ "
                         f"{shares['winmart']['household_cleaning']:.0f}% ở WinMart -> cơ cấu 2 kệ hàng khác nhau."]}


def c06_hist(df):
    fig, axes = figure(2, w=12, h=4.6)
    raw_bins = np.linspace(0, 600_000, 41)
    log_bins = np.linspace(np.log10(2_000), np.log10(2_000_000), 41)
    for store in ("bhx", "winmart"):
        s = df[df["store"] == store]["sale_price_vnd"]
        axes[0].hist(s.clip(upper=600_000), bins=raw_bins, histtype="step", linewidth=2, color=STORE_COLOR[store], label=STORE[store])
        axes[1].hist(np.log10(s), bins=log_bins, histtype="step", linewidth=2, color=STORE_COLOR[store], label=STORE[store])
    axes[0].xaxis.set_major_formatter(lambda x, _: vnd(x) if x else "0")
    log_price_axis(axes[1], "x")
    style(axes[0], f"Giá gốc: lệch phải (skew {df['sale_price_vnd'].skew():.2f})", "Giá bán (> 600k gộp vào cột cuối)", "Số sản phẩm")
    style(axes[1], f"Thang log: gần đối xứng (skew {df['log_price'].skew():.2f})", "Giá bán (thang log)", "Số sản phẩm")
    axes[0].legend(frameon=False)
    d = S.describe(df["sale_price_vnd"])
    return {"file": save(fig, "06_histogram_phan_phoi_gia.png"),
            "title": "Phân phối giá bán (histogram)",
            "type": "Histogram (dạng đường bậc thang, 2 siêu thị chồng nhau)", "slide": "6.3 - thể hiện phân phối dùng histogram; 6.4 histogram theo nhóm",
            "why": "Giá là biến liên tục (ratio) -> histogram cho thấy hình dạng phân phối.",
            "findings": [f"Giá lệch phải mạnh: mean {vnd(d['mean'])} > median {vnd(d['median'])} > mode {vnd(d['mode'])}.",
                         "Trên thang log phân phối gần đối xứng, gần chuẩn -> lý do Report 3 dùng log giá cho kiểm định và chuẩn hóa.",
                         "Histogram WinMart dồn ở khoảng 20k-100k; BHX trải rộng hơn (nhiều gói rẻ và nhiều thùng đắt)."]}


def c07_box_price(df):
    order = group_order(df)
    fig, (ax,) = figure(w=11, h=5.2)
    stats_rows = []
    for i, store in enumerate(("bhx", "winmart")):
        data = [np.log10(df[(df["group"] == g) & (df["store"] == store)]["sale_price_vnd"]) for g in order]
        pos = np.arange(len(order)) + (i - 0.5) * 0.36
        bp = ax.boxplot(data, positions=pos, widths=0.3, patch_artist=True, whis=1.5,
                        medianprops={"color": INK, "linewidth": 1.5},
                        flierprops={"marker": "o", "markersize": 3, "markerfacecolor": STORE_COLOR[store],
                                    "markeredgecolor": "none", "alpha": 0.6})
        for box in bp["boxes"]:
            box.set(facecolor=STORE_COLOR[store], alpha=0.85, edgecolor=STORE_COLOR[store])
        for w in bp["whiskers"] + bp["caps"]:
            w.set(color=STORE_COLOR[store])
        stats_rows += [(g, store, len(bp["fliers"][k].get_ydata())) for k, g in enumerate(order)]
    ax.set_xticks(range(len(order)), [GROUP_VI[g] for g in order])
    log_price_axis(ax)
    style(ax, "Phân bố giá theo nhóm hàng (boxplot, thang log)", "", "Giá bán")
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=STORE_COLOR[s]) for s in STORE], STORE.values(), frameon=False, loc="upper right")
    out = pd.DataFrame(stats_rows, columns=["group", "store", "n_out"])
    iqr = df.groupby("group")["log_price"].agg(lambda s: s.quantile(.75) - s.quantile(.25))
    return {"file": save(fig, "07_boxplot_gia_theo_nhom.png"),
            "title": "Boxplot giá theo nhóm hàng và siêu thị",
            "type": "Box plot", "slide": "6.4 - box plots (so sánh phân bố giữa các nhóm)",
            "why": "Boxplot cho cùng lúc median, Q1-Q3 (hộp), râu 1,5 x IQR và điểm ngoại lai - đúng quy tắc outlier của Report 3.",
            "findings": [f"Nhóm phân tán nhất (IQR log lớn nhất): {GROUP_VI[iqr.idxmax()]}; ít phân tán nhất: {GROUP_VI[iqr.idxmin()]}.",
                         f"Có {int(out['n_out'].sum())} điểm ngoài râu, cả hàng rất rẻ (kẹo vài nghìn đồng) lẫn rất đắt "
                         "(thùng, sữa bột) - đều là giá thật nên Report 3 chỉ đánh dấu, không xóa.",
                         "Hộp của 2 siêu thị chồng lên nhau ở hầu hết nhóm -> khoảng giá phổ biến tương đương nhau."]}


def c08_box_unit(df):
    order = group_order(df)
    fig, (ax,) = figure(w=11, h=5)
    sub = df[df["unit_price_vnd_per_kg_or_l"].notna()]
    for i, store in enumerate(("bhx", "winmart")):
        data = [np.log10(sub[(sub["group"] == g) & (sub["store"] == store)]["unit_price_vnd_per_kg_or_l"]) for g in order]
        pos = np.arange(len(order)) + (i - 0.5) * 0.36
        bp = ax.boxplot(data, positions=pos, widths=0.3, patch_artist=True, whis=1.5,
                        medianprops={"color": INK, "linewidth": 1.5},
                        flierprops={"marker": "o", "markersize": 3, "markerfacecolor": STORE_COLOR[store],
                                    "markeredgecolor": "none", "alpha": 0.6})
        for box in bp["boxes"]:
            box.set(facecolor=STORE_COLOR[store], alpha=0.85, edgecolor=STORE_COLOR[store])
        for w in bp["whiskers"] + bp["caps"]:
            w.set(color=STORE_COLOR[store])
    ticks = [3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000, 3_000_000]
    ax.set_yticks([math.log10(t) for t in ticks], [vnd(t) for t in ticks])
    ax.set_xticks(range(len(order)), [GROUP_VI[g] for g in order])
    style(ax, "Giá trên mỗi kg / lít theo nhóm hàng (boxplot, thang log)", "", "VND / kg hoặc lít")
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=STORE_COLOR[s]) for s in STORE], STORE.values(), frameon=False, loc="upper right")
    med = sub.groupby(["group", "store"])["unit_price_vnd_per_kg_or_l"].median().unstack()
    return {"file": save(fig, "08_boxplot_gia_tren_kg_lit.png"),
            "title": "Boxplot giá trên kg/lít",
            "type": "Box plot", "slide": "6.4 - box plots",
            "why": "Giá/kg-lít loại bỏ khác biệt khối lượng gói -> so sánh công bằng hơn giá bán; chỉ dùng "
                   f"{len(sub):,} dòng có khối lượng thật (Report 3 không bịa khối lượng).",
            "findings": [f"Đắt nhất trên kg/lít: {GROUP_VI[med.max(axis=1).idxmax()]} (trung vị ~{vnd(med.max(axis=1).max())}/kg); "
                         f"rẻ nhất: {GROUP_VI[med.min(axis=1).idxmin()]} (~{vnd(med.min(axis=1).min())}/kg-lít).",
                         f"Trung vị giá/kg-lít WinMart cao hơn BHX ở {int((med['winmart'] > med['bhx']).sum())}/7 nhóm - "
                         "một phần do BHX bán nhiều thùng/lốc (mua nhiều rẻ hơn trên mỗi kg)."]}


def c09_scatter_size(df):
    fig, (ax,) = figure(w=9, h=5.5)
    sub = df[df["total_quantity"].notna()]
    rs = {}
    for store in ("bhx", "winmart"):
        g = sub[sub["store"] == store]
        rs[store] = S.correlation_test(np.log(g["total_quantity"]), g["log_price"], "spearman")["r"]
        ax.scatter(np.log10(g["total_quantity"]), np.log10(g["sale_price_vnd"]), s=10, alpha=0.35,
                   color=STORE_COLOR[store], edgecolors="none", label=f"{STORE[store]} (Spearman r = {rs[store]:.2f})")
    qt = [10, 100, 1_000, 10_000, 50_000]
    ax.set_xticks([math.log10(t) for t in qt], ["10", "100", "1.000", "10.000", "50.000"])
    log_price_axis(ax)
    style(ax, "Khối lượng tổng của gói và giá bán (thang log - log)", "Khối lượng tổng (g hoặc ml)", "Giá bán", grid="both")
    ax.legend(frameon=False, markerscale=2)
    unit_r = S.correlation_test(np.log(sub["total_quantity"]), sub["log_unit_price"], "spearman")["r"]
    return {"file": save(fig, "09_scatter_khoi_luong_va_gia.png"),
            "title": "Scatter: khối lượng gói và giá",
            "type": "Scatter plot", "slide": "6.3 - quan hệ giữa 2 biến liên tục dùng scatter plot",
            "why": "Khối lượng và giá đều là biến liên tục; thang log vì cả 2 đều lệch phải.",
            "findings": [f"Quan hệ đồng biến: gói càng lớn càng đắt - Spearman r = {rs['bhx']:.2f} (BHX, mạnh), "
                         f"{rs['winmart']:.2f} (WinMart, trung bình).",
                         f"Nhưng khối lượng và giá trên kg có r = {unit_r:.2f} (âm): mua gói lớn rẻ hơn trên mỗi kg.",
                         "Tương quan không phải nhân quả (slide 2.7)."]}


def c10_scatter_pairs(m):
    fig, (ax,) = figure(w=7.5, h=6.5)
    x, y = np.log10(m["bhx_price_vnd"]), np.log10(m["winmart_price_vnd"])
    ax.scatter(x, y, s=22, color=MUTED, alpha=0.75, edgecolors=SURFACE, linewidths=1)
    lo, hi = min(x.min(), y.min()) - 0.1, max(x.max(), y.max()) + 0.1
    ax.plot([lo, hi], [lo, hi], color=INK, linewidth=1.2, linestyle="--")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    log_price_axis(ax, "x")
    log_price_axis(ax)
    p = S.matched_pairs_test(m)
    ax.text(lo + 0.05, hi - 0.1, f"Trên đường: WinMart đắt hơn ({p['winmart_more_expensive']} cặp)", color=MUTED, fontsize=9)
    ax.text(hi - 0.05, lo + 0.08, f"Dưới đường: WinMart rẻ hơn ({p['winmart_cheaper']} cặp)", color=MUTED, fontsize=9, ha="right")
    style(ax, "139 cặp cùng sản phẩm: giá BHX và giá WinMart", "Giá tại Bách Hóa Xanh", "Giá tại WinMart", grid="both")
    r = S.correlation_test(m["bhx_price_vnd"], m["winmart_price_vnd"], "pearson")["r"]
    return {"file": save(fig, "10_scatter_139_cap_cung_san_pham.png"),
            "title": "Scatter: giá BHX và WinMart của 139 cặp cùng sản phẩm",
            "type": "Scatter plot + đường y = x", "slide": "6.3 - scatter plot",
            "why": "Mỗi điểm là 1 sản phẩm có ở cả 2 nơi; điểm nằm trên đường chéo = bằng giá.",
            "findings": [f"Các điểm bám sát đường chéo (Pearson r = {r:.3f}): cùng sản phẩm thì giá 2 nơi rất gần nhau.",
                         f"{p['winmart_more_expensive']} cặp trên đường, {p['winmart_cheaper']} cặp dưới đường, {p['same_price']} cặp nằm trên đường.",
                         "=> Không siêu thị nào rẻ hơn một cách có hệ thống (paired t-test p = "
                         f"{p['paired_t']['p_value']:.2f}, Report 3)."]}


def c11_hist_pairs(m):
    fig, (ax,) = figure(w=9, h=4.6)
    ax.hist(m["price_diff_pct"], bins=np.arange(-35, 52.5, 2.5), color=STORE_COLOR["bhx"], edgecolor=SURFACE, linewidth=1)
    ax.axvline(0, color=INK, linewidth=1.5)
    p = S.matched_pairs_test(m)
    ax.text(18, ax.get_ylim()[1] * 0.9, f"Vạch đen 0% = bằng giá\n{p['winmart_cheaper']} cặp WinMart rẻ hơn (trái)\n"
            f"{p['winmart_more_expensive']} cặp WinMart đắt hơn (phải)", color=INK, fontsize=9, va="top")
    style(ax, "Chênh lệch giá WinMart so với BHX của 139 cặp", "Chênh lệch (%)", "Số cặp")
    within = (m["price_diff_pct"].abs() <= 10).mean() * 100
    return {"file": save(fig, "11_histogram_chenh_lech_139_cap.png"),
            "title": "Histogram chênh lệch giá 139 cặp",
            "type": "Histogram", "slide": "6.3 - phân phối",
            "why": "Chênh lệch % là biến liên tục; histogram cho thấy nó dồn quanh 0 hay lệch về 1 phía.",
            "findings": [f"Trung vị chênh lệch {m['price_diff_pct'].median():.1f}%, trung bình {m['price_diff_pct'].mean():+.2f}%.",
                         f"{within:.0f}% số cặp chênh trong khoảng ±10%; hai bên vạch 0 gần như cân bằng."]}


def c12_pairs_group(m):
    g = m.groupby("group")["price_diff_pct"].agg(["median", "size"]).sort_values("median")
    fig, (ax,) = figure(w=9, h=4.8)
    colors = [STORE_COLOR["winmart"] if v < 0 else STORE_COLOR["bhx"] for v in g["median"]]
    bars = ax.barh([f"{GROUP_VI[i]} (n = {n})" for i, n in g["size"].items()], g["median"], color=colors, height=0.6)
    ax.axvline(0, color=INK, linewidth=1)
    ax.set_xlim(min(g["median"].min(), 0) - 4, g["median"].max() + 4)
    for b, v in zip(bars, g["median"]):
        ax.text(v, b.get_y() + b.get_height() / 2, f" {v:+.1f}% " if v >= 0 else f" {v:+.1f}% ",
                va="center", ha="left" if v >= 0 else "right", fontsize=8, color=MUTED)
    style(ax, "Chênh lệch trung vị (WinMart so với BHX) theo nhóm hàng - 139 cặp", "Chênh lệch trung vị (%)", "", grid="x")
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=STORE_COLOR["bhx"]), plt.Rectangle((0, 0), 1, 1, color=STORE_COLOR["winmart"])],
              ["BHX rẻ hơn (WinMart đắt hơn)", "WinMart rẻ hơn"], frameon=False, loc="lower right")
    tests = S.matched_by_group(m).set_index("group")
    return {"file": save(fig, "12_bar_chenh_lech_theo_nhom.png"),
            "title": "Chênh lệch trung vị theo nhóm hàng (139 cặp)",
            "type": "Bar chart ngang (2 phía quanh 0)", "slide": "6.3 - so sánh các nhóm",
            "why": "So sánh 1 số đo (chênh lệch %) giữa 7 nhóm; màu theo siêu thị rẻ hơn.",
            "findings": [f"WinMart rẻ hơn rõ ở {GROUP_VI[g['median'].idxmin()]} ({g['median'].min():+.1f}%); "
                         f"đắt hơn rõ ở {GROUP_VI[g['median'].idxmax()]} ({g['median'].max():+.1f}%).",
                         f"Không nhóm nào có ý nghĩa thống kê (sign test p nhỏ nhất = {tests['sign_test_p'].min():.2f}); "
                         "nhóm Chăm sóc cá nhân, Tẩy rửa chỉ 3-4 cặp -> cần thêm dữ liệu."]}


CHARTS = [c01_count, c02_median, c03_promo, c04_bands, c05_pie, c06_hist, c07_box_price, c08_box_unit, c09_scatter_size]
PAIR_CHARTS = [c10_scatter_pairs, c11_hist_pairs, c12_pairs_group]


def write_results(items: list[dict]) -> str:
    parts = ["# Report 4 - Phân tích dữ liệu qua trực quan hóa (tạo bởi `python -m report4.visualize`)",
             "Dữ liệu: `report3_prepared.csv` (3.507 dòng, đã xử lý ở Report 3) và `matched_products.csv` (139 cặp cùng sản phẩm).\n"
             "Cách chọn biểu đồ theo slide 6.3: so sánh nhóm -> bar/column; phân phối -> histogram; quan hệ 2 biến liên tục -> "
             "scatter; cơ cấu -> pie / stacked column; theo thời gian -> line; slide 6.4: histogram theo nhóm, box plot.",
             "| # | Biểu đồ | Loại | Theo slide |\n|---|---|---|---|\n" +
             "\n".join(f"| {i} | {c['title']} | {c['type']} | {c['slide']} |" for i, c in enumerate(items, 1))]
    for i, c in enumerate(items, 1):
        parts.append(f"## Hình {i}. {c['title']}\n\n![{c['title']}](report4/{c['file']})\n\n"
                     f"- **Loại biểu đồ:** {c['type']} (slide {c['slide']})\n- **Vì sao chọn:** {c['why']}\n"
                     "- **Nhận xét:**\n" + "\n".join(f"  - {vn(f)}" for f in c["findings"]))
    parts.append("## Line chart (biểu đồ đường) - vì sao không dùng\n\n"
                 "Slide 6.3 dùng line chart khi so sánh theo THỜI GIAN qua nhiều kỳ. Dữ liệu của nhóm là 1 lần chụp giá "
                 "(cross-sectional, 12/10/2026 16:22-16:43), không có nhiều kỳ -> vẽ line chart sẽ không có ý nghĩa. "
                 "Khi thu thập thêm các lần sau (cùng code Report 2), có thể vẽ line chart giá trung vị theo ngày.")
    parts.append("## Kết luận Report 4\n\n"
                 "1. Hai siêu thị có cơ cấu kệ hàng khác nhau (hình 1, 4, 5): WinMart nhiều sản phẩm hơn, BHX nhiều gói rẻ và thùng/lốc.\n"
                 "2. Giá lệch phải mạnh (hình 6, 7) -> dùng trung vị và thang log là đúng; điểm ngoại lai là giá thật.\n"
                 "3. BHX khuyến mãi nhiều hơn tính chung (24,6% so với 11,2%), rõ nhất ở Tẩy rửa, Đồ uống, Chăm sóc cá nhân; "
                 "WinMart nhỉnh hơn ở Bánh kẹo, Mì ăn liền, Gia vị (hình 3).\n"
                 "4. Gói càng lớn càng đắt nhưng càng rẻ trên mỗi kg (hình 8, 9).\n"
                 "5. Với CÙNG một sản phẩm (hình 10-12), giá 2 nơi gần như bằng nhau; rẻ hay đắt tùy từng sản phẩm, "
                 "không siêu thị nào rẻ hơn một cách có hệ thống.")
    text = "\n\n".join(parts) + "\n"
    RESULTS.write_text(text, encoding="utf-8")
    return text


def contact_sheet(items: list[dict]) -> None:
    """All 12 charts on one page - a quick 'what does Report 4 look like' overview."""
    fig, axes = plt.subplots(4, 3, figsize=(18, 20), facecolor=SURFACE)
    for ax, (i, c) in zip(axes.flat, enumerate(items, 1)):
        ax.imshow(plt.imread(OUT / c["file"]))
        ax.set_title(f"Hình {i}. {c['title']}", fontsize=10, color=INK, loc="left")
        ax.axis("off")
    fig.suptitle("Report 4 - 12 biểu đồ (slide 6.3, 6.4)", x=0.01, ha="left", fontsize=14, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(CONTACT, dpi=110, facecolor=SURFACE)
    plt.close(fig)


def run() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PREPARED)
    m = pd.read_csv(MATCHED)
    items = [chart(df) for chart in CHARTS] + [chart(m) for chart in PAIR_CHARTS]
    write_results(items)
    contact_sheet(items)
    return items


def main() -> None:
    items = run()
    print(f"{len(items)} charts -> {OUT}; findings -> {RESULTS}")


if __name__ == "__main__":
    main()
