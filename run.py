"""
GoldShield AI -- Single-Command Launcher
Run: python run.py
Opens the dashboard at http://localhost:8000
"""

import sys
import os
from pathlib import Path

# Ensure the goldshield package is importable
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Set working directory to root so goldshield.db is read correctly
os.chdir(project_root)

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    import uvicorn
    from goldshield.config import SERVER_HOST, SERVER_PORT

    print()
    print("  +==================================================+")
    print("  |           GoldShield AI                           |")
    print("  |   Non-Destructive Gold Verification System        |")
    print("  |   Tata Steel / Canara Bank Hackathon 2026         |")
    print("  +==================================================+")
    print(f"  |   Dashboard: http://localhost:{SERVER_PORT}              |")
    print(f"  |   API Docs:  http://localhost:{SERVER_PORT}/docs          |")
    print("  +==================================================+")
    print()

    # Check for API keys
    from goldshield.config import GEMINI_API_KEY, MISTRAL_API_KEY
    if GEMINI_API_KEY:
        print("  [OK] Gemini API key detected")
    else:
        print("  [!!] No GEMINI_API_KEY -- will use mock/demo mode")
    if MISTRAL_API_KEY:
        print("  [OK] Mistral API key detected")
    else:
        print("  [!!] No MISTRAL_API_KEY -- will use mock/demo mode")
    print()

    uvicorn.run(
        "goldshield.backend.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
