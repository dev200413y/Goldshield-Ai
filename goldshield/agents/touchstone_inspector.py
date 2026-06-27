"""
GoldShield AI — Touchstone / Reflectance Inspector (Agent 4)
Analyzes the streak left on a touchstone under the traditional rub test.

NOTE: This agent inherits the same blind spot as the manual touchstone test
(it only reads the outer layer). Included for completeness and cross-checking,
NOT as the primary contamination detector (that's the Density Inspector).
"""

import logging
from typing import List

from goldshield.models import TouchstoneResult, InspectorResult
from goldshield.vision.vision_provider import vision_call, extract_json_from_response

logger = logging.getLogger("goldshield.agents.touchstone")

TOUCHSTONE_ANALYSIS_PROMPT = """You are an expert gold assayer analyzing a touchstone test result.

A touchstone test works by rubbing a gold item against a dark, fine-grained stone (like lydite/basalt).
The streak left on the stone is compared to reference streaks from known-purity gold samples.

Analyze this photo of a touchstone streak and evaluate:

1. **Streak Color**: Genuine gold leaves a characteristic yellow-gold streak.
   - 24K: Rich, deep yellow-gold
   - 22K: Slightly warmer/darker yellow-gold
   - 18K: Paler yellow, may have slight greenish or reddish tint depending on alloy
   - Plated/fake: May show different color, inconsistent streak, or fade quickly

2. **Streak Width**: Should be relatively uniform along the mark
3. **Streak Luster**: Genuine gold maintains a bright metallic sheen in the streak
4. **Streak Consistency**: Even color throughout, vs. patchy or multi-toned

Compare against reference characteristics for genuine gold streaks.

Return as JSON:
{
  "streak_analysis": {
    "color": "description of streak color",
    "width": "description",
    "luster": "description",
    "comparison": "how it compares to genuine gold reference"
  },
  "result": "PASS" or "FLAG",
  "confidence": 0.0-1.0,
  "streak_color_match": "summary comparison with declared caratage reference"
}

FLAG if the streak color, consistency, or luster is inconsistent with genuine gold.
PASS if the streak matches expected characteristics.

IMPORTANT: Remember that a PASS here only confirms the SURFACE LAYER is gold — 
it cannot detect a non-gold core underneath. State this honestly."""


async def inspect(photos_base64: List[str]) -> TouchstoneResult:
    """
    Run the Touchstone / Reflectance Inspector.
    Expects a photo of the streak mark on the touchstone.
    """
    if not photos_base64:
        return TouchstoneResult(
            result=InspectorResult.INCONCLUSIVE,
            streak_color_match="No touchstone photo provided for analysis.",
            provider="none",
        )

    photo = photos_base64[0]
    response_text, provider = await vision_call(photo, TOUCHSTONE_ANALYSIS_PROMPT)
    parsed = extract_json_from_response(response_text)

    # Extract results
    result_str = parsed.get("result", "PASS").upper()
    if result_str == "FLAG":
        result = InspectorResult.FLAG
    elif result_str == "INCONCLUSIVE":
        result = InspectorResult.INCONCLUSIVE
    else:
        result = InspectorResult.PASS

    streak_match = parsed.get(
        "streak_color_match",
        parsed.get("streak_analysis", {}).get("comparison", "Analysis complete.")
    )

    return TouchstoneResult(
        result=result,
        streak_color_match=streak_match,
        provider=provider,
    )
