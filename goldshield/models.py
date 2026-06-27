"""
GoldShield AI — Data Models
Pydantic models matching AGENTS.md output schemas exactly.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ───────────────────────────────────────────────────────────────────

class InspectorResult(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    INCONCLUSIVE = "INCONCLUSIVE"


class MatchResult(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"


# ─── Appraisal Input ────────────────────────────────────────────────────────

class AppraisalInput(BaseModel):
    """Input data for a new gold appraisal."""
    customer_ref: str = Field(..., description="Customer reference ID (stays local, never sent to AI)")
    item_description: str = Field(..., description="Description of the jewelry item")
    item_type: str = Field(default="ring", description="Type: ring, bangle, chain, pendant, etc.")
    weight_grams: float = Field(..., gt=0, description="Weight in grams from digital scale")
    declared_purity: str = Field(default="22K", description="Declared caratage: 24K, 22K, 18K, etc.")
    branch_id: str = Field(default="BR-001", description="Branch identifier")
    # Photos are handled separately via file upload, not embedded in this model


# ─── Agent 1: Density & Volume Inspector ────────────────────────────────────

class DensityResult(BaseModel):
    """Output of the Density & Volume Inspector agent."""
    density_gcm3: float = Field(..., description="Computed density in g/cm³")
    estimated_volume_cm3: float = Field(..., description="Estimated volume in cm³")
    expected_range: List[float] = Field(..., description="Expected density range [low, high] for declared purity")
    result: InspectorResult = Field(..., description="PASS, FLAG, or INCONCLUSIVE")
    reason: str = Field(..., description="Human-readable explanation")
    provider: str = Field(default="mock", description="Which AI provider answered")


# ─── Agent 2: Surface & Seam Inspector ──────────────────────────────────────

class SurfaceResult(BaseModel):
    """Output of the Surface & Seam Inspector agent."""
    result: InspectorResult = Field(...)
    location: Optional[str] = Field(None, description="Where the anomaly was found")
    observation: str = Field(..., description="What was observed")
    provider: str = Field(default="mock")


# ─── Agent 3: Hallmark Verification Inspector ──────────────────────────────

class HallmarkResult(BaseModel):
    """Output of the Hallmark Verification Inspector agent."""
    result: InspectorResult = Field(...)
    hallmark_detected: Optional[str] = Field(None, description="Detected hallmark text, e.g. BIS 916 HUID-XXXXX")
    confidence: float = Field(..., ge=0, le=1, description="OCR confidence 0–1")
    provider: str = Field(default="mock")


# ─── Agent 4: Touchstone / Reflectance Inspector ───────────────────────────

class TouchstoneResult(BaseModel):
    """Output of the Touchstone / Reflectance Inspector agent."""
    result: InspectorResult = Field(...)
    streak_color_match: str = Field(..., description="Comparison with reference gold streak")
    provider: str = Field(default="mock")


# ─── Agent 5: Light-Signature Inspector ─────────────────────────────────────

class LightSignatureResult(BaseModel):
    """Output of the Light-Signature Inspector agent."""
    result: InspectorResult = Field(...)
    reflectance_consistency: str = Field(..., description="Score or description of consistency")
    provider: str = Field(default="mock")


# ─── Agent 6: Risk Officer (Fusion) ─────────────────────────────────────────

class RiskOfficerVerdict(BaseModel):
    """Output of the Risk Officer Agent — fuses all 5 inspector outputs."""
    authenticity_score: int = Field(..., ge=0, le=100, description="0–100 authenticity score")
    fraud_probability: int = Field(..., ge=0, le=100, description="0–100 fraud probability")
    confidence: int = Field(..., ge=0, le=100, description="System confidence in this verdict")
    suspicious_area: Optional[str] = Field(None, description="Most suspicious physical area")
    reasoning: str = Field(..., description="Plain-language explanation for bank auditors")
    recommendation: str = Field(..., description="Action recommendation")
    escalated: bool = Field(..., description="Whether manual verification is flagged")

    # Sub-results for transparency
    density_result: Optional[DensityResult] = None
    surface_result: Optional[SurfaceResult] = None
    hallmark_result: Optional[HallmarkResult] = None
    touchstone_result: Optional[TouchstoneResult] = None
    light_signature_result: Optional[LightSignatureResult] = None


# ─── Agent 7: Gold Rate & LTV ──────────────────────────────────────────────

class ValuationResult(BaseModel):
    """Output of the Gold Rate & LTV Agent."""
    gold_rate_per_gram: float = Field(..., description="Rate used (INR per gram, for declared purity)")
    rate_source: str = Field(..., description="Where rate came from: live_api / cached")
    fair_market_value: float = Field(..., description="FMV = weight × purity × rate")
    loan_amount_requested: float = Field(default=0)
    ltv_percent: float = Field(..., description="LTV = loan / FMV × 100")
    ltv_cap: float = Field(default=75.0)
    violation: bool = Field(..., description="True if LTV exceeds cap")


# ─── Agent 8: Custody & Fingerprint ─────────────────────────────────────────

class FingerprintRecord(BaseModel):
    """Output of the Custody & Fingerprint Agent."""
    fingerprint_id: str = Field(..., description="Unique ID, e.g. GF-2026-001245")
    visual_hash: str = Field(..., description="Hash of visual embedding")
    hallmark_signature: Optional[str] = None
    density_signature: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClosureVerification(BaseModel):
    """Result of closure re-verification."""
    fingerprint_id: str
    match_confidence: float = Field(..., ge=0, le=1)
    result: MatchResult
    verified_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Full Appraisal Response ────────────────────────────────────────────────

class AppraisalResponse(BaseModel):
    """Complete appraisal response combining all agent outputs."""
    appraisal_id: int
    customer_ref: str
    item_description: str
    weight_grams: float
    declared_purity: str
    created_at: str

    # Verification results (populated after verification run)
    verification: Optional[RiskOfficerVerdict] = None

    # Valuation results (populated after valuation run)
    valuation: Optional[ValuationResult] = None

    # Fingerprint (populated after fingerprint generation)
    fingerprint: Optional[FingerprintRecord] = None
