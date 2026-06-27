"""
GoldShield AI — Gold Rate & LTV Agent (Agent 7)
Fetches current gold rate, computes fair market value, and validates loan-to-value.

Method:
  1. Get current gold rate (live API → cached fallback)
  2. Compute FMV = weight × purity_factor × rate_per_gram
  3. Compute LTV = loan_amount / FMV × 100
  4. Flag if LTV exceeds cap (default 75% per RBI norms)
"""

import logging
from datetime import datetime

from goldshield.models import ValuationResult
from goldshield.config import (
    CACHED_GOLD_RATE_24K,
    GOLD_RATE_API_URL,
    GOLD_RATE_API_KEY,
    PURITY_FACTORS,
    LTV_CAP_PERCENT,
)

logger = logging.getLogger("goldshield.agents.gold_rate_ltv")


async def _fetch_live_gold_rate() -> float:
    """
    Attempt to fetch live gold rate from API.
    Returns rate per gram in INR for 24K gold.
    """
    if not GOLD_RATE_API_KEY:
        raise ValueError("No gold rate API key configured")

    import httpx
    headers = {
        "x-access-token": GOLD_RATE_API_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(GOLD_RATE_API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Gold API returns price per troy ounce — convert to per gram
        price_per_ounce = data.get("price", 0)
        price_per_gram = price_per_ounce / 31.1035
        return round(price_per_gram, 2)


async def analyze(
    weight_grams: float,
    declared_purity: str = "22K",
    loan_amount_requested: float = 0.0,
) -> ValuationResult:
    """
    Run the Gold Rate & LTV Agent.

    1. Fetch current gold rate (live or cached)
    2. Compute fair market value
    3. Validate LTV against cap
    """
    # Step 1: Get gold rate
    rate_source = "cached"
    rate_24k = CACHED_GOLD_RATE_24K

    try:
        live_rate = await _fetch_live_gold_rate()
        if live_rate > 0:
            rate_24k = live_rate
            rate_source = "live_api"
            logger.info(f"Live gold rate fetched: ₹{rate_24k}/gram (24K)")
    except Exception as e:
        logger.warning(f"Live gold rate fetch failed: {e}. Using cached rate: ₹{rate_24k}/gram")
        rate_source = f"cached (live fetch failed: {str(e)[:50]})"

    # Step 2: Compute rate for declared purity
    purity_factor = PURITY_FACTORS.get(declared_purity, 0.916)
    rate_per_gram = rate_24k * purity_factor

    # Step 3: Compute fair market value
    fair_market_value = round(weight_grams * rate_per_gram, 2)

    # Step 4: Compute LTV
    if loan_amount_requested > 0 and fair_market_value > 0:
        ltv_percent = round((loan_amount_requested / fair_market_value) * 100, 2)
    else:
        ltv_percent = 0.0

    # Step 5: Check LTV violation
    violation = ltv_percent > LTV_CAP_PERCENT

    if violation:
        logger.warning(
            f"LTV VIOLATION: {ltv_percent}% exceeds cap of {LTV_CAP_PERCENT}%. "
            f"Loan: ₹{loan_amount_requested}, FMV: ₹{fair_market_value}"
        )

    return ValuationResult(
        gold_rate_per_gram=round(rate_per_gram, 2),
        rate_source=rate_source,
        fair_market_value=fair_market_value,
        loan_amount_requested=loan_amount_requested,
        ltv_percent=ltv_percent,
        ltv_cap=LTV_CAP_PERCENT,
        violation=violation,
    )
