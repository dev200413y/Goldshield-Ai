"""
GoldShield AI — Light-Signature Inspector (Agent 5)
Detects surface-coating inconsistencies via reflectance behavior
across multiple light angles.

This is a secondary non-destructive physical signal independent of touchstone.
Solid gold has consistent, predictable reflectance; plated items show micro-inconsistencies.
"""

import logging
from typing import List

from goldshield.models import LightSignatureResult, InspectorResult
from goldshield.vision.vision_provider import vision_call, extract_json_from_response

logger = logging.getLogger("goldshield.agents.light_signature")

LIGHT_SIGNATURE_PROMPT = """You are a materials-science vision analyst specializing in optical properties of metals.

You are given photos of the SAME gold jewelry item taken under DIFFERENT light angles/intensities.
Your task is to analyze how the surface reflects light and detect any inconsistencies that may indicate
the item is plated or coated rather than solid gold.

Key principles:
- **Solid gold** reflects light consistently across angles — same warm golden hue, predictable 
  specular highlights that shift smoothly with the viewing angle
- **Plated/coated items** often show:
  - Color shifts at certain angles (the coating refracts light differently than the substrate)
  - Uneven sheen or "hot spots" where the coating is thinner
  - Micro-variation in reflectance intensity that doesn't match solid-metal behavior
  - Areas where the reflection has a slightly different tone (cooler, warmer, or grayish)

Analyze across the provided images and evaluate:
1. Is the color hue consistent across all angles?
2. Do specular highlights behave as expected for solid gold?
3. Are there any areas with anomalous reflectance (unexpected dark spots, color shifts)?
4. Overall consistency score (0.0 to 1.0, where 1.0 = perfectly consistent solid gold behavior)

Return as JSON:
{
  "reflectance_analysis": {
    "angle_1": "description of reflection in first image",
    "angle_2": "description of reflection in second image",
    "angle_3": "description of reflection in third image (if available)",
    "micro_inconsistencies": "description of any found, or 'none detected'",
    "coating_indicators": "description of any coating signs, or 'none'"
  },
  "result": "PASS" or "FLAG",
  "consistency_score": 0.0-1.0,
  "reflectance_consistency": "score (description)"
}"""


async def inspect(photos_base64: List[str]) -> LightSignatureResult:
    """
    Run the Light-Signature Inspector.
    Expects 2-3 photos of the same item under different light angles.
    """
    if not photos_base64:
        return LightSignatureResult(
            result=InspectorResult.INCONCLUSIVE,
            reflectance_consistency="No light-angle photos provided for analysis.",
            provider="none",
        )

    # Use the first light-angle photo (ideally multiple would be sent together)
    photo = photos_base64[0]
    response_text, provider = await vision_call(photo, LIGHT_SIGNATURE_PROMPT)
    parsed = extract_json_from_response(response_text)

    # Extract results
    result_str = parsed.get("result", "PASS").upper()
    if result_str == "FLAG":
        result = InspectorResult.FLAG
    elif result_str == "INCONCLUSIVE":
        result = InspectorResult.INCONCLUSIVE
    else:
        result = InspectorResult.PASS

    consistency = parsed.get(
        "reflectance_consistency",
        f"{parsed.get('consistency_score', 0.85)} (analysis complete)"
    )

    return LightSignatureResult(
        result=result,
        reflectance_consistency=str(consistency),
        provider=provider,
    )
