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
```bash
git clone <this repo> && cd tourpay-copilot
python3 -m unittest discover -s tests      # 14 tests, offline
python3 -m tourpay                          # open http://localhost:8080
```
Without credentials the app runs in **mock PayPal + built-in rules** mode (clearly labelled in the page header); on the page, send `3 x 45k + 80k, pay in USD`, open the mock approval link, then say `confirm payment`. With your own PayPal **sandbox** credentials and an optional Gemini key (see below) it runs against the real sandbox and a real model.

## Run it (Python 3.9+, standard library only)
```bash
python3 -m unittest discover -s tests        # 10 tests
python3 -m tourpay                           # http://localhost:8080, mock PayPal, rules brain
```
Real PayPal sandbox: create a sandbox REST app at developer.paypal.com, copy `.env.example` to `.env`, fill `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`, restart. The header badge shows `PayPal: SANDBOX`.
AI brain (optional, priority in this order): `ANTHROPIC_API_KEY` (Claude, default model `claude-haiku-5-5`, paid API), `GEMINI_API_KEY` (free tier available), or `LLM_BASE_URL` for any OpenAI-compatible server. The model is only called when the built-in rules cannot parse a message, so a demo costs cents.

## Demo captions (only for recording the demo video)
Set `DEMO_CAPTIONS=1` to enable a caption bar that a script can drive through `POST /api/caption`. It is off by default and has no effect otherwise.

## What is tested, and what is not (honest status)
- Tested (offline, deterministic): amount parsing in zh/en/vi, FX maths including zero-decimal currencies, the full order lifecycle against a built-in **mock** PayPal, multi-language replies, demo limits, unsupported-currency fallback.
- Run end-to-end over HTTP in mock mode.
- **Verified against the real PayPal sandbox (2026-10-31):** OAuth, order creation (`PAYER_ACTION_REQUIRED`), buyer approval on the sandbox checkout, automatic capture through the return URL, final status `COMPLETED` with a capture id, and a full refund (`REFUNDED`). `scripts/verify_sandbox.py` checks credentials without printing them.
- **Model-assisted path verified live with Gemini (free tier, 2026-10-31):** Chinese numerals, Vietnamese number words, English number words, pay-vs-quote intent and off-topic refusal; plus offline tests with a fake model, including bad/unsafe model output. Model names go stale (`gemini-2.5-flash` returned 404 for a new account), so `Gemini` tries fallback models on 404/429/503. **Not verified live:** the Claude and OpenAI-compatible HTTP calls (need a key); every model error falls back to the rules brain.
- Free-tier note: Google may use free-tier prompts to improve its models, so the app only sends the one-line bill message, never personal data.
- Vietnamese strings were written with AI help and **need review by a native speaker**.
- Supported currency list is a conservative set; verify against PayPal's current docs.

## Limits and legal notes
Sandbox only: no real money moves. Rates are mid-market; PayPal applies its own spread and fees. Cryptocurrency is not legal tender for payments in Vietnam, and this project does not handle crypto. General information only, not legal or financial advice.

## Layout
`tourpay/parse.py` (zh/en/vi amounts, currency, language) · `fx.py` · `paypal_client.py` (Orders v2 + mock) · `tools.py` · `agent.py` · `server.py` · `static/index.html` · `tests/`
