import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tourpay import fx
from tourpay.agent import Agent
from tourpay.paypal_client import PayPal, PayPalError
from tourpay.parse import detect_currency, detect_lang, total_vnd
from tourpay.tools import Store, Tools

fx.rates = lambda: ({"USD": 1.0, "VND": 25000.0, "EUR": 0.9, "JPY": 150.0, "CNY": 7.0}, "test")   # offline, deterministic

def make_agent():
    pp = PayPal("", "")                       # mock mode
    tools = Tools(pp, Store(os.path.join(tempfile.mkdtemp(), "o.json")))
    return pp, tools, Agent(tools, None)

class Parse(unittest.TestCase):
    def test_sums(self):
        self.assertEqual(total_vnd("3 x 45k + 80k, pay in USD"), 215000)
        self.assertEqual(total_vnd("账单 450,000 VND,用美元付"), 450000)
        self.assertEqual(total_vnd("tổng 1,2 triệu"), 1200000)
        self.assertEqual(total_vnd("coffee 45.000 và bánh 80.000"), 125000)
        self.assertEqual(total_vnd("total 1.250.000 vnd"), 1250000)
        self.assertIsNone(total_vnd("hello there"))
    def test_currency_and_lang(self):
        self.assertEqual(detect_currency("pay in EUR"), "EUR"); self.assertEqual(detect_currency("用美元付"), "USD")
        self.assertEqual(detect_currency("thanh toán bằng GBP"), "GBP"); self.assertEqual(detect_currency("no currency here"), "USD")
        self.assertEqual(detect_lang("你好"), "zh"); self.assertEqual(detect_lang("xin chào bạn"), "vi"); self.assertEqual(detect_lang("hello"), "en")

class TooSmall(unittest.TestCase):
    def test_tiny_amounts_are_refused_before_calling_paypal(self):
        pp, tools, _ = make_agent()
        r = tools.create_payment(100, "USD")                                   # 100 VND = 0.00 USD
        self.assertEqual(r["error"], "too_small"); self.assertEqual(tools.list_orders(), []); self.assertEqual(pp._mock_orders, {})

