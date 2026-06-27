"""
GoldShield AI — Density & Volume Inspector (Agent 1)
THE core agent that looks THROUGH the coating — directly solving the touchstone blind spot.

Method:
  1. Send multi-angle photos to vision model to estimate item dimensions
  2. Apply jewelry-shape heuristics (ring=torus, chain=cylindrical links, etc.)
  3. Calculate volume in cm³
  4. Compute density = weight / volume
  5. Compare against expected range for declared caratage
"""

import math
import logging
from typing import List

from goldshield.models import DensityResult, InspectorResult
from goldshield.config import GOLD_DENSITY_TABLE, JEWELRY_SHAPES, FRAUD_METAL_DENSITIES, USE_PHOTOGRAMMETRY
from goldshield.vision.vision_provider import vision_call, extract_json_from_response
from goldshield.vision.photogrammetry import ColmapPipeline

logger = logging.getLogger("goldshield.agents.density")

# ─── Volume Estimation by Shape ─────────────────────────────────────────────

def _torus_volume(outer_diameter_mm: float, inner_diameter_mm: float, thickness_mm: float) -> float:
    """Volume of a torus (ring approximation). V = 2π²Rr²"""
    R = (outer_diameter_mm + inner_diameter_mm) / 4.0  # major radius (center of tube)
    r = (outer_diameter_mm - inner_diameter_mm) / 4.0   # minor radius (tube radius)
    if r <= 0:
        r = thickness_mm / 2.0
    volume_mm3 = 2 * math.pi**2 * R * r**2
    return volume_mm3 / 1000.0  # convert mm³ to cm³


def _hollow_cylinder_volume(outer_diameter_mm: float, inner_diameter_mm: float, width_mm: float) -> float:
    """Volume of a hollow cylinder (bangle approximation). V = π(R²-r²)h"""
    R = outer_diameter_mm / 2.0
    r = inner_diameter_mm / 2.0
    volume_mm3 = math.pi * (R**2 - r**2) * width_mm
    return volume_mm3 / 1000.0


def _cylindrical_links_volume(link_diameter_mm: float, link_count: int, link_length_mm: float) -> float:
    """Volume of chain/bracelet approximated as cylindrical links."""
    r = link_diameter_mm / 2.0
    volume_per_link_mm3 = math.pi * r**2 * link_length_mm
    total_mm3 = volume_per_link_mm3 * link_count
    return total_mm3 / 1000.0


def _flat_disc_volume(diameter_mm: float, thickness_mm: float) -> float:
    """Volume of a flat disc (pendant/coin approximation). V = πr²h"""
    r = diameter_mm / 2.0
    volume_mm3 = math.pi * r**2 * thickness_mm
    return volume_mm3 / 1000.0


def _rectangular_prism_volume(length_mm: float, width_mm: float, height_mm: float) -> float:
    """Volume of a rectangular prism (gold bar approximation)."""
    volume_mm3 = length_mm * width_mm * height_mm
    return volume_mm3 / 1000.0


