"""
GoldShield AI — Visual 3D Generator (Path 1: Presentation Layer)

Generates an AI-powered 3D model (.glb) from an uploaded jewelry photo
using InstantMesh via the Hugging Face Spaces Gradio API.

PURPOSE: Cosmetic only — gives the branch officer / judges a rotatable,
realistic-looking 3D reference of the appraised item in the dashboard.

CRITICAL: This model must NEVER be used as a source of volume_cm3 for
density calculation. That is the sole responsibility of volume_estimator.py.
"""

import os
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("goldshield.vision.visual_3d_generator")


async def generate_visual_model(
    image_base64: str,
    appraisal_id: int,
    photo_store_dir: Optional[Path] = None,
) -> Optional[str]:
    """
    Generate a 3D .glb model from a single jewelry photo using InstantMesh.

    Args:
        image_base64: Base64-encoded JPEG/PNG of the jewelry item.
        appraisal_id: Appraisal ID (used for file naming).
        photo_store_dir: Directory to save the .glb file. 
                         Defaults to photo_store/{appraisal_id}/.

    Returns:
        The serve path (e.g. "/api/models/{id}/visual_model.glb") if successful,
        or None if generation fails (the frontend will show a fallback).
    """
    from goldshield.config import ENABLE_VISUAL_3D, INSTANTMESH_HF_SPACE

    if not ENABLE_VISUAL_3D:
        logger.info("Visual 3D generation is DISABLED via config.")
        return None

    # Determine output directory
    if photo_store_dir is None:
        photo_store_dir = Path(__file__).resolve().parent.parent / "photo_store" / str(appraisal_id)
    photo_store_dir.mkdir(parents=True, exist_ok=True)

    glb_output_path = photo_store_dir / "visual_model.glb"
    serve_path = f"/api/models/{appraisal_id}/visual_model.glb"

    # If model already exists (e.g., re-run), return it
    if glb_output_path.exists():
        logger.info(f"Visual model already exists at {glb_output_path}")
        return serve_path

    # Save the image to a temp file for the API call
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
    except Exception as e:
        logger.error(f"Failed to decode image for 3D generation: {e}")
        return None

    temp_img_path = photo_store_dir / "input_for_3d.png"
    temp_img_path.write_bytes(img_bytes)

    # Try to call the InstantMesh HF Space via Gradio client
    try:
        return await _call_instantmesh_api(
            image_path=str(temp_img_path),
            output_path=str(glb_output_path),
            hf_space=INSTANTMESH_HF_SPACE,
            serve_path=serve_path,
        )
    except Exception as e:
        logger.warning(f"InstantMesh API call failed: {e}. Visual model unavailable — fallback will be used.")
        return None


async def _call_instantmesh_api(
    image_path: str,
    output_path: str,
    hf_space: str,
    serve_path: str,
) -> Optional[str]:
    """
    Call the InstantMesh Hugging Face Space via the Gradio Client API.
    
    The HF Space accepts a single image and returns a 3D mesh.
    Free-tier spaces may be sleeping and take 60-90s to wake up.
    """
    import asyncio
    from concurrent.futures import ProcessPoolExecutor

    try:
        # Run the blocking gradio_client call in a separate process
        # to avoid Windows SSL/threading conflicts with the asyncio event loop
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool,
                _sync_gradio_call,
                image_path, output_path, hf_space,
            )
        
        if result:
            logger.info(f"3D model generated successfully: {output_path}")
            return serve_path
        return None
    except Exception as e:
        logger.warning(f"Gradio call error: {e}")
        return None


def _sync_gradio_call(image_path: str, output_path: str, hf_space: str) -> bool:
    """
    Synchronous wrapper for the gradio_client API call.
    This runs in a thread pool via asyncio.run_in_executor().
    """
    try:
        from gradio_client import Client, handle_file

        logger.info(f"Connecting to TripoSR HF Space: stabilityai/TripoSR...")
        client = Client('stabilityai/TripoSR')

        # Step 1: Preprocess the image (remove background)
        logger.info("Step 1/2: Preprocessing image...")
        preprocessed = client.predict(
            handle_file(image_path),
            True,
            0.85,
            api_name="/preprocess",
        )

        # Step 2: Generate 3D mesh
        logger.info("Step 2/2: Generating 3D mesh...")
        
        obj_file, glb_file = client.predict(
            handle_file(preprocessed),
            256,
            api_name="/generate",
        )

        # The result should be a file path to the generated .glb mesh
        # Copy it to our output location
        if glb_file and os.path.exists(str(glb_file)):
            import shutil
            shutil.copy2(str(glb_file), output_path)
            logger.info("TripoSR generation successful.")
            return True
        else:
            logger.warning("GLB file not found in TripoSR response.")
            return False

    except ImportError:
        logger.warning(
            "gradio_client not installed. Install with: pip install gradio_client\n"
            "Visual 3D model generation will be skipped — fallback procedural model will be shown."
        )
        return False
    except Exception as e:
        logger.warning(f"TripoSR generation failed: {e}")
        return False
