"""Regression tests for QA-001: messages that merely MENTION refund/capture must not move money, and a refund needs a
two-step explicit confirmation. Every test counts calls that reach the (mock) PayPal client - asserting on the reply text
alone would not prove that no refund/capture happened. All offline: mock PayPal, fake model, no network, no keys."""
import os, sys, tempfile, threading, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tourpay import fx
from tourpay.agent import Agent, REFUND_CONFIRM_SECS
from tourpay.paypal_client import PayPal
from tourpay.tools import Store, Tools

fx.rates = lambda: ({"USD": 1.0, "VND": 25000.0, "EUR": 0.9, "JPY": 150.0, "CNY": 7.0}, "test")   # same table as test_core (shared module-level patch)


class SpyPayPal(PayPal):
    """Mock PayPal that records every refund/capture call that reaches it."""
    def __init__(self):
        super().__init__("", "")
        self.refund_calls, self.capture_calls = [], []
    def refund(self, capture_id):
        self.refund_calls.append(capture_id); return super().refund(capture_id)
    def capture(self, order_id):
        self.capture_calls.append(order_id); return super().capture(order_id)


class FakeLLM:
    """Stands in for the model. `out` is the JSON it 'returns'; `prompts` records whether it was consulted at all."""
    name = "fake"
    def __init__(self, out): self.out, self.prompts = out, []
    def complete(self, prompt): self.prompts.append(prompt); return self.out


class Clock:
    def __init__(self): self.now = 1000.0
    def __call__(self): return self.now


def build(llm=None):
    pp = SpyPayPal(); clock = Clock()
    tools = Tools(pp, Store(os.path.join(tempfile.mkdtemp(), "o.json")))
    return pp, tools, Agent(tools, llm, clock=clock), clock

def completed_order(pp, ag, text="100k pay in USD"):
    oid = ag.handle(text)["order"]["id"]
    pp.mock_approve(oid); ag.handle("confirm payment")
    assert pp.get_order(oid)["status"] == "COMPLETED"
    return oid


class NotACommand(unittest.TestCase):
    """Negations and questions (en/zh/vi), judged on a COMPLETED order: no PayPal refund call, order untouched."""
    MESSAGES = [
        "please don't refund", "no refund, thanks", "do not refund it", "never mind the refund", "cancel the refund",
        "hold off on the refund", "refund is not needed",
        "what is your refund policy?", "how long does a refund take?", "if I refund, what happens?", "Do I get a refund?",
        "不要退款", "先别退款", "不用退款了", "取消退款", "退款政策是什么", "能退款吗？", "如果退款会怎样",
        "đừng hoàn tiền", "không cần hoàn tiền", "hủy hoàn tiền", "chính sách hoàn tiền thế nào?", "nếu hoàn tiền thì sao?",
    ]
    def test_no_refund_call_and_no_pending_confirmation(self):
        for msg in self.MESSAGES:
            with self.subTest(msg=msg):
                pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
                r = ag.handle(msg)
                self.assertEqual(pp.refund_calls, [], r["reply"])
                self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")
                self.assertIsNone(ag.pending_refund)                       # not even a proposal
                ag.handle("confirm refund"); ag.handle("yes")               # a later 'yes' has nothing to confirm
                self.assertEqual(pp.refund_calls, [])
                self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")

    def test_replies_are_in_the_users_language(self):
        pp, tools, ag, _ = build(); completed_order(pp, ag)
        self.assertIn("没有退款", ag.handle("不要退款")["reply"])
        self.assertIn("Không", ag.handle("đừng hoàn tiền")["reply"])
        self.assertIn("Nothing was refunded", ag.handle("what is your refund policy?")["reply"])
        self.assertEqual(pp.refund_calls, [])

    def test_ordinary_queries_are_not_financial_actions(self):
        pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
        for msg in ["status", "status " + oid, "receipt", "how can I pay in Vietnam?", "how much is 450k in USD?", "状态", "trạng thái"]:
            ag.handle(msg)
        self.assertEqual((pp.refund_calls, ag.pending_refund), ([], None))
        self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")


