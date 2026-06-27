"""
GoldShield AI — Vision Provider
Shared vision_call() with automatic fallback: Gemini → Mistral → Ollama → Mock.
SECURITY: Never sends customer identity data — only jewelry photos + analysis prompts.
"""

import base64
import json
import re
import logging
from typing import Tuple, Optional

from goldshield.config import (
    GEMINI_API_KEY, MISTRAL_API_KEY,
    GEMINI_MODEL, MISTRAL_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    VISION_PROVIDER_ORDER,
)

logger = logging.getLogger("goldshield.vision")


async def vision_call(
    image_base64: str,
    prompt: str,
    providers: Optional[list] = None,
) -> Tuple[str, str]:
    """
    Send an image + prompt to a vision model and get a text response.

    Args:
        image_base64: Base64-encoded image data (JPEG/PNG).
        prompt: The analysis prompt (must NOT contain customer identity data).
        providers: Override provider order. Defaults to config VISION_PROVIDER_ORDER.

    Returns:
        Tuple of (response_text, provider_name).
        provider_name is one of: "gemini", "mistral", "ollama", "mock".

    Raises:
        RuntimeError: If all providers fail (shouldn't happen — mock is always last).
    """
    provider_order = providers or VISION_PROVIDER_ORDER
    last_error = None

    for provider in provider_order:
        try:
            if provider == "gemini" and GEMINI_API_KEY:
                result = await _call_gemini(image_base64, prompt)
                logger.info("Vision call answered by Gemini")
                return result, "gemini"

            elif provider == "mistral" and MISTRAL_API_KEY:
                result = await _call_mistral(image_base64, prompt)
                logger.info("Vision call answered by Mistral")
                return result, "mistral"

            elif provider == "ollama":
                result = await _call_ollama(image_base64, prompt)
                logger.info("Vision call answered by Ollama (local)")
                return result, "ollama"

            elif provider == "mock":
                result = _call_mock(prompt)
                logger.info("Vision call answered by Mock (demo mode)")
                return result, "mock"

        except Exception as e:
            last_error = e
            logger.warning(f"Provider '{provider}' failed: {e}. Trying next...")
            continue

    # Should never reach here since mock doesn't fail, but just in case
    raise RuntimeError(f"All vision providers failed. Last error: {last_error}")


# ─── Gemini Provider ────────────────────────────────────────────────────────

async def _call_gemini(image_base64: str, prompt: str) -> str:
    """Call Google Gemini 2.5 Flash vision API."""
    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": image_base64
                    }
                },
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ─── Mistral Provider ───────────────────────────────────────────────────────

async def _call_mistral(image_base64: str, prompt: str) -> str:
    """Call Mistral Pixtral / Large vision API."""
    import httpx

    url = "https://api.mistral.ai/v1/chat/completions"

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


# ─── Ollama Provider (Local) ────────────────────────────────────────────────

async def _call_ollama(image_base64: str, prompt: str) -> str:
    """Call local Ollama vision model (llava / llama3.2-vision)."""
    import httpx

    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["response"]


# ─── Mock Provider (Demo Mode) ──────────────────────────────────────────────

def _call_mock(prompt: str) -> str:
    """
    Returns realistic mock responses for demo/testing when no AI provider is available.
    Parses the prompt to determine which inspector is calling and returns appropriate JSON.
    """
    prompt_lower = prompt.lower()

    if "density" in prompt_lower or "volume" in prompt_lower or "dimension" in prompt_lower:
        return json.dumps({
            "item_type": "ring",
            "estimated_dimensions": {
                "outer_diameter_mm": 20.0,
                "inner_diameter_mm": 16.0,
                "thickness_mm": 3.5,
                "width_mm": 6.0
            },
            "reference_object_detected": True,
            "reference_object": "1 rupee coin (25mm diameter)",
            "confidence": 0.85
        })

    elif "surface" in prompt_lower or "seam" in prompt_lower or "solder" in prompt_lower:
        return json.dumps({
            "surface_analysis": {
                "color_consistency": "uniform golden hue across all visible surfaces",
                "solder_joints": "no visible solder joints or repair marks detected",
                "wear_patterns": "light wear consistent with regular use, no substrate exposure",
                "plating_edges": "no plating boundary lines detected",
                "anomalies": []
            },
            "result": "PASS",
            "confidence": 0.88,
            "observations": "Surface appears consistent with solid gold construction. No signs of plating, coating, or base-metal exposure detected."
        })

    elif "hallmark" in prompt_lower or "bis" in prompt_lower or "huid" in prompt_lower:
        return json.dumps({
            "hallmark_analysis": {
                "bis_mark_detected": True,
                "caratage_code": "916",
                "huid": "AB12CD3456",
                "hallmarking_center": "Detected",
                "jeweler_id": "Detected",
                "placement": "inner band, standard position",
                "font_consistency": "consistent with official BIS stamps"
            },
            "result": "PASS",
            "confidence": 0.93,
            "full_hallmark_text": "BIS 916 HUID-AB12CD3456"
        })

    elif "touchstone" in prompt_lower or "streak" in prompt_lower:
        return json.dumps({
            "streak_analysis": {
                "color": "rich yellow-gold, consistent with 22K reference",
                "width": "uniform, approximately 2mm",
                "luster": "bright metallic sheen maintained across streak length",
                "comparison": "matches 22K gold reference streak characteristics"
            },
            "result": "PASS",
            "confidence": 0.87,
            "streak_color_match": "consistent with 22K gold reference"
        })

    elif "light" in prompt_lower or "reflectance" in prompt_lower or "angle" in prompt_lower:
        return json.dumps({
            "reflectance_analysis": {
                "angle_1": "warm golden reflection, consistent intensity",
                "angle_2": "slight natural variation, within normal range for solid gold",
                "angle_3": "consistent golden hue, no unexpected color shifts",
                "micro_inconsistencies": "none detected",
                "coating_indicators": "none"
            },
            "result": "PASS",
            "consistency_score": 0.89,
            "reflectance_consistency": "0.89 (within normal range)"
        })

    else:
        return json.dumps({
            "analysis": "Image analyzed successfully",
            "observations": "No specific anomalies detected in visual inspection",
            "result": "PASS",
            "confidence": 0.85
        })


def extract_json_from_response(response_text: str) -> dict:
    """
    Extract JSON from a vision model response that may contain markdown or extra text.
    Handles cases where the model wraps JSON in ```json ... ``` blocks.
    """
    # Try direct JSON parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Return raw text wrapped in a dict
    return {"raw_response": response_text, "parse_error": True}
