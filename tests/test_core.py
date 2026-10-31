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
        self.assertIn("Refund issued", ag.handle("refund")["reply"])
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

class Fx(unittest.TestCase):
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
