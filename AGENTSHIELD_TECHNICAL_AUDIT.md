# AgentShield technical audit

**Review date:** 2026-11-10  
**Scope:** Source and local project review. The backend was stopped during this review; no live endpoint or PayPal transaction could be verified. This document reports observed implementation and limitations, not a production security certification.

## Executive summary

AgentShield is a local fraud-investigation prototype with a usable analyst workflow, deterministic heuristic scoring, Isolation Forest anomaly signals, NetworkX relationship analysis, and a PayPal Sandbox adapter alongside simulated demo records. Payment actions are intended to require human-entered details and eligibility checks.

It is not ready for public or production deployment: API routes lack caller authentication/authorization, PayPal transaction processing was not verified end-to-end in this review, and the audit log is not tamper-proof. The demo should label seeded payment data as simulated and describe AI/ML capabilities precisely.

## Findings by severity

### Critical — No API caller authentication or authorization

The API accepts requests without an authenticated user identity or role. Names entered into the UI are self-reported. If the API is reachable by an untrusted client, callers may attempt protected state-changing operations. Keep the service on `127.0.0.1`; do not host it publicly until authentication, authorization, and server-side role checks are implemented.

### High — PayPal integration not verified end-to-end

The source contains Sandbox adapter code, but the local seeded payment operations are simulated. At review time the backend was not running, so credentials, OAuth, Orders, Captures, Refunds, and live eligibility could not be probed. A connectivity/OAuth result alone does not prove an order or capture succeeded.

### Medium — Human identity is not verified

Approval and refund forms collect a reviewer name and reason. Those fields improve audit context but do not establish that the person is authorized. Enforce identity and roles on the server before using this outside a local demo.

### Medium — Audit history is mutable storage

Audit events are stored in SQLite. No hash chain, append-only storage, or independent retention control was verified.

### Medium — Scores and graph flags are heuristic

Risk scores are deterministic rule/ML outputs and are not calibrated fraud probabilities. Shared device, payment identity, and IP records are local associations. They are investigation signals, not proof of fraud or account authorization. The UI should not imply a confidence percentage unless it is calibrated and supported by validation data.

### Low — Performance and scale are unmeasured

No large-dataset graph, query, memory, or response-time benchmark was run. The demo dataset cannot support a production-scale performance claim.

## Evidence and safe actions

- Source review found `CASE_FRAUD_905` linked to `TXN_FRAUD_905` and local `PAY_OP_905`; the seeded operation has no capture ID and is marked uncaptured/ineligible.
- Case-detail timeline output is based on stored execution, approval, and local payment-operation records; it must not be described as proof of a completed PayPal call.
- The local graph describes database associations and configured demo rules. No live IP reputation or independent device-hardware check is established by those records.
- No refund, capture, order creation, approval/rejection, attack, database seed/reset, or deletion was performed as part of this review.
- No live API check was possible because the backend was stopped. No performance benchmark was run.

## Submission readiness

The project can be presented as a local prototype if the demo clearly distinguishes simulated records from PayPal Sandbox activity and discloses the limitations above. Before submission, confirm the public repository has a license and setup instructions, verify the exact demo from a clean install, upload a public video under three minutes, and show a real Sandbox flow only after separately verifying it with disposable Sandbox accounts. Do not expose the current unauthenticated API publicly.
