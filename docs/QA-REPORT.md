# QA report: TourPay Copilot (own product, self-QA)

This is QA I ran on my **own** project, not a client product. It found one high-severity bug (QA-001, now fixed on `main` via PR #1) and four smaller issues that are still open and listed honestly below. Done with AI coding agents (Codex, Claude Code); the findings were reproduced by running the app, not only by reading code.

| Field | Value |
|---|---|
| Version tested | the commit before PR #1 (29 offline tests passing) |
| Date | 2026-11-01 |
| Environment | Python 3.12, Linux, localhost, **mock PayPal + rules brain** (no keys, no model, no real or sandbox money) |
| Not tested | real PayPal sandbox for the fix, the Gemini/Claude model paths, browser UI rendering, mobile layout, accessibility |

## QA-001 — HIGH — Messages that *mention* refund issued an immediate refund (FIXED)
- **Steps:** (1) `100k pay in USD`; (2) approve in the mock page → COMPLETED; (3) send `please don't refund`.
- **Actual (before):** the order was refunded. Also reproduced with `不要退款`, `no refund, thanks`, and `what is your refund policy?` (4 of 4).
- **Cause:** a keyword match on `refund` / `退款` / `hoàn tiền` treated any message containing the word as a command, with no negation or question check and no confirmation step.
- **Fix (PR #1, merged):** a clause-level guard classifies the keyword's clause as negated, question or command (en/zh/vi). A refund request now only *proposes* (order, amount, "nothing refunded yet"); the refund runs only after an explicit confirmation for the **same order** within 120 s. The model path cannot bypass this; the same-root capture misfire (`don't confirm payment`) is fixed too.
- **Evidence:** 46 offline tests (17 new in `tests/test_refund_guard.py`) including a spy PayPal client that counts calls and asserts order state is unchanged; mutation checks confirm the new tests fail if the guard is removed.
- **Not verified:** the full two-step refund against the real PayPal sandbox, and with a real model. The demo video still shows the earlier one-step refund.

## QA-002 — MEDIUM — Mixed-intent message silently drops the new amount (open)
`50k, pay in usd, refund` after any order is treated as a refund of the previous order; the 50k request is ignored with no mention. Expected: create the order, refund, or ask which.

## QA-003 — LOW (mock mode only) — Order id reflected unescaped on the mock approval page (open)
`GET /mock/approve?id=<b>x</b>'` inserts the id into HTML without escaping. Limited impact (mock mode, localhost-only server with Host check); fix with `html.escape` / `quote`.

## QA-004 — LOW (docs) — No-key quick start cannot read Chinese number words (open)
`三杯咖啡每杯四万五，付 SGD` returns generic help without a model key. The README lists Chinese numerals as a feature, but they need AI mode; one README line or a clearer reply would avoid confusion.

## QA-005 — LOW / product decision — Dashboard shows no gross after refunds (open)
After 4 orders completed then refunded the summary shows an empty "charged" and 15.52 USD "refunded", so gross vs net cannot be reconciled from the summary (CSV rows keep both). Question for the product owner: show gross, refunded and net separately?

## Checks that passed (not bugs)
Hostile Host header → 403; malformed JSON → 400; unknown mock order → 404; unsupported currency (CNY) → clear message listing the 12 supported ones; 1 VND → "too small to charge"; confirming before approval is refused; double refund is refused; zh/vi replies work (`3 x 45k + 80k` → 215,000 VND = 8.33 USD in all three languages); CSV rows match order states.
