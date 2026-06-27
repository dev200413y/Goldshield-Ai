"""
GoldShield AI — Surface & Seam Inspector (Agent 2)
Detects visual evidence of plating, soldering, or base-metal exposure.
"""

import logging
from typing import List

from goldshield.models import SurfaceResult, InspectorResult
from goldshield.vision.vision_provider import vision_call, extract_json_from_response

logger = logging.getLogger("goldshield.agents.surface")

SURFACE_ANALYSIS_PROMPT = """You are an expert gold jewelry analyst inspecting a piece of jewelry for authenticity.
Analyze this image carefully and look for the following signs of potential counterfeiting or plating:

1. **Solder joints**: Any visible solder marks that appear different in color or texture from the rest
2. **Color inconsistency**: Areas where the gold color differs, especially at edges, joints, clasps, or bends
3. **Wear patterns**: Any areas where wear has exposed a different-colored metal underneath the surface
4. **Plating edges**: Visible boundaries where a gold coating meets a different substrate material
5. **Surface texture**: Uneven or inconsistent surface finish that might indicate electroplating
6. **Construction anomalies**: Any signs inconsistent with solid-gold manufacturing techniques

Return your analysis as JSON with these fields:
{
  "surface_analysis": {
    "color_consistency": "description",
    "solder_joints": "description",
    "wear_patterns": "description",
    "plating_edges": "description",
    "anomalies": ["list of specific anomalies found, if any"]
  },
  "result": "PASS" or "FLAG",
  "location": "where the most significant finding is, or null",
  "confidence": 0.0-1.0,
  "observations": "summary observation"
}

Be thorough but honest. If the image quality limits your analysis, say so.
Only FLAG if you see genuine evidence of plating or base-metal exposure."""


async def inspect(photos_base64: List[str]) -> SurfaceResult:
    """
    Run the Surface & Seam Inspector on multi-angle photos.
    Uses the first available photo; could be enhanced to analyze multiple angles.
    """
    if not photos_base64:
        return SurfaceResult(
            result=InspectorResult.INCONCLUSIVE,
            location=None,
            observation="No photos provided for surface analysis.",
            provider="none",
        )

    # Analyze primary photo (ideally the highest-detail close-up)
    photo = photos_base64[0]
    response_text, provider = await vision_call(photo, SURFACE_ANALYSIS_PROMPT)
    parsed = extract_json_from_response(response_text)

    # Extract results
    result_str = parsed.get("result", "PASS").upper()
    if result_str == "FLAG":
        result = InspectorResult.FLAG
    elif result_str == "INCONCLUSIVE":
        result = InspectorResult.INCONCLUSIVE
    else:
        result = InspectorResult.PASS

    location = parsed.get("location", None)
    observation = parsed.get("observations", parsed.get("observation", "Analysis complete."))

    # If there are anomalies listed, include them in the observation
    surface_detail = parsed.get("surface_analysis", {})
    anomalies = surface_detail.get("anomalies", [])
    if anomalies:
        observation += f" Anomalies detected: {', '.join(anomalies)}"

    return SurfaceResult(
        result=result,
        location=location,
        observation=observation,
        provider=provider,
    )
