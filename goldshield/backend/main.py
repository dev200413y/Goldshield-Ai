"""
GoldShield AI — FastAPI Backend
All endpoints for appraisal, verification, valuation, fingerprint, and dashboard.
Serves the frontend static files as well.
"""

import os
import sys
import base64
import logging
import asyncio
import shutil
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ─── Setup paths ─────────────────────────────────────────────────────────────
# Add parent directory to path so goldshield package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from goldshield.backend.database import db
from goldshield.agents import (
    density_inspector,
    surface_inspector,
    hallmark_inspector,
    touchstone_inspector,
    light_signature_inspector,
    risk_officer,
    gold_rate_ltv_agent,
    custody_fingerprint_agent,
)
from goldshield.vision.visual_3d_generator import generate_visual_model

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("goldshield.backend")

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="GoldShield AI",
    description="Multi-agent non-destructive gold verification system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory photo storage (per appraisal) — for prototype only
_photo_store: dict = {}


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.post("/api/appraisal")
async def create_appraisal(
    customer_ref: str = Form(...),
    item_description: str = Form("Gold jewelry item"),
    item_type: str = Form("ring"),
    weight_grams: float = Form(...),
    declared_purity: str = Form("22K"),
    branch_id: str = Form("BR-001"),
    photos: List[UploadFile] = File(default=[]),
):
    """Create a new appraisal with uploaded photos."""
    # Read and encode photos
    photos_base64 = []
    if not photos or (len(photos) == 1 and not photos[0].filename):
        raise HTTPException(status_code=400, detail="At least one photo is required for verification")

    for photo in photos:
        content = await photo.read()
        encoded = base64.b64encode(content).decode("utf-8")
        photos_base64.append(encoded)

    # Save to database
    appraisal_id = db.create_appraisal(
        customer_ref=customer_ref,
        item_description=item_description,
        item_type=item_type,
        weight_grams=weight_grams,
        declared_purity=declared_purity,
        branch_id=branch_id,
        photos_count=len(photos_base64),
    )

    # Store photos in memory (prototype — production would use object storage)
    _photo_store[appraisal_id] = photos_base64

    # Also persist photos to disk for the Records screen
    photo_dir = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id)
    photo_dir.mkdir(parents=True, exist_ok=True)
    for idx, photo_b64 in enumerate(photos_base64):
        photo_path = photo_dir / f"photo_{idx}.jpg"
        photo_path.write_bytes(base64.b64decode(photo_b64))

    logger.info(f"Appraisal {appraisal_id} created: {item_description}, {weight_grams}g, {declared_purity}")

    return {
        "appraisal_id": appraisal_id,
        "status": "created",
        "photos_uploaded": len(photos_base64),
        "message": f"Appraisal created. Use POST /api/appraisal/{appraisal_id}/verify to run verification.",
    }


@app.get("/api/appraisal/{appraisal_id}")
async def get_appraisal(appraisal_id: int):
    """Get appraisal details with verification and valuation results."""
    appraisal = db.get_appraisal(appraisal_id)
    if not appraisal:
        raise HTTPException(status_code=404, detail="Appraisal not found")

    verification = db.get_verification(appraisal_id)
    fingerprint = db.get_fingerprint(appraisal_id)

    return {
        **appraisal,
        "verification": verification,
        "fingerprint": fingerprint,
    }


@app.get("/api/models/{appraisal_id}/visual_model.glb")
async def serve_visual_model(appraisal_id: int):
    """Serve the AI-generated visual 3D model (.glb) for the dashboard viewer.
    
    NOTE: This model is for PRESENTATION ONLY. It must never be used as a
    source of volume for density calculation — that comes from volume_estimator.py.
    """
    glb_path = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id) / "visual_model.glb"
    if not glb_path.exists():
        raise HTTPException(status_code=404, detail="Visual 3D model not available for this appraisal")
    return FileResponse(str(glb_path), media_type="model/gltf-binary", filename="visual_model.glb")


@app.get("/api/photos/{appraisal_id}/{photo_index}")
async def serve_photo(appraisal_id: int, photo_index: int):
    """Serve an uploaded photo for the 2D gallery fallback."""
    photo_path = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id) / f"photo_{photo_index}.jpg"
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(str(photo_path), media_type="image/jpeg")


