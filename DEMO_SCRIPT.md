# AgentShield — 3-Minute Hackathon Demo Video Script

**Target Duration:** 2:35–2:50 (Strictly under 3:00)  
**Mode:** Read-only navigation on local loopback (`http://localhost:3000`).  
**Rules:** Do not click destructive demo controls, do not approve/reject cases during recording, and do not execute captures or refunds.

---

### 0:00–0:22 — The Problem & Overview

**Screen:** [Dashboard (`/dashboard`)](http://localhost:3000/dashboard)

**Action:** Hover over KPI metric cards (Total Analyzed, High-Risk Anomalies, Human Review Queue).

**Narration:**  
> “When payment fraud strikes, risk analysts don’t just need an alert—they need context, evidence, and clear boundaries on remediation. Autonomous systems that trigger financial actions without human oversight create massive operational risk.  
> AgentShield is an explainable payment fraud investigation workbench built for PayPal Sandbox. It combines deterministic risk scoring, relationship-graph clustering, and an evidence-backed dossier to give investigators total clarity before any payment action is authorized.”

---

### 0:22–0:52 — Transaction Triage & Heuristic Risk Signals

**Screen:** [Transactions (`/transactions`)](http://localhost:3000/transactions)

**Action:** Click on `TXN_FRAUD_901` ($2,450.00 USD, Critical Threat). Open the right-hand forensic intelligence drawer. Show the contributing risk factors (Emulator detection, Proxy IP, Shared Device).

**Narration:**  
> “On the Transactions workspace, every incoming payment is evaluated. Rather than relying on a black-box LLM to determine financial risk, AgentShield uses a deterministic heuristic engine coupled with an Isolation Forest anomaly detector.  
> For transaction 901, the system flags an Android emulator runtime, an anonymizing proxy exit node, and a shared device fingerprint with 100% mathematical explainability.”

---

### 0:52–1:25 — Syndicate Graph Intelligence

**Screen:** [Fraud Networks (`/fraud-networks`)](http://localhost:3000/fraud-networks)

**Action:** Select cluster `CLUSTER_001` or node `TXN_FRAUD_901`. Click `Fit View` and inspect connected accounts and shared credit cards.

**Narration:**  
> “Single transactions often conceal organized rings. AgentShield’s relationship graph maps connected entities across accounts, devices, and payment credentials using NetworkX.  
> Reviewers can visually trace credential stuffing and multi-account velocity collisions, inspecting underlying evidence IDs directly instead of guessing why a cluster was flagged.”

---

### 1:25–2:00 — Investigation Dossier & Human Approval Gate

**Screen:** [Investigations (`/investigations`)](http://localhost:3000/investigations)

**Action:** Open `CASE_FRAUD_901`. Scroll through the Autonomous Agent Reasoning Timeline, evidence cards with source corroboration, and highlight the **Human Review Gate**. Then briefly click `CASE_FRAUD_905` to show the **State Integrity Alert** banner.

**Narration:**  
> “In the Investigation Workspace, multi-agent findings are synthesized into an audit-ready dossier. Every evidence record includes source sensors, corroboration counts, and alternative explanations.  
> Crucially, AgentShield enforces a strict Human-in-the-Loop approval gate: automated agents can recommend remediation, but cannot execute financial actions without an explicit, named reviewer sign-off.  
> On legacy case 905, our integrity engine detects a pre-existing state conflict and blocks all financial actions automatically.”

---

### 2:00–2:35 — PayPal Sandbox Integration & Settlement Safeguards

**Screen:** [Payments (`/payments`)](http://localhost:3000/payments)

**Action:** Scroll through the Payment Operations table. Point to `PAY_4755283F3153` labeled `LIVE PAYPAL SANDBOX` with status `CREATED · Awaiting Buyer`. Point to the pre-seeded simulation records labeled `SIMULATED SANDBOX (DEMO)`. Point to `PAY_OP_905` showing `Ineligible (No Capture)` and `State Mismatch (Blocked)`.

**Narration:**  
> “In Payment Operations, we clearly separate simulated demo data from real PayPal Sandbox API operations.  
> Pre-seeded records are explicitly tagged as local simulations. Meanwhile, order PAY_4755283F3153 was created live via PayPal Sandbox Orders v2 API in ‘Created — Awaiting Buyer’ status.  
> To remain truthful to judges: buyer checkout, capture, and refund remain unperformed and unverified in this demo. Uncaptured payments have no settled funds, and the server strictly blocks refund execution.”

---

### 2:35–2:55 — Chronological Audit Trail & Disclosures

**Screen:** [Audit Center (`/audit`)](http://localhost:3000/audit)

**Action:** Scroll through the chronological audit ledger showing `PAYPAL_ORDER_CREATED`, `HUMAN_APPROVAL_GRANTED`, and `TRANSITION_REJECTED` events.

**Narration:**  
> “Every case decision, order creation, and transition rejection is recorded in our chronological audit ledger.  
> For transparency: this demo runs loopback-only with mutation authentication guards, reviewer names are self-reported, and the audit log is a relational SQLite table rather than a blockchain ledger.  
> AgentShield delivers speed, explainability, and governance—keeping human reviewers firmly in control of payment security.”

---

### Recording Checklist for Presenter

- [ ] Video runtime is under 3 minutes (recommended 2:40).
- [ ] Browser zoom is at 100% or 110% for readable font.
- [ ] No terminals, credentials, `.env` files, or checkout URLs are visible on screen.
- [ ] Audio is clean with clear voiceover and no background copyrighted music.
- [ ] Uploaded to YouTube as Public or Unlisted, and link added to Devpost submission.
