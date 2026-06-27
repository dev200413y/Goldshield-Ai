"""
GoldShield AI — Custody & Fingerprint Agent (Agent 8)
Generates Digital Gold Fingerprint at intake, re-verifies at closure.

Intake: Combines visual hash + hallmark signature + density signature → unique fingerprint ID
Closure: Re-scan comparison with similarity scoring → match/mismatch

A low match triggers mandatory hold and manual investigation before release.
This addresses in-custody tampering/swap risk.
"""

import hashlib
import logging
import random
import string
from datetime import datetime
from typing import Optional

from goldshield.models import (
    FingerprintRecord,
    ClosureVerification,
    MatchResult,
    DensityResult,
    HallmarkResult,
)
from goldshield.config import FINGERPRINT_MATCH_THRESHOLD

logger = logging.getLogger("goldshield.agents.custody_fingerprint")


def _generate_fingerprint_id() -> str:
    """Generate a unique fingerprint ID in format GF-YYYY-XXXXXX."""
    year = datetime.utcnow().year
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"GF-{year}-{random_part}"


def _compute_visual_hash(photos_base64: list) -> str:
    """
    Compute a hash from the visual content of photos.
    In production, this would use a visual embedding model.
    For the prototype, we use a content hash of the image data.
    """
    hasher = hashlib.sha256()
    for photo in photos_base64:
        hasher.update(photo.encode('utf-8')[:1000])  # Hash first 1000 chars
    return hasher.hexdigest()[:32]


def generate_fingerprint(
    photos_base64: list,
    hallmark_result: Optional[HallmarkResult] = None,
    density_result: Optional[DensityResult] = None,
) -> FingerprintRecord:
    """
    Generate a Digital Gold Fingerprint at intake.

    Combines:
    1. Visual hash (from photos)
    2. Hallmark signature (OCR'd text)
    3. Density signature (computed density value)

    Returns a unique fingerprint record with ID GF-YYYY-XXXXXX.
    """
    visual_hash = _compute_visual_hash(photos_base64) if photos_base64 else "no-photos"

    hallmark_sig = None
    if hallmark_result and hallmark_result.hallmark_detected:
        hallmark_sig = hallmark_result.hallmark_detected

    density_sig = None
    if density_result:
        density_sig = density_result.density_gcm3

    fingerprint = FingerprintRecord(
        fingerprint_id=_generate_fingerprint_id(),
        visual_hash=visual_hash,
        hallmark_signature=hallmark_sig,
        density_signature=density_sig,
        created_at=datetime.utcnow(),
    )

    logger.info(f"Generated fingerprint: {fingerprint.fingerprint_id}")
    return fingerprint


def verify_closure(
    original: FingerprintRecord,
    closure_photos_base64: list,
    closure_hallmark: Optional[HallmarkResult] = None,
    closure_density: Optional[DensityResult] = None,
) -> ClosureVerification:
    """
    Verify at loan closure that the returned item matches the original fingerprint.

    Compares:
    1. Visual hash similarity
    2. Hallmark signature match
    3. Density signature proximity

    Returns a numeric match_confidence (not just boolean) per requirements.
    """
    scores = []

    # Visual hash comparison
    closure_visual_hash = _compute_visual_hash(closure_photos_base64) if closure_photos_base64 else "no-photos"
    if original.visual_hash == closure_visual_hash:
        scores.append(1.0)
    else:
        # In production, use embedding cosine similarity instead of exact match
        # For prototype, partial credit if photos exist
        scores.append(0.6 if closure_photos_base64 else 0.0)

    # Hallmark comparison
    if original.hallmark_signature and closure_hallmark:
        if closure_hallmark.hallmark_detected == original.hallmark_signature:
            scores.append(1.0)
        else:
            scores.append(0.3)
    elif original.hallmark_signature:
        scores.append(0.5)  # Can't compare — no closure hallmark
    else:
        scores.append(0.8)  # Neither had hallmark — neutral

    # Density comparison
    if original.density_signature and closure_density:
        density_diff = abs(original.density_signature - closure_density.density_gcm3)
        if density_diff < 0.5:
            scores.append(1.0)
        elif density_diff < 1.5:
            scores.append(0.7)
        elif density_diff < 3.0:
            scores.append(0.4)
        else:
            scores.append(0.1)
    elif original.density_signature:
        scores.append(0.5)
    else:
        scores.append(0.8)

    # Weighted average (visual: 40%, hallmark: 30%, density: 30%)
    weights = [0.4, 0.3, 0.3]
    match_confidence = sum(s * w for s, w in zip(scores, weights))
    match_confidence = round(match_confidence, 2)

    # Determine result
    if match_confidence >= FINGERPRINT_MATCH_THRESHOLD:
        result = MatchResult.MATCH
    elif match_confidence >= 0.5:
        result = MatchResult.INCONCLUSIVE
    else:
        result = MatchResult.MISMATCH

    if result != MatchResult.MATCH:
        logger.warning(
            f"Closure verification {result.value} for {original.fingerprint_id}: "
            f"confidence {match_confidence} (threshold: {FINGERPRINT_MATCH_THRESHOLD})"
        )

    return ClosureVerification(
        fingerprint_id=original.fingerprint_id,
        match_confidence=match_confidence,
        result=result,
        verified_at=datetime.utcnow(),
    )
