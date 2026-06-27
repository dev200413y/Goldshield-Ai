# GoldShield AI — Agent Specifications

## 1. Density & Volume Inspector

**Responsibility:** Estimate the item's true volume non-destructively and compute density to detect internally contaminated cores — the direct answer to the hackathon's stated touchstone blind spot.

**Inputs:** Multi-angle photos (4–10), weight in grams, optional reference-object scale marker in frame.

**Method:**
- Baseline: estimate dimensions from photos using a known reference object (coin/ruler in frame) for scale, approximate volume using jewelry-shape heuristics (ring = torus approximation, chain = cylindrical-link approximation, etc.).
- Enhancement (optional, time-permitting): photogrammetry-based 3D reconstruction (e.g., Polycam) for a more accurate volume figure.
- Density = weight ÷ volume. Compare against expected range for declared caratage.

**Output:**
```json
{ "density_gcm3": 16.1, "expected_range": [17.7, 17.9], "result": "FLAG", "reason": "density below expected 22K range" }
```

**Why this agent matters most:** This is the only signal that looks *through* the coating regardless of how convincing the surface appears — directly solving the stated problem of a thick gold layer hiding a base-metal or tungsten core.

**Known limitation (stated honestly):** Tungsten's density (19.25 g/cm³) is close enough to gold's (19.3 g/cm³) that this signal alone can be inconclusive for tungsten specifically. This is why the system is multi-signal — see Risk Officer Agent.

---

## 2. Surface & Seam Inspector

**Responsibility:** Detect visual evidence of plating, soldering, or base-metal exposure.

**Inputs:** Multi-angle photos.

**Method:** Frontier vision model (Gemini/Mistral Pixtral) prompted to identify: solder joints, color inconsistency at edges/joints/clasps, uneven wear exposing a different-colored substrate, visible seams inconsistent with solid-gold construction.

**Output:**
```json
{ "result": "FLAG", "location": "bottom joint", "observation": "color inconsistency suggesting plating edge" }
```

---

## 3. Hallmark Verification Inspector

**Responsibility:** Verify BIS hallmark presence, placement, and pattern consistency.

**Inputs:** Close-up photo of the hallmark stamp.

**Method:** Vision model performs OCR + pattern-matching against expected BIS hallmark format (mark, caratage code, jeweler ID, hallmarking center mark). Flags missing, malformed, or inconsistently placed hallmarks.

**Output:**
```json
{ "result": "PASS", "hallmark_detected": "BIS 916 HUID-XXXXX", "confidence": 0.93 }
```

---

## 4. Touchstone / Reflectance Inspector

**Responsibility:** Analyze the streak left on a touchstone under the traditional rub test, but with consistent, repeatable visual analysis rather than a human's subjective read.

**Inputs:** Photo of the streak mark under controlled/standard lighting.

**Method:** Vision model compares streak color, width, and luster against a reference set of known-genuine-gold streak characteristics.

**Output:**
```json
{ "result": "PASS", "streak_color_match": "consistent with 22K gold reference" }
```

**Note:** This agent inherits the same blind spot as the manual touchstone test (it only reads the outer layer) — it is included for completeness and consistency-checking against the other signals, not as the primary contamination detector. The Density & Volume Inspector carries that responsibility.

---

## 5. Light-Signature Inspector

**Responsibility:** Detect surface-coating inconsistencies via reflectance behavior across multiple light angles — a secondary non-destructive physical signal independent of touchstone.

**Inputs:** 2–3 photos of the item under different light angles/intensities.

**Method:** Vision model analyzes how brightness/reflectance/color shifts across the light-angle photo set. Genuine solid gold has a consistent, predictable reflectance behavior; plated or coated items frequently show micro-inconsistencies (uneven sheen, color shift at certain angles) as the coating interacts with light differently than solid metal.

**Output:**
```json
{ "result": "PASS", "reflectance_consistency": "0.89 (within normal range)" }
```

---

## 6. Risk Officer Agent (Fusion)

**Responsibility:** Combine all five inspector outputs into one explainable, escalation-aware verdict.

**Inputs:** Outputs of Agents 1–5.

**Logic:**
- If all signals pass with high confidence → high authenticity score, low fraud probability, no escalation.
- If one signal flags but others pass → moderate fraud probability, reasoning names the specific flagged signal and location, recommend manual review for that specific concern.
- If density is borderline/inconclusive (the tungsten edge case) AND surface/hallmark/touchstone all pass → **explicit escalation**, with reasoning stating the known density-matching limitation rather than asserting false certainty.
- If multiple signals flag → high fraud probability, strong escalation.

**Output:**
```json
{
  "authenticity_score": 82,
  "fraud_probability": 17,
  "confidence": 91,
  "suspicious_area": "bottom joint",
  "reasoning": "Density mismatch (16.1 g/cm3 vs expected 17.7-17.9) combined with color inconsistency at solder joint",
  "recommendation": "Manual verification required",
  "escalated": true
}
```

---

## 7. Gold Rate & LTV Agent

**Responsibility:** Fetch current gold rate, compute fair market value, and validate the requested loan amount against the LTV cap.

**Inputs:** Verified weight, declared/verified purity, current loan request amount.

**Method:** Calls a configured gold-rate source (live API if available, else most-recent cached rate with a staleness warning). Computes `fair_market_value = weight × purity_factor × rate_per_gram`. Computes `ltv_percent = loan_amount / fair_market_value × 100`. Flags if `ltv_percent` exceeds the configured cap (default 75%).

**Output:**
```json
{ "fair_market_value": 54200, "ltv_percent": 71.2, "ltv_cap": 75, "violation": false }
```

---

## 8. Custody & Fingerprint Agent

**Responsibility:** Generate the Digital Gold Fingerprint at intake, log custody events through the loan's lifetime, and re-verify at closure.

**Inputs (intake):** Verification-layer photos, hallmark data, density signature.
**Inputs (closure):** Fresh scan of the item being returned.

**Method:** At intake, combines a visual embedding (from the photos), the hallmark signature, and the density value into a single fingerprint record, assigned an ID (`GF-YYYY-XXXXXX`). At closure, repeats the embedding/signature extraction on the fresh scan and compares against the stored fingerprint using similarity scoring.

**Output (closure):**
```json
{ "fingerprint_id": "GF-2026-001245", "match_confidence": 0.97, "result": "MATCH" }
```
A low match_confidence triggers a mandatory hold and manual investigation before the item can be released — this is the system's answer to in-custody tampering/swap risk, a real gold-loan threat the original problem statement does not cover.

---

## 9. Why Five Verification Agents Instead of One Combined Model

Each inspector is scoped narrowly and independently testable — exactly the same reasoning applied in RegAgent's agent design. This matters doubly here because:
1. Each signal has a **different, named physical/visual basis** (density physics vs. visual seam detection vs. OCR pattern-matching vs. reflectance behavior) — collapsing them into one model call would make the reasoning output far less explainable to a bank auditor.
2. It allows the Risk Officer Agent to make **principled escalation decisions** based on which specific signals agree or disagree, rather than a single opaque confidence number.
3. It keeps the known tungsten-density limitation isolated to one agent's output rather than contaminating the whole system's credibility — the system can say "this exact signal is inconclusive here, here's why, and here's what we're doing about it."
