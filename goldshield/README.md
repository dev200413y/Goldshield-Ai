# GoldShield AI

**Tata Steel / Canara Bank Hackathon 2026 Submission**

GoldShield AI is a non-destructive, multi-agent AI verification system for gold loan processing. It solves the critical blind spot in modern gold loans: detecting internally contaminated jewelry (e.g., Tungsten cores) that pass traditional surface-level touchstone tests, while simultaneously monitoring portfolio LTV exposure and securing the digital custody chain.

## 🚀 Key Features

1. **Multi-Agent Verification Pipeline**
   - **Density & Volume Inspector (The Core Solution):** Uses photogrammetry heuristics (or full COLMAP 3D reconstruction) to estimate volume and calculate physical density, directly exposing internal base-metal cores.
   - **Surface & Seam Inspector:** Vision AI detects plating boundaries, uneven wear, and hidden solder joints.
   - **Hallmark Verification:** OCR and pattern matching against standard BIS HUID formats.
   - **Light-Signature Inspector:** Analyzes multi-angle reflectance consistency.
   - **Risk Officer (Fusion Agent):** Aggregates all 4 signals to produce a final Authenticity Score and Fraud Probability, with smart escalation routing.

2. **Digital Gold Fingerprint**
   - Generates a unique cryptographic hash (`GF-YYYY-XXXXXX`) combining the physical density signature, hallmark OCR data, and visual embeddings.
   - Prevents "in-custody swapping" by allowing the bank to re-verify the exact item upon loan closure.

3. **Live Valuation & LTV Enforcement**
   - Fetches live gold rates, calculates Fair Market Value (FMV), and strictly enforces the RBI 75% Loan-To-Value (LTV) cap at the point of appraisal.

## 🛠️ Architecture

- **Backend:** FastAPI, SQLite (Audit Log)
- **Frontend:** Vanilla HTML/CSS/JS (Glassmorphism, 3D CSS rendering)
- **Vision Models:** Multi-provider fallback (Gemini 2.5 Flash → Mistral Large → Ollama Local → Mock)
- **Photogrammetry:** COLMAP integration (available via feature flag `USE_PHOTOGRAMMETRY=True`)

## 💻 How to Run (Local Demo)

**Prerequisites:** Python 3.10+

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys (Optional but recommended):**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_google_ai_key
   MISTRAL_API_KEY=your_mistral_key
   ```
   *Note: If no API keys are provided, the system seamlessly falls back to a realistic Mock/Demo mode.*

3. **Start the Server:**
   ```bash
   python run.py
   ```

4. **Access the Dashboard:**
   - Dashboard: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`

## 🧊 3D Volume Reconstruction

To ensure a smooth live presentation, the dashboard defaults to an instant **AI-heuristic volume estimation** paired with a simulated Holographic 3D UI. 

For millimeter-accurate production environments, you can enable the fully integrated **COLMAP Multi-View Stereo photogrammetry pipeline** by setting `USE_PHOTOGRAMMETRY=True` in your environment. (Requires Nvidia CUDA and takes 5-15 minutes per appraisal).
