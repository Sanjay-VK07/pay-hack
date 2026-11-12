# AgentShield

> **Autonomous FinTech Fraud Investigation Workbench with Human-in-the-Loop Governance for PayPal Sandbox**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black?logo=next.js)](https://nextjs.org)
[![PayPal](https://img.shields.io/badge/PayPal-Sandbox%20Orders%20v2-00457C?logo=paypal)](https://developer.paypal.com)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Clustering-orange)](https://networkx.org)

AgentShield is an explainable fraud investigation platform built for payment operations teams handling PayPal transactions. It bridges the gap between raw fraud signals and high-stakes financial remediation by combining **deterministic heuristic risk scoring**, **relationship-graph syndicate analysis**, and **evidence-backed investigation dossiers**—all governed by a mandatory **Human-in-the-Loop approval gate** before any payment action can be authorized.

---

## The Problem

Traditional payment fraud detection presents two major operational failures:
1. **Alert Fatigue & Context Fragmentation:** Fraud analysts receive thousands of isolated alerts with black-box risk scores, but lack the cross-account relationship maps and evidence trails needed to make rapid, defensible decisions.
2. **The Danger of Unchecked Autonomous Remediation:** When autonomous agents or LLMs are granted direct access to payment gateways, hallucinations or adversarial inputs can trigger unauthorized refunds, unwarranted account freezes, and costly operational churn.

**AgentShield solves both:** it automates data enrichment, heuristic scoring, graph correlation, and dossier generation, while keeping financial execution strictly locked behind named human approval.

---

## Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Transaction Ingestion                           │
│     (Amounts, Cards, Device Fingerprints, IP / Geolocation, Merch)     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Deterministic Risk & Anomaly Engine                  │
│   • Mathematical Heuristics (Emulator, Proxy/VPN, Velocity, Carding)   │
│   • scikit-learn Isolation Forest Unsupervised Anomaly Detection       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  NetworkX Relationship Graph Engine                    │
│   • Multi-entity bipartite projection (Accounts, Devices, Cards, IPs)  │
│   • Coordinated syndicate cluster discovery (Louvain & connected comps)│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Autonomous Multi-Agent Investigation Pipeline            │
│   1. Data Enrichment   2. Heuristic Analysis   3. Graph Intelligence   │
│   4. Forensic Corroboration    5. Mitigation Planning                  │
│   (Optional LLM Summarization: Gemini / OpenAI for narrative synthesis)│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Human-in-the-Loop Review Gate                        │
│   • Explicit reviewer sign-off required                                │
│   • State integrity engine checks linked transaction/case consistency  │
│   • Terminal state guards reject invalid or duplicate transitions     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PayPal Sandbox Settlement Adapter                    │
│   • Host confined strictly to https://api-m.sandbox.paypal.com         │
│   • Verified OAuth 2.0 token exchange & Orders v2 creation            │
│   • Reversals blocked on uncaptured payments (No settled funds)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Chronological Audit Ledger (SQLite)                 │
│      Immutable timestamped tracking of all decisions and API events   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. 100% Explainable Deterministic Risk Scoring
- Mathematical scoring on a 0–100 scale evaluating concrete risk indicators:
  - **Runtime Environment:** Headless browsers, Android/iOS emulators (BlueStacks, Nox).
  - **Network Identity:** Tor exit nodes, datacenter proxies, anonymizing VPN gateways.
  - **Velocity & Behavioral Collisions:** Multi-account card reuse, rapid-checkout velocity.
- Integrated `scikit-learn` Isolation Forest algorithm delivers unsupervised anomaly scores alongside deterministic heuristic weights.
- **Evidence Traceability:** Every risk score maps to discrete evidence records containing source sensor IDs, baseline values, corroboration counts, and alternative explanations.

### 2. Syndicate Graph Clustering (NetworkX)
- Discovers organized carding rings and fraud networks by evaluating shared credentials across accounts.
- Identifies identity collisions: accounts sharing the same physical device fingerprint, payment card hash, or IP subnet.
- Renders interactive force-directed graph visualizations in React Flow with cluster isolation, node filtering, and 2-hop neighbor inspection.

### 3. Investigation Dossier Workspace
- Synthesizes findings from a 6-stage autonomous agent pipeline into an audit-ready case file.
- Corroborates facts across sensors, calculating corroboration confidence scores.
- Optional Gemini or OpenAI integration can generate readable executive summaries, but generative models **never** calculate risk scores or authorize remediation.

### 4. Human-in-the-Loop Governance & Safety Guards
- **Approval Gate:** Automated agents can only recommend actions (e.g. `REFUND_TRANSACTION`, `LOCK_ACCOUNT`). Reversals cannot execute without explicit, named human approval.
- **State Integrity Engine (`CASE_FRAUD_905`):** The engine cross-validates cases, transactions, and payment operations. In the demo dataset, `CASE_FRAUD_905` contains an uncaptured payment marked `APPROVED` while the case is `PENDING_REVIEW`. The system surfaces a prominent **State Integrity Alert** banner and blocks all financial actions automatically.
- **Terminal State Protection:** Cases in terminal states (`ACTION_COMPLETED`, `CLOSED`, `REJECTED`) reject re-approval attempts with HTTP 400 and log `TRANSITION_REJECTED` in the audit ledger.

### 5. PayPal Sandbox Integration
- Connects exclusively to the official PayPal Sandbox API (`https://api-m.sandbox.paypal.com`).
- Includes adapters for **Orders v2**, **Captures v2**, and **Refunds**.
- Implements strict financial safety rules: uncaptured payments cannot be refunded because no settled funds exist.

---

## PayPal Sandbox Verification Scope

To ensure complete transparency during evaluation:

| Component | Status | Details |
| :--- | :--- | :--- |
| **API Endpoint Host** | **Verified** | Verified against `https://api-m.sandbox.paypal.com`. Any attempt to configure live URLs raises an immediate configuration exception. |
| **OAuth 2.0 Authentication** | **Verified** | Live token exchange via `POST /v1/oauth2/token` against Sandbox succeeds and issues valid bearer tokens. |
| **Sandbox Order Creation** | **Verified** | Order `3A365272FB586030R` (`PAY_4755283F3153`) created live via PayPal Orders v2 API in `CREATED · Awaiting Buyer` status. |
| **Buyer Approval** | **Unperformed** | Requires human buyer login at the PayPal checkout URL. Not executed during automated testing. |
| **Order Capture** | **Safely Blocked** | Blocked server-side until buyer checkout is completed. |
| **Refund Execution** | **Safely Blocked** | Uncaptured orders have no settled funds; refund endpoints safely reject uncaptured records. |
| **Pre-Seeded Payments** | **Simulated** | Records `PAY_OP_901`–`PAY_OP_906` are synthetic local records clearly labeled `SIMULATED SANDBOX (DEMO)` in the UI. |

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | FastAPI, Python 3.9+, Pydantic v2, uvicorn |
| **Database & ORM** | SQLite, SQLAlchemy |
| **Data Science & Graph** | NetworkX, scikit-learn (Isolation Forest), NumPy |
| **Frontend Framework** | Next.js 14 (App Router), React 18, TypeScript |
| **UI Components & Styling** | Tailwind CSS, Lucide React, Recharts |
| **Interactive Graph** | React Flow (@xyflow/react) |
| **Data Grid** | AG Grid (ag-grid-react, ag-grid-community) |
| **Payment Integration** | PayPal Developer Platform (Sandbox Orders v2 / Captures v2 / Refunds) |

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.9 or higher
- Node.js 18.x or higher with `npm`

### 1. Clone & Configure
```bash
git clone https://github.com/Sanjay-VK07/pay-hack.git
cd pay-hack
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Start FastAPI server on loopback
python -m app.main
```
The backend initializes on `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend

# Install dependencies
npm ci

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Environment Configuration

Configuration is managed via `backend/.env`. Placeholders are documented in `backend/.env.example`:

| Key | Default | Description |
| :--- | :--- | :--- |
| `API_HOST` | `127.0.0.1` | Loopback address for secure local execution. |
| `PORT` | `8000` | Port for the FastAPI server. |
| `DATABASE_URL` | `sqlite:///./agentshield.db` | Local SQLite database file path. |
| `PAYPAL_BASE_URL` | `https://api-m.sandbox.paypal.com` | **Sandbox only.** Live endpoints are rejected. |
| `PAYPAL_CLIENT_ID` | `""` | PayPal Sandbox Developer App Client ID. |
| `PAYPAL_CLIENT_SECRET` | `""` | PayPal Sandbox Developer App Secret. |
| `AGENTSHIELD_API_KEY` | `""` | Optional key to protect mutating endpoints outside loopback. |
| `GEMINI_API_KEY` | `""` | Optional key for narrative summary generation. |
| `OPENAI_API_KEY` | `""` | Optional alternative for narrative summary generation. |

> **Note:** Do not commit `.env` to version control. The repository `.gitignore` automatically excludes all environment files, local databases, and credentials.

---

## Application Workspaces & Routes

| URL | Workspace | Description |
| :--- | :--- | :--- |
| [`/dashboard`](http://localhost:3000/dashboard) | **Command Center** | Live telemetry, KPI metrics, risk distributions, and a 4-step Judge Quickstart guide. |
| [`/transactions`](http://localhost:3000/transactions) | **Transactions** | AG Grid ledger with deterministic scores. Click any transaction (e.g. `TXN_FRAUD_901`) to open the forensic intelligence drawer. |
| [`/fraud-networks`](http://localhost:3000/fraud-networks) | **Fraud Networks** | Interactive React Flow relationship graph visualizing shared cards, devices, and syndicate rings. |
| [`/investigations`](http://localhost:3000/investigations) | **Investigation Workspace** | Multi-agent reasoning timelines, evidence corroboration cards, human review gates, and the `CASE_FRAUD_905` state integrity alert. |
| [`/payments`](http://localhost:3000/payments) | **Payment Operations** | Payment ledger clearly distinguishing live Sandbox orders (`PAY_4755283F3153`) from simulated demo records. |
| [`/audit`](http://localhost:3000/audit) | **Audit Center** | Chronological relational audit log tracking approvals, order creations, and transition rejections. |
| [`/settings`](http://localhost:3000/settings) | **Settings & Health** | PayPal Sandbox OAuth connectivity diagnostics and system health indicators. |

---

## Safe Testing

AgentShield includes an automated test suite designed with **strict database isolation**. Tests use a fixture that copies the database into `/tmp/test_agentshield_*.db` at import time, ensuring that running tests **never** modifies, seeds, or deletes records from the primary `backend/agentshield.db` database.

### Run Isolated Backend Tests
```bash
cd backend
venv/bin/python -m pytest -q \
  app/tests/test_live_system_verification.py \
  app/tests/test_safe_paypal_adapter.py \
  app/tests/test_safeguards_and_auth.py
```
*Expected output:* `19 passed, 0 failed in ~0.30s`.

### Run Frontend Production Build
```bash
cd frontend
npm run build
```
*Expected output:* `Compiled successfully`, 0 TypeScript errors, 12 static pages generated.

---

## Security Architecture

1. **Mutation Authentication Guard:** All 14 mutating API routes (`POST /api/investigations/*`, `POST /api/payments/*`, `POST /api/transactions/*`, `POST /api/demo/*`) enforce authentication via `X-AgentShield-Key` or `Authorization: Bearer <key>` when `AGENTSHIELD_API_KEY` is configured.
2. **Loopback Confinement:** By default, mutations without an API key are restricted to loopback addresses (`127.0.0.1`, `::1`) for frictionless local evaluation. Remote callers receive HTTP 403 Forbidden.
3. **Read-Only Demonstration Access:** Query endpoints (`GET /api/*`) remain open so evaluators can inspect telemetry and dossiers without authentication barriers.
4. **Relational Audit Trail:** All case approvals, rejections, order creations, and transition attempts are recorded chronologically in a dedicated relational audit table.

---

## Submission & Demo Documentation

- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md):** Complete time-coded (2:40 target) walkthrough script for video recording.
- **[SUBMISSION_DRAFT.md](SUBMISSION_DRAFT.md):** Complete hackathon submission copy, architectural breakdown, and disclosure notes.

---

## License

This project is open-source software licensed under the [MIT License](LICENSE).