@app.post("/api/appraisal/{appraisal_id}/verify")
async def run_verification(appraisal_id: int):
    """
    Run all 5 inspector agents + Risk Officer fusion on an appraisal.
    This is the core verification pipeline.
    """
    appraisal = db.get_appraisal(appraisal_id)
    if not appraisal:
        raise HTTPException(status_code=404, detail="Appraisal not found")

    photos = _photo_store.get(appraisal_id, [])
    weight = appraisal["weight_grams"]
    item_type = appraisal.get("item_type", "ring")
    purity = appraisal.get("declared_purity", "22K")

    logger.info(f"Starting verification pipeline for appraisal {appraisal_id}")

    # ─── Run all 5 inspectors + visual 3D model in PARALLEL ──────────────
    # Visual model (Path 1) runs concurrently but is purely cosmetic.
    # Density calculation (Path 2) comes from volume_estimator.py inside density_inspector.
    async def _safe_visual_model():
        """Generate visual model without crashing if it fails."""
        try:
            return await generate_visual_model(
                image_base64=photos[0] if photos else "",
                appraisal_id=appraisal_id,
            )
        except Exception as e:
            logger.warning(f"Visual 3D model generation failed (non-fatal): {e}")
            return None

    (
        density_result,
        surface_result,
        hallmark_result,
        touchstone_result,
        light_result,
        visual_model_url,
    ) = await asyncio.gather(
        density_inspector.inspect(photos_base64=photos, weight_grams=weight, item_type=item_type, declared_purity=purity),
        surface_inspector.inspect(photos_base64=photos),
        hallmark_inspector.inspect(photos_base64=photos),
        touchstone_inspector.inspect(photos_base64=photos),
        light_signature_inspector.inspect(photos_base64=photos),
        _safe_visual_model(),
    )
    
    logger.info(f"  Density: {density_result.result.value} ({density_result.density_gcm3} g/cm³) via {density_result.provider}")
    logger.info(f"  Surface: {surface_result.result.value} via {surface_result.provider}")
    logger.info(f"  Hallmark: {hallmark_result.result.value} ({hallmark_result.hallmark_detected}) via {hallmark_result.provider}")
    logger.info(f"  Touchstone: {touchstone_result.result.value} via {touchstone_result.provider}")
    logger.info(f"  Light-Signature: {light_result.result.value} via {light_result.provider}")

    # ─── Agent 6: Risk Officer (Fusion) ─────────────────────────────────
    verdict = risk_officer.fuse(
        density=density_result,
        surface=surface_result,
        hallmark=hallmark_result,
        touchstone=touchstone_result,
        light_signature=light_result,
    )
    logger.info(
        f"  VERDICT: Score={verdict.authenticity_score}, "
        f"Fraud={verdict.fraud_probability}%, Escalated={verdict.escalated}"
    )

    # ─── Save to database ───────────────────────────────────────────────
    verdict_dict = verdict.model_dump()
    # Convert sub-results to serializable dicts
    for key in ["density_result", "surface_result", "hallmark_result",
                "touchstone_result", "light_signature_result"]:
        if verdict_dict.get(key):
            verdict_dict[key] = verdict_dict[key]
    db.save_verification(appraisal_id, verdict_dict)

    # ─── Auto-generate fingerprint ──────────────────────────────────────
    fingerprint = custody_fingerprint_agent.generate_fingerprint(
        photos_base64=photos,
        hallmark_result=hallmark_result,
        density_result=density_result,
    )
    fp_dict = fingerprint.model_dump()
    fp_dict["created_at"] = fp_dict["created_at"].isoformat()
    db.save_fingerprint(appraisal_id, fp_dict)
    logger.info(f"  Fingerprint: {fingerprint.fingerprint_id}")

    if visual_model_url:
        logger.info(f"  Visual 3D model: {visual_model_url}")
    else:
        logger.info("  Visual 3D model: unavailable (fallback will be used)")

    return {
        "appraisal_id": appraisal_id,
        "status": "verified",
        "verdict": verdict_dict,
        "fingerprint": fp_dict,
        "visual_model_url": visual_model_url,
    }