class RefundNeedsConfirmation(unittest.TestCase):
    def test_explicit_request_only_proposes_then_confirm_refunds_once(self):
        for ask, yes, lang_marker in [("refund", "confirm refund", "NOTHING has been refunded"), ("请退款", "确认退款", "尚未退款"),
                                      ("hoàn tiền", "xác nhận hoàn tiền", "CHƯA hoàn tiền"), ("please refund order {oid}", "yes", "NOTHING"),
                                      ("I want a refund", "ok", "NOTHING"), ("你能帮我退款吗", "是的", "尚未退款")]:
            with self.subTest(ask=ask):
                pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
                r = ag.handle(ask.format(oid=oid))
                self.assertIn(lang_marker, r["reply"]); self.assertIn(oid, r["reply"]); self.assertIn("4.00 USD", r["reply"])
                self.assertEqual(pp.refund_calls, []); self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")
                done = ag.handle(yes)
                self.assertEqual(done["order"]["status"], "REFUNDED"); self.assertEqual(len(pp.refund_calls), 1)
                self.assertEqual(pp.refund_calls[0], tools.store.orders[oid]["capture_id"])
                ag.handle("yes"); ag.handle(yes)                                  # replays do nothing
                self.assertEqual(len(pp.refund_calls), 1)

    def test_cancel_or_anything_else_drops_the_proposal(self):
        for follow in ["no", "don't", "不要", "đừng", "status", "receipt", "what is your refund policy?", "blah", "50k pay in USD", "please wait"]:
            with self.subTest(follow=follow):
                pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
                ag.handle("refund"); ag.handle(follow)
                ag.handle("yes"); ag.handle("confirm refund")
                self.assertEqual(pp.refund_calls, [])
                self.assertEqual(tools.store.orders[oid]["status"], "COMPLETED")

    def test_no_pending_means_confirm_does_nothing(self):
        pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
        for msg in ["confirm refund", "yes", "ok", "确认退款", "xác nhận hoàn tiền", "confirm refund " + oid]:
            ag.handle(msg)
        self.assertEqual(pp.refund_calls, [])

    def test_confirmation_for_another_order_or_after_switching_does_not_reuse_old_proposal(self):
        pp, tools, ag, _ = build()
        a = completed_order(pp, ag, "100k pay in USD"); b = completed_order(pp, ag, "200k pay in USD")
        ag.handle("refund " + a)                                                  # proposal for A
        ag.handle("confirm refund " + b)                                          # names B: mismatch -> dropped, nothing refunded
        ag.handle("yes")
        self.assertEqual(pp.refund_calls, [])
        ag.handle("refund " + a); ag.handle("refund " + b)                        # A replaced by B
        ag.handle("confirm refund")
        self.assertEqual(pp.refund_calls, [tools.store.orders[b]["capture_id"]])
        self.assertEqual((tools.store.orders[a]["status"], tools.store.orders[b]["status"]), ("COMPLETED", "REFUNDED"))

    def test_confirmation_expires(self):
        pp, tools, ag, clock = build(); oid = completed_order(pp, ag)
        ag.handle("refund"); clock.now += REFUND_CONFIRM_SECS + 1
        r = ag.handle("confirm refund")
        self.assertEqual(pp.refund_calls, []); self.assertIn("Nothing was refunded", r["reply"])
        ag.handle("refund"); clock.now += REFUND_CONFIRM_SECS - 1                  # inside the window it still works
        ag.handle("confirm refund"); self.assertEqual(len(pp.refund_calls), 1)

    def test_not_yet_paid_order_is_never_proposed(self):
        pp, tools, ag, _ = build(); ag.handle("100k pay in USD")
        self.assertIn("cannot", ag.handle("refund")["reply"].lower()); self.assertIsNone(ag.pending_refund)
        ag.handle("confirm refund"); self.assertEqual(pp.refund_calls, [])


