# PayPal AI Hackathon submission draft

## Project title

AgentShield — evidence-led fraud investigation for PayPal payments

## Short description

AgentShield helps payment-risk teams move from an isolated alert to a reviewable investigation. It combines deterministic risk factors, an Isolation Forest anomaly signal, and a NetworkX relationship graph to connect suspicious activity across accounts and devices. Its investigation workflow brings supporting records and alternative explanations into one dossier, while payment eligibility and human approval remain explicit safeguards. PayPal Sandbox OAuth and API adapters are present; the seeded ledger is clearly labeled as simulation data, and the demo does not claim those records were processed by PayPal.

## What is different

AgentShield is designed around evidence traceability: graph relationships point to stored transaction and identity records, and investigation steps surface evidence with source identifiers. The risk score comes from deterministic factors; optional generative AI can summarize evidence but does not set risk or authorize financial actions. Uncaptured payments remain ineligible for refunds. This is an analyst review tool, not autonomous money movement.

## Tools used

- **PayPal Developer Platform:** The application includes adapters for Orders v2, Captures v2, and Refunds against Sandbox. OAuth connectivity and live Sandbox order creation (`PAY_4755283F3153`, Sandbox ID `3A365272FB586030R`, status `CREATED — Awaiting Buyer`) have been verified, while buyer checkout, capture, and refund remain unperformed and unverified. Pre-seeded demo records (`PAY_OP_901`–`PAY_OP_906`) are local simulations (`SIMULATED SANDBOX`). The demo demonstrates verified order creation, status visibility, and human-in-the-loop settlement safeguards.
- **AI/ML:** scikit-learn Isolation Forest contributes anomaly signals. The application supports optional Gemini/OpenAI evidence summaries; deterministic scoring remains the risk-score source. Provider status must be demonstrated during recording: do not describe generative AI as active unless an actual summary request succeeds.
- **Other tools:** FastAPI, SQLAlchemy, NetworkX, Next.js, React, AG Grid, and React Flow.

## Suggested three-minute demo

1. **0:00–0:20 — The problem:** Explain that fraud review needs to connect weak signals without allowing an AI to approve or refund a payment.
2. **0:20–0:50 — Transaction triage:** Open the transaction ledger, search a suspicious transaction, and show its deterministic score and contributing factors.
3. **0:50–1:20 — Network context:** Open the fraud graph, select the transaction, and show the related account/device/payment-identity evidence and edge details.
4. **1:20–2:05 — Investigation dossier:** Show the evidence list, alternative explanations, agent timeline, and the linked transaction/device identifiers.
5. **2:05–2:35 — Payment safety & Sandbox order:** Show the payment operations workspace, distinguishing the verified Sandbox order `PAY_4755283F3153` (`CREATED — Awaiting Buyer`) from pre-seeded demo simulations (`SIMULATED SANDBOX`). Show the uncaptured `CASE_FRAUD_905` / `PAY_OP_905` record marked `State Mismatch (Blocked)` with refund disabled. State clearly that buyer checkout, capture, and refund remain unperformed and unverified.
6. **2:35–2:55 — Audit and close:** Show the chronological relational audit page (`/audit`) and summarize the value: faster evidence review with a human-controlled financial decision.

## Before submission (Presenter Checklist to Complete)

- [ ] **Public Git repository & GitHub URL:** Push this codebase to your team's public GitHub repository (the MIT `LICENSE` is already included).
- [ ] **Demo video recording & upload:** Record a sub-3-minute video adhering to `DEMO_SCRIPT.md`, upload as Public or Unlisted (YouTube / Vimeo / Loom), and add the URL to the submission form.
- [ ] **PayPal Developer Sandbox credentials:** If judges will evaluate the code themselves, instruct them to insert their own Sandbox Client ID / Secret into `backend/.env`. (Never commit or share your private client credentials).
- [ ] **AI Provider demonstration (optional):** If you wish to demonstrate generative AI summaries during the demo video, ensure `GEMINI_API_KEY` or `OPENAI_API_KEY` is set and verify an actual summary request succeeds beforehand. Otherwise, present the 100% functional deterministic fallback.
- [ ] **Devpost submission form:** Fill out the project overview, paste repository link, video link, and list team members.

## Known limitations (disclose to judges)

1. **Mutation authentication guard & loopback confinement.** Mutating endpoints enforce `AGENTSHIELD_API_KEY` when configured; unauthenticated mutations from non-loopback network callers are rejected with HTTP 403. Reviewer names entered during approval are self-reported for local demo workflow convenience. Read-only demo endpoints remain open for frictionless inspection.
2. **Demo payment records vs Live Sandbox order.** The five demo payment records (`PAY_OP_901`–`PAY_OP_906`) are pre-seeded local simulations (`SIMULATED SANDBOX`). A live PayPal Sandbox order (`PAY_4755283F3153`, Sandbox ID `3A365272FB586030R`) was verified in `CREATED — Awaiting Buyer` status via `POST /v2/checkout/orders`; buyer approval, capture, and refund remain unperformed and unverified.
3. **Legacy record inconsistency (`CASE_FRAUD_905`).** The pre-seeded demo dataset includes an uncaptured authorization (`PAY_OP_905`) with a legacy `APPROVED` label while the case is `PENDING_REVIEW`. The application detects and flags this inconsistency (`approval_integrity_valid: false`), surfaces warnings across the UI, and server guards strictly reject any payment action on it.
4. **Audit trail is relational, not cryptographic.** The audit log is a standard SQLite table with chronological state-transition records. It is not hash-chained or immutably stored.
5. **AI provider status must be demonstrated.** Deterministic heuristics and scikit-learn Isolation Forest signals are implemented. Describe Gemini/OpenAI summaries as active only after observing a successful request; a configured key alone is not proof.
