"""Report 3 (EDA) - chạy 3 phần và ghi kết quả ra reports_py/report3_results.md (tiếng Việt).

  1. Tìm hiểu dữ liệu đã thu thập   (slide 6.1: loại dữ liệu, loại biến; slide 2.3 data understanding)
  2. Các ý nghĩa thống kê           (slide 6.2: mean, median, mode, variance, std, range + tương quan + kiểm định)
  3. Xử lý dữ liệu                  (slide 2.3 / 2.6: trùng lặp, sửa lỗi, missing value, outlier, normalize,
                                     binning, dummy) -> data/processed_py/report3_prepared.csv

Chạy: python -m report3.run
"""
import re

import pandas as pd

from report2 import settings
from report3 import preprocess as P
from report3 import stats as S

RESULTS_FILE = settings.REPORTS_DIR / "report3_results.md"
MATCHED_FILE = settings.PROCESSED_DIR / "matched_products.csv"

# Biến chính và loại biến theo slide 6.1 (categorical / ordinal / interval / ratio); các cột khác là cột truy vết
VARIABLES = [
    ("store", "categorical (nominal)", "siêu thị: bhx / winmart"),
    ("group", "categorical (nominal)", "nhóm hàng, 7 giá trị"),
    ("category_slug", "categorical (nominal)", "trang danh mục trên website"),
    ("brand", "categorical (nominal)", "thương hiệu"),
    ("unit_label", "categorical (nominal)", "đơn vị bán: Gói, Chai, Thùng..."),
    ("size_unit", "categorical (nominal)", "g / ml"),
    ("sale_price_vnd", "ratio (số liên tục)", "giá bán (VND) - có số 0 thật, 100k = 2 x 50k"),
    ("list_price_vnd", "ratio (số liên tục)", "giá niêm yết trước giảm giá (VND)"),
    ("discount_pct", "ratio (số liên tục)", "% giảm giá = (niêm yết - bán) / niêm yết x 100"),
    ("size_value", "ratio (số liên tục)", "khối lượng / dung tích 1 món (g hoặc ml)"),
    ("pack_count", "ratio (số rời rạc - đếm)", "số món trong 1 đơn vị bán"),
    ("total_quantity", "ratio (số liên tục)", "khối lượng tổng = size_value x pack_count"),
    ("unit_price_vnd_per_kg_or_l", "ratio (số liên tục, tính ra)", "giá trên 1 kg hoặc 1 lít"),
    ("stock_qty", "ratio (số rời rạc - đếm)", "số lượng tồn kho (chỉ WinMart)"),
    ("is_promotion", "categorical (nhị phân có/không)", "có khuyến mãi (giá niêm yết > giá bán)"),
    ("collected_at", "interval (thời gian, không có số 0 tự nhiên)", "thời điểm thu thập, +07:00"),
    ("product_code", "categorical (mã định danh, không đem tính)", "mã sản phẩm của siêu thị"),
    ("barcode", "categorical (mã định danh, không đem tính)", "mã vạch (chỉ WinMart)"),
]
NUMERIC = ["sale_price_vnd", "list_price_vnd", "discount_pct", "size_value", "pack_count", "total_quantity",
           "unit_price_vnd_per_kg_or_l", "stock_qty"]


def vn(text: str) -> str:
    """Kiểu số Việt Nam trong câu chữ: 2,095 -> 2.095 và 24.6 -> 24,6 (giữ nguyên số slide như 6.3)."""
    text = re.sub(r"(\d),(\d{3})\b", "\\1\u2009\\2", text)
    text = re.sub(r"(?<!slide )(?<!mục )(?<!Mục )(?<![\d.])(\d+)\.(\d+)", r"\1,\2", text)
    return text.replace("\u2009", ".")


def fmt(x, digits=0) -> str:
    if isinstance(x, (int, float)) and pd.notna(x):
        return f"{x:,.{digits}f}".replace(",", "\u2009").replace(".", ",").replace("\u2009", ".")
    return str(x)


