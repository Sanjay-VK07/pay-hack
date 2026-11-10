# PayPal AI Hackathon submission draft

## Project title

AgentShield — evidence-led fraud investigation for PayPal payments

## Short description

AgentShield helps payment-risk teams investigate suspicious transactions without letting an AI model make the financial decision. A deterministic risk engine and Isolation Forest anomaly detector flag unusual activity; NetworkX connects accounts, devices, payment identities, and network indicators; a multi-agent workflow assembles traceable evidence and alternative explanations. Investigators can inspect PayPal Sandbox capture eligibility and review an explicit approval step before a supported remediation flow.

## What is different

AgentShield treats AI as an investigation assistant. Its risk score comes from deterministic factors, and the graph links are grounded in stored transaction and identity records. Uncaptured payments stay ineligible for refunds. The interface shows the reasoning trail so an analyst can review evidence before taking action.

## Tools used

- **PayPal Developer Platform:** PayPal Orders, capture verification, and refund adapters target PayPal Sandbox when credentials are configured. A clearly labeled simulator supports local exploration without credentials.
- **AI/ML:** scikit-learn Isolation Forest contributes anomaly signals. The optional Gemini/OpenAI provider summarizes investigation evidence; deterministic scoring remains authoritative. The current local configuration has no Gemini/OpenAI key and no PayPal Sandbox credentials, so the current run uses the deterministic provider and simulator. Do not claim a live Sandbox transaction was demonstrated unless one has been verified separately.
- **Other tools:** FastAPI, SQLAlchemy, NetworkX, Next.js, React, AG Grid, and React Flow.

## Suggested three-minute demo

1. **0:00–0:20 — The problem:** Explain that fraud review needs to connect weak signals without allowing an AI to approve or refund a payment.
2. **0:20–0:50 — Transaction triage:** Open the transaction ledger, search a suspicious transaction, and show its deterministic score and contributing factors.
3. **0:50–1:20 — Network context:** Open the fraud graph, select the transaction, and show the related account/device/payment-identity evidence and edge details.
4. **1:20–2:05 — Investigation dossier:** Show the evidence list, alternative explanations, agent timeline, and the linked transaction/device identifiers.
5. **2:05–2:35 — Payment safety:** Show a captured payment’s eligibility metadata and the uncaptured `CASE_FRAUD_905` record marked ineligible. Do not execute a refund in the recording unless a separate PayPal Sandbox run is intentionally prepared and verified.
6. **2:35–2:55 — Audit and close:** Show the audit page and summarize the value: faster evidence review with a human-controlled financial decision.

## Before submission

- Publish the source repository with the MIT license in `LICENSE`.
- Configure a PayPal Developer Sandbox app and provide judges safe setup instructions. Never publish client secrets.
- Decide whether to configure an AI provider for the recorded run; keep the deterministic fallback clearly labeled.
- Record and publicly upload an English demo video under three minutes, with no third-party copyrighted music or unlicensed marks.
- Rehearse a fresh local install from the README and verify the exact run shown in the video.
- Do not expose the current unauthenticated API on a shared or public network.
