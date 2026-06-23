"""
services/ai.py
Generates AI remarks + ML risk for a patient.

Flow:
  1. Always run local ML risk engine (ml_risk.py) → instant, no API needed.
  2. If LOVABLE_API_KEY is set, call the Lovable AI Gateway with the risk
     report as context → richer narrative from Gemini.
  3. If API unavailable/fails, fall back to the ML report text.
  4. Always append the fixed medical disclaimer.
"""
import os
import requests as req_lib
from datetime import datetime
from flask import current_app

from services.ml_risk import analyse_patient, report_to_text, RISK_COLORS, RISK_ICONS

DISCLAIMER = (
    "⚠️ MEDICAL DISCLAIMER: This assessment is for informational purposes only "
    "and does not constitute medical advice. Always consult a qualified healthcare "
    "professional for diagnosis and treatment decisions."
)

FALLBACK_NOTE = "AI narrative unavailable — showing ML risk analysis only."


def _compute_age(dob) -> int:
    today = datetime.utcnow().date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def generate_remarks(patient) -> str:
    """
    Main entry point called by routes.
    Returns a rich text block ready to store in Patient.remarks.
    Raises _GatewayError on 429/402 from the AI gateway.
    """
    # ── Step 1: Local ML risk analysis (always runs) ────────────────────────
    report = analyse_patient(patient)
    ml_text = report_to_text(report)

    # ── Step 2: Try AI Gateway for narrative enrichment ─────────────────────
    api_key = current_app.config.get("LOVABLE_API_KEY", "").strip()
    if api_key:
        try:
            narrative = _call_gateway(patient, report, api_key)
            combined = (
                f"{ml_text}\n\n"
                f"--- AI CLINICAL NARRATIVE ---\n{narrative}"
            )
            return combined + "\n\n" + DISCLAIMER
        except _GatewayError:
            raise
        except Exception:
            pass  # Fall through to ML-only

    # ── Step 3: ML-only fallback ────────────────────────────────────────────
    return ml_text + "\n\n" + DISCLAIMER


def _call_gateway(patient, report, api_key: str) -> str:
    """Call Lovable AI Gateway and return the narrative text."""
    model = current_app.config.get("AI_MODEL", "google/gemini-2.5-flash-preview")
    gateway_url = current_app.config.get(
        "AI_GATEWAY_URL", "https://ai.gateway.lovable.dev/v1/chat/completions"
    )

    age = _compute_age(patient.date_of_birth)
    conditions = ", ".join(report.conditions)
    abnormal = [m for m in report.markers if m.risk_level != "Low"]
    abnormal_desc = "; ".join(
        f"{m.name} {m.value} {m.unit} ({m.status})" for m in abnormal
    ) if abnormal else "none"

    prompt = (
        f"Patient: {patient.full_name}, Age: {age}.\n"
        f"Lab Values: Glucose {patient.glucose} mg/dL, "
        f"Haemoglobin {patient.haemoglobin} g/dL, "
        f"Cholesterol {patient.cholesterol} mg/dL.\n"
        f"Pre-computed risk score: {report.risk_score}/100 ({report.overall_risk} risk).\n"
        f"Flagged conditions: {conditions}.\n"
        f"Abnormal markers: {abnormal_desc}.\n\n"
        "Write a concise, evidence-based clinical narrative (4-6 sentences) for a doctor's notes. "
        "Explain WHY each flagged value is concerning, what disease processes are indicated, "
        "and what the most important next clinical steps are. "
        "Be specific and actionable. Do not repeat the raw numbers — interpret them."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior clinical physician writing structured notes "
                    "for a patient health record. Be concise, specific, and evidence-based. "
                    "Focus on clinical interpretation and actionable recommendations."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 450,
        "temperature": 0.35,
    }

    response = req_lib.post(gateway_url, json=payload, headers=headers, timeout=30)

    if response.status_code == 429:
        raise _GatewayError(429, "Rate limit reached — AI narrative skipped. ML analysis saved.")
    if response.status_code == 402:
        raise _GatewayError(402, "AI credits exhausted — ML analysis saved. Top up your Lovable account.")
    if response.status_code != 200:
        return FALLBACK_NOTE

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def get_risk_meta(patient) -> dict:
    """
    Return risk metadata for the current patient WITHOUT regenerating remarks.
    Used by templates for colour coding when remarks already exist.
    """
    report = analyse_patient(patient)
    return {
        "overall_risk": report.overall_risk,
        "risk_score": report.risk_score,
        "color": RISK_COLORS.get(report.overall_risk, "secondary"),
        "icon": RISK_ICONS.get(report.overall_risk, "bi-question-circle"),
        "conditions": report.conditions,
        "markers": report.markers,
        "recommendations": report.recommendations,
    }


class _GatewayError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)
