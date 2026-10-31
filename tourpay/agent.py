"""The agent. Language models are used ONLY to understand messy requests (intent + amounts + currency) and to answer
small talk; all money maths and PayPal calls are deterministic tools. With no API key it runs fully on built-in rules."""
import json, os, re, urllib.error, urllib.request
from .i18n import t
from .parse import detect_currency, detect_lang, has_negative, total_vnd, unsupported_currency
from .tools import PAYPAL_CURRENCIES

ORDER_RE = re.compile(r"\b(MOCK-[A-Z0-9]{6,}|[0-9A-Z]{17})\b")
RX = {
    "capture": re.compile(r"\b(capture|confirm payment|collect)\b|确认收款|收款确认|已经付|付完|xác nhận thanh toán|ghi nhận", re.I),
    "status": re.compile(r"\b(status|paid\??|did .* pay)\b|状态|付了吗|付款了吗|trạng thái|đã thanh toán chưa", re.I),
    "refund": re.compile(r"\brefund\b|退款|hoàn tiền", re.I),
    "receipt": re.compile(r"receipt|收据|biên lai", re.I),
    "options": re.compile(r"how (can|do|should) i pay|payment (options|methods)|ways to pay|怎么付|如何付|付款方式|怎么支付|cách thanh toán|thanh toán như thế nào|làm sao để thanh toán", re.I),
    "pay": re.compile(r"\b(pay|paypal|link|invoice|charge|checkout|bill)\b|付款|付|收款|支付|thanh toán|trả|hóa đơn", re.I),
    "quote": re.compile(r"how much|convert|quote|exchange|多少|换算|报价|折合|bao nhiêu|quy đổi", re.I),
}

class LLMError(Exception):
    pass

class Anthropic:
    """Claude via the Anthropic Messages API (paid API key from platform.claude.com; separate from a Claude Pro subscription)."""
    name = "claude"
    def __init__(self, key, model):
        self.key, self.model = key, model
    def complete(self, prompt):
        body = {"model": self.model, "max_tokens": 300, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        h = {"Content-Type": "application/json", "x-api-key": self.key, "anthropic-version": "2023-06-01"}
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(), h), timeout=30))
            return "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        except Exception as e:
            raise LLMError(str(e)[:200])

class Gemini:
    """Google Gemini (free tier available). Tries the configured model first, then fallbacks when a model is
    gone for new accounts (404), rate limited (429) or briefly overloaded (503)."""
    name = "gemini"
    FALLBACKS = ("gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest")
    def __init__(self, key, model):
        self.key = key
        self.models = [model] + [m for m in self.FALLBACKS if m != model]
        self.model = model
    def complete(self, prompt):
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
        h = {"Content-Type": "application/json", "x-goog-api-key": self.key}        # header, not URL: keys in URLs get logged
        last = "no model tried"
        for m in self.models:
            url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % m
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), h), timeout=30))
                self.model = m
                return d["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = "HTTP %s on %s" % (e.code, m)
                if e.code not in (404, 429, 500, 503): break
            except Exception as e:
                last = (type(e).__name__ + " on " + m)[:200]
        raise LLMError(last)

class OpenAICompat:
    name = "openai-compatible"
    def __init__(self, base, key, model):
        self.base, self.key, self.model = base.rstrip("/"), key, model
    def complete(self, prompt):
        body = {"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        h = {"Content-Type": "application/json"}
        if self.key: h["Authorization"] = "Bearer " + self.key
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(self.base + "/chat/completions", json.dumps(body).encode(), h), timeout=60))
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(str(e)[:200])