class ModelCannotBypass(unittest.TestCase):
    """The model may output intent=refund (even for a negated message, or naming another order). Still no refund."""
    REFUND = '{"intent":"refund","amount_vnd":null,"currency":"USD","order_id":"%s"}'

    def test_model_refund_intent_only_proposes(self):
        pp, tools, ag, _ = build(FakeLLM(self.REFUND % "null")); oid = completed_order(pp, ag)
        ag.llm = FakeLLM(self.REFUND % "null")
        r = ag.handle("hãy trả lại tiền cho khách")                                # no rules keyword -> model says refund
        self.assertEqual(r["brain"], "fake"); self.assertIn(oid, r["reply"])
        self.assertEqual(pp.refund_calls, []); self.assertIsNotNone(ag.pending_refund)
        n = len(ag.llm.prompts)
        ag.handle("again please, return the customer's money")                    # model says refund again: still a proposal
        self.assertEqual(pp.refund_calls, [])
        ag.handle("yes")                                                          # confirmation is decided before the model is asked
        self.assertEqual(len(pp.refund_calls), 1)

    def test_confirmation_never_consults_the_model(self):
        pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
        ag.handle("refund"); ag.llm = FakeLLM(self.REFUND % "null")
        ag.handle("confirm refund")
        self.assertEqual(ag.llm.prompts, []); self.assertEqual(len(pp.refund_calls), 1)

    def test_model_refund_intent_for_negated_or_question_message_is_blocked(self):
        for msg in ["no, keep the money, don't send it back", "不要把钱还给客人", "is it possible to send the money back?",
                    "đừng trả lại tiền cho khách"]:
            with self.subTest(msg=msg):
                pp, tools, ag, _ = build(); oid = completed_order(pp, ag)
                ag.llm = FakeLLM(self.REFUND % oid)
                r = ag.handle(msg)
                self.assertEqual(r["brain"], "fake"); self.assertIn(r.get("guard"), ("negated", "question"))
                self.assertIsNone(ag.pending_refund)
                ag.llm = None                                                      # follow-ups judged by rules only
                ag.handle("yes"); ag.handle("confirm refund")
                self.assertEqual(pp.refund_calls, [])

    def test_model_cannot_redirect_to_another_order(self):
        pp, tools, ag, _ = build()
        a = completed_order(pp, ag, "100k pay in USD"); b = completed_order(pp, ag, "200k pay in USD")   # last_order = B
        ag.llm = FakeLLM(self.REFUND % a)                                          # model names A; the user never typed it
        ag.handle("trả lại tiền cho khách đi"); ag.handle("yes")
        self.assertEqual(pp.refund_calls, [tools.store.orders[b]["capture_id"]])   # proposal was for the order the user is on
        self.assertEqual(tools.store.orders[a]["status"], "COMPLETED")


class CaptureSameRoot(unittest.TestCase):
    """capture had the same keyword-only trigger. Negated/question forms must not call PayPal capture."""
    def approved(self):
        pp, tools, ag, _ = build(); oid = ag.handle("100k pay in USD")["order"]["id"]; pp.mock_approve(oid)
        return pp, tools, ag, oid
    def test_negated_or_question_does_not_capture(self):
        for msg in ["don't confirm payment", "do not capture it", "not yet, don't collect", "what does capture mean?", "should I confirm payment?",
                    "不要确认收款", "还没付完", "已经付了吗？", "đừng xác nhận thanh toán", "xác nhận thanh toán là gì?"]:
            with self.subTest(msg=msg):
                pp, tools, ag, oid = self.approved()
                ag.handle(msg)
                self.assertEqual(pp.capture_calls, []); self.assertEqual(pp.get_order(oid)["status"], "APPROVED")
    def test_explicit_capture_still_works_in_all_languages(self):
        for msg in ["confirm payment", "capture", "确认收款", "xác nhận thanh toán"]:
            with self.subTest(msg=msg):
                pp, tools, ag, oid = self.approved()
                self.assertIn("COMPLETED", ag.handle(msg)["reply"]); self.assertEqual(pp.capture_calls, [oid])
    def test_model_capture_intent_is_gated_too(self):
        pp, tools, ag, oid = self.approved()
        ag.llm = FakeLLM('{"intent":"capture","order_id":null}')
        r = ag.handle("lass das bitte, nicht abbuchen? no")                        # negation marker 'no' + model says capture
        self.assertEqual(pp.capture_calls, []); self.assertEqual(r.get("guard"), "negated")


class HttpGuard(unittest.TestCase):
    def test_over_http_negation_does_not_refund_and_two_step_does(self):
        import json, urllib.request
        from http.server import ThreadingHTTPServer
        from tourpay.server import make_handler
        pp, tools, ag, _ = build()
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pp, tools, ag)); base = "http://127.0.0.1:%d" % srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        def chat(m):
            req = urllib.request.Request(base + "/api/chat", json.dumps({"message": m}).encode(), {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=10))
        try:
            oid = chat("100k pay in USD")["order"]["id"]
            urllib.request.urlopen(base + "/mock/confirm?id=" + oid, timeout=10).read()
            for m in ["please don't refund", "不要退款", "no refund, thanks", "what is your refund policy?"]: chat(m)
            self.assertEqual(pp.refund_calls, [])
            chat("refund"); self.assertEqual(pp.refund_calls, [])
            self.assertEqual(chat("confirm refund")["order"]["status"], "REFUNDED"); self.assertEqual(len(pp.refund_calls), 1)
        finally:
            srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
