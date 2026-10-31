# Design

Flow: message -> `Agent._understand` (rules first; model only if rules find nothing) -> deterministic tool -> localized reply.

Tools: `quote_price`, `create_payment` (PayPal Orders v2 `intent=CAPTURE`, `user_action=PAY_NOW`), `check_payment`, `capture_payment` (only when status is APPROVED), `receipt`, `payment_options`.

PayPal: OAuth2 client-credentials, `PayPal-Request-Id` for idempotency, return URL carries `token=<order id>` and triggers capture.

Safeguards: demo limit per order; unsupported currencies fall back to USD with a visible warning; the model cannot create amounts (it can only suggest an integer VND total that the code validates); mock mode is clearly labelled; no secrets in the repo (`.env` is ignored).

Next steps: native-speaker review of Vietnamese; real sandbox verification; merchant dashboard (daily reconciliation); QR deep links; webhook handling instead of polling.