class HttpLayer(unittest.TestCase):
    """The real HTTP server, in mock mode, on an ephemeral port."""
    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        from tourpay.server import make_handler
        pp, tools, agent = make_agent()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pp, tools, agent))
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()
    def get(self, path):
        import urllib.request
        return urllib.request.urlopen(self.base + path, timeout=10).read().decode()
    def post(self, path, obj):
        import json, urllib.error, urllib.request
        req = urllib.request.Request(self.base + path, json.dumps(obj).encode(), {"Content-Type": "application/json"})
        try: return urllib.request.urlopen(req, timeout=10).status
        except urllib.error.HTTPError as e: return e.code
    def chat(self, msg):
        import json, urllib.request
        req = urllib.request.Request(self.base + "/api/chat", json.dumps({"message": msg}).encode(), {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=10))
    def test_full_flow_over_http(self):
        import json
        self.assertEqual(json.loads(self.get("/api/health"))["paypal"], "MOCK (no credentials)")
        self.assertIn("TourPay Copilot", self.get("/"))
        order = self.chat("3 x 45k + 80k, pay in USD")["order"]
        self.assertEqual((order["amount_vnd"], order["value"]), (215000, "8.60"))
        self.get("/mock/confirm?id=" + order["id"])                             # payer approves -> redirect -> capture
        self.assertIn("COMPLETED", self.chat("status")["reply"])
        summary = json.loads(self.get("/api/summary"))["today"]
        self.assertEqual((summary["completed"], summary["vnd_collected"]), (1, 215000))
        self.assertIn("COMPLETED", self.get("/api/export.csv"))
        self.assertIn("NOTHING has been refunded", self.chat("refund")["reply"])
        self.assertIn("Refund issued", self.chat("confirm refund")["reply"])
    def test_demo_caption_endpoint_is_off_by_default(self):
        import json
        self.assertEqual(json.loads(self.get("/api/caption"))["text"], "")
        self.assertEqual(self.post("/api/caption", {"text": "x"}), 404)
    def raw(self, method, path, headers, body=None):
        import http.client
        host, port = self.base[len("http://"):].split(":")
        c = http.client.HTTPConnection(host, int(port), timeout=10); c.request(method, path, body, headers); r = c.getresponse(); r.read(); c.close(); return r.status
    def test_foreign_host_and_cross_site_origin_are_refused(self):
        self.assertEqual(self.raw("GET", "/api/health", {"Host": "evil.example"}), 403)             # DNS rebinding
        self.assertEqual(self.raw("POST", "/api/chat", {"Host": "localhost:8080", "Origin": "https://evil.example", "Content-Type": "application/json"}, b'{"message":"pay 450k"}'), 403)   # CSRF
        self.assertEqual(self.raw("POST", "/api/chat", {"Host": "localhost:8080", "Origin": "http://localhost:8080", "Content-Type": "application/json"}, b'{"message":"hello"}'), 200)
    def test_bad_or_huge_content_length(self):
        self.assertEqual(self.raw("POST", "/api/chat", {"Host": "localhost", "Content-Length": "abc"}), 400)
        self.assertEqual(self.raw("POST", "/api/chat", {"Host": "localhost", "Content-Length": "99999999"}), 413)
    def test_cancel_redirect_and_ui_message(self):
        import http.client
        host, port = self.base[len("http://"):].split(":")
        c = http.client.HTTPConnection(host, int(port), timeout=10); c.request("GET", "/paypal/cancel"); r = c.getresponse(); r.read(); c.close()
        self.assertEqual((r.status, r.getheader("Location")), (302, "/?cancelled=1"))
        self.assertIn("Payment cancelled", self.get("/"))                       # the page shows a message for ?cancelled=1
    def test_bad_input_does_not_crash_the_server(self):
        self.assertEqual(self.post("/api/chat", {"message": "x" * 5000}), 200)
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as cm: self.get("/nope")
        self.assertEqual(cm.exception.code, 404)                                # unknown path -> 404, server keeps running
        self.assertEqual(self.post("/api/chat", {"message": "hello"}), 200)

class Listing(unittest.TestCase):
    def test_list_orders_hides_other_mode(self):
        pp, tools, ag = make_agent()
        ag.handle("pay 100k")
        tools.store.orders["REAL-1"] = {"id": "REAL-1", "mock": False, "created": 1, "amount_vnd": 1, "value": "1", "currency": "USD", "status": "COMPLETED"}
        ids = [o["id"] for o in tools.list_orders()]
        self.assertEqual(len(ids), 1); self.assertTrue(ids[0].startswith("MOCK-"))

class RefundAndSummary(unittest.TestCase):
    def test_refund_lifecycle_and_summary_and_csv(self):
        pp, tools, ag = make_agent()
        oid = ag.handle("100k pay in USD")["order"]["id"]
        self.assertIn("cannot", ag.handle("refund")["reply"].lower())        # not paid yet
        pp.mock_approve(oid); ag.handle("confirm payment")
        s = tools.summary()["today"]; self.assertEqual((s["completed"], s["vnd_collected"], s["collected_by_currency"]), (1, 100000, {"USD": 4.0}))
        self.assertIn("NOTHING has been refunded", ag.handle("refund")["reply"])      # step 1: summary only
        self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")                # still not refunded
        self.assertIn("Refund issued", ag.handle("confirm refund")["reply"])          # step 2: explicit confirmation
        self.assertIn("REFUNDED", ag.handle("status")["reply"])               # stays REFUNDED after a status check
        s = tools.summary()["today"]; self.assertEqual((s["completed"], s["refunded"], s["refunded_by_currency"]), (0, 1, {"USD": 4.0}))
        csv_text = tools.export_csv(); self.assertTrue(csv_text.startswith("order_id,")); self.assertIn("REFUNDED", csv_text)

class FakeLLM:
    name = "fake"
    def __init__(self, out): self.out = out
    def complete(self, prompt): return self.out if not isinstance(self.out, Exception) else (_ for _ in ()).throw(self.out)

