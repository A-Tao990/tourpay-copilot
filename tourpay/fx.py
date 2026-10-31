"""VND <-> payment-currency conversion. PayPal cannot settle in VND, so VND prices must be converted.
Uses a public mid-market rate (open.er-api.com) with a 1h cache and a clearly-flagged offline fallback."""
import json, time, urllib.request

ZERO_DECIMAL = {"JPY", "HUF", "TWD"}               # PayPal requires whole numbers for these
FALLBACK_VND_PER_USD = 25800.0                      # only used when the live rate is unreachable
_cache = {"t": 0.0, "rates": None}

def rates():
    if _cache["rates"] and time.time() - _cache["t"] < 3600:
        return _cache["rates"], "live"
    try:
        d = json.load(urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=10))
        if d.get("result") == "success":
            _cache.update(t=time.time(), rates=d["rates"])
            return d["rates"], "live"
    except Exception:
        pass
    return {"USD": 1.0, "VND": FALLBACK_VND_PER_USD}, "fallback"

def quote(amount_vnd: float, currency: str):
    currency = currency.upper()
    r, src = rates()
    if currency not in r or "VND" not in r:
        r, src = {"USD": 1.0, "VND": FALLBACK_VND_PER_USD}, "fallback"
        if currency != "USD":
            raise ValueError("no rate for " + currency)
    vnd_per_unit = r["VND"] / r[currency]
    value = amount_vnd / vnd_per_unit
    value = round(value) if currency in ZERO_DECIMAL else round(value + 1e-9, 2)
    return {"amount_vnd": int(amount_vnd), "currency": currency, "value": ("%d" % value) if currency in ZERO_DECIMAL else ("%.2f" % value),
            "vnd_per_unit": round(vnd_per_unit, 2), "rate_source": src,
            "note": "mid-market rate; PayPal applies its own conversion spread and fees"}