def md_table(df: pd.DataFrame, digits: int = 1) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(r[c], digits) if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ phần 1
def part1_understanding(clean: pd.DataFrame, matched: pd.DataFrame) -> str:
    t = pd.to_datetime(clean["collected_at"])
    counts = pd.crosstab(clean["group"], clean["store"], margins=True, margins_name="tổng").reset_index()
    var_rows = pd.DataFrame([{"biến": v, "loại biến (slide 6.1)": k, "ý nghĩa": m,
                              "số giá trị khác nhau": int(clean[v].nunique()),
                              "% thiếu": round(clean[v].isna().mean() * 100, 1)} for v, k, m in VARIABLES])
    levels = pd.DataFrame([
        ("categorical (nominal)", "store, group, brand, unit_label, is_promotion",
         "đếm, tỉ lệ %, mode", "mean, median vô nghĩa (không có thứ tự, không có khoảng cách)"),
        ("ordinal", "phân khúc giá sau binning: rẻ < trung bình < cao (mục 3.5)",
         "thêm median, so sánh thứ tự", "hiệu số, mean vô nghĩa (khoảng cách giữa các bậc không cố định)"),
        ("interval", "collected_at (thời điểm)", "thêm hiệu số (khoảng thời gian), mean",
         "tỉ số vô nghĩa (không có số 0 tự nhiên)"),
        ("ratio", "giá, khối lượng, số lượng trong gói, % giảm giá",
         "tất cả: mean, median, mode, variance, std, range, CV, tỉ số", "-"),
    ], columns=["loại biến", "biến trong bài", "chỉ số dùng được (slide 6.1 / 6.2)", "không dùng được"])
    units = clean["unit_label"].value_counts().head(8)
    body = [
        f"- Nguồn: dữ liệu sạch của Report 2 `clean_observations.csv` ({len(clean):,} dòng x {clean.shape[1]} cột), "
        f"lần thu thập {', '.join(clean['run_id'].unique())}.",
        f"- Thu thập {t.min():%d/%m/%Y %H:%M} -> {t.max():%H:%M} (+07:00): 1 lần chụp giá = **cross-sectional data** "
        "(slide 6.1), không phải time series. Đây là **sample** (7 nhóm hàng, mỗi siêu thị 1 khu vực giá) của "
        "**population** là toàn bộ sản phẩm của 2 chuỗi siêu thị (slide 6.2).",
        f"- 1 dòng = giá của 1 sản phẩm tại 1 siêu thị. BHX {int((clean['store'] == 'bhx').sum()):,} dòng, "
        f"WinMart {int((clean['store'] == 'winmart').sum()):,} dòng; {clean['category_slug'].nunique()} trang danh mục; "
        f"{clean['brand'].nunique()} thương hiệu.",
        f"- Dữ liệu **multivariate** (slide 6.1): mỗi quan sát có {clean.shape[1]} biến. Mục 2.2 đến mục 2.4 phân tích "
        "**univariate** (từng biến một); mục 2.5 và các biểu đồ scatter của Report 4 phân tích 2 biến cùng lúc.",
        f"- Sản phẩm ghép cặp (cùng thương hiệu + khối lượng + số lượng + vị ở cả 2 siêu thị): {len(matched)} cặp.",
    ]
    return "\n\n".join([
        "## 1. Data understanding - Tìm hiểu dữ liệu đã thu thập", *map(vn, body),
        "### Số dòng theo nhóm hàng và siêu thị", md_table(counts),
        "### Biến và loại biến (slide 6.1)", md_table(var_rows),
        "### Loại biến nào dùng chỉ số nào (slide 6.1 / 6.2)", md_table(levels),
        "### Đơn vị bán (8 loại nhiều nhất)", ", ".join(f"{k}: {v}" for k, v in units.items()),
    ])