@app.post("/api/valuation")
async def run_valuation(
    appraisal_id: int = Form(...),
    loan_amount: float = Form(0),
):
    """Run Gold Rate & LTV calculation for an appraisal."""
    appraisal = db.get_appraisal(appraisal_id)
    if not appraisal:
        raise HTTPException(status_code=404, detail="Appraisal not found")

    valuation = await gold_rate_ltv_agent.analyze(
        weight_grams=appraisal["weight_grams"],
        declared_purity=appraisal.get("declared_purity", "22K"),
        loan_amount_requested=loan_amount,
    )

    val_dict = valuation.model_dump()
    db.save_valuation(appraisal_id, val_dict)

    logger.info(
        f"Valuation for appraisal {appraisal_id}: FMV=₹{valuation.fair_market_value}, "
        f"LTV={valuation.ltv_percent}%"
    )

    return {
        "appraisal_id": appraisal_id,
        "valuation": val_dict,
    }


@app.get("/api/gold-rate")
async def get_gold_rate():
    """Get current gold rate for display."""
    from goldshield.config import CACHED_GOLD_RATE_24K, PURITY_FACTORS
    rates = {}
    for purity, factor in PURITY_FACTORS.items():
        rates[purity] = round(CACHED_GOLD_RATE_24K * factor, 2)
    return {
        "base_rate_24k": CACHED_GOLD_RATE_24K,
        "rates_per_gram": rates,
        "currency": "INR",
        "source": "cached",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get branch-level dashboard statistics."""
    stats = db.get_dashboard_stats()
    return stats


@app.get("/api/appraisals")
async def list_appraisals(limit: int = 50):
    """List all appraisals with their verification status."""
    appraisals = db.list_appraisals(limit=limit)
    return {"appraisals": appraisals}


@app.get("/api/appraisal/{appraisal_id}/full")
async def get_full_appraisal(appraisal_id: int):
    """Get complete appraisal with all verification, valuation, and fingerprint data."""
    full = db.get_full_appraisal(appraisal_id)
    if not full:
        raise HTTPException(status_code=404, detail="Appraisal not found")
    return full


@app.get("/api/appraisals/detailed")
async def list_appraisals_detailed(limit: int = 100):
    """List all appraisals with joined verification, valuation, and fingerprint data.
    Used by the Records screen."""
    appraisals = db.list_appraisals_detailed(limit=limit)
    return {"appraisals": appraisals}


@app.get("/api/appraisal/{appraisal_id}/photos")
async def get_appraisal_photos(appraisal_id: int):
    """Get base64-encoded photos for an appraisal."""
    # Check in-memory first
    if appraisal_id in _photo_store:
        return {"photos": _photo_store[appraisal_id]}

    # Fallback to disk
    photo_dir = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id)
    if not photo_dir.exists():
        return {"photos": []}

    photos = []
    for photo_path in sorted(photo_dir.glob("photo_*.jpg")):
        photo_data = base64.b64encode(photo_path.read_bytes()).decode("utf-8")
        photos.append(photo_data)

    return {"photos": photos}

@app.get("/api/appraisal/{appraisal_id}/model3d")
async def get_appraisal_model3d(appraisal_id: int):
    """
    Get the AI-generated 3D model URL for an appraisal.
    Simulates calling Tripo3D or returns a fallback model.
    """
    from goldshield.vision.reconstruction3d import generate_3d_model
    
    # Try to get the first photo from storage
    photos = []
    if appraisal_id in _photo_store:
        photos = _photo_store[appraisal_id]
    else:
        photo_dir = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id)
        if photo_dir.exists():
            for photo_path in sorted(photo_dir.glob("photo_*.jpg")):
                photo_data = base64.b64encode(photo_path.read_bytes()).decode("utf-8")
                photos.append(photo_data)
                break
                
    photo_b64 = photos[0] if photos else ""
    
    # Call the integration
    model_url = generate_3d_model(appraisal_id, photo_b64)
    
    return {"model_url": model_url}



# ─── Static File Serving (Frontend) ─────────────────────────────────────────
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/")
async def serve_index():
    """Serve the main dashboard page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "GoldShield AI API is running. Frontend not found at expected path."}

# Mount static files (CSS, JS)
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

import mimetypes
mimetypes.add_type("model/gltf-binary", ".glb")

models_dir = Path(__file__).resolve().parent.parent / "photo_store"
if models_dir.exists():
    app.mount("/api/models", StaticFiles(directory=str(models_dir)), name="models")
