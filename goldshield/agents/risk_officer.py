"""
GoldShield AI — Risk Officer Agent (Agent 6 — Fusion)
Combines all five inspector outputs into one explainable, escalation-aware verdict.

KEY DESIGN RULE: Never force a binary genuine/fake verdict. When signals disagree
or confidence is low, output "Manual Verification Required" rather than guessing.
The tungsten-density-matching limitation must be stated explicitly when relevant.
"""

import logging
from typing import Optional

from goldshield.models import (
    RiskOfficerVerdict,
    DensityResult,
    SurfaceResult,
    HallmarkResult,
    TouchstoneResult,
    LightSignatureResult,
    InspectorResult,
)
from goldshield.config import (
    RISK_ESCALATION_THRESHOLD,
    RISK_FLAG_THRESHOLD,
    RISK_HIGH_FLAG_THRESHOLD,
)

logger = logging.getLogger("goldshield.agents.risk_officer")


def fuse(
    density: Optional[DensityResult],
    surface: Optional[SurfaceResult],
    hallmark: Optional[HallmarkResult],
    touchstone: Optional[TouchstoneResult],
    light_signature: Optional[LightSignatureResult],
) -> RiskOfficerVerdict:
    """
    Fuse all 5 inspector outputs into a single explainable verdict.

    Logic:
    - All pass with high confidence → high authenticity, low fraud, no escalation
    - One flag, others pass → moderate fraud, name the specific signal, recommend review
    - Density borderline + others pass → explicit tungsten escalation
    - Multiple flags → high fraud, strong escalation
    """
    # Collect all results
    results = {}
    flags = []
    passes = []
    inconclusive = []
    reasoning_parts = []

    # ─── Analyze each inspector's output ────────────────────────────────

    if density:
        results["density"] = density.result
        if density.result == InspectorResult.FLAG:
            flags.append(("density", density.reason))
            reasoning_parts.append(f"⚠ DENSITY: {density.reason}")
        elif density.result == InspectorResult.INCONCLUSIVE:
            inconclusive.append(("density", density.reason))
            reasoning_parts.append(f"⚡ DENSITY (inconclusive): {density.reason}")
        else:
            passes.append("density")
            reasoning_parts.append(f"✓ Density: {density.density_gcm3} g/cm³ — within expected range")
    else:
        inconclusive.append(("density", "Density analysis not performed"))

    if surface:
        results["surface"] = surface.result
        if surface.result == InspectorResult.FLAG:
            flags.append(("surface", f"{surface.location}: {surface.observation}" if surface.location else surface.observation))
            reasoning_parts.append(f"⚠ SURFACE: {surface.observation}" + (f" at {surface.location}" if surface.location else ""))
        elif surface.result == InspectorResult.INCONCLUSIVE:
            inconclusive.append(("surface", surface.observation))
        else:
            passes.append("surface")
            reasoning_parts.append(f"✓ Surface: {surface.observation}")
    else:
        inconclusive.append(("surface", "Surface analysis not performed"))

    if hallmark:
        results["hallmark"] = hallmark.result
        if hallmark.result == InspectorResult.FLAG:
            flags.append(("hallmark", f"Hallmark issue — confidence: {hallmark.confidence:.0%}"))
            reasoning_parts.append(f"⚠ HALLMARK: Verification failed (confidence: {hallmark.confidence:.0%})")
        elif hallmark.result == InspectorResult.INCONCLUSIVE:
            inconclusive.append(("hallmark", "Hallmark could not be clearly read"))
        else:
            passes.append("hallmark")
            reasoning_parts.append(f"✓ Hallmark: {hallmark.hallmark_detected} (confidence: {hallmark.confidence:.0%})")
    else:
        inconclusive.append(("hallmark", "Hallmark analysis not performed"))

    if touchstone:
        results["touchstone"] = touchstone.result
        if touchstone.result == InspectorResult.FLAG:
            flags.append(("touchstone", touchstone.streak_color_match))
            reasoning_parts.append(f"⚠ TOUCHSTONE: {touchstone.streak_color_match}")
        elif touchstone.result == InspectorResult.INCONCLUSIVE:
            inconclusive.append(("touchstone", touchstone.streak_color_match))
        else:
            passes.append("touchstone")
            reasoning_parts.append(f"✓ Touchstone: {touchstone.streak_color_match}")
    else:
        inconclusive.append(("touchstone", "Touchstone analysis not performed"))

    if light_signature:
        results["light_signature"] = light_signature.result
        if light_signature.result == InspectorResult.FLAG:
            flags.append(("light_signature", light_signature.reflectance_consistency))
            reasoning_parts.append(f"⚠ LIGHT-SIGNATURE: {light_signature.reflectance_consistency}")
        elif light_signature.result == InspectorResult.INCONCLUSIVE:
            inconclusive.append(("light_signature", light_signature.reflectance_consistency))
        else:
            passes.append("light_signature")
            reasoning_parts.append(f"✓ Light-Signature: reflectance {light_signature.reflectance_consistency}")
    else:
        inconclusive.append(("light_signature", "Light-signature analysis not performed"))

    # ─── Fusion Logic ───────────────────────────────────────────────────

    total_signals = len(flags) + len(passes) + len(inconclusive)
    flag_count = len(flags)
    pass_count = len(passes)
    inconclusive_count = len(inconclusive)

    # Determine suspicious area (from the most critical flag)
    suspicious_area = None
    if flags:
        # Priority: density > surface > hallmark > touchstone > light
        priority_order = ["density", "surface", "hallmark", "touchstone", "light_signature"]
        for signal in priority_order:
            for flag_name, flag_reason in flags:
                if flag_name == signal:
                    suspicious_area = flag_name
                    break
            if suspicious_area:
                break
        if not suspicious_area:
            suspicious_area = flags[0][0]

    # ─── Case 1: All pass ───────────────────────────────────────────────
    if flag_count == 0 and inconclusive_count == 0:
        authenticity_score = 92
        fraud_probability = 5
        confidence = 88
        recommendation = "Verification passed — proceed with appraisal"
        escalated = False
        reasoning_parts.append("\n→ All 5 verification signals passed. High confidence in authenticity.")

    # ─── Case 2: All pass but some inconclusive ────────────────────────
    elif flag_count == 0 and inconclusive_count > 0:
        authenticity_score = 78
        fraud_probability = 12
        confidence = 65
        recommendation = "Mostly passed — manual review recommended for inconclusive signals"
        escalated = inconclusive_count >= 2
        reasoning_parts.append(
            f"\n→ {pass_count} signals passed, {inconclusive_count} inconclusive. "
            f"No flags raised but full confidence not achievable."
        )

    # ─── Case 3: Density specifically inconclusive (tungsten edge case) ─
    elif (density and density.result == InspectorResult.INCONCLUSIVE
          and flag_count == 0):
        authenticity_score = 70
        fraud_probability = 20
        confidence = 55
        recommendation = (
            "ESCALATION REQUIRED — Density is inconclusive due to the known tungsten-density-matching "
            "limitation. Tungsten (19.25 g/cm³) is dangerously close to gold (19.3 g/cm³). "
            "Non-destructive verification alone cannot distinguish them with certainty. "
            "Recommend lab-grade testing (XRF, specific gravity via hydrostatic weighing) "
            "for definitive verification."
        )
        escalated = True
        suspicious_area = "density (tungsten edge case)"
        reasoning_parts.append(
            "\n→ TUNGSTEN LIMITATION: This system honestly acknowledges that density-based "
            "detection has a known blind spot for tungsten cores. All other visual signals "
            "passed, but this does NOT rule out a sophisticated tungsten-core counterfeit. "
            "Mandatory escalation to manual/lab verification."
        )

    # ─── Case 4: Single flag ───────────────────────────────────────────
    elif flag_count == 1:
        authenticity_score = 55
        fraud_probability = 40
        confidence = 72
        flag_name, flag_reason = flags[0]
        recommendation = (
            f"Manual verification required — {flag_name} inspector flagged an anomaly. "
            f"Other signals did not corroborate, so this may be a false positive, "
            f"but caution is warranted."
        )
        escalated = True
        reasoning_parts.append(
            f"\n→ 1 signal flagged ({flag_name}), {pass_count} passed, "
            f"{inconclusive_count} inconclusive. Moderate concern — recommend manual review "
            f"focused on the {flag_name} finding."
        )

    # ─── Case 5: Multiple flags ────────────────────────────────────────
    elif flag_count >= RISK_HIGH_FLAG_THRESHOLD:
        authenticity_score = max(15, 100 - (flag_count * 25))
        fraud_probability = min(90, 30 + (flag_count * 20))
        confidence = 85
        flag_names = [f[0] for f in flags]
        recommendation = (
            f"HIGH RISK — {flag_count} independent signals flagged anomalies "
            f"({', '.join(flag_names)}). Strong recommendation against proceeding "
            f"without thorough manual and/or lab verification."
        )
        escalated = True
        reasoning_parts.append(
            f"\n→ MULTIPLE FLAGS: {flag_count} independent verification signals detected "
            f"anomalies. The probability of all being false positives simultaneously "
            f"is low. This item requires mandatory manual verification before any "
            f"loan can be sanctioned."
        )

    # ─── Fallback ──────────────────────────────────────────────────────
    else:
        authenticity_score = 50
        fraud_probability = 35
        confidence = 60
        recommendation = "Manual verification required — mixed signals from inspectors"
        escalated = True
        reasoning_parts.append(
            f"\n→ Mixed results: {flag_count} flags, {pass_count} passes, "
            f"{inconclusive_count} inconclusive. Cannot make a confident automated determination."
        )

    # ─── Build final reasoning ──────────────────────────────────────────
    full_reasoning = "\n".join(reasoning_parts)

    return RiskOfficerVerdict(
        authenticity_score=authenticity_score,
        fraud_probability=fraud_probability,
        confidence=confidence,
        suspicious_area=suspicious_area,
        reasoning=full_reasoning,
        recommendation=recommendation,
        escalated=escalated,
        density_result=density,
        surface_result=surface,
        hallmark_result=hallmark,
        touchstone_result=touchstone,
        light_signature_result=light_signature,
    )
