# GoldShield AI — Problem Statement & Solution

> Additional Problem Statement — Tata Steel / Canara Bank Hackathon 2026
> Theme: Identification of Spurious Gold in Gold Loan Processing
> Constraint: Frontier AI / Internet access allowed for THIS problem statement only. Item cannot be broken/destroyed.

---

## 1. Problem Statement (as given)

When a customer applies for a gold loan, the pledged gold must be verified for authenticity as part of the appraisal process. Conventional methods have a critical blind spot: **if an item is internally contaminated (e.g., a base-metal or tungsten core) and coated with a thick layer of genuine gold, the standard stone-rubbing (touchstone) test only reads the outer gold layer and fails to detect the adulteration beneath.**

The hackathon seeks an effective, low-cost solution suitable for **branch-level deployment**, distinguishing genuine gold from coated/contaminated counterfeits **non-destructively**, using:
- Photos of the jewelry
- Weight of the jewelry
- Stone shine / light-reflectance signature
- Any other innovative, cost-effective method

---

## 2. Why This Problem Matters Beyond "Is It Fake or Not"

Most teams will treat this as a pure fraud-detection classification problem. We deliberately went further, because a gold loan isn't a single moment — **it's a lifecycle**: appraisal → loan disbursal → custody for months/years → closure/release. Fraud and risk can enter at *any* of these points, not just at intake:

| Lifecycle Stage | Risk | Conventional System | GoldShield AI |
|---|---|---|---|
| Appraisal | Spurious/coated gold accepted as genuine | Touchstone only — blind to internal contamination | Multi-signal non-destructive verification |
| Valuation | Wrong loan amount sanctioned vs actual gold value | Manual rate lookup, error-prone | Live gold-rate engine + auto LTV validation |
| Custody | Pledged item swapped/tampered while in bank vault | No systematic way to verify "is this still the same item" | Digital Gold Fingerprint, re-checked at closure |
| Price movement | Bank's collateral value drops below loan exposure (gold price falls) | Reactive, manual monitoring | Automated margin-call alerting |
| Portfolio level | Bank doesn't have real-time visibility into total gold-backed exposure/risk | Spreadsheets, delayed MIS reports | Live regional/branch risk dashboard |

This reframing is the core of our pitch: **the touchstone blind spot is a symptom of a bigger gap — banks lack an end-to-end, verifiable, non-destructive gold-loan intelligence system.**

---

## 3. Our Solution — GoldShield AI

GoldShield AI is a multi-agent, multi-signal verification and risk-management system for gold loan processing, built around five specialist inspector agents that fuse non-destructive signals into a single explainable verdict, plus four bank-grade lifecycle features that go beyond the original problem statement.

### 3.1 Core Verification Layer (answers the stated problem)

Five inspector agents analyze the same non-destructive inputs given in the problem statement (photos, weight, stone shine/light signature):

1. **Density & Volume Inspector** — estimates true volume via multi-angle photos/photogrammetry, combines with weight to compute density, and flags mismatches against gold's known density (19.3 g/cm³). This is the signal that looks *through* the coating — the direct answer to the touchstone blind spot.
2. **Surface & Seam Inspector** — frontier vision model analyzes photos for solder joints, color inconsistency, plating edges, wear patterns exposing a base-metal core.
3. **Hallmark Verification Inspector** — vision-based OCR and pattern check on BIS hallmark (presence, placement, font, caratage code).
4. **Touchstone / Reflectance Inspector** — analyzes the streak/shine left on a testing stone under controlled light, comparing color and luster against genuine-gold reference patterns.
5. **Light-Signature Inspector** — analyzes how the surface reflects light across multiple angles/intensities; coated or plated items show micro-inconsistencies in this behavior that a single touchstone reading cannot reveal.

A **Risk Officer Agent** fuses all five signals into one explainable verdict: authenticity score, fraud probability, confidence, and a plain-language reason ("Suspicious Area: bottom joint. Reason: density mismatch + color inconsistency.").

> **Honest limitation, stated upfront:** Tungsten's density (19.25 g/cm³) is dangerously close to gold's (19.3 g/cm³), so density alone can occasionally be fooled. GoldShield AI does not claim certainty it cannot achieve non-destructively — when signals disagree or confidence is low, the system escalates to mandatory manual verification rather than auto-approving. This is a design feature, not a gap we're hiding.

### 3.2 Lifecycle & Bank-Risk Layer (our unique additions, beyond the stated problem)

The four additions below are what make this a **bank deployment-ready product**, not just a fraud classifier:

1. **Gold Rate Engine + Loan-to-Value (LTV) Monitor** — fetches the current gold rate (per gram, 22K/24K equivalent) at the moment of appraisal, computes the pledged item's fair market value, and validates the requested loan amount against the regulatory LTV cap (~75% per RBI gold loan norms). If gold prices subsequently fall and the bank's collateral coverage weakens, the system automatically flags the loan for a margin call / customer notice.
2. **Vault Custody Ledger** — every pledged item is logged with its exact physical storage location (branch, vault, locker/box ID), and every handling event (movement, inspection, handover) is timestamped and attributed to a staff ID — a chain-of-custody record for accountability.
3. **Digital Gold Fingerprint + Closure Re-verification** — at appraisal, the system generates a unique fingerprint (visual embedding + hallmark pattern + density signature) for the pledged item, stored as e.g. `GF-2026-001245`. **At loan closure, before the item is returned to the customer, the system re-scans it and compares against the original fingerprint.** A mismatch flags a potential swap during custody — directly addressing a real and serious gold-loan risk (insider tampering) that the original problem statement doesn't even mention.
4. **Portfolio Risk Dashboard** — aggregates across all loans: total gold-backed loan book value, total grams held by branch/region, current market exposure, price-sensitivity ("if gold falls X%, exposure becomes Y"), and early-warning signals feeding into NPA risk assessment.

---

## 4. Why This Solution Is Defensible (not just impressive-sounding)

- Every verification signal maps to something genuinely demoable live, with real photos and real weight data.
- The one true physical limitation (tungsten density-matching) is acknowledged and handled via escalation, not hidden or oversold.
- The four lifecycle additions are not exotic research — they are standard banking-risk concepts (LTV monitoring, custody chain, asset re-verification, portfolio dashboards) **applied for the first time to the specific gold-loan-fraud blind spot the hackathon raised.**
- The system is positioned correctly to the audience: this is being demoed to **Canara Bank**, a financial institution — so framing the solution around loan economics, risk exposure, and custody accountability (not just "is it fake gold") is what will resonate with bank-side judges specifically.

---

## 5. One-Line Pitch

> "Most solutions answer 'is this gold real.' GoldShield AI answers the bank's actual question: is this gold real, is it valued correctly, is it still the same item we appraised, and what is our exposure if gold prices move — all without ever touching or damaging the customer's jewelry."
