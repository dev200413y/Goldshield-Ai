"""
GoldShield AI — Volume Estimator (Path 2: Measurement Layer)

Standalone module for estimating jewelry volume from uploaded photos using
reference-object scale detection + geometric shape heuristics.

This is the ONLY source of volume_cm3 used by the Density & Volume Inspector.
The visual 3D model (Path 1: InstantMesh) must NEVER be used for this calculation.

Method:
  1. Vision AI detects a reference object (₹1 coin = 25mm, ruler, etc.) in the photo
  2. Computes pixel-to-cm scale ratio from the reference object
  3. Estimates physical dimensions (mm) of the jewelry item
  4. Applies jewelry-shape heuristics (torus, hollow cylinder, etc.) to compute volume
  5. Returns volume_cm3 + metadata for the density inspector
"""

import math
import logging
from typing import List, Dict, Any, Optional

from goldshield.vision.vision_provider import vision_call, extract_json_from_response
from goldshield.config import JEWELRY_SHAPES

logger = logging.getLogger("goldshield.vision.volume_estimator")


# ─── Reference Object Database ──────────────────────────────────────────────
# Known physical sizes for common reference objects (in mm)
REFERENCE_OBJECTS = {
    "1_rupee_coin": {"diameter_mm": 25.0, "description": "₹1 coin"},
    "2_rupee_coin": {"diameter_mm": 27.0, "description": "₹2 coin"},
    "5_rupee_coin": {"diameter_mm": 23.0, "description": "₹5 coin"},
    "10_rupee_coin": {"diameter_mm": 27.0, "description": "₹10 coin"},
    "ruler_cm": {"unit_mm": 10.0, "description": "Ruler (1 cm mark)"},
    "us_quarter": {"diameter_mm": 24.3, "description": "US Quarter"},
    "credit_card": {"width_mm": 85.6, "height_mm": 53.98, "description": "Standard credit card"},
}


# ─── Volume Calculation Functions ────────────────────────────────────────────
# These are pure math — no AI, no estimation. Given precise dimensions, they
# return the exact geometric volume.

def _torus_volume(outer_d_mm: float, inner_d_mm: float, thickness_mm: float) -> float:
    """Ring approximation: V = 2π²Rr²"""
    R = (outer_d_mm + inner_d_mm) / 4.0
    r = (outer_d_mm - inner_d_mm) / 4.0
    if r <= 0:
        r = thickness_mm / 2.0
    return (2 * math.pi**2 * R * r**2) / 1000.0  # mm³ → cm³


def _hollow_cylinder_volume(outer_d_mm: float, inner_d_mm: float, width_mm: float) -> float:
    """Bangle approximation: V = π(R²-r²)h"""
    R = outer_d_mm / 2.0
    r = inner_d_mm / 2.0
    return (math.pi * (R**2 - r**2) * width_mm) / 1000.0


def _cylindrical_links_volume(link_d_mm: float, link_count: int, link_len_mm: float) -> float:
    """Chain/bracelet approximation: sum of cylindrical links."""
    r = link_d_mm / 2.0
    return (math.pi * r**2 * link_len_mm * link_count) / 1000.0


def _flat_disc_volume(diameter_mm: float, thickness_mm: float) -> float:
    """Pendant/coin approximation: V = πr²h"""
    r = diameter_mm / 2.0
    return (math.pi * r**2 * thickness_mm) / 1000.0


def _rectangular_prism_volume(length_mm: float, width_mm: float, height_mm: float) -> float:
    """Gold bar approximation: V = l×w×h"""
    return (length_mm * width_mm * height_mm) / 1000.0


def calculate_volume_from_dimensions(shape_type: str, dimensions: dict) -> float:
    """
    Given a shape type and dimension dict, compute the geometric volume in cm³.
    This is pure math — deterministic and repeatable.
    """
    shape = JEWELRY_SHAPES.get(shape_type, "flat_disc")

    try:
        if shape == "torus":
            return _torus_volume(
                dimensions.get("outer_diameter_mm", 20.0),
                dimensions.get("inner_diameter_mm", 16.0),
                dimensions.get("thickness_mm", 3.0),
            )
        elif shape == "hollow_cylinder":
            return _hollow_cylinder_volume(
                dimensions.get("outer_diameter_mm", 70.0),
                dimensions.get("inner_diameter_mm", 64.0),
                dimensions.get("width_mm", 8.0),
            )
        elif shape == "cylindrical_links":
            return _cylindrical_links_volume(
                dimensions.get("link_diameter_mm", 2.0),
                dimensions.get("link_count", 200),
                dimensions.get("link_length_mm", 5.0),
            )
        elif shape in ("flat_disc", "flat_cylinder", "small_disc"):
            return _flat_disc_volume(
                dimensions.get("diameter_mm", 25.0),
                dimensions.get("thickness_mm", 2.0),
            )
        elif shape == "rectangular_prism":
            return _rectangular_prism_volume(
                dimensions.get("length_mm", 50.0),
                dimensions.get("width_mm", 25.0),
                dimensions.get("height_mm", 5.0),
            )
        else:
            # Fallback: bounding box with 60% fill factor
            l = dimensions.get("length_mm", 25.0)
            w = dimensions.get("width_mm", 20.0)
            h = dimensions.get("thickness_mm", 3.0)
            return (l * w * h * 0.6) / 1000.0
    except Exception as e:
        logger.warning(f"Volume calculation error: {e}, using fallback")
        return 2.0  # Safe fallback for a typical ring


