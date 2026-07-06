"""
GoldShield AI — Hallmark Verification Inspector (Agent 3)
Verifies BIS hallmark presence, placement, and pattern consistency via OCR.
"""

import logging
from typing import List

from goldshield.models import HallmarkResult, InspectorResult
from goldshield.vision.vision_provider import vision_call, extract_json_from_response

logger = logging.getLogger("goldshield.agents.hallmark")

HALLMARK_ANALYSIS_PROMPT = """You are an expert at reading and verifying hallmarks, assay marks, and stamps on gold jewelry and bullion.

Analyze this close-up image of a jewelry hallmark stamp or bullion assay mark.

For Indian Jewelry (BIS Hallmark), check for:
1. **BIS Logo**: The triangular BIS standard mark
2. **Purity/Caratage Code**: 999 (24K), 916 (22K), 875 (21K), 750 (18K), 585 (14K)
3. **HUID**: A 6-character alphanumeric code
4. **Assaying Centre / Jeweller Mark**

For International Bullion / Bars:
1. **Assayer/Refiner Logo or Name**: e.g., Credit Suisse, PAMP, Valcambi, etc.
2. **Purity/Fineness**: e.g., 999.9, 999
3. **Weight**: e.g., 1 Kilo, 1 oz
4. **Serial Number**: If present.

Return your analysis as JSON:
{
  "hallmark_analysis": {
    "bis_mark_detected": true/false,
    "caratage_code": "e.g., 916, 999.9",
    "huid": "HUID or Serial Number if detected",
    "hallmarking_center": "detected or not",
    "jeweler_id": "detected Maker/Refiner",
    "placement": "description of where the mark is",
    "font_consistency": "description"
  },
  "result": "PASS" or "FLAG",
  "confidence": 0.0-1.0,
  "full_hallmark_text": "complete text as read from the stamp"
}

FLAG if: hallmark/assay mark is missing, malformed, or doesn't match expected formats.
PASS if: hallmark OR international bullion mark appears genuine with all required components present."""


async def inspect(photos_base64: List[str]) -> HallmarkResult:
    """
    Run the Hallmark Verification Inspector.
    Expects at least one close-up photo of the hallmark stamp area.
    """
    if not photos_base64:
        return HallmarkResult(
            result=InspectorResult.INCONCLUSIVE,
            hallmark_detected=None,
            confidence=0.0,
            provider="none",
        )

    # Use the hallmark close-up photo (ideally provided separately)
    photo = photos_base64[-1] if len(photos_base64) > 1 else photos_base64[0]
    response_text, provider = await vision_call(photo, HALLMARK_ANALYSIS_PROMPT)
    parsed = extract_json_from_response(response_text)

    # Extract results
    result_str = parsed.get("result", "PASS").upper()
    if result_str == "FLAG":
        result = InspectorResult.FLAG
    elif result_str == "INCONCLUSIVE":
        result = InspectorResult.INCONCLUSIVE
    else:
        result = InspectorResult.PASS

    hallmark_text = parsed.get("full_hallmark_text", None)
    confidence = float(parsed.get("confidence", 0.85))

    # Build detected hallmark string from components if full text not available
    if not hallmark_text:
        analysis = parsed.get("hallmark_analysis", {})
        if analysis.get("bis_mark_detected"):
            parts = ["BIS"]
            if analysis.get("caratage_code"):
                parts.append(analysis["caratage_code"])
            if analysis.get("huid"):
                parts.append(f"HUID-{analysis['huid']}")
            hallmark_text = " ".join(parts)

    return HallmarkResult(
        result=result,
        hallmark_detected=hallmark_text,
        confidence=confidence,
        provider=provider,
    )