# ------------------------------------------------------------------ phần 2
def part2_statistics(df: pd.DataFrame, matched: pd.DataFrame) -> str:
    keep = ["n", "mean", "median", "mode", "std", "variance", "cv_pct", "q1", "q3", "iqr", "min", "max", "range", "skew", "kurtosis"]
    all_vars = pd.DataFrame([{"biến": c, **{k: S.describe(df[c])[k] for k in
                                            ("n", "mean", "median", "mode", "std", "variance", "min", "max", "range", "skew")}}
                             for c in NUMERIC])
    price = S.describe_by(df, "sale_price_vnd", ["store"])[["store"] + keep]
    overall = S.describe(df["sale_price_vnd"])
    log_d = S.describe(df["log_price"])
    by_group = S.describe_by(df, "sale_price_vnd", ["group", "store"])[["group", "store", "n", "median", "iqr", "cv_pct"]]
    unit = S.describe_by(df, "unit_price_vnd_per_kg_or_l", ["store"])[["store"] + keep]
    promo = S.promotion_test(df)
    overall_test = S.overall_price_test(df)
    pairs = S.matched_pairs_test(matched)
    pair_groups = S.matched_by_group(matched)
    size_corr = S.size_price_correlation(df)
    corr = S.correlation_matrix(df).round(2).reset_index().rename(columns={"index": ""})
    ci = pairs["geo_mean_ratio_ci95_pct"]
    bhx_r = size_corr[(size_corr.store == "bhx") & (size_corr.method == "spearman")].iloc[0]
    wm_r = size_corr[(size_corr.store == "winmart") & (size_corr.method == "spearman")].iloc[0]
    meanings = pd.DataFrame([
        ("mean", "trung bình = tổng / số quan sát; bị vài sản phẩm rất đắt kéo lên"),
        ("median", "giá trị đứng giữa khi xếp từ nhỏ đến lớn; không bị giá trị cực đoan ảnh hưởng -> giá 'điển hình' khi dữ liệu lệch"),
        ("mode", "giá trị xuất hiện nhiều nhất; dùng được cả cho biến phân loại"),
        ("range", "max - min: độ rộng toàn bộ dữ liệu, rất nhạy với giá trị cực đoan"),
        ("variance", "trung bình bình phương khoảng cách tới mean; đơn vị là VND bình phương nên khó đọc trực tiếp"),
        ("std", "căn bậc hai của variance, cùng đơn vị VND: giá thường cách trung bình bao nhiêu"),
        ("CV%", "std / mean x 100: độ phân tán tương đối, so được giữa các nhóm có mức giá khác nhau"),
        ("Q1, Q3, IQR", "mốc 25% / 75%; IQR = Q3 - Q1 = độ rộng 50% dữ liệu ở giữa, bền với outlier"),
        ("skewness", "độ lệch: > 0 đuôi dài bên phải (ít món rất đắt); skew lớn hơn 1 (hoặc nhỏ hơn -1) là lệch mạnh"),
        ("kurtosis", "pandas tính excess kurtosis (chuẩn = 0); > 3 là nhiều giá trị cực đoan"),
        ("p-value", "nếu thật sự không có khác biệt, xác suất thấy chênh lệch lớn như vậy; p < 0,05 = có ý nghĩa thống kê"),
    ], columns=["chỉ số", "ý nghĩa"])
    tests = [
        f"**H1. Tỉ lệ sản phẩm khuyến mãi của 2 siêu thị có khác nhau không?** Chi-square 2x2: "
        f"chi2 = {promo['chi2']:.1f}, p = {promo['p_value']:.1e} -> {S.verdict_vi(promo['p_value'])}. "
        f"Tỉ lệ khuyến mãi BHX {promo['promo_share_pct']['bhx']}% vs WinMart {promo['promo_share_pct']['winmart']}%; "
        f"mức giảm trung bình khi có khuyến mãi BHX {promo['mean_discount_when_promo']['bhx']}%, "
        f"WinMart {promo['mean_discount_when_promo']['winmart']}%.",
        f"**H2. Giá trên kệ hàng có khác nhau không (mọi sản phẩm, không ghép cặp)?** Mann-Whitney U: "
        f"z = {overall_test['z']:.2f}, p = {overall_test['p_value']:.1e} -> {S.verdict_vi(overall_test['p_value'])}; "
        f"P(giá WinMart > giá BHX) = {overall_test['prob_a_greater']:.2f}. Lưu ý: 2 siêu thị bán khác mặt hàng, khác quy "
        "cách, nên đây là so sánh cơ cấu kệ hàng, không phải giá của cùng một sản phẩm.",
        f"**H3. Cùng một sản phẩm thì nơi nào rẻ hơn? ({pairs['n_pairs']} cặp ghép)** "
        f"WinMart rẻ hơn {pairs['winmart_cheaper']}, đắt hơn {pairs['winmart_more_expensive']}, bằng giá {pairs['same_price']}. "
        f"Chênh lệch trung vị {pairs['median_diff_pct']:.1f}%, trung bình {pairs['mean_diff_pct']:.2f}%. "
        f"Paired t-test trên log(WinMart / BHX): t = {pairs['paired_t']['t']:.2f}, p = {pairs['paired_t']['p_value']:.2f}; "
        f"sign test chính xác p = {pairs['sign_test']['p_value']:.2f}; chênh lệch trung bình hình học "
        f"{pairs['geo_mean_ratio_pct']:+.2f}% (khoảng tin cậy 95% bootstrap {ci[0]:+.2f}% đến {ci[1]:+.2f}%) -> "
        f"{S.verdict_vi(pairs['paired_t']['p_value'])}: không siêu thị nào rẻ hơn một cách có hệ thống.",
    ]
    return "\n\n".join([
        "## 2. Statistics - Các ý nghĩa thống kê",
        "### 2.1 Ý nghĩa các chỉ số (slide 6.2)", md_table(meanings),
        "### 2.2 Thống kê mô tả (univariate)",
        vn("Tất cả biến số (ratio) - tương tự df.describe() của slide 2.7:"), md_table(all_vars, 1),
        vn(f"Giá bán (VND) theo siêu thị:"), md_table(price, 1),
        vn(f"Ý nghĩa: giá bán {S.shape_meaning_vi(overall)}"),
        vn(f"Sau khi lấy log: {S.shape_meaning_vi(log_d)} -> kiểm định và chuẩn hóa dùng log giá."),
        "### 2.3 Giá bán theo nhóm hàng và siêu thị", md_table(by_group, 1),
        "### 2.4 Giá trên kg / lít (chỉ các dòng biết khối lượng thật)", md_table(unit, 1),
        "### 2.5 Correlation - Tương quan (Spearman, thang log)", md_table(corr, 2),
        vn(f"Gói càng lớn càng đắt: Spearman r = {bhx_r.r:.2f} ở BHX ({S.strength_vi(bhx_r.r)}), "
           f"{wm_r.r:.2f} ở WinMart ({S.strength_vi(wm_r.r)}), cả hai {S.verdict_vi(max(bhx_r.p_value, wm_r.p_value))}. "
           "Khối lượng tổng và giá trên kg tương quan âm: mua gói lớn rẻ hơn trên mỗi kg. Tương quan không phải nhân quả."),
        "### 2.6 Significance tests - Kiểm định ý nghĩa thống kê (alpha = 0,05)", *map(vn, tests),
        vn("Kiểm định 139 cặp theo nhóm hàng (sign test; nhóm có ít cặp không thể đạt ý nghĩa thống kê):"),
        md_table(pair_groups, 2),
    ])


