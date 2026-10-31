"""Tiny standard-library web server: chat UI, JSON API, PayPal return handler, and a mock PayPal approval page."""
import json, os, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import fx
from .agent import Agent, llm_from_env
from .paypal_client import PayPal
from .tools import Store, Tools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env_file():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))

def build(port):
    pp = PayPal(return_url="http://localhost:%d/paypal/return" % port, cancel_url="http://localhost:%d/paypal/cancel" % port)
    tools = Tools(pp, Store(os.path.join(ROOT, "data", "orders.json")))
    return pp, tools, Agent(tools, llm_from_env())

def make_handler(pp, tools, agent):
    demo = os.environ.get("DEMO_CAPTIONS") == "1"          # off by default; used only to record the demo video
    caption = {"text": ""}
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode()
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
            for k, v in (headers or {}).items(): self.send_header(k, v)
            self.end_headers(); self.wfile.write(b)
        def _redirect(self, url): self._send(302, b"", "text/plain", {"Location": url})
        def do_GET(self):
            u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
            if u.path == "/":
                with open(os.path.join(ROOT, "static", "index.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/health":
                _, src = fx.rates()
                return self._send(200, {"paypal": "MOCK (no credentials)" if pp.mock else "SANDBOX", "brain": agent.llm.name if agent.llm else "rules", "fx": src, "captions": demo})
            if u.path == "/api/caption": return self._send(200, {"text": caption["text"] if demo else ""})
            if u.path == "/api/orders": return self._send(200, tools.list_orders())
            if u.path == "/api/summary": return self._send(200, tools.summary())
            if u.path == "/api/export.csv":
                return self._send(200, tools.export_csv(), "text/csv; charset=utf-8", {"Content-Disposition": "attachment; filename=tourpay-orders.csv"})
            if u.path == "/paypal/return":
                oid = (q.get("token") or [""])[0]
                try: tools.capture_payment(oid)
                except Exception: pass
                return self._redirect("/?paid=" + urllib.parse.quote(oid))
            if u.path == "/paypal/cancel": return self._redirect("/?cancelled=1")
            if u.path == "/mock/approve" and pp.mock:
                oid = (q.get("id") or [""])[0]
                html = "<h2>Mock PayPal (sandbox simulation)</h2><p>Order %s</p><a href='/mock/confirm?id=%s'>Approve payment</a>" % (oid, oid)
                return self._send(200, html, "text/html; charset=utf-8")
            if u.path == "/mock/confirm" and pp.mock:
                oid = (q.get("id") or [""])[0]
                try: pp.mock_approve(oid)
                except KeyError: return self._send(404, {"error": "unknown order"})
                return self._redirect("/paypal/return?token=" + urllib.parse.quote(oid))
            return self._send(404, {"error": "not found"})
        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try: data = json.loads(self.rfile.read(n) or b"{}")
            except Exception: return self._send(400, {"error": "bad json"})
            if self.path == "/api/caption" and demo:
                caption["text"] = str(data.get("text", ""))[:300]; return self._send(200, {"ok": True})
            if self.path == "/api/chat":
                return self._send(200, agent.handle(str(data.get("message", ""))[:1000]))
            return self._send(404, {"error": "not found"})
    return H

def main():
    load_env_file()
    port = int(os.environ.get("PORT", "8080"))
    pp, tools, agent = build(port)
    print("TourPay Copilot on http://localhost:%d | PayPal: %s | brain: %s" % (port, "MOCK" if pp.mock else "SANDBOX", agent.llm.name if agent.llm else "rules"))
    ThreadingHTTPServer(("127.0.0.1", port), make_handler(pp, tools, agent)).serve_forever()

if __name__ == "__main__":
    main()
