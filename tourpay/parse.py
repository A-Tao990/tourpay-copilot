"""Understand messy multilingual (zh / en / vi) payment requests: VND amounts, simple sums, currency, language.
Amounts are read conservatively: dates, times and phone numbers are ignored, and a bare number is only an amount when it is
big enough (5+ digits), has thousands separators, carries a unit (k, nghìn, tr, triệu, 万...) or is followed by VND."""
import re

CURRENCIES = {  # words -> ISO code
    "USD": ["usd", "$", "dollar", "dollars", "美元", "美金", "刀", "đô", "do la"], "EUR": ["eur", "euro", "欧元", "€"],
    "GBP": ["gbp", "pound", "英镑", "£"], "SGD": ["sgd", "新币", "新加坡元"], "AUD": ["aud", "澳元", "澳币"], "CAD": ["cad", "加元"],
    "HKD": ["hkd", "港币", "港元"], "JPY": ["jpy", "yen", "日元", "日币"], "THB": ["thb", "baht", "泰铢"], "TWD": ["twd", "新台币", "台币"],
    "MYR": ["myr", "ringgit", "马币"], "PHP": ["php", "peso", "比索"], "CNY": ["cny", "rmb", "人民币", "元人民币"],
}
# ISO codes people may type that this demo does not support (so we can say so instead of silently using USD)
KNOWN_UNSUPPORTED = ("RUB", "KRW", "INR", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "MXN", "BRL", "ZAR", "TRY", "AED", "SAR", "IDR", "ILS", "NZD", "KHR", "LAK", "MMK")
UNIT = {"k": 1_000, "nghìn": 1_000, "ngàn": 1_000, "千": 1_000, "tr": 1_000_000, "triệu": 1_000_000, "m": 1_000_000, "万": 10_000, "萬": 10_000}
_DATE = re.compile(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")
_PHONE = re.compile(r"(?<![\d.,])(?:\+?84|0)\d{8,10}(?![\d.,])")
_NUM = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(nghìn|ngàn|triệu|tr|k|m|千|万|萬)?(?![a-zA-Zà-ỹ])")
_VND_MARK = re.compile(r"^\s*(?:vnd|vnđ|đ|đồng|dong|越南盾|盾)")

def _to_float(s):
    s = s.strip()
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))

def parse_amounts(text):
    """Return list of (amount_vnd, quantity), e.g. '3 x 45k + 80k' -> [(45000, 3), (80000, 1)]; '1tr2' -> 1,200,000."""
    t = _PHONE.sub(" ", _DATE.sub(" ", text.lower()))
    items = []
    for m in _NUM.finditer(t):
        raw, unit = m.group(1), m.group(2)
        end = m.end()
        base = _to_float(raw)
        if unit:
            mult = UNIT[unit]
            frac = re.match(r"(\d{1,3})(?!\d)", t[end:])          # Vietnamese shorthand: 1tr2 = 1.2 million, 45k5 = 45,500
            if frac and mult >= 1000 and not re.search(r"[.,]", raw):
                base += float("0." + frac.group(1))
            val = base * mult
        else:
            has_sep = bool(re.search(r"[.,]\d{3}", raw))
            marked = bool(_VND_MARK.match(t[end:]))
            big_plain = len(re.sub(r"\D", "", raw)) >= 5 and not re.search(r"[.,]", raw)
            if not (has_sep or marked or big_plain):
                continue
            val = base
        pre = t[max(0, m.start() - 12):m.start()]
        mq = re.search(r"(\d+)\s*(?:x|×|\*)\s*$", pre)
        qty = int(mq.group(1)) if mq else 1
        if val >= 1:
            items.append((val, qty))
    return items

def has_negative(text):
    """A minus sign directly in front of a number (dates and phone numbers are ignored first)."""
    t = _PHONE.sub(" ", _DATE.sub(" ", text))
    return bool(re.search(r"(?<![\w\d])[-−]\s*\d", t))

def total_vnd(text):
    items = parse_amounts(text)
    return int(round(sum(v * q for v, q in items))) if items else None

def detect_currency(text, default="USD"):
    t = text.lower()
    for code, words in CURRENCIES.items():
        if code.lower() in re.findall(r"[a-z]{3}", t) or any(w in t for w in words if not w.isascii() or len(w) > 3 or w in "$€£"):
            return code
    return default

def unsupported_currency(text):
    """An ISO code the user typed that we know but do not support (e.g. RUB), else None."""
    for m in re.finditer(r"\b([A-Za-z]{3})\b", text):
        if m.group(1).upper() in KNOWN_UNSUPPORTED:
            return m.group(1).upper()
    return None

def detect_lang(text):
    if re.search(r"[\u4e00-\u9fff]", text): return "zh"
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", text.lower()): return "vi"
    return "en"
