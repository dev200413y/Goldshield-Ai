"""
GoldShield AI — Database Layer (SQLite)
Tables match ARCHITECTURE.md §3. Append-only audit_log — no update/delete exposed.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from goldshield.config import DATABASE_PATH

logger = logging.getLogger("goldshield.backend.database")

# ─── Schema ─────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS appraisals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_ref TEXT NOT NULL,
    item_description TEXT,
    item_type TEXT DEFAULT 'ring',
    weight_grams REAL NOT NULL,
    declared_purity TEXT DEFAULT '22K',
    branch_id TEXT DEFAULT 'BR-001',
    photos_count INTEGER DEFAULT 0,
    water_volume_cm3 REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    density_result TEXT,
    surface_result TEXT,
    hallmark_result TEXT,
    touchstone_result TEXT,
    light_signature_result TEXT,
    authenticity_score INTEGER,
    fraud_probability INTEGER,
    confidence INTEGER,
    reasoning TEXT,
    recommendation TEXT,
    suspicious_area TEXT,
    escalated INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS gold_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    fingerprint_id TEXT UNIQUE NOT NULL,
    visual_hash TEXT,
    hallmark_signature TEXT,
    density_signature REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    gold_rate_per_gram REAL,
    rate_source TEXT,
    fair_market_value REAL,
    loan_amount_requested REAL DEFAULT 0,
    ltv_percent REAL,
    ltv_cap REAL DEFAULT 75.0,
    ltv_violation INTEGER DEFAULT 0,
    valued_at TEXT NOT NULL,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS custody_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    branch_id TEXT,
    vault_id TEXT,
    locker_id TEXT,
    event_type TEXT,
    staff_id TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS closure_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    fingerprint_id TEXT,
    match_confidence REAL,
    match_result TEXT,
    verified_at TEXT NOT NULL,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appraisal_id INTEGER NOT NULL,
    principal_amount REAL,
    disbursed_at TEXT,
    status TEXT DEFAULT 'active',
    current_ltv REAL,
    margin_call_flag INTEGER DEFAULT 0,
    FOREIGN KEY (appraisal_id) REFERENCES appraisals(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    action TEXT NOT NULL,
    actor TEXT DEFAULT 'system',
    timestamp TEXT NOT NULL,
    details TEXT
);
"""


