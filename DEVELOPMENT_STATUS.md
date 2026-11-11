# AgentShield development status

**Reviewed:** 2026-11-10. This is a local hackathon prototype, not a production fraud platform.

## What is implemented

- Next.js interface for a transaction ledger, investigation records, relationship graph, payments view, and relational audit log.
- FastAPI backend with SQLite, deterministic heuristic scoring, scikit-learn Isolation Forest, NetworkX graph traversal, and agent-shaped workflow records.
- PayPal Sandbox adapter code and a simulator. The seeded payment records are local simulations and are not PayPal transactions.
- Human-entered approval and refund reasons; uncaptured payment records remain ineligible for refunds.

## What this review verified

- Source inspection found the seeded case `CASE_FRAUD_905` linked to `TXN_FRAUD_905` and `PAY_OP_905`; that local payment record has no capture ID and is ineligible for refund.
- Case detail reads now build timeline entries from stored executions, approval records, and local payment-operation records instead of generating a fixed sequence of completed stages.
- Evidence confidence, source reliability, corroboration count, graph-edge confidence, and risk contribution are no longer fabricated as defaults in the reviewed paths.
- Payment and case screens request a reviewer name and reason before enabling refund-related controls.
- No financial mutation, case approval/rejection, attack, seed, reset, or deletion was performed during this review.

The backend was not running at review time, so live API behavior and current PayPal connectivity could not be checked. Earlier local observations of OAuth connectivity are historical and do not establish that a Sandbox order, capture, or refund was processed.

## Important limitations

- API caller authentication and authorization are not implemented. Keep the backend bound to loopback; reviewer names are self-reported.
- PayPal Sandbox order/capture/refund end-to-end behavior has not been verified in this review. Demo ledger rows are simulated.
- Gemini/OpenAI summaries are optional. Configure and verify an actual provider request before claiming generative AI is active. The risk score remains heuristic/ML output, not a calibrated fraud probability.
- The audit log is a normal SQLite table, not immutable or cryptographically chained.
- No performance benchmark was run. Do not claim production scale based on the demo dataset.

## Next work, in priority order

1. Verify one complete PayPal Sandbox order and capture flow with disposable Sandbox buyer/merchant accounts; document exactly which API calls succeeded. Keep refunds out of the judge demo unless a separate disposable transaction and explicit approval are used.
2. Add API authentication and role-based authorization before any shared or hosted deployment.
3. Configure an AI provider if desired; verify that generated summaries cite only supplied evidence and preserve deterministic scoring and human controls.
4. Rehearse a clean install, record a public YouTube demo under three minutes, and ensure the public repository has its license and setup instructions.
5. Measure performance only after selecting realistic larger datasets and recording reproducible methods/results.
