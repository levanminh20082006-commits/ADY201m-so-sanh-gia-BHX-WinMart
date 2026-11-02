"""Small, testable helpers to turn raw text into clean values.

Every function returns None when the text gives no evidence - we never guess.
"""
import re
import unicodedata

# ---------------------------------------------------------------- prices
_PRICE_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+)")


def parse_price(value) -> int | None:
    """'345.000đ' -> 345000, '16.500 ₫' -> 16500, 92000.0 -> 92000, 'Liên hệ' -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value)) if value == value else None  # NaN check
    match = _PRICE_RE.search(str(value).replace("\xa0", " "))
    if not match:
        return None
    return int(re.sub(r"[.,]", "", match.group(1)))  # VND has no decimals: dots/commas are thousands


_CARD_PRICE_LINE = re.compile(r"^\d{1,3}(?:\.\d{3})+\s*[₫đ]$")


def card_prices(card_text) -> list[int]:
    """Prices shown on a product card, in display order. Only lines that are ONLY a price count,
    so promo lines like 'Mua 2 gói với giá 120.600 ₫' are ignored."""
    lines = [line.replace(" ", " ").strip() for line in str(card_text or "").splitlines()]
    return [parse_price(line) for line in lines if _CARD_PRICE_LINE.match(line)]


def parse_percent(value) -> int | None:
    """'-9%' -> 9."""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", str(value or ""))
    return round(float(match.group(1).replace(",", "."))) if match else None


# ---------------------------------------------------------------- text
def clean_text(value) -> str | None:
    """Unicode NFC + collapse spaces. Keeps Vietnamese accents."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value))).strip()
    return text or None


def strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFD", value)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_text(value) -> str:
    """'Sữa tươi TH true MILK 180ml' -> 'sua tuoi th true milk 180ml' (for comparing)."""
    text = strip_accents(clean_text(value) or "").lower()
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)          # 1,5l -> 1.5l
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)       # keep dots only inside numbers
    return re.sub(r"\s+", " ", text).strip()


def brand_key(brand) -> str | None:
    """Brand comparison key: 'TH true MILK' / 'TH TRUE MILK' -> 'thtruemilk'."""
    key = normalize_text(brand).replace(" ", "").replace(".", "")
    return key or None


# ---------------------------------------------------------------- size and packaging
_UNITS = {"kg": (1000, "g"), "g": (1, "g"), "gr": (1, "g"), "gram": (1, "g"), "gam": (1, "g"),
          "ml": (1, "ml"), "l": (1000, "ml"), "lit": (1000, "ml"), "litre": (1000, "ml")}
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|gram|gam|gr|g|ml|lit|litre|l)\b")
# '1.5L/1.75L' (the '/' becomes a space): two sizes, we cannot know which one is sold
_AMBIGUOUS_SIZE = re.compile(r"\d\s*(?:kg|g|ml|l)\s+\d+(?:\.\d+)?\s*(?:kg|g|ml|l)\b")

PACK_WORDS = r"hop|chai|lon|goi|bich|tui|ly|chiec|vi|hu|cuon|banh|thanh|qua|trung|lo|tep|mieng|vien|cai|cay|tuyp|binh|can|thanh"
_PACK_COUNT_BEFORE = re.compile(rf"\b(\d+)\s*({PACK_WORDS})\b")             # '48 hop', '30 goi'
_PACK_X_BEFORE = re.compile(r"\b(\d+)\s*[x*]\s*\d")                         # '4 x 180ml'
_PACK_X_AFTER = re.compile(r"\d\s*(?:ml|g|l|kg)\s*[x*]\s*(\d+)\b")          # '180ml x 4'
_PACK_CONTAINER = re.compile(r"\b(?:loc|thung|bo|combo|day|loc)\s*(\d+)\b(?!\s*(?:ml|g|l|kg|%|\.))")  # 'loc 4'
MULTIPACK_HINT = re.compile(r"\b(thung|loc|combo|bo|day|set|bich \d|goi \d)\b")


def parse_size(text) -> dict:
    """First weight/volume in the text -> {'size_value': 180.0, 'size_unit': 'ml', 'size_text': '180ml'}.

    Converted to base units: kg -> g, L -> ml. Returns Nones if not found.
    """
    norm = normalize_text(text)
    match = _SIZE_RE.search(norm)
    if not match or _AMBIGUOUS_SIZE.search(norm):
        return {"size_value": None, "size_unit": None, "size_text": None}
    factor, unit = _UNITS[match.group(2)]
    return {"size_value": round(float(match.group(1)) * factor, 3), "size_unit": unit,
            "size_text": match.group(0)}


def parse_pack_count(text) -> int | None:
    """How many units are sold together: 'Thùng 48 hộp sữa 180ml' -> 48, 'Lốc 4 hộp x 180ml' -> 4.

    Returns 1 only when the text has no multipack words at all; None when it is unclear.
    """
    norm = normalize_text(text)
    for regex in (_PACK_COUNT_BEFORE, _PACK_X_BEFORE, _PACK_X_AFTER, _PACK_CONTAINER):
        match = regex.search(norm)
        if match:
            count = int(match.group(1))
            if 1 <= count <= 500:
                return count
    return None if MULTIPACK_HINT.search(norm) else 1


