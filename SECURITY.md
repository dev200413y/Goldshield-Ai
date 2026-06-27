# GoldShield AI — Security & Data Handling

## 1. Core Context Difference vs. RegAgent

Unlike RegAgent (which must run fully air-gapped), **this problem statement explicitly permits internet access and frontier AI APIs.** Security here is therefore not about "zero network calls" — it's about handling what *does* leave the system responsibly: customer jewelry photos, valuation data, and custody records sent to third-party vision APIs (Gemini, Mistral).

---

## 2. Threat Model

| Risk | Mitigation |
|---|---|
| Customer jewelry photos / identifying data sent to a third-party API without consent or awareness | Strip or avoid sending customer-identifying metadata alongside images; send only the jewelry photo itself, not customer name/account linked in the same payload to the vision API |
| Free-tier vision API logs/uses prompt data to improve their product | Disclose this explicitly in the pitch and in any real deployment plan; avoid sending any genuinely sensitive customer identity data on free tiers (per provider free-tier data-use policies) |
| Single point of failure if one AI provider is down/rate-limited during a live demo or real operation | Multi-provider fallback chain (Gemini → Mistral → local Ollama) — see ARCHITECTURE.md §2.2 |
| Tampering with the custody log or fingerprint record to cover up a swap | Append-only audit_log and custody_log tables; no update/delete path exposed via the API for historical entries |
| Fingerprint comparison being gamed (e.g., resubmitting the same original photos at closure instead of a fresh scan) | Require a fresh, timestamped capture at closure with basic anti-replay checks (e.g., metadata/timestamp validation); flagged as a known limitation requiring stronger anti-spoofing in production |
| Gold-rate manipulation (feeding a false rate to misstate LTV) | Gold rate source should be a single configured, logged value per valuation event, with the source recorded in the audit log for traceability |
| Unauthorized access to valuation/custody/dashboard data | Role-based access control — see §4 |

---

## 3. Data Sent to External AI Providers — What and Why

Each inspector agent call sends only what it needs:
- Density & Volume Inspector: photos + weight (no customer identity)
- Surface, Hallmark, Touchstone, Light-Signature Inspectors: relevant photos only
- No agent sends customer name, account number, or loan amount to an external vision API — that data stays entirely within the local backend/database and is only combined with verification results after the external call returns.

This separation (verification signals out, customer identity never out) is a deliberate design choice and should be highlighted in the pitch as a privacy-by-design decision, even though full air-gapping isn't required for this problem statement.

---

## 4. Access Control

**Prototype scope:** branch-staff-facing dashboard, single-role demo login.

**Production roadmap (stated honestly):**
- Branch staff: can create appraisals, view their branch's loans, cannot view other branches' portfolio data.
- Regional/risk officers: can view aggregated regional dashboard, cannot edit individual custody logs.
- Compliance/audit role: read-only access to the full audit trail across all branches.
- Closure release action should require a second authorized staff member's confirmation (maker-checker principle, standard in banking operations) in addition to the system's fingerprint match — the system supports, not replaces, human authorization at the point of asset release.

---

## 5. Audit Trail as the Backbone of Trust

Every appraisal, valuation, custody event, and closure verification writes an immutable, timestamped row to `audit_log`. This serves the same dual purpose as in RegAgent:
1. **Regulatory defensibility** — a complete, ordered history of how each pledged item was handled, valued, and released.
2. **Fraud forensics** — if a swap or valuation dispute is later alleged, the custody log and fingerprint comparison record are the first place to establish what actually happened.

---

## 6. Honest Limitations (Prototype Scope)

- No production-grade anti-spoofing on the closure re-scan (e.g., proving the photo was taken live, not replayed) — flagged as a needed hardening step before real deployment.
- No encryption-at-rest configured for the local PostgreSQL volume in this prototype.
- Tungsten-density-matching remains an inherent limitation of any purely non-destructive, branch-level system — addressed via escalation to manual/lab verification, not claimed as solved.
- Free-tier AI provider data-use policies (prompts may be used to improve provider models) apply to any image sent during free-tier usage — production deployment would require paid-tier agreements with appropriate data-processing terms before handling real customer images.
- Maker-checker (dual authorization) for physical asset release is described as a requirement but not enforced in the prototype's UI flow — noted directly rather than glossed over.
