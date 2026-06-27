# Antigravity Agent Instructions — GoldShield AI Project

> Place this file at the repo root as `ANTIGRAVITY.md`. In your first Antigravity prompt, say: "Read ANTIGRAVITY.md, PROBLEM_AND_SOLUTION.md, REQUIREMENTS.md, ARCHITECTURE.md, AGENTS.md, and SECURITY.md before writing any code."

---

## 1. Context to load first, in order

1. `PROBLEM_AND_SOLUTION.md` — what problem this solves and why, including the 4 bank-specific additions beyond the literal hackathon ask
2. `REQUIREMENTS.md` — functional/non-functional requirements, explicit in/out of scope
3. `ARCHITECTURE.md` — system diagram, data model, deployment topology
4. `AGENTS.md` — exact responsibility and output format for each of the 6 agents (5 inspectors + Risk Officer) plus the Gold Rate/LTV and Custody/Fingerprint agents
5. `SECURITY.md` — data-handling rules, especially what may/may not be sent to external AI providers

Do not invent a different architecture or agent boundary than documented. This design has already been finalized for hackathon presentation.

---

## 2. Key difference from the RegAgent project (same team, different constraint)

**This project is allowed to use the internet and frontier AI APIs.** Do not apply RegAgent's air-gapped/no-external-API constraint here — that was specific to the other problem statement. This project should:
- Call Gemini 2.5 Flash as the primary vision provider
- Fall back to Mistral (Pixtral / Mistral Large 3 vision) if Gemini fails or rate-limits
- Fall back further to a local Ollama vision model (llava or llama3.2-vision) if both external providers fail
- Implement this as a single shared `vision_call(image, prompt)` function with try/except fallthrough — do not duplicate this logic per agent

---

## 3. Hard rules — never violate

- Never send customer-identifying data (name, account number, loan amount) in the same payload as a jewelry photo to an external vision API. Identity data stays local; only verification-relevant images go to vision providers. See `SECURITY.md` §3.
- Never implement a workflow, fallback, or "enhancement" that requires damaging, cutting, drilling, or melting the jewelry item. Every method must remain strictly non-destructive, per the problem statement's explicit constraint.
- Never claim or hardcode a "100% certain genuine/fake" output. The Risk Officer Agent must always support an escalation/manual-review path for low-confidence or conflicting-signal cases — this is a requirement, not optional polish.
- Do not silently drop the tungsten-density-matching limitation from the Risk Officer Agent's reasoning output when it's relevant — the honest-limitation framing is part of the product's credibility and must show up in the actual generated explanation text, not just the docs.

---

## 4. Agent implementation rules

Follow `AGENTS.md` exactly for each of:
1. Density & Volume Inspector — baseline: bounding-box/reference-object volume estimate; optional enhancement: Polycam-based photogrammetry input if a 3D scan is provided
2. Surface & Seam Inspector
3. Hallmark Verification Inspector
4. Touchstone / Reflectance Inspector
5. Light-Signature Inspector
6. Risk Officer Agent (fusion — combines 1–5, must support escalation per §3 above)
7. Gold Rate & LTV Agent — deterministic math once given a rate; rate source itself can be a live API call or a manually configured cached value
8. Custody & Fingerprint Agent — generates fingerprint at intake, re-verifies at closure; must produce a numeric match_confidence, not just a boolean

Use LangGraph for orchestration, consistent with the RegAgent project's pattern, even though this project is not air-gapped.

---

## 5. Project structure to follow

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
│   └── vision_provider.py   # shared fallback wrapper: Gemini -> Mistral -> Ollama
├── backend/                  # FastAPI app
├── frontend/                  # React dashboard (Branch view + Regional view)
├── sample-data/                # self-created test photos, weights, evidence
├── docker-compose.yml
├── README.md (if generated separately)
├── PROBLEM_AND_SOLUTION.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── AGENTS.md
└── SECURITY.md
```

---

## 6. Database

Use the schema in `ARCHITECTURE.md` §3 (`appraisals`, `verification_results`, `gold_fingerprints`, `valuations`, `custody_log`, `closure_verifications`, `loans`, `audit_log`) as the baseline. Every meaningful event must write to `audit_log` — non-negotiable per the project's audit-trail philosophy.

---

## 7. Demo-readiness requirements for generated code

- Every external AI call site must have a visible try/except fallback chain, since this will be demonstrated live and provider downtime/rate-limits are a real risk.
- Include a small "Powered by: Gemini / Mistral / Local" indicator in the dashboard UI wherever a verification result is shown — turns provider fallback into a visible reliability feature during the demo rather than a hidden implementation detail.
- Pin dependency versions in `requirements.txt`/`package.json` for demo reproducibility.
- Do not regenerate or rewrite the five documentation files unless explicitly asked — flag discrepancies instead of silently changing the docs to match code.