def estimate_volume(item_type: str, dimensions: dict) -> float:
    """
    Estimate volume based on item type and extracted dimensions.
    Falls back to a bounding-box approximation if specific shape params are missing.
    """
    shape = JEWELRY_SHAPES.get(item_type, "flat_disc")

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
        elif shape == "flat_disc":
            return _flat_disc_volume(
                dimensions.get("diameter_mm", 25.0),
                dimensions.get("thickness_mm", 2.0),
            )
        elif shape == "flat_cylinder":
            return _flat_disc_volume(
                dimensions.get("diameter_mm", 30.0),
                dimensions.get("thickness_mm", 3.0),
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
        logger.warning(f"Volume estimation error: {e}, using fallback")
        return 2.0  # Safe fallback for a typical ring


def _identify_possible_core_metal(density: float) -> str:
    """If density doesn't match gold, suggest what metal it might be."""
    closest_metal = None
    closest_diff = float('inf')
    for metal, metal_density in FRAUD_METAL_DENSITIES.items():
        diff = abs(density - metal_density)
        if diff < closest_diff:
            closest_diff = diff
            closest_metal = metal
    if closest_diff < 1.5:
        return closest_metal
    return "unknown alloy"


async def inspect(
    photos_base64: List[str],
    weight_grams: float,
    item_type: str = "ring",
    declared_purity: str = "22K",
) -> DensityResult:
    """
    Run the Density & Volume Inspector.
    
    1. Vision model estimates dimensions from photos
    2. Volume is calculated using shape heuristics
    3. Density is computed and compared to expected range
    """
    # Get expected density range
    expected_range = list(GOLD_DENSITY_TABLE.get(declared_purity, (17.7, 17.9)))

    # Step 1: Volume Estimation
    provider_used = "none"
    volume_cm3 = 0.0

    if USE_PHOTOGRAMMETRY and photos_base64:
        logger.info("Photogrammetry is ENABLED. Running COLMAP 3D Reconstruction...")
        pipeline = ColmapPipeline()
        pipeline.save_images(photos_base64)
        mesh_vol = pipeline.run_pipeline()
        
        if mesh_vol is not None:
            volume_cm3 = mesh_vol
            provider_used = "colmap_photogrammetry"
        else:
            logger.warning("Photogrammetry pipeline failed or COLMAP missing. Falling back to AI heuristics.")

    if volume_cm3 <= 0:
        # Fallback to AI heuristic estimation
        dimension_prompt = f"""You are analyzing photos of a gold {item_type} for volume estimation.
A reference object (coin or ruler) may be visible in the frame for scale.

Please estimate the following dimensions in millimeters:
- For a ring: outer_diameter_mm, inner_diameter_mm, thickness_mm, width_mm
- For a bangle: outer_diameter_mm, inner_diameter_mm, width_mm
- For a chain/necklace/bracelet: link_diameter_mm, link_count (estimate), link_length_mm
- For a pendant/coin: diameter_mm, thickness_mm
- For a bar: length_mm, width_mm, height_mm

Also identify the item type if possible.

Return your answer as JSON with an "estimated_dimensions" object and "item_type" field.
If a reference object is visible, note it in a "reference_object" field."""

        # Use first photo for dimension estimation
        photo = photos_base64[0] if photos_base64 else ""
        response_text, provider_used = await vision_call(photo, dimension_prompt)
        parsed = extract_json_from_response(response_text)

        # Extract dimensions
        dimensions = parsed.get("estimated_dimensions", {})
        detected_type = parsed.get("item_type", item_type)
        
        # Calculate heuristic volume
        volume_cm3 = estimate_volume(detected_type or item_type, dimensions)

    # Step 2: Compute density
    if volume_cm3 <= 0:
        volume_cm3 = 0.01  # Prevent division by zero
    density = weight_grams / volume_cm3

    # Step 4: Compare against expected range
    low, high = expected_range
    tolerance = 2.0  # Allow ±2 g/cm³ tolerance for estimation errors

    if low - tolerance <= density <= high + tolerance:
        if low <= density <= high:
            result = InspectorResult.PASS
            reason = (
                f"Density {density:.2f} g/cm³ is within the expected range "
                f"[{low}–{high}] for {declared_purity} gold."
            )
        else:
            result = InspectorResult.PASS
            reason = (
                f"Density {density:.2f} g/cm³ is near the expected range "
                f"[{low}–{high}] for {declared_purity} gold (within estimation tolerance)."
            )
    else:
        # Check for tungsten edge case
        tungsten_density = FRAUD_METAL_DENSITIES["tungsten"]
        if abs(density - tungsten_density) < 0.5 and declared_purity in ("24K", "22K"):
            result = InspectorResult.INCONCLUSIVE
            reason = (
                f"Density {density:.2f} g/cm³ is close to both gold ({high} g/cm³) "
                f"and tungsten ({tungsten_density} g/cm³). "
                f"KNOWN LIMITATION: Tungsten's density (19.25 g/cm³) is dangerously close "
                f"to gold's (19.3 g/cm³) — this signal alone cannot distinguish them. "
                f"Escalation to additional verification methods recommended."
            )
        else:
            possible_metal = _identify_possible_core_metal(density)
            if density < low:
                result = InspectorResult.FLAG
                reason = (
                    f"Density {density:.2f} g/cm³ is BELOW the expected range "
                    f"[{low}–{high}] for {declared_purity} gold. "
                    f"Possible core material: {possible_metal} ({FRAUD_METAL_DENSITIES.get(possible_metal, '?')} g/cm³). "
                    f"This suggests the item may contain a non-gold core beneath the surface layer."
                )
            else:
                result = InspectorResult.FLAG
                reason = (
                    f"Density {density:.2f} g/cm³ is ABOVE the expected range "
                    f"[{low}–{high}] for {declared_purity} gold. "
                    f"Possible heavy-metal contamination or measurement anomaly."
                )

    return DensityResult(
        density_gcm3=round(density, 2),
        estimated_volume_cm3=round(volume_cm3, 4),
        expected_range=expected_range,
        result=result,
        reason=reason,
        provider=provider_used,
    )
