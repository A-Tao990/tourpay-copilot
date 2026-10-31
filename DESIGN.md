# Design

Flow: message -> `Agent._understand` (rules first; the model is asked only when rules find nothing, and its answer is validated) -> deterministic tool -> localized reply.

Tools: `quote_price`, `create_payment` (PayPal Orders v2 `intent=CAPTURE`, `user_action=PAY_NOW`), `check_payment`, `capture_payment` (only when status is APPROVED), `refund_payment` (only for COMPLETED payments with a capture id), `receipt`, `payment_options`, `summary` (merchant reconciliation, Vietnam time), `export_csv`.

Money: all conversions use `Decimal` (round half up; whole numbers for JPY/HUF/TWD) and are returned as exact strings; amounts below one payable unit are refused before calling PayPal; a demo limit caps each order.

PayPal: OAuth2 client-credentials, `PayPal-Request-Id` for idempotency, the return URL carries `token=<order id>` and triggers capture; refunds use `/v2/payments/captures/{id}/refund`. A refunded order stays REFUNDED even though PayPal still reports the order as COMPLETED.

Safeguards: unsupported currencies fall back to USD with a visible warning; the model cannot create amounts (it can only suggest an integer VND total that the code validates against the limits); every model error falls back to the rules brain; mock mode is clearly labelled; no secrets in the repo (`.env` is ignored); the server listens on localhost only.

Verified against the real PayPal sandbox: order creation, buyer approval, automatic capture, refund. Verified live with Gemini (free tier).

Next steps: native-speaker review of the Vietnamese strings; webhooks instead of polling; QR deep links (VietQR); multi-merchant accounts with authentication; a "pay with Claude" brain once a paid key is available.