# ─── AI-Powered Dimension Estimation ────────────────────────────────────────

DIMENSION_PROMPT = """You are a precision measurement system analyzing photos of gold jewelry.

CRITICAL TASK: Estimate the physical dimensions of the jewelry item in the photo.

STEP 1 — REFERENCE OBJECT DETECTION:
Look for any of these known-size reference objects in the frame:
- ₹1 coin (25mm diameter)
- ₹2 coin (27mm diameter)  
- ₹5 coin (23mm diameter)
- ₹10 coin (27mm diameter)
- Ruler with cm markings
- Credit card (85.6mm × 54mm)

If a reference object is found, use its known size to calibrate your pixel-to-mm scale.
If NO reference object is found, estimate dimensions based on typical jewelry proportions.

STEP 2 — ITEM IDENTIFICATION:
Identify the jewelry type: ring, bangle, chain, pendant, earring, necklace, bracelet, coin, or bar.

STEP 3 — DIMENSION ESTIMATION:
Based on the item type, estimate these dimensions in millimeters:

For a RING: outer_diameter_mm, inner_diameter_mm, thickness_mm, width_mm
For a BANGLE: outer_diameter_mm, inner_diameter_mm, width_mm
For a CHAIN/NECKLACE/BRACELET: link_diameter_mm, link_count (estimate), link_length_mm
For a PENDANT/COIN: diameter_mm, thickness_mm
For a BAR: length_mm, width_mm, height_mm

Return your answer as JSON with these exact fields:
{{
  "reference_object": {{
    "type": "1_rupee_coin" or "ruler_cm" or "none",
    "detected": true/false,
    "known_size_mm": 25.0
  }},
  "item_type": "ring",
  "estimated_dimensions": {{
    "outer_diameter_mm": 20.0,
    "inner_diameter_mm": 16.0,
    "thickness_mm": 3.0,
    "width_mm": 5.0
  }},
  "scale_confidence": 0.85,
  "measurement_notes": "Reference coin detected, calibrated scale used"
}}

The item being analyzed is described as: {item_type}
Weight on scale: {weight_grams}g
Declared purity: {declared_purity}

Be as precise as possible. The volume calculated from your dimensions will be used
to compute density for fraud detection.
"""


async def estimate_volume(
    photos_base64: List[str],
    item_type: str = "ring",
    weight_grams: float = 10.0,
    declared_purity: str = "22K",
) -> Dict[str, Any]:
    """
    Estimate the volume of a jewelry item from uploaded photos.
    
    This is the SOLE source of volume data for the Density & Volume Inspector.
    
    Returns:
        {
            "volume_cm3": float,
            "dimensions": dict,
            "reference_detected": str,  
            "scale_confidence": float,
            "method": "reference_scale_heuristic" | "ai_estimation",
            "provider": str,
            "measurement_notes": str,
        }
    """
    if not photos_base64:
        logger.warning("No photos provided for volume estimation. Using weight-based fallback.")
        # Weight-based rough estimate: assume density near expected for declared purity
        # This is a last-resort fallback
        return {
            "volume_cm3": weight_grams / 17.8,  # Assume ~22K density
            "dimensions": {},
            "reference_detected": "none",
            "scale_confidence": 0.1,
            "method": "weight_fallback",
            "provider": "none",
            "measurement_notes": "No photos available — used weight-based density assumption (low confidence).",
        }

    # Build the prompt with item context
    prompt = DIMENSION_PROMPT.format(
        item_type=item_type,
        weight_grams=weight_grams,
        declared_purity=declared_purity,
    )

    # Use the first photo for dimension estimation
    photo = photos_base64[0]
    response_text, provider = await vision_call(photo, prompt)
    parsed = extract_json_from_response(response_text)

    # Extract structured fields
    dimensions = parsed.get("estimated_dimensions", {})
    detected_type = parsed.get("item_type", item_type)
    ref_info = parsed.get("reference_object", {})
    scale_confidence = parsed.get("scale_confidence", 0.5)
    notes = parsed.get("measurement_notes", "")

    # Determine reference detection status
    ref_detected = "none"
    if isinstance(ref_info, dict):
        if ref_info.get("detected", False):
            ref_detected = ref_info.get("type", "unknown")
    elif isinstance(ref_info, str) and ref_info.lower() not in ["none", "false", "no"]:
        ref_detected = ref_info

    # Calculate volume using shape heuristics
    volume_cm3 = calculate_volume_from_dimensions(detected_type or item_type, dimensions)

    # Determine method label
    method = "reference_scale_heuristic" if ref_detected != "none" else "ai_estimation"

    logger.info(
        f"Volume estimated: {volume_cm3:.4f} cm³ | "
        f"Method: {method} | Reference: {ref_detected} | "
        f"Confidence: {scale_confidence} | Provider: {provider}"
    )

    return {
        "volume_cm3": volume_cm3,
        "dimensions": dimensions,
        "reference_detected": ref_detected,
        "scale_confidence": scale_confidence,
        "method": method,
        "provider": provider,
        "measurement_notes": notes,
    }
