import os
import time
import logging
import base64
import tempfile
import shutil
from pathlib import Path

# Only import gradio_client if available
try:
    from gradio_client import Client, handle_file
except ImportError:
    Client = None
    handle_file = None

from goldshield.config import INSTANTMESH_HF_SPACE

logger = logging.getLogger(__name__)

class InstantMeshProvider:
    """
    Integration with TencentARC/InstantMesh via Hugging Face Spaces
    for Image-to-3D generation.
    """
    def __init__(self):
        self.api_key = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        self.space_id = INSTANTMESH_HF_SPACE

    def is_configured(self):
        return bool(self.api_key) and Client is not None

    def generate_3d_model(self, image_base64: str, output_path: str) -> str:
        """
        Calls InstantMesh to generate a 3D model from an image.
        Saves the GLB file to output_path and returns it.
        """
        if not self.is_configured():
            if Client is None:
                logger.warning("gradio_client not installed. Using fallback 3D generation.")
            else:
                logger.warning("HUGGINGFACEHUB_API_TOKEN not found. Using fallback 3D generation.")
            return ""

        try:
            logger.info("Initializing InstantMesh Gradio Client...")
            client = Client(self.space_id, token=self.api_key)
            
            # Save base64 to temp file
            if image_base64.startswith("data:image"):
                image_base64 = image_base64.split(",")[1]
            img_data = base64.b64decode(image_base64)
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_data)
                tmp_path = tmp.name
                
            try:
                logger.info("InstantMesh Step 1: Preprocessing image (bg removal)...")
                processed_img = client.predict(
                    input_image=handle_file(tmp_path),
                    do_remove_background=True,
                    api_name="/preprocess"
                )
                
                logger.info("InstantMesh Step 2: Generating multi-views...")
                # Ensure we handle the format returned by gradio
                img_arg = handle_file(processed_img) if isinstance(processed_img, str) else processed_img
                client.predict(
                    input_image=img_arg,
                    sample_steps=75,
                    sample_seed=42,
                    api_name="/generate_mvs"
                )
                
                logger.info("InstantMesh Step 3: Making 3D model...")
                obj_path, glb_path = client.predict(
                    api_name="/make3d"
                )
                
                logger.info(f"InstantMesh generation complete! GLB saved to temp: {glb_path}")
                
                # Copy to output path
                shutil.copy(glb_path, output_path)
                
                return output_path
                
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            
        except Exception as e:
            logger.error(f"Error calling InstantMesh: {e}")
            return ""

instantmesh_provider = InstantMeshProvider()

def generate_3d_model(appraisal_id: int, image_base64: str) -> str:
    """
    Main entry point for the Image-to-3D reconstruction.
    Returns a GLB URL path if successful, otherwise empty string (fallback).
    """
    logger.info(f"Starting 3D reconstruction for appraisal {appraisal_id}...")
    
    if not image_base64:
        logger.warning("No image provided for 3D reconstruction.")
        return ""
    
    # Target path in our public directory
    model_dir = Path(__file__).resolve().parent.parent.parent / "models"
    model_dir.mkdir(exist_ok=True)
    out_path = model_dir / f"{appraisal_id}_visual_model.glb"
    
    # Generate using InstantMesh
    result_path = instantmesh_provider.generate_3d_model(image_base64, str(out_path))
    
    if result_path:
        return f"/api/models/{appraisal_id}_visual_model.glb"
        
    # If no API key or failed, return empty string so frontend uses realistic fallback
    return ""