def llm_from_env():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return Anthropic(os.environ["ANTHROPIC_API_KEY"], os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"))
    if os.environ.get("GEMINI_API_KEY"):
        return Gemini(os.environ["GEMINI_API_KEY"], os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    if os.environ.get("LLM_BASE_URL"):
        return OpenAICompat(os.environ["LLM_BASE_URL"], os.environ.get("LLM_API_KEY", ""), os.environ.get("LLM_MODEL", "local"))
    return None

EXTRACT_PROMPT = """You help a small shop in Vietnam charge foreign tourists through PayPal. Prices are in Vietnamese dong (VND).
Read the user's message (it may be Chinese, English or Vietnamese) and return ONLY JSON:
{"intent": "quote|pay|status|capture|receipt|refund|options|other", "amount_vnd": <integer total in VND or null>, "currency": "<ISO code the tourist pays in, default USD>",
 "order_id": "<order id if mentioned else null>", "reply": "<short friendly answer in the user's language, only when intent is other>"}
Intent: use "pay" when the customer wants to pay or names a payment currency to pay in ("pay in EUR", "用欧元付", "thanh toán bằng đô la"); use "quote" ONLY when they just ask how much it would be in another currency.
Rules: never invent amounts; sum line items yourself (e.g. 3 cups at 45k plus a 80k cake = 215000). "k"=thousand, "tr"/"triệu"=million. If unsure use null.
User message: """

class Agent:
    def __init__(self, tools, llm=None):
        self.tools, self.llm, self.last_order = tools, llm, None

    # ---- understanding
    def _rules(self, text):
        oid = (ORDER_RE.search(text.upper()) or [None, None])[1] if ORDER_RE.search(text.upper()) else None
        amount = total_vnd(text)
        cur = detect_currency(text)
        if RX["options"].search(text): return {"intent": "options"}
        if RX["refund"].search(text) and (oid or self.last_order): return {"intent": "refund", "order_id": oid}
        if RX["receipt"].search(text): return {"intent": "receipt", "order_id": oid}
        if RX["capture"].search(text) and (oid or self.last_order): return {"intent": "capture", "order_id": oid}
        if RX["status"].search(text) and (oid or self.last_order): return {"intent": "status", "order_id": oid}
        if amount and has_negative(text): return {"intent": "negative"}
        bad = unsupported_currency(text) or (cur if cur not in PAYPAL_CURRENCIES else None)
        if amount and bad and not (RX["quote"].search(text) and not RX["pay"].search(text)): return {"intent": "bad_currency", "code": bad}
        if amount:
            if RX["pay"].search(text) and not RX["quote"].search(text): return {"intent": "pay", "amount_vnd": amount, "currency": cur}
            return {"intent": "quote" if RX["quote"].search(text) else "pay", "amount_vnd": amount, "currency": cur}
        return {"intent": "other"}

    def _understand(self, text):
        r = self._rules(text)
        if r["intent"] != "other" or not self.llm:
            return r, "rules"
        try:
            raw = self.llm.complete(EXTRACT_PROMPT + text)
            j = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
            j["intent"] = j.get("intent") if j.get("intent") in ("quote", "pay", "status", "capture", "receipt", "refund", "options", "other") else "other"
            if j.get("amount_vnd") is not None:
                j["amount_vnd"] = int(j["amount_vnd"])
            j["currency"] = (j.get("currency") or "USD").upper()
            return j, self.llm.name
        except Exception:
            return r, "rules"

    # ---- acting
    def handle(self, text):
        lang = detect_lang(text)
        try:
            u, brain = self._understand(text)
            oid = u.get("order_id") or self.last_order
            it = u["intent"]
            if it == "negative":
                return {"reply": t("negative", lang), "lang": lang, "brain": brain}
            if it == "bad_currency":
                return {"reply": t("bad_currency", lang, code=u["code"], supported=", ".join(sorted(PAYPAL_CURRENCIES))), "lang": lang, "brain": brain}
            if it == "pay" and u.get("amount_vnd") and (u.get("currency") or "USD") not in PAYPAL_CURRENCIES:
                return {"reply": t("bad_currency", lang, code=u["currency"], supported=", ".join(sorted(PAYPAL_CURRENCIES))), "lang": lang, "brain": brain}
            if it in ("quote", "pay") and not u.get("amount_vnd"):
                return {"reply": t("help", lang), "lang": lang, "brain": brain}
            if it == "quote":
                q = self.tools.quote_price(u["amount_vnd"], u.get("currency", "USD"), lang)
                return {"reply": q["text"], "lang": lang, "brain": brain, "quote": q}
            if it == "pay":
                o = self.tools.create_payment(u["amount_vnd"], u.get("currency", "USD"), "Tourist payment (VND %s)" % "{:,}".format(u["amount_vnd"]), lang)
                if "id" in o: self.last_order = o["id"]
                return {"reply": o["text"], "lang": lang, "brain": brain, "order": o if "id" in o else None}
            if it == "status" and oid:
                s = self.tools.check_payment(oid, lang); return {"reply": s["text"], "lang": lang, "brain": brain, "order": s}
            if it == "capture" and oid:
                c = self.tools.capture_payment(oid, lang); return {"reply": c["text"], "lang": lang, "brain": brain, "order": c}
            if it == "refund" and oid:
                r = self.tools.refund_payment(oid, lang); return {"reply": r["text"], "lang": lang, "brain": brain, "order": r}
            if it == "receipt" and oid:
                return {"reply": self.tools.receipt(oid, lang), "lang": lang, "brain": brain}
            if it == "options":
                return {"reply": self.tools.payment_options(lang), "lang": lang, "brain": brain}
            return {"reply": u.get("reply") or t("help", lang), "lang": lang, "brain": brain}
        except Exception as e:
            return {"reply": t("error", lang, err=str(e)[:200]), "lang": lang, "brain": "error"}