class ModelAssisted(unittest.TestCase):
    def agent(self, out):
        pp = PayPal("", ""); tools = Tools(pp, Store(os.path.join(tempfile.mkdtemp(), "o.json"))); return Agent(tools, FakeLLM(out)), tools
    def test_model_fills_in_what_rules_cannot_parse(self):
        ag, tools = self.agent('{"intent":"pay","amount_vnd":135000,"currency":"EUR","order_id":null,"reply":""}')
        r = ag.handle("三杯咖啡每杯四万五")                       # Chinese numerals: rules find no amount
        self.assertEqual(r["brain"], "fake"); self.assertEqual(r["order"]["amount_vnd"], 135000); self.assertEqual(r["order"]["currency"], "EUR")
    def test_model_output_is_validated(self):
        ag, _ = self.agent('here you go: {"intent":"hack","amount_vnd":"lots","currency":"usd"}')
        self.assertEqual(ag.handle("三杯咖啡每杯四万五")["brain"], "rules")      # bad JSON/intent -> safe fallback to rules
        ag, _ = self.agent(RuntimeError("network down"))
        self.assertIn("越南盾", ag.handle("三杯咖啡每杯四万五")["reply"])          # model failure -> (Chinese) help text, no crash
    def test_rules_win_when_they_can_parse(self):
        ag, _ = self.agent('{"intent":"pay","amount_vnd":1,"currency":"USD"}')
        r = ag.handle("3 x 45k + 80k, pay in USD"); self.assertEqual(r["brain"], "rules"); self.assertEqual(r["order"]["amount_vnd"], 215000)
    def test_model_amount_cannot_exceed_demo_limit(self):
        ag, _ = self.agent('{"intent":"pay","amount_vnd":99999999999,"currency":"USD"}')
        self.assertIn("上限", ag.handle("三杯咖啡每杯四万五")["reply"])               # replies in the user's language

class ParseRegressions(unittest.TestCase):
    """Inputs that used to produce wrong money."""
    def test_dates_times_and_phones_are_not_amounts(self):
        self.assertEqual(total_vnd("booked on 2026-11-05, total 300k"), 300000)    # was 302,026
        self.assertEqual(total_vnd("my phone is 0901234567 please pay 200k"), 200000)  # was 901 million
        self.assertEqual(total_vnd("call +84 901 234 567 total 80k"), 80000)
        self.assertEqual(total_vnd("1/12/2026 pay 90k"), 90000)
        self.assertEqual(total_vnd("at 10:30 pay 200k"), 200000)
        self.assertEqual(total_vnd("in 2026 pay 450000"), 450000)
        self.assertIsNone(total_vnd("hello 2026")); self.assertIsNone(total_vnd("pay 3"))
    def test_vietnamese_shorthand(self):
        self.assertEqual(total_vnd("pay 1tr2 USD"), 1200000)                          # was 1,000,000
        self.assertEqual(total_vnd("pay 2tr5"), 2500000); self.assertEqual(total_vnd("pay 45k5"), 45500)
        self.assertEqual(total_vnd("pay 1,5 triệu EUR"), 1500000); self.assertEqual(total_vnd("pay 1.5k"), 1500)
    def test_chinese_and_explicit_vnd(self):
        self.assertEqual(total_vnd("100万越南盾"), 1000000); self.assertEqual(total_vnd("三杯咖啡 4万5"), 45000)
        self.assertEqual(total_vnd("pay 5000 VND"), 5000); self.assertEqual(total_vnd("pay 45.000"), 45000)