# ------------------------------------------------------------------ phần 3
PRICE_BINS = [0, 20_000, 100_000, float("inf")]
PRICE_LABELS = ["low (< 20k)", "medium (20k - 100k)", "high (>= 100k)"]


def price_band(price: pd.Series) -> pd.Series:
    """Binning (slide 2.6): giá bán -> biến ordinal."""
    return pd.cut(price, bins=PRICE_BINS, labels=PRICE_LABELS, right=False)


def duplicate_check(clean: pd.DataFrame) -> pd.DataFrame:
    """Slide 2.3: data preparation removes duplicates - check that none is left."""
    data_cols = [c for c in clean.columns if c not in ("observation_id", "row_id", "raw_file")]
    return pd.DataFrame([
        ("trùng row_id (cùng vị trí trong file gốc)", int(clean["row_id"].duplicated().sum())),
        ("trùng (siêu thị, mã sản phẩm)", int(clean.duplicated(["store", "product_code"]).sum())),
        ("trùng toàn bộ nội dung dòng", int(clean.duplicated(subset=data_cols).sum())),
    ], columns=["kiểm tra", "số dòng trùng"])


def part3_preprocessing(clean: pd.DataFrame, df: pd.DataFrame, log: dict) -> str:
    missing = pd.DataFrame(log["missing_before"])
    decisions = {
        "list_price_vnd": "điền = giá bán (không có khuyến mãi)", "brand": "điền 'UNKNOWN' + cột cờ",
        "brand_key": "điền 'unknown'", "pack_count": "điền 1 (mode, 74% số dòng) vào pack_count_filled + cột cờ",
        "size_value": "không bịa cho giá/kg; median theo siêu thị + danh mục (log) chỉ ở log_size_filled + cột cờ",
        "size_unit": "để trống (không đoán được)", "size_source": "để trống",
        "pack_source": "để trống", "total_quantity": "tính lại sau khi sửa; trống khi thiếu khối lượng / số lượng",
        "unit_price_vnd_per_kg_or_l": "tính lại sau khi sửa; trống khi thiếu khối lượng / số lượng",
        "flash_sale_price_vnd": "-> cột có/không is_flash_sale",
    }
    missing["decision"] = missing["column"].map(decisions).fillna("để trống (không áp dụng)")
    missing["type"] = missing["type"].map({"structural": "thiếu do cấu trúc", "real gap": "thiếu thật"})
    fixes = pd.DataFrame(log["pack_fix_examples"]).rename(columns={"name_clean": "name", "pack_count": "new_pack"})
    params = pd.DataFrame(log["scaling_params"]).T.reset_index().rename(columns={"index": "feature"})
    norm_cols = [f"log_price{s}" for s in ("", "_minmax", "_z", "_robust")]
    scaled = df[norm_cols].assign(log_price_simple_scaling=df["log_price"] / df["log_price"].max())   # slide 2.6: x / max
    norm_check = scaled.describe().T[["mean", "std", "min", "max"]].reset_index().rename(columns={"index": "column"})
    bands = pd.crosstab(price_band(df["sale_price_vnd"]), df["store"], margins=True, margins_name="tổng")
    bands = bands.reset_index().rename(columns={"sale_price_vnd": "phân khúc giá"})
    outlier_examples = df[df["log_price_outlier"]].nlargest(5, "sale_price_vnd")[["store", "group", "name_clean", "sale_price_vnd"]]
    o, fx, imp = log["outliers"], log["pack_fixes"], log["imputed"]
    return "\n\n".join([
        "## 3. Data preprocessing - Xử lý dữ liệu",
        vn(f"Đầu ra: `data/processed_py/report3_prepared.csv` ({log['rows_out']:,} dòng, không xóa dòng nào; "
           "file của Report 2 không bị sửa)."),
        vn("Kiểm tra trùng lặp (slide 2.3 - data preparation loại bỏ dòng trùng): Report 2 đã loại 200 dòng trùng; "
           "kiểm tra lại trên dữ liệu đầu vào Report 3:"), md_table(duplicate_check(clean)),
        "### 3.1 Fix wrong values - Sửa giá trị sai (pack count)",
        vn(f"Đã sửa {sum(fx.values())} giá trị: {fx.get('selling_unit_label', 0)} lấy theo đơn vị bán (lốc), "
           f"{fx.get('number_is_part_of_name', 0)} số là một phần của tên sản phẩm, {fx.get('n_x_size_in_name', 0)} dạng "
           "'số x khối lượng'. Một con số trong tên sản phẩm bị đọc nhầm thành số lượng "
           "(vd 'Wake Up 247' -> 247 lon, giá 141 đ/lít); WinMart bán lốc 6 ('Gói (Lốc) 6') nhưng tên ghi 'Thùng 24' "
           "-> giá là của đơn vị bán; '25*20g' -> 25 gói."),
        md_table(fixes),
        "### 3.2 Missing values - Xử lý giá trị thiếu",
        vn("Hai loại: **thiếu do cấu trúc** (website không công bố, hoặc sự kiện không xảy ra -> không phải lỗi, để trống) và "
           "**thiếu thật** (thông tin có nhưng không đọc được -> chỉ điền khi có quy tắc an toàn, luôn kèm cột cờ). "
           "Các cách xử lý theo slide 2.6: drop, thay bằng giá trị trung tâm / tần suất (mode), thay theo quy tắc, để nguyên."),
        md_table(missing, 2),
        vn(f"Đã điền: giá niêm yết {imp['list_price']} ô, thương hiệu {imp['brand']} ô, số lượng trong gói "
           f"{imp['pack_count']} ô, khối lượng {imp['size (features only)']} ô (chỉ ở cột đặc trưng cho mô hình). "
           f"Giá/kg-lít có cho {log['unit_price_available']:,} dòng. Ô trống còn lại trong 4 cột đặc trưng "
           f"({', '.join(log['missing_after_features'])}): {sum(log['missing_after_features'].values())}."),
        "### 3.3 Outliers - Giá trị ngoại lai (quy tắc IQR trong từng nhóm hàng)",
        vn(f"Chỉ đánh dấu, không xóa: theo giá gốc {o['price_outlier']} dòng, theo log giá {o['log_price_outlier']} dòng, "
           f"theo log giá/kg {o['unit_price_outlier']} dòng. Đây là giá thật (thùng 12-40 món, mỹ phẩm, yến) nên xóa sẽ làm "
           "lệch dữ liệu; lấy log để giảm ảnh hưởng."),
        md_table(outlier_examples, 0),
        "### 3.4 Normalisation - Chuẩn hóa (slide 2.6)",
        vn(f"- Log: `log(x)` - đưa giá lệch phải về gần đối xứng (skew {df['sale_price_vnd'].skew():.2f} -> "
           f"{df['log_price'].skew():.2f}).\n"
           "- Simple feature scaling: `x / max` -> giá trị trong (0, 1]; cách đơn giản nhất trong slide 2.6, giữ tỉ lệ giữa các giá trị.\n"
           "- Min-max: `(x - min) / (max - min)` -> khoảng [0, 1]; nhạy với giá trị cực đoan.\n"
           "- Z-score: `(x - mean) / std` -> mean 0, std 1; tốt nhất sau khi lấy log, khi dữ liệu gần chuẩn.\n"
           "- Robust: `(x - median) / IQR` -> không bị outlier ảnh hưởng; không dùng được khi IQR = 0 "
           "(discount_pct và pack_count: 75% số dòng có cùng giá trị)."),
        "Tham số (lưu lại để dữ liệu mới được chuẩn hóa đúng như cũ):", md_table(params, 3),
        "Kiểm tra trên log giá:", md_table(norm_check, 3),
        "### 3.5 Binning and encoding - Chia khoảng và mã hóa (slide 2.6)",
        vn("Binning: giá bán chia thành 3 khoảng -> biến số trở thành biến **ordinal** (rẻ < trung bình < cao). "
           "Dùng cho biểu đồ của Report 4."), md_table(bands),
        vn("Dummy variables: is_promotion, is_flash_sale -> 0/1; store và group -> các cột one-hot "
           "(store_bhx, store_winmart, group_*), vì mô hình thống kê không nhận chữ."),
    ])


def run() -> str:
    clean = pd.read_csv(P.CLEAN_FILE)
    matched = pd.read_csv(MATCHED_FILE)
    df, log = P.prepare(clean)
    df.to_csv(P.PREPARED_FILE, index=False, encoding="utf-8-sig")
    text = "\n\n".join(["# Report 3 - EDA: kết quả (tạo bởi `python -m report3.run`)",
                        part1_understanding(clean, matched), part2_statistics(df, matched),
                        part3_preprocessing(clean, df, log)]) + "\n"
    RESULTS_FILE.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    run()
    print(f"Wrote {RESULTS_FILE} and {P.PREPARED_FILE}")


if __name__ == "__main__":
    main()
