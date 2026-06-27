# GoldShield AI — Requirements

## 1. Functional Requirements

### 1.1 Intake & Verification
- FR1: System shall accept multi-angle photos (minimum 4, recommended 8–10) of a jewelry item via upload or live capture.
- FR2: System shall accept a manually entered weight value (grams) from a digital scale.
- FR3: System shall accept a photo of the touchstone streak / reflectance test under controlled lighting.
- FR4: System shall accept 2–3 photos of the item under different light angles/intensities for light-signature analysis.
- FR5: System shall estimate item volume from multi-angle photos (photogrammetry) without requiring water displacement or any destructive/contact-based volume method.
- FR6: System shall compute density = weight / estimated volume and compare against gold's expected density range (per declared caratage, e.g., 22K ≈ 17.7–17.9 g/cm³, 24K ≈ 19.3 g/cm³).
- FR7: System shall run vision-based analysis for surface/seam anomalies, hallmark verification, touchstone reflectance, and light-signature consistency.
- FR8: System shall fuse all signal outputs into a single authenticity score (0–100), fraud probability (0–100%), and confidence level, with human-readable reasoning.
- FR9: System shall flag low-confidence or conflicting-signal cases for mandatory manual verification rather than auto-approving or auto-rejecting.

### 1.2 Valuation & Loan Logic
- FR10: System shall fetch the current gold rate (per gram, by caratage) from a configurable source (live API when internet available; manually entered/cached rate otherwise).
- FR11: System shall compute the pledged item's fair market value using weight × purity × current rate.
- FR12: System shall validate the requested/sanctioned loan amount against the configured Loan-to-Value (LTV) cap (default 75%, configurable per current RBI norms) and flag violations.
- FR13: System shall support periodic re-valuation of active loans against updated gold rates and flag loans whose effective LTV has breached the safe threshold (margin call candidates).

### 1.3 Custody & Lifecycle
- FR14: System shall generate a unique Digital Gold Fingerprint per item at appraisal time (visual embedding + hallmark data + density signature), stored with a unique ID (e.g., `GF-YYYY-XXXXXX`).
- FR15: System shall log the physical storage location (branch, vault, locker/box ID) for every pledged item, and timestamp every custody event (storage, movement, handover) with the responsible staff ID.
- FR16: At loan closure, system shall require a fresh scan of the item and compare it against the original Digital Gold Fingerprint, producing a match/mismatch result before release is authorized.
- FR17: System shall block or flag release if the closure fingerprint comparison falls below a configurable match-confidence threshold.

### 1.4 Reporting & Dashboard
- FR18: System shall provide a branch-level dashboard showing: today's appraisals, flagged/high-risk cases, pending manual verifications, active loan count and value.
- FR19: System shall provide a regional/portfolio-level dashboard showing: total gold-backed loan book value, total grams held (by branch/region), current market exposure, price-sensitivity projection, and NPA-risk signal aggregation.
- FR20: System shall maintain an immutable audit log of every appraisal, valuation, custody event, and closure verification, exportable for regulatory/audit purposes.

## 2. Non-Functional Requirements

- NFR1: **Frontier AI / internet access is permitted for this problem statement** (unlike the RegAgent build) — system may call external vision APIs (Gemini, Mistral Pixtral) directly.
- NFR2: System shall implement multi-provider fallback for vision inference (primary → secondary → local) to avoid single-point-of-failure during live demo or production use, given free-tier rate limits.
- NFR3: End-to-end appraisal (photo capture to verdict) shall complete in under 2 minutes to be realistically usable at branch level.
- NFR4: System must be non-destructive — no requirement, workflow, or fallback may involve damaging, cutting, or melting the pledged item.
- NFR5: All sensitive data (customer identity, item value, custody logs) must be access-controlled; see SECURITY.md.
- NFR6: System shall be cost-effective enough for branch-level deployment — no requirement for specialized lab equipment (X-ray, CT scan, spectrometer) in the baseline build.
- NFR7: System architecture shall keep the verification layer (Section 1.1) decoupled from the lifecycle layer (Sections 1.2–1.3), so either can be demoed/evaluated independently.

## 3. Inputs (exactly as permitted by the problem statement)

- Photos of the jewelry (multi-angle)
- Weight of the jewelry
- Stone shine / touchstone streak photo
- Light-signature photos (multiple angles/intensities)
- **Cannot break or destroy the item** — no melting, cutting, drilling, or acid testing

## 4. Out of Scope (explicitly, for this build)

- X-ray, CT scan, or any imaging requiring specialized lab hardware
- Full 3D reconstruction via NeRF/Gaussian Splatting (noted as future-phase roadmap only)
- Eddy-current/conductivity hardware sensor integration (noted as future-phase roadmap only)
- Multi-bank fraud-network graph analysis (requires data this prototype doesn't have)
- Customer-facing mobile app (branch-staff-facing dashboard only, in this build)

## 5. Success Criteria for Demo

- Live appraisal of a real jewelry item end-to-end, producing an explainable authenticity verdict
- Live demonstration of LTV calculation against a fetched/cached gold rate
- Live demonstration of Digital Gold Fingerprint generation and a closure re-verification match/mismatch
- Dashboard showing at least branch-level aggregated view with sample data
- Honest articulation of the tungsten-density-matching limitation and how the system escalates rather than overclaims
