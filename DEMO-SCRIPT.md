# Demo video (2:20, English captions burned into the picture, no voice)
The recorded demo follows this order (it is produced by a script that drives the browser; see the repository history):
1. (0:00) What it is and the problem: shops price in VND, PayPal cannot settle in VND.
2. (0:13) A Chinese bill in plain words ("3 coffees at 45,000, a cake at 80,000, pay in euros"): Gemini understands it, plain code computes 215,000 VND = about 7.5 EUR and creates a PayPal sandbox order.
3. (0:36) An English bill ("3 x 45k + 80k, pay in USD"), then "Pay with PayPal" opens the sandbox checkout.
4. (0:55) The payer approves; the app captures automatically and the order is COMPLETED.
5. (1:10) A Vietnamese quote, then the honest "how can I pay in Vietnam?" answer (crypto is not legal tender for payments in Vietnam).
6. (1:45) Merchant dashboard (today's totals by currency, CSV export) and a real PayPal refund.
7. (2:10) Closing: open source (MIT), tests, runs with no keys in mock mode, repository address.
