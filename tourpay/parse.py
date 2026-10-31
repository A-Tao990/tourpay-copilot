"""Understand messy multilingual (zh / en / vi) payment requests: VND amounts, simple sums, currency, language."""
import re

CURRENCIES = {  # words -> ISO code
    "USD": ["usd", "$", "dollar", "dollars", "美元", "美金", "刀", "đô", "do la"], "EUR": ["eur", "euro", "欧元", "€"],
    "GBP": ["gbp", "pound", "英镑", "£"], "SGD": ["sgd", "新币", "新加坡元"], "AUD": ["aud", "澳元", "澳币"], "CAD": ["cad", "加元"],
    "HKD": ["hkd", "港币", "港元"], "JPY": ["jpy", "yen", "日元", "日币"], "THB": ["thb", "baht", "泰铢"], "TWD": ["twd", "新台币", "台币"],
    "MYR": ["myr", "ringgit", "马币"], "PHP": ["php", "peso", "比索"], "CNY": ["cny", "rmb", "人民币", "元人民币"],
}
UNIT = {"k": 1_000, "nghìn": 1_000, "ngàn": 1_000, "千": 1_000, "tr": 1_000_000, "triệu": 1_000_000, "m": 1_000_000, "万": 10_000, "萬": 10_000}
_NUM = r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(nghìn|ngàn|triệu|tr|k|m|千|万|萬)?(?![a-zA-Z])"

def _to_float(s):
    s = s.strip()
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))

def parse_amounts(text):
    """Return list of (amount_vnd, multiplier) found in text, e.g. '3 x 45k + 80k' -> [(45000,3),(80000,1)]."""
    t = text.lower().replace("vnd", " ").replace("đ", " ").replace("dong", " ").replace("越南盾", " ").replace("盾", " ")
    items = []
    for m in re.finditer(_NUM, t):
        raw, unit = m.group(1), m.group(2)
        val = _to_float(raw) * (UNIT.get(unit, 1) if unit else 1)
        pre = t[max(0, m.start() - 12):m.start()]
        qty = 1
        mq = re.search(r"(\d+)\s*(?:x|×|\*)\s*$", pre)
        if mq: qty = int(mq.group(1))
        if val >= 1000 or unit:
            items.append((val, qty))
    return items

def total_vnd(text):
    items = parse_amounts(text)
    return int(sum(v * q for v, q in items)) if items else None

def detect_currency(text, default="USD"):
    t = text.lower()
    for code, words in CURRENCIES.items():
        if code.lower() in re.findall(r"[a-z]{3}", t) or any(w in t for w in words if not w.isascii() or len(w) > 3 or w in "$€£"):
            return code
    return default

def detect_lang(text):
    if re.search(r"[一-鿿]", text): return "zh"
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", text.lower()): return "vi"
    return "en"
