#!/usr/bin/env python3
"""Verify PayPal SANDBOX credentials without printing them: OAuth token, then create (not capture) a 1.00 USD test order."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tourpay.server import load_env_file
from tourpay.paypal_client import PayPal, PayPalError

load_env_file()
pp = PayPal()
if pp.mock:
    sys.exit("No PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET found in .env (still mock mode).")
if "api-m.paypal.com" in pp.base and "sandbox" not in pp.base:
    sys.exit("Refusing to run against a non-sandbox endpoint.")
try:
    pp._token()
    print("OK  OAuth token obtained from the sandbox (credentials are valid; nothing printed).")
    o = pp.create_order("1.00", "USD", "TourPay Copilot sandbox verification", "verify-" + os.urandom(4).hex())
    print("OK  Test order created:", o["id"], o["status"])
    print("    Approval link present:", bool(o["approve_url"]))
except PayPalError as e:
    msg = str(e)
    for secret in (pp.client_id, pp.secret):
        if secret: msg = msg.replace(secret, "***")
    sys.exit("FAILED: " + msg)
