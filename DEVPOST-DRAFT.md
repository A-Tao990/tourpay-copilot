# Devpost draft (edit before submitting; the submitter is the entrant)
**Name:** TourPay Copilot
**Tagline:** An AI payment assistant that lets a tourist in Vietnam pay a VND bill through PayPal, in Chinese, English or Vietnamese.
**Inspiration:** I live in Vietnam. Small shops price in dong, tourists arrive from everywhere, and PayPal cannot settle in dong. Closing the gap takes a calculator, a translator and a payment link.
**What it does:** (see README) understands a bill in three languages, converts at a live rate, creates and tracks a PayPal order, captures after approval, issues a receipt, refunds, gives the merchant a reconciliation dashboard with CSV export, and explains local payment options honestly.
**How we built it:** Python standard library only; PayPal Orders v2 (sandbox); deterministic tools for all money logic; optional LLM only for understanding; mock PayPal for tests; built with AI coding agents under my direction.
**Challenges:** keeping the language model away from arithmetic; VND is not a PayPal currency; zero-decimal currencies; honest labelling of what is verified.
**Accomplishments:** end-to-end order lifecycle with tests; works with no API key; trilingual replies.
**What we learned:** use models for language, code for money.
**What's next:** native-speaker review, webhooks instead of polling, QR deep links, multi-merchant support.
**Built with:** Python, PayPal Orders v2 API, open.er-api.com FX, optional Gemini / any OpenAI-compatible model.