# ---------------------------------------------------------------- variant words
# Words that change WHICH product it is (sugar level, flavour). Two products that disagree
# on these are different products. Matched on ACCENTED lowercase text, because without
# accents 'dâu' (strawberry), 'dầu' (oil) and 'đậu' (bean) all become 'dau'.
VARIANT_WORDS = [
    # sugar / fat / formula
    "không đường", "rất ít đường", "ít đường", "có đường", "đường đen", "tách béo", "nguyên kem",
    "không lactose", "zero", "light", "ít béo", "canxi", "nguyên chất", "có thạch", "organic", "a2",
    "ít ngọt", "không ngọt", "không calo", "giảm đường",
    # product form
    "cửa trước", "cửa trên", "ly", "mini",
    # product line
    "sữa tươi", "sữa chua", "đậu nành", "lúa mạch", "yến mạch", "gạo lứt", "hạt sen", "óc chó", "hạnh nhân",
    # flavours
    "dâu tây", "dâu", "socola", "sô cô la", "chocolate", "vani", "cam", "nho", "táo", "chuối", "dừa", "dứa",
    "cà phê", "trà xanh", "matcha", "khoai môn", "bạc hà", "chanh dây", "chanh", "đào", "xoài",
    "việt quất", "lựu", "kiwi", "nha đam", "cacao", "ca cao", "mật ong", "gừng", "tôm", "bò", "gà", "heo",
    "sườn", "lẩu thái", "chua cay", "kim chi", "cua", "hải sản", "nấm", "tỏi", "ớt", "me", "mè",
    "trái cây", "bưởi", "sen", "ổi", "dưa lưới", "vải", "đậu đỏ", "đậu xanh",
    "phô mai", "caramel", "tắc", "bắp", "cay", "không cay", "chay", "muối", "tiêu", "sả", "nghệ",
]
_SYNONYMS = {"sô cô la": "socola", "chocolate": "socola", "ca cao": "cacao"}
_VARIANT_RES = [(w, re.compile(rf"(?<!\w){re.escape(w)}(?!\w)")) for w in sorted(VARIANT_WORDS, key=len, reverse=True)]

# 'Soft' attributes: names often leave them out, so they only count when BOTH names state one.
# process conflict -> different product; sauce label conflict -> a human must check (NEEDS_REVIEW).
EXCLUSIVE_GROUPS = {"process": ["tiệt trùng", "thanh trùng"], "sauce_label": ["nước mắm", "nước chấm"]}
REVIEW_ONLY_GROUPS = {"sauce_label"}

# Descriptive words that do not change the product (ignored when comparing leftover words).
GENERIC_WORDS = set(("huong vi an lien uong nuoc tiet trung thanh hoa tan cao cap thuong hang dac biet kieu "
                     "san xuat tu nhien chinh moi loai nho lon tui dang co thit that sach ngot mat nhe").split())


def distinctive_extras(tokens_a: set, tokens_b: set) -> tuple[set, set]:
    """Meaningful words that only one of the two names has (generic words removed)."""
    return (tokens_a - tokens_b) - GENERIC_WORDS, (tokens_b - tokens_a) - GENERIC_WORDS


def variant_words(text) -> set[str]:
    """Variant keywords present in the accented text, longest phrase first ('dâu tây' wins over 'dâu')."""
    remaining = (clean_text(text) or "").lower()
    found = set()
    for word, regex in _VARIANT_RES:
        if regex.search(remaining):
            found.add(_SYNONYMS.get(word, word))
            remaining = regex.sub(" ", remaining)
    return found


def exclusive_attributes(text) -> dict[str, str]:
    """{'process': 'tiệt trùng'} if the text states it."""
    lower = (clean_text(text) or "").lower()
    found = {}
    for group, words in EXCLUSIVE_GROUPS.items():
        hits = [w for w in words if re.search(rf"(?<!\w){w}(?!\w)", lower)]
        if len(hits) == 1:
            found[group] = hits[0]
    return found


STOP_WORDS = set(("hop chai lon goi bich tui ly chiec vi hu cuon banh thanh qua lo tep mieng vien cai cay tuyp "
                  "binh can loc thung bo combo day set x ml g l kg lit gram gam gr va voi cho loai moi").split())


def name_tokens(text, brand=None) -> set[str]:
    """Meaningful words of a name, without brand words, sizes, numbers and packaging words."""
    brand_words = set(normalize_text(brand).split()) if brand else set()
    tokens = set()
    for token in normalize_text(text).split():
        if token in STOP_WORDS or token in brand_words or re.fullmatch(r"[\d.]+[a-z]*", token):
            continue
        tokens.add(token)
    return tokens


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0