class Database:
    """SQLite database manager for GoldShield AI."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    # ─── Audit Log (append-only, no update/delete) ──────────────────────

    def audit(self, entity_type: str, entity_id: int, action: str,
              actor: str = "system", details: str = ""):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, actor, timestamp, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entity_type, entity_id, action, actor, datetime.utcnow().isoformat(), details)
        )
        conn.commit()
        conn.close()

    # ─── Appraisals ─────────────────────────────────────────────────────

    def create_appraisal(self, customer_ref: str, item_description: str,
                         item_type: str, weight_grams: float,
                         declared_purity: str, branch_id: str,
                         photos_count: int = 0, water_volume_cm3: float = None) -> int:
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        cursor = conn.execute(
            "INSERT INTO appraisals (customer_ref, item_description, item_type, "
            "weight_grams, declared_purity, branch_id, photos_count, water_volume_cm3, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (customer_ref, item_description, item_type, weight_grams,
             declared_purity, branch_id, photos_count, water_volume_cm3, now)
        )
        appraisal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.audit("appraisal", appraisal_id, "created", details=f"weight={weight_grams}g, purity={declared_purity}")
        return appraisal_id

    def get_appraisal(self, appraisal_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM appraisals WHERE id = ?", (appraisal_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_appraisals(self, limit: int = 50) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT a.*, v.authenticity_score, v.fraud_probability, v.escalated "
            "FROM appraisals a "
            "LEFT JOIN verification_results v ON a.id = v.appraisal_id "
            "ORDER BY a.created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ─── Verification Results ───────────────────────────────────────────

    def save_verification(self, appraisal_id: int, verdict: Dict) -> int:
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        cursor = conn.execute(
            "INSERT INTO verification_results (appraisal_id, density_result, surface_result, "
            "hallmark_result, touchstone_result, light_signature_result, authenticity_score, "
            "fraud_probability, confidence, reasoning, recommendation, suspicious_area, "
            "escalated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                appraisal_id,
                json.dumps(verdict.get("density_result")) if verdict.get("density_result") else None,
                json.dumps(verdict.get("surface_result")) if verdict.get("surface_result") else None,
                json.dumps(verdict.get("hallmark_result")) if verdict.get("hallmark_result") else None,
                json.dumps(verdict.get("touchstone_result")) if verdict.get("touchstone_result") else None,
                json.dumps(verdict.get("light_signature_result")) if verdict.get("light_signature_result") else None,
                verdict.get("authenticity_score", 0),
                verdict.get("fraud_probability", 0),
                verdict.get("confidence", 0),
                verdict.get("reasoning", ""),
                verdict.get("recommendation", ""),
                verdict.get("suspicious_area"),
                1 if verdict.get("escalated") else 0,
                now,
            )
        )
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.audit("verification", result_id, "completed",
                   details=f"appraisal={appraisal_id}, score={verdict.get('authenticity_score')}")
        return result_id

    def get_verification(self, appraisal_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM verification_results WHERE appraisal_id = ? ORDER BY created_at DESC LIMIT 1",
            (appraisal_id,)
        ).fetchone()
        conn.close()
        if row:
            result = dict(row)
            for key in ["density_result", "surface_result", "hallmark_result",
                        "touchstone_result", "light_signature_result"]:
                if result.get(key):
                    result[key] = json.loads(result[key])
            return result
        return None

    # ─── Valuations ─────────────────────────────────────────────────────

    def save_valuation(self, appraisal_id: int, valuation: Dict) -> int:
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        cursor = conn.execute(
            "INSERT INTO valuations (appraisal_id, gold_rate_per_gram, rate_source, "
            "fair_market_value, loan_amount_requested, ltv_percent, ltv_cap, "
            "ltv_violation, valued_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                appraisal_id,
                valuation.get("gold_rate_per_gram", 0),
                valuation.get("rate_source", "cached"),
                valuation.get("fair_market_value", 0),
                valuation.get("loan_amount_requested", 0),
                valuation.get("ltv_percent", 0),
                valuation.get("ltv_cap", 75.0),
                1 if valuation.get("violation") else 0,
                now,
            )
        )
        val_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.audit("valuation", val_id, "computed",
                   details=f"appraisal={appraisal_id}, fmv={valuation.get('fair_market_value')}")
        return val_id

    # ─── Fingerprints ───────────────────────────────────────────────────

    def save_fingerprint(self, appraisal_id: int, fingerprint: Dict) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO gold_fingerprints (appraisal_id, fingerprint_id, visual_hash, "
            "hallmark_signature, density_signature, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                appraisal_id,
                fingerprint.get("fingerprint_id"),
                fingerprint.get("visual_hash"),
                fingerprint.get("hallmark_signature"),
                fingerprint.get("density_signature"),
                fingerprint.get("created_at", datetime.utcnow().isoformat()),
            )
        )
        fp_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.audit("fingerprint", fp_id, "generated",
                   details=f"appraisal={appraisal_id}, fp_id={fingerprint.get('fingerprint_id')}")
        return fp_id

    def get_fingerprint(self, appraisal_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM gold_fingerprints WHERE appraisal_id = ? ORDER BY created_at DESC LIMIT 1",
            (appraisal_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    # ─── Valuations (Read) ──────────────────────────────────────────────

    def get_valuation(self, appraisal_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM valuations WHERE appraisal_id = ? ORDER BY valued_at DESC LIMIT 1",
            (appraisal_id,)
        ).fetchone()
        conn.close()
        if row:
            result = dict(row)
            result["violation"] = bool(result.get("ltv_violation", 0))
            return result
        return None

    # ─── Full Appraisal (Joined) ────────────────────────────────────────

    def get_full_appraisal(self, appraisal_id: int) -> Optional[Dict]:
        """Get complete appraisal with verification, valuation, and fingerprint."""
        appraisal = self.get_appraisal(appraisal_id)
        if not appraisal:
            return None

        verification = self.get_verification(appraisal_id)
        valuation = self.get_valuation(appraisal_id)
        fingerprint = self.get_fingerprint(appraisal_id)

        return {
            **appraisal,
            "verification": verification,
            "valuation": valuation,
            "fingerprint": fingerprint,
        }

    # ─── Detailed Appraisals List ───────────────────────────────────────

    def list_appraisals_detailed(self, limit: int = 100) -> List[Dict]:
        """List appraisals with joined verification, valuation, and fingerprint data."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT a.*, "
            "v.authenticity_score, v.fraud_probability, v.confidence, v.escalated, "
            "v.reasoning, v.recommendation, v.suspicious_area, "
            "v.density_result, v.surface_result, v.hallmark_result, "
            "v.touchstone_result, v.light_signature_result, "
            "val.gold_rate_per_gram, val.rate_source, val.fair_market_value, "
            "val.loan_amount_requested, val.ltv_percent, val.ltv_cap, val.ltv_violation, "
            "fp.fingerprint_id, fp.visual_hash, fp.hallmark_signature, fp.density_signature "
            "FROM appraisals a "
            "LEFT JOIN verification_results v ON a.id = v.appraisal_id "
            "LEFT JOIN valuations val ON a.id = val.appraisal_id "
            "LEFT JOIN gold_fingerprints fp ON a.id = fp.appraisal_id "
            "ORDER BY a.created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()

        results = []
        for r in rows:
            record = dict(r)
            # Parse JSON inspector results
            for key in ["density_result", "surface_result", "hallmark_result",
                        "touchstone_result", "light_signature_result"]:
                if record.get(key):
                    try:
                        record[key] = json.loads(record[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            record["violation"] = bool(record.get("ltv_violation", 0))
            results.append(record)

        return results

    # ─── Dashboard Aggregates ───────────────────────────────────────────

    def get_dashboard_stats(self) -> Dict:
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) as c FROM appraisals").fetchone()["c"]
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) as c FROM appraisals WHERE created_at LIKE ?",
            (f"{today}%",)
        ).fetchone()["c"]

        flagged = conn.execute(
            "SELECT COUNT(*) as c FROM verification_results WHERE escalated = 1"
        ).fetchone()["c"]

        avg_score = conn.execute(
            "SELECT AVG(authenticity_score) as avg FROM verification_results"
        ).fetchone()["avg"] or 0

        total_weight = conn.execute(
            "SELECT SUM(weight_grams) as total FROM appraisals"
        ).fetchone()["total"] or 0

        total_fmv = conn.execute(
            "SELECT SUM(fair_market_value) as total FROM valuations"
        ).fetchone()["total"] or 0

        conn.close()

        return {
            "total_appraisals": total,
            "today_appraisals": today_count,
            "flagged_cases": flagged,
            "average_authenticity_score": round(avg_score, 1),
            "total_gold_grams": round(total_weight, 2),
            "total_portfolio_value": round(total_fmv, 2),
        }


# ─── Global instance ────────────────────────────────────────────────────────
db = Database()
