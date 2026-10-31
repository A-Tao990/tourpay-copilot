# TourPay Copilot

_Built by John together with AI coding agents (Claude Code and Codex). I set the goals, made the judgment calls and verified the results; the agents wrote and ran much of the code._

An AI payment assistant for tourists in Vietnam, built on the **PayPal Orders API (sandbox)**.

**The problem.** Vietnamese shops price in Vietnamese dong (VND), but PayPal cannot settle in VND. A foreign tourist who wants to pay with PayPal needs someone to add up the bill, convert it, create a payment link and reconcile it, often across a language barrier.

**What it does.** Tell it, in Chinese, English or Vietnamese, something like `3 x 45k + 80k, pay in USD`. It sums the items, converts at a live mid-market rate, creates a PayPal sandbox order, returns the payer link, checks the order, captures the payment once the payer has approved it, and produces a receipt in the payer's language. It can refund a completed payment, shows a **merchant reconciliation dashboard** (today in Vietnam time, all-time, by currency) with CSV export, and answers "how can I pay in Vietnam?" with honest, general information.

## Design principle: the model never touches money
Language models are good at understanding messy requests and bad at arithmetic. So:
- The **AI brain** only extracts intent, amount, currency and order id from a message, and answers small talk.
- Every **amount, rate, PayPal call and receipt** comes from deterministic code (`tourpay/tools.py`, `fx.py`, `paypal_client.py`) with tests.
- With no API key it runs entirely on built-in rules, so the demo never depends on a network model.

## Quick start for judges (no accounts or keys needed)
Requires Python 3.9+ and nothing else (standard library only).
```bash
git clone https://github.com/A-Tao990/tourpay-copilot && cd tourpay-copilot
python3 -m unittest discover -s tests      # 29 tests, offline
python3 -m tourpay                          # open http://localhost:8080
```
Without credentials the app runs in **mock PayPal + built-in rules** mode (clearly labelled in the page header). On the page, send `3 x 45k + 80k, pay in USD`, open the mock approval link, then say `confirm payment`, `status`, `refund`, or look at the merchant dashboard.

## Run it against the real PayPal sandbox and a real model (optional)
No test credentials are shipped (they would be secrets); you create your own free ones in a few minutes:
1. At developer.paypal.com open **Apps & Credentials → Sandbox** and use (or create) a REST app; copy its Client ID and Secret.
2. `cp .env.example .env`, fill `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`, restart. The header badge shows `PayPal: SANDBOX`. `python3 scripts/verify_sandbox.py` checks the credentials without printing them.
3. Click **Pay with PayPal (sandbox)** on an order and log in with a sandbox *personal* (buyer) account from **Testing tools → Sandbox accounts**; the app captures automatically when you return.
4. AI brain (optional, priority in this order): `GEMINI_API_KEY` (free tier, used in the demo video), `ANTHROPIC_API_KEY` (Claude, default model `claude-haiku-5-5`), or `LLM_BASE_URL` for any OpenAI-compatible server.

## AI tools used, and how
- **In the product (runtime): Google Gemini** (`gemini-3.5-flash-lite`, free tier, with fallbacks). It reads messy bills the rules cannot (Chinese numerals such as 三杯咖啡每杯四万五, Vietnamese number words), decides pay-vs-quote intent and answers small talk. Its output is validated and it never computes or sees money. Optional alternatives: Claude (Anthropic API) or any OpenAI-compatible server (neither verified live).
- **PayPal developer platform:** Orders v2 (create, get, capture) and Payments v2 refunds, sandbox environment.
- **In development: Claude Code and Codex** wrote and ran much of the code and tests under my direction.

## New work during the hackathon
The whole project was created during the Submission Period (first commit 2026-10-31; see the git history). No prior code was reused.

## Demo captions (only for recording the demo video)
Set `DEMO_CAPTIONS=1` to enable a caption bar that a script can drive through `POST /api/caption`. It is off by default and has no effect otherwise.

## What is tested, and what is not (honest status)
- Tested (offline, deterministic, 29 tests): amount parsing in zh/en/vi, FX maths with `Decimal` (exact, round half up, zero-decimal currencies), hostile inputs (dates, phone numbers, negatives), localhost-only request guards (Host/Origin checks), the full order lifecycle against a built-in **mock** PayPal, refunds, the merchant summary and CSV, multi-language replies, demo limits, a minimum-amount guard, unsupported-currency fallback, and the **real HTTP server** on an ephemeral port (full flow, 404s, oversized input).
- **Verified against the real PayPal sandbox (2026-10-31):** OAuth, order creation (`PAYER_ACTION_REQUIRED`), buyer approval on the sandbox checkout, automatic capture through the return URL, final status `COMPLETED` with a capture id, and a full refund (`REFUNDED`). `scripts/verify_sandbox.py` checks credentials without printing them.
- **Model-assisted path verified live with Gemini (free tier, 2026-10-31):** Chinese numerals, Vietnamese number words, English number words, pay-vs-quote intent and off-topic refusal; plus offline tests with a fake model, including bad/unsafe model output. Model names go stale (`gemini-2.5-flash` returned 404 for a new account), so `Gemini` tries fallback models on 404/429/503. **Not verified live:** the Claude and OpenAI-compatible HTTP calls (need a key); every model error falls back to the rules brain.
- Free-tier note: Google may use free-tier prompts to improve its models, so the app only sends the one-line bill message, never personal data.
- Vietnamese strings were written with AI help and **need review by a native speaker**.
- The 12 supported currencies (AUD, CAD, EUR, GBP, HKD, JPY, MYR, PHP, SGD, THB, TWD, USD) were each probed against the real sandbox on 2026-10-31; CNY was rejected by PayPal (`CURRENCY_NOT_SUPPORTED`) and is therefore not offered.

## Limits and legal notes
Single-merchant demo: the agent remembers the last order per process, there is no authentication, and the server listens on localhost only. Amount parsing is rule-based with a model fallback; the app always echoes the interpreted VND amount and the converted value before the payer approves.

Sandbox only: no real money moves. Rates are mid-market; PayPal applies its own spread and fees. Cryptocurrency is not legal tender for payments in Vietnam, and this project does not handle crypto. General information only, not legal or financial advice.

## Layout
`tourpay/parse.py` (zh/en/vi amounts, currency, language) · `fx.py` (Decimal FX) · `paypal_client.py` (Orders v2 + refunds + mock) · `tools.py` · `agent.py` (rules first, optional model) · `i18n.py` · `server.py` · `static/index.html` · `scripts/verify_sandbox.py` · `tests/`
