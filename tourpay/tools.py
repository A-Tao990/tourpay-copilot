"""Deterministic tools the agent can call. Money maths is done here, never by the language model."""
import json, os, threading, time, uuid
from decimal import Decimal
from . import fx
from .i18n import t
from .paypal_client import PayPal, PayPalError

DEMO_LIMIT_VND = 50_000_000
# Probed against the real PayPal sandbox on 2026-10-31: these 12 were accepted; CNY was rejected (CURRENCY_NOT_SUPPORTED).
PAYPAL_CURRENCIES = {"USD", "EUR", "GBP", "AUD", "CAD", "SGD", "HKD", "JPY", "THB", "TWD", "MYR", "PHP"}

class Store:
    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        try:
            with open(path) as f: self.orders = json.load(f)
        except Exception: self.orders = {}
    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f: json.dump(self.orders, f, indent=1, ensure_ascii=False)

class Tools:
    def __init__(self, paypal: PayPal, store: Store):
        self.pp, self.store = paypal, store

    def quote_price(self, amount_vnd, currency="USD", lang="en"):
        q = fx.quote(amount_vnd, currency)
        q["text"] = t("quote", lang, vnd="{:,}".format(q["amount_vnd"]), value=q["value"], cur=q["currency"], rate="{:,}".format(q["vnd_per_unit"]), src=q["rate_source"])
        return q

    def create_payment(self, amount_vnd, currency="USD", description="Tourist payment", lang="en"):
        amount_vnd = int(amount_vnd)
        if amount_vnd <= 0: raise ValueError("amount must be positive")
        if amount_vnd > DEMO_LIMIT_VND: return {"error": "too_big", "text": t("too_big", lang, limit="{:,}".format(DEMO_LIMIT_VND))}
        currency = currency.upper()
        warn = ""
        if currency not in PAYPAL_CURRENCIES:
            warn, currency = t("usd_fallback", lang), "USD"
        q = fx.quote(amount_vnd, currency)
        if Decimal(q["value"]) <= 0:
            return {"error": "too_small", "text": t("too_small", lang, vnd="{:,}".format(amount_vnd), value=q["value"], cur=currency)}
        ref = "tp-" + uuid.uuid4().hex[:16]
        o = self.pp.create_order(q["value"], currency, description, ref)
        rec = {"id": o["id"], "ref": ref, "amount_vnd": amount_vnd, "currency": currency, "value": q["value"], "vnd_per_unit": q["vnd_per_unit"],
               "rate_source": q["rate_source"], "description": description, "status": o["status"], "approve_url": o["approve_url"], "mock": o.get("mock", False),
               "created": int(time.time()), "lang": lang}
        with self.store.lock:
            self.store.orders[o["id"]] = rec; self.store.save()
        rec["text"] = warn + t("created", lang, vnd="{:,}".format(amount_vnd), value=q["value"], cur=currency, oid=o["id"], url=o["approve_url"])
        return rec

    def check_payment(self, order_id, lang="en"):
        st = self.pp.get_order(order_id)
        with self.store.lock:
            o = self.store.orders.get(order_id)
            if o and o["status"] != "REFUNDED":          # PayPal still reports a refunded order's ORDER as COMPLETED
                o["status"] = st["status"]; self.store.save()
            shown = o["status"] if o else st["status"]
        return {"id": order_id, "status": shown, "text": t("status", lang, oid=order_id, status=shown)}

    def capture_payment(self, order_id, lang="en"):
        st = self.pp.get_order(order_id)
        if st["status"] != "APPROVED":
            return {"id": order_id, "status": st["status"], "text": t("need_approval", lang, oid=order_id, status=st["status"])}
        c = self.pp.capture(order_id)
        with self.store.lock:
            if order_id in self.store.orders:
                self.store.orders[order_id].update(status=c["status"], capture_id=c.get("capture_id")); self.store.save()
        return {**c, "text": t("captured", lang, oid=order_id, status=c["status"], cap=c.get("capture_id"))}

    def refund_payment(self, order_id, lang="en"):
        o = self.store.orders.get(order_id)
        if not o: raise PayPalError("unknown order")
        if o["status"] != "COMPLETED" or not o.get("capture_id"):
            return {"id": order_id, "status": o["status"], "text": t("cannot_refund", lang, oid=order_id, status=o["status"])}
        r = self.pp.refund(o["capture_id"])
        with self.store.lock:
            o.update(status="REFUNDED", refund_id=r.get("id")); self.store.save()
        return {"id": order_id, "status": "REFUNDED", "refund_id": r.get("id"),
                "text": t("refunded", lang, oid=order_id, value=o["value"], cur=o["currency"], rid=r.get("id"))}

    def summary(self):
        """Merchant reconciliation: today (Vietnam time, UTC+7) and all-time."""
        from datetime import datetime, timedelta, timezone
        vn = timezone(timedelta(hours=7)); today = datetime.now(vn).date(); orders = self.list_orders()
        def agg(os_):
            done = [o for o in os_ if o["status"] == "COMPLETED"]; ref = [o for o in os_ if o["status"] == "REFUNDED"]
            def by(lst):
                d = {}
                for o in lst: d[o["currency"]] = d.get(o["currency"], Decimal(0)) + Decimal(o["value"])
                return {k: float(v) for k, v in d.items()}
            return {"orders": len(os_), "completed": len(done), "refunded": len(ref), "pending": len(os_) - len(done) - len(ref),
                    "vnd_collected": sum(o["amount_vnd"] for o in done), "collected_by_currency": by(done), "refunded_by_currency": by(ref)}
        return {"date": str(today), "timezone": "UTC+7 (Vietnam)", "today": agg([o for o in orders if datetime.fromtimestamp(o["created"], vn).date() == today]), "all": agg(orders)}

    def export_csv(self):
        import csv, io
        from datetime import datetime, timedelta, timezone
        vn = timezone(timedelta(hours=7)); buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["order_id", "created_vn_time", "amount_vnd", "currency", "charged", "vnd_per_unit", "rate_source", "status", "capture_id", "refund_id", "description"])
        for o in reversed(self.list_orders()):
            w.writerow([o["id"], datetime.fromtimestamp(o["created"], vn).strftime("%Y-%m-%d %H:%M:%S"), o["amount_vnd"], o["currency"], o["value"],
                        o["vnd_per_unit"], o["rate_source"], o["status"], o.get("capture_id", ""), o.get("refund_id", ""), o["description"]])
        return buf.getvalue()

    def receipt(self, order_id, lang="en"):
        o = self.store.orders.get(order_id)
        if not o: raise PayPalError("unknown order")
        return t("receipt", lang, oid=o["id"], vnd="{:,}".format(o["amount_vnd"]), value=o["value"], cur=o["currency"], status=o["status"],
                 rate="{:,}".format(o["vnd_per_unit"]), src=o["rate_source"])

    def payment_options(self, lang="en"):
        return t("options", lang)

    def list_orders(self):
        """Only orders of the current mode (mock orders are hidden in real-sandbox mode and vice versa)."""
        return sorted((o for o in self.store.orders.values() if bool(o.get("mock")) == self.pp.mock), key=lambda o: -o["created"])