class SafetyReplies(unittest.TestCase):
    def test_unsupported_currency_is_refused_not_silently_usd(self):
        _, tools, ag = make_agent()
        r = ag.handle("pay 450k in RUB"); self.assertNotIn("order", r); self.assertIn("RUB", r["reply"]); self.assertEqual(tools.list_orders(), [])
        self.assertIn("RUB", ag.handle("用 RUB 付 450k")["reply"])
    def test_cny_is_refused_because_paypal_rejects_it(self):                    # probed on the real sandbox: CURRENCY_NOT_SUPPORTED
        _, tools, ag = make_agent()
        r = ag.handle("账单 450,000 越南盾,用人民币付"); self.assertNotIn("order", r); self.assertIn("CNY", r["reply"]); self.assertIn("USD", r["reply"])
        self.assertEqual(tools.list_orders(), [])
        self.assertIn("quote", ag.handle("450k 越南盾折合多少人民币？"))          # a quote in CNY is still fine (no PayPal call)
    def test_negative_amount_is_refused(self):
        _, tools, ag = make_agent()
        r = ag.handle("pay -450k"); self.assertNotIn("order", r); self.assertEqual(tools.list_orders(), [])
    def test_currency_fallback_warning_is_localized(self):
        _, tools, _ = make_agent()
        self.assertIn("改用美元", tools.create_payment(100000, "RUB", "x", "zh")["text"])
        self.assertNotIn("CNY", __import__("tourpay.tools", fromlist=["x"]).PAYPAL_CURRENCIES)
        self.assertIn("dùng USD", tools.create_payment(100000, "RUB", "x", "vi")["text"])

class Fx(unittest.TestCase):
    def test_decimal_rounding_is_half_up_and_exact(self):
        self.assertEqual(fx.quote(1, "USD")["value"], "0.00")                  # 1 VND at 25,000 VND/USD
        self.assertEqual(fx.quote(125, "USD")["value"], "0.01")                # 0.005 rounds half up
        self.assertEqual(fx.quote(215000, "USD")["value"], "8.60")
        self.assertIsInstance(fx.quote(100000, "EUR")["value"], str)           # money is returned as an exact string
    def test_quote(self):
        q = fx.quote(250000, "USD"); self.assertEqual(q["value"], "10.00")
        self.assertEqual(fx.quote(250000, "JPY")["value"], "1500")            # zero-decimal currency

class Flow(unittest.TestCase):
    def test_full_mock_lifecycle(self):
        pp, tools, ag = make_agent()
        r = ag.handle("3 x 45k + 80k, pay in USD")
        self.assertIn("order", r); oid = r["order"]["id"]
        self.assertEqual(r["order"]["amount_vnd"], 215000); self.assertEqual(r["order"]["value"], "8.60")
        self.assertIn("CREATED", ag.handle("status")["reply"])
        self.assertIn("approve", ag.handle("confirm payment")["reply"].lower())   # cannot capture before approval
        pp.mock_approve(oid)
        self.assertIn("COMPLETED", ag.handle("confirm payment")["reply"])
        self.assertIn("RECEIPT", ag.handle("receipt")["reply"])
    def test_languages(self):
        _, _, ag = make_agent()
        self.assertIn("越南盾", ag.handle("账单 450,000 越南盾,用美元付")["reply"])
        self.assertIn("Đã tạo", ag.handle("tổng 1,2 triệu, thanh toán bằng EUR")["reply"])
        self.assertIn("EUR", ag.handle("tổng 1,2 triệu, thanh toán bằng EUR")["reply"])
    def test_quote_only_and_options(self):
        _, _, ag = make_agent()
        r = ag.handle("how much is 450k in USD?"); self.assertIn("quote", r); self.assertNotIn("order", r)
        self.assertIn("VietQR", ag.handle("how can I pay in Vietnam?")["reply"])
    def test_limits_and_fallbacks(self):
        _, _, ag = make_agent()
        self.assertIn("limit", ag.handle("pay 900,000,000 VND")["reply"].lower())
        r = ag.handle("pay 500k in RUB"); self.assertIn("USD", r["reply"])      # unsupported -> USD
        self.assertIn("VND", ag.handle("blah blah")["reply"])                    # help text
    def test_unknown_order(self):
        _, _, ag = make_agent()
        r = ag.handle("status of MOCK-DEADBEEF1234")
        self.assertEqual(r["brain"], "error"); self.assertIn("unknown", r["reply"].lower())

if __name__ == "__main__":
    unittest.main()
