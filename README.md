# AgentShield

AgentShield is a fraud investigation workbench for PayPal Sandbox transactions. It combines deterministic risk scoring and relationship-graph analysis with an evidence-led investigation workflow, then keeps payment remediation behind explicit case approval and capture-eligibility checks.

## What the demo shows

1. Review a transaction and its deterministic risk factors.
2. Explore related accounts, devices, payment identities, and network indicators in the fraud graph.
3. Open an investigation dossier with evidence, alternative explanations, agent activity, and a reasoning timeline.
4. Inspect payment capture and refund eligibility. Uncaptured transactions remain ineligible; AgentShield does not invent capture IDs.
5. Review the audit trail and distinguish PayPal Sandbox operations from simulator results.

The deterministic engine is the source of the risk score. An optional Gemini or OpenAI provider can help summarize evidence; without provider credentials the app uses its deterministic fallback.

## Run locally

Requirements: Python 3.9 or newer and Node.js with npm.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

The backend listens on `127.0.0.1:8000` by default. It creates the SQLite database and loads the demo dataset only when the database contains no transactions. The API documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

## Configuration

Edit `backend/.env` for local configuration. Keep credentials out of source control and use PayPal **Sandbox** credentials only. With no PayPal credentials, the app labels simulator operations as simulated. Optional AI configuration uses `GEMINI_API_KEY` or `OPENAI_API_KEY`; neither is required for the deterministic fallback.

`API_HOST` defaults to `127.0.0.1`. Do not bind the demo service to a public or shared network: investigator names submitted to the API are not backed by a login or identity provider yet. Do not use real payment credentials or customer data.

## Implementation

- **Frontend:** Next.js, React, AG Grid, React Flow, Recharts
- **Backend:** FastAPI, SQLAlchemy, SQLite, NetworkX, scikit-learn
- **Payment integration:** PayPal Sandbox adapter with clearly labeled simulator fallback
- **AI:** Optional Gemini/OpenAI summarization with deterministic risk scoring as the decision source

## Safe checks

From `backend/`:

```bash
venv/bin/python -m pytest -q app/tests/test_live_system_verification.py
```

From `frontend/`:

```bash
npm run build
```

Some other automated workflow tests intentionally approve cases or execute simulator refunds. Review those test files before running them.

## Current demonstration limitation

The application models investigator approval but does not yet authenticate API callers or assign verified roles. Run it only on loopback with demo data; do not expose it as a hosted payment service until identity and authorization controls are implemented.
