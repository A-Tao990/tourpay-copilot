"""Minimal PayPal Orders v2 client (sandbox by default) with an offline MOCK mode for development and tests.
Real mode needs PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (sandbox REST app credentials) in the environment."""
import base64, json, os, time, urllib.error, urllib.request, uuid

SANDBOX = "https://api-m.sandbox.paypal.com"

class PayPalError(Exception):
    pass

class PayPal:
    def __init__(self, client_id=None, secret=None, base=SANDBOX, return_url="http://localhost:8080/paypal/return",
                 cancel_url="http://localhost:8080/paypal/cancel"):
        self.client_id = client_id if client_id is not None else os.environ.get("PAYPAL_CLIENT_ID", "")
        self.secret = secret if secret is not None else os.environ.get("PAYPAL_CLIENT_SECRET", "")
        self.base, self.return_url, self.cancel_url = base, return_url, cancel_url
        self.mock = not (self.client_id and self.secret)
        self._tok, self._tok_exp = None, 0.0
        self._mock_orders = {}

    # ---- low level
    def _request(self, method, path, body=None, headers=None):
        h = {"Content-Type": "application/json"}; h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=(json.dumps(body).encode() if body is not None else None), headers=h, method=method)
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "ignore")
            try:
                j = json.loads(raw); d = (j.get("details") or [{}])[0]
                raise PayPalError("PayPal rejected the request (%s %s): %s" % (j.get("name", e.code), d.get("issue", ""), (d.get("description") or j.get("message") or "")[:160]))
            except (ValueError, AttributeError):
                raise PayPalError("PayPal HTTP %s: %s" % (e.code, raw[:200]))

    def _token(self):
        if self._tok and time.time() < self._tok_exp - 30:
            return self._tok
        basic = base64.b64encode(("%s:%s" % (self.client_id, self.secret)).encode()).decode()
        req = urllib.request.Request(self.base + "/v1/oauth2/token", data=b"grant_type=client_credentials", method="POST",
                                     headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            raise PayPalError("PayPal auth failed (check sandbox credentials): HTTP %s" % e.code)
        self._tok, self._tok_exp = d["access_token"], time.time() + int(d.get("expires_in", 300))
        return self._tok

    def _auth(self):
        return {"Authorization": "Bearer " + self._token()}

    # ---- orders
    def create_order(self, value, currency, description, reference_id):
        if self.mock:
            oid = "MOCK-" + uuid.uuid4().hex[:12].upper()
            self._mock_orders[oid] = {"id": oid, "status": "CREATED", "value": value, "currency": currency, "description": description}
            return {"id": oid, "status": "CREATED", "approve_url": "/mock/approve?id=" + oid, "mock": True}
        body = {"intent": "CAPTURE",
                "purchase_units": [{"reference_id": reference_id[:256], "description": description[:127],
                                    "amount": {"currency_code": currency, "value": value}}],
                "payment_source": {"paypal": {"experience_context": {
                    "return_url": self.return_url, "cancel_url": self.cancel_url, "user_action": "PAY_NOW",
                    "brand_name": "TourPay Copilot (sandbox)", "shipping_preference": "NO_SHIPPING"}}}}
        d = self._request("POST", "/v2/checkout/orders", body, {**self._auth(), "PayPal-Request-Id": reference_id})
        link = next((l["href"] for l in d.get("links", []) if l.get("rel") in ("payer-action", "approve")), None)
        return {"id": d["id"], "status": d["status"], "approve_url": link, "mock": False}

    def get_order(self, order_id):
        if self.mock:
            o = self._mock_orders.get(order_id)
            if not o: raise PayPalError("unknown mock order")
            return {"id": o["id"], "status": o["status"]}
        d = self._request("GET", "/v2/checkout/orders/" + order_id, None, self._auth())
        return {"id": d["id"], "status": d["status"]}

    def capture(self, order_id):
        if self.mock:
            o = self._mock_orders.get(order_id)
            if not o: raise PayPalError("unknown mock order")
            if o["status"] != "APPROVED": raise PayPalError("order not approved yet (status %s)" % o["status"])
            o["status"] = "COMPLETED"
            return {"id": order_id, "status": "COMPLETED", "capture_id": "MOCKCAP-" + order_id[-6:]}
        d = self._request("POST", "/v2/checkout/orders/%s/capture" % order_id, {}, {**self._auth(), "PayPal-Request-Id": "cap-" + order_id})
        cap = (((d.get("purchase_units") or [{}])[0].get("payments") or {}).get("captures") or [{}])[0]
        return {"id": d["id"], "status": d["status"], "capture_id": cap.get("id")}

    def refund(self, capture_id):
        if self.mock:
            return {"id": "MOCKREF-" + capture_id[-6:], "status": "COMPLETED"}
        d = self._request("POST", "/v2/payments/captures/%s/refund" % capture_id, {}, {**self._auth(), "PayPal-Request-Id": "ref-" + capture_id})
        return {"id": d.get("id"), "status": d.get("status")}

    def mock_approve(self, order_id):                      # simulates the payer approving on paypal.com (mock only)
        o = self._mock_orders[order_id]; o["status"] = "APPROVED"; return o
