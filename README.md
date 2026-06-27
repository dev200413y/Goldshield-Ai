# GoldShield AI — Non-Destructive Spurious Gold Detection for Gold Loan Processing

> Additional Problem Statement — Tata Steel / Canara Bank Hackathon 2026
> Status: Idea → Build Phase (Antigravity)
> Presentation Window: Up to 2nd week of July 2026 (additional, two presentations required)
> Constraint: Internet + Frontier AI APIs allowed for this problem statement (unlike the core RegAgent submission)

---

## 1. What This Is

GoldShield AI is a multi-agent, non-destructive verification and risk-management system for gold loan processing at Indian banks. It answers the hackathon's literal question — *"is this pledged gold genuine, or coated/contaminated counterfeit?"* — and goes further, addressing the full bank-side lifecycle: valuation, loan-to-value compliance, custody accountability, and portfolio risk.

See `PROBLEM_AND_SOLUTION.md` for the full problem framing and solution rationale.

---

## 2. Why We Took This On

This is an **additional, optional problem statement** alongside our core submission (RegAgent — Agentic Regulatory Intelligence & Compliance). We volunteered because:
- Internet + frontier AI access is allowed here, making it fast to prototype well using the same multi-agent patterns proven in RegAgent.
- It's a genuinely interesting, real-world fraud problem with a clear non-destructive constraint.
- It let us demonstrate range — an air-gapped compliance system (RegAgent) and an internet-connected, multi-modal fraud-detection system (GoldShield AI), built by the same approach.

---

## 3. Core Idea in One Paragraph

A customer's jewelry is photographed from multiple angles, weighed, and photographed under a touchstone test and varying light. Five specialist AI agents independently analyze these non-destructive signals — density/volume, surface/seams, hallmark, touchstone reflectance, and light-signature — and a Risk Officer agent fuses them into an explainable authenticity verdict, escalating to manual review rather than guessing when signals disagree. On top of this, the system computes the item's fair market value against live gold rates, validates the loan amount against RBI's LTV cap, tracks custody in the vault, and re-verifies the item's Digital Gold Fingerprint at loan closure to catch in-custody tampering.

---

## 4. Documentation Map

| File | Purpose |
|---|---|
| `PROBLEM_AND_SOLUTION.md` | Problem statement, our reframing, solution overview, one-line pitch |
| `REQUIREMENTS.md` | Functional/non-functional requirements, explicit scope and out-of-scope |
| `ARCHITECTURE.md` | System diagram, design principles, data model, deployment topology |
| `AGENTS.md` | Detailed spec for all 8 agents (5 inspectors, Risk Officer, Gold Rate/LTV, Custody/Fingerprint) |
| `SECURITY.md` | Data-handling rules, what goes to external AI providers, access control |
| `TEST_DATA.md` | How we are generating/sourcing test photos, weights, and evidence — since real counterfeit gold samples aren't available |
| `DEMO_SCRIPT.md` | Rehearsed live-presentation script (for both required presentations) |
| `ANTIGRAVITY.md` | Build instructions for Antigravity — read this first when generating code |

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Multi-agent orchestration | LangGraph |
| Vision/LLM (primary) | Gemini 2.5 Flash (free tier, vision-native) |
| Vision/LLM (fallback) | Mistral (Pixtral / Mistral Large 3 vision, free Experiment tier) |
| Vision/LLM (local backup) | Ollama (llava / llama3.2-vision) — zero rate limit |
| 3D volume estimate (optional enhancement) | Polycam (photogrammetry, free tier) |
| Backend | FastAPI |
| Database | PostgreSQL (local Docker) |
| Frontend | React (Branch + Regional dashboard views) |
| Deployment | Docker Compose |

Full fallback rationale is in `ARCHITECTURE.md` §2.2.

---

## 6. Quick Start

```bash
# 1. Get free API keys (no credit card needed for either)
#    Gemini: aistudio.google.com
#    Mistral: console.mistral.ai (phone verification only)

# 2. Set environment variables
export GEMINI_API_KEY=your_key
export MISTRAL_API_KEY=your_key

# 3. (Optional local fallback) pull a vision model
ollama pull llava

# 4. Start everything
docker-compose up --build

# 5. Open the dashboard
http://localhost:3000

# 6. Run an appraisal
#    Upload multi-angle photos, weight, touchstone photo, light-angle photos
#    via the dashboard's "New Appraisal" flow
```

---

## 7. Project Structure

```
goldshield/
├── agents/
│   ├── density_inspector.py
│   ├── surface_inspector.py
│   ├── hallmark_inspector.py
│   ├── touchstone_inspector.py
│   ├── light_signature_inspector.py
│   ├── risk_officer.py
│   ├── gold_rate_ltv_agent.py
│   └── custody_fingerprint_agent.py
├── vision/
│   └── vision_provider.py     # Gemini -> Mistral -> Ollama fallback wrapper
├── backend/                    # FastAPI app
├── frontend/                    # React dashboard
├── sample-data/                  # self-created test photos, weights, evidence
├── docker-compose.yml
├── README.md
├── PROBLEM_AND_SOLUTION.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── AGENTS.md
├── SECURITY.md
├── TEST_DATA.md
├── DEMO_SCRIPT.md
└── ANTIGRAVITY.md
```

---

## 8. Honest Status

This is an idea-phase build moving into Antigravity-assisted implementation. The verification layer (5 inspector agents + Risk Officer) is the priority to get working end-to-end first; the lifecycle layer (Gold Rate/LTV, Custody/Fingerprint) follows once the core verification demo is solid. See `REQUIREMENTS.md` §5 for demo success criteria.
