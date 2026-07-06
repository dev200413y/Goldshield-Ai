"""
GoldShield AI — Configuration
Centralized config: API keys, density reference tables, LTV caps, provider priority.
"""

import os
from typing import Dict, Tuple


# ─── API Keys (from environment) ────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ─── Vision Provider Priority ───────────────────────────────────────────────
# Order matters: first available provider with a valid key is used.
VISION_PROVIDER_ORDER = ["gemini", "mistral", "ollama", "mock"]

# ─── Photogrammetry Feature Flag ────────────────────────────────────────────
# If True, the backend will attempt to run the full COLMAP 3D reconstruction
# pipeline on uploaded photos (Takes 5-15 mins, requires CUDA).
# If False, uses AI vision heuristics for instant volume estimation (Demo mode).
USE_PHOTOGRAMMETRY = os.getenv("USE_PHOTOGRAMMETRY", "False").lower() == "true"

# ─── Visual 3D Model (InstantMesh) ──────────────────────────────────────────
# Path 1: Cosmetic 3D model for the dashboard viewer.
# NEVER used for volume/density calculation — that's volume_estimator.py's job.
INSTANTMESH_HF_SPACE = os.getenv("INSTANTMESH_HF_SPACE", "TencentARC/InstantMesh")
ENABLE_VISUAL_3D = os.getenv("ENABLE_VISUAL_3D", "True").lower() == "true"

# ─── Gemini Config ───────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

# ─── Mistral Config ─────────────────────────────────────────────────────────
MISTRAL_MODEL = "mistral-large-latest"

# ─── Ollama Config ──────────────────────────────────────────────────────────
OLLAMA_MODEL = "llava"

# ─── Gold Density Reference Table (g/cm³) ───────────────────────────────────
# Source: standard metallurgical references for common gold alloys
GOLD_DENSITY_TABLE: Dict[str, Tuple[float, float]] = {
    "24K": (19.25, 19.35),   # Pure gold: 19.3 g/cm³ ± tolerance
    "22K": (17.70, 17.90),   # 91.6% gold
    "21K": (17.00, 17.30),   # 87.5% gold
    "20K": (16.40, 16.70),   # 83.3% gold
    "18K": (15.20, 15.60),   # 75.0% gold
    "14K": (13.00, 13.50),   # 58.3% gold
    "10K": (11.30, 11.80),   # 41.7% gold
}

# Known fraudulent metal densities for comparison
FRAUD_METAL_DENSITIES: Dict[str, float] = {
    "tungsten":  19.25,   # Dangerously close to gold — explicit limitation
    "lead":      11.34,
    "copper":     8.96,
    "brass":      8.50,
    "steel":      7.85,
    "zinc":       7.13,
    "aluminum":   2.70,
}

# ─── Jewelry Shape Heuristics (for volume estimation) ───────────────────────
# Maps jewelry type → geometric approximation method
JEWELRY_SHAPES = {
    "ring":     "torus",
    "bangle":   "hollow_cylinder",
    "chain":    "cylindrical_links",
    "pendant":  "flat_disc",
    "earring":  "small_disc",
    "necklace": "cylindrical_links",
    "bracelet": "cylindrical_links",
    "coin":     "flat_cylinder",
    "bar":      "rectangular_prism",
}

# ─── Loan-to-Value Configuration ────────────────────────────────────────────
LTV_CAP_PERCENT = float(os.getenv("LTV_CAP_PERCENT", "75.0"))  # RBI norm

# ─── Gold Rate Configuration ────────────────────────────────────────────────
# Cached fallback rate (per gram, 24K, INR) — updated manually if no live API
CACHED_GOLD_RATE_24K = float(os.getenv("CACHED_GOLD_RATE_24K", "7800.0"))
GOLD_RATE_API_URL = os.getenv(
    "GOLD_RATE_API_URL",
    "https://www.goldapi.io/api/XAU/INR"
)
GOLD_RATE_API_KEY = os.getenv("GOLD_RATE_API_KEY", "")

# Purity factors (fraction of pure gold)
PURITY_FACTORS: Dict[str, float] = {
    "24K": 1.000,
    "22K": 0.916,
    "21K": 0.875,
    "20K": 0.833,
    "18K": 0.750,
    "14K": 0.583,
    "10K": 0.417,
}

# ─── Risk Officer Thresholds ────────────────────────────────────────────────
RISK_ESCALATION_THRESHOLD = 0.60     # Confidence below this → escalate
RISK_FLAG_THRESHOLD = 1              # Number of flags to trigger moderate risk
RISK_HIGH_FLAG_THRESHOLD = 2         # Number of flags to trigger high risk

# ─── Fingerprint Configuration ──────────────────────────────────────────────
FINGERPRINT_MATCH_THRESHOLD = 0.85   # Below this → mandatory hold at closure

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "goldshield.db")

# ─── Server ─────────────────────────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
# Railway passes the 'PORT' environment variable, so check that first
SERVER_PORT = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8000")))
