# GoldShield AI — System Architecture

## 1. High-Level Architecture

```
                    ┌───────────────────────────────┐
                    │         INTAKE LAYER           │
                    │  Multi-angle photos            │
                    │  Weight (manual entry)         │
                    │  Touchstone streak photo        │
                    │  Light-signature photos         │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
        ┌──────────────────────────────────────────────────┐
        │           VERIFICATION LAYER (LangGraph)           │
        │                                                    │
        │  ┌────────────┐ ┌────────────┐ ┌────────────────┐ │
        │  │  Density & │ │  Surface & │ │   Hallmark     │ │
        │  │  Volume    │ │  Seam      │ │   Verification │ │
        │  │  Inspector │ │  Inspector │ │   Inspector     │ │
        │  └────────────┘ └────────────┘ └────────────────┘ │
        │  ┌────────────┐ ┌────────────┐                    │
        │  │ Touchstone │ │   Light-   │                    │
        │  │ Inspector  │ │  Signature │                    │
        │  │            │ │  Inspector │                    │
        │  └────────────┘ └────────────┘                    │
        │                  │                                │
        │                  ▼                                │
        │          Risk Officer Agent (fusion)               │
        │   → authenticity score, fraud %, confidence,       │
        │     plain-language reasoning, escalation flag       │
        └──────────────────────┬─────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │             VALUATION LAYER                        │
        │  Gold Rate Engine (live API / cached rate)         │
        │       ↓                                            │
        │  Fair Market Value = weight × purity × rate        │
        │       ↓                                            │
        │  LTV Validator (vs RBI cap, configurable)          │
        │       ↓                                            │
        │  Margin-Call Monitor (periodic re-valuation)        │
        └──────────────────────┬─────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │            LIFECYCLE / CUSTODY LAYER                │
        │  Digital Gold Fingerprint Generator                 │
        │  (visual embedding + hallmark + density signature)  │
        │       ↓                                            │
        │  Vault Custody Ledger (location, handler, timestamp)│
        │       ↓ (at loan closure)                          │
        │  Closure Re-verification Agent                      │
        │  (re-scan vs original fingerprint → match/mismatch) │
        └──────────────────────┬─────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │              PERSISTENCE LAYER                       │
        │   PostgreSQL: appraisals, fingerprints, custody log, │
        │   valuations, loans, audit_log                       │
        └──────────────────────┬─────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │              DASHBOARD LAYER (React)                 │
        │   Branch View | Regional/Portfolio View              │
        │   Risk Alerts | Audit Trail Viewer                   │
        └──────────────────────────────────────────────────┘
```

---

## 2. Design Principles

### 2.1 Verification and lifecycle layers are decoupled
The five inspector agents (verification layer) answer the hackathon's literal question — "is this gold genuine." The valuation and custody layers are independent additions that consume the verification output but don't block it. This means the core fraud-detection demo works standalone, and the bank-risk features can be demoed as a clear "and here's what else this enables" extension — reducing risk if time runs short before the July presentation.

### 2.2 Multi-provider AI with automatic fallback
Since this problem statement explicitly allows internet and frontier AI APIs, the system is **not air-gapped** (unlike RegAgent). To avoid demo failure from free-tier rate limits or provider downtime:
```
Primary:   Gemini 2.5 Flash (vision-native, generous free tier)
Fallback:  Mistral (Pixtral / Large 3 vision, free Experiment tier)
Local backup: Ollama + llava/llama3.2-vision (zero rate limit, no internet needed)
```
Each inspector agent calls a shared `vision_call()` wrapper that tries providers in order and falls back transparently. The dashboard can optionally display which provider answered, framed as a reliability feature.

### 2.3 Honest escalation over false confidence
The Risk Officer Agent does not force a binary genuine/fake verdict. When signals disagree (e.g., density passes but surface flags an anomaly) or confidence is below threshold, the system outputs "Manual Verification Required" rather than guessing. This directly addresses the known tungsten-density-matching edge case without overclaiming capability the system doesn't have.

### 2.4 Reusing the RegAgent pattern
This project deliberately reuses the multi-agent LangGraph pattern, FastAPI backend, PostgreSQL persistence, and React dashboard approach already proven in the RegAgent build — same team, same stack, faster execution, consistent audit-log philosophy (append-only, fully timestamped).

---

## 3. Data Model (PostgreSQL — core tables)

```
appraisals
  id, customer_ref, item_description, weight_grams, declared_purity,
  photos_ref, created_at, branch_id

verification_results
  id, appraisal_id, density_result, surface_result, hallmark_result,
  touchstone_result, light_signature_result, authenticity_score,
  fraud_probability, confidence, reasoning, escalated (bool), created_at

gold_fingerprints
  id, appraisal_id, fingerprint_id (e.g. GF-2026-001245),
  visual_embedding, hallmark_signature, density_signature, created_at

valuations
  id, appraisal_id, gold_rate_per_gram, purity_used, fair_market_value,
  loan_amount_requested, ltv_percent, ltv_violation (bool), valued_at

custody_log
  id, appraisal_id, branch_id, vault_id, locker_id, event_type
  (stored/moved/handed_over), staff_id, timestamp

closure_verifications
  id, appraisal_id, closure_scan_ref, match_result (pass/fail),
  match_confidence, verified_at

loans
  id, appraisal_id, principal_amount, disbursed_at, status,
  current_ltv (recomputed periodically), margin_call_flag

audit_log
  id, entity_type, entity_id, action, actor, timestamp, details
```

---

## 4. Deployment Topology (prototype)

```
docker-compose.yml
 ├── postgres
 ├── backend (FastAPI)
 ├── frontend (React)
 └── [External: Gemini API, Mistral API — called over internet]
 └── [Local fallback: Ollama, runs as host process]
```

This is intentionally **not air-gapped** — internet access and frontier AI APIs are explicitly permitted and expected for this problem statement, unlike RegAgent.

---

## 5. Why a Live 3D Reconstruction (Polycam) Is Optional, Not Core

Photogrammetry-based volume estimation (via a tool like Polycam) improves density accuracy but is not required for the system to function — a simpler bounding-box/reference-object volume estimate from standard multi-angle photos is the default path, with 3D-scan-based volume as an enhancement path if time allows before the July presentation. This keeps the core demo dependency-light.

---

## 6. Production Roadmap (Stated Honestly, Not Built in Prototype)

| Prototype (this build) | Production (future) |
|---|---|
| Photo-based volume estimate (bounding box / simple photogrammetry) | Full 3D reconstruction (NeRF/Gaussian Splatting) for hollow-section detection |
| Density mismatch as sole physical signal beyond vision | Eddy-current/conductivity hardware sensor for tungsten-density-match edge cases |
| Single-bank deployment | Cross-branch/cross-bank fraud-network graph analysis |
| Cached/manually entered gold rate fallback | Live regulated gold-rate feed integration (e.g., IBJA reference rate) |
| Branch-staff dashboard only | Customer-facing transparency portal showing their item's appraisal report |
