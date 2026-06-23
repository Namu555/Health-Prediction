"""
services/ml_risk.py
Local rule-based ML risk engine.

Acts as the primary fallback when the AI Gateway is unavailable
AND enriches the AI prompt with pre-computed risk scores.

Reference ranges used:
  Glucose (fasting):  Normal  70–99 mg/dL
                      Pre-DM  100–125 mg/dL
                      DM      ≥ 126 mg/dL
  Haemoglobin:        Male    13.5–17.5 g/dL
                      Female  12.0–15.5 g/dL
                      (we use combined range 12–17)
  Cholesterol (total):Optimal < 200 mg/dL
                      Borderline 200–239 mg/dL
                      High    ≥ 240 mg/dL
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


# ── Risk level constants ────────────────────────────────────────────────────
LOW      = "Low"
MODERATE = "Moderate"
HIGH     = "High"
CRITICAL = "Critical"

RISK_COLORS = {
    LOW:      "success",
    MODERATE: "warning",
    HIGH:     "danger",
    CRITICAL: "danger",
}

RISK_ICONS = {
    LOW:      "bi-check-circle-fill",
    MODERATE: "bi-exclamation-circle-fill",
    HIGH:     "bi-exclamation-triangle-fill",
    CRITICAL: "bi-x-octagon-fill",
}


# ── Per-marker analysis ──────────────────────────────────────────────────────
@dataclass
class MarkerResult:
    name: str
    value: float
    unit: str
    status: str          # "Normal", "Low", "Pre-diabetic", etc.
    risk_level: str      # LOW / MODERATE / HIGH / CRITICAL
    note: str


@dataclass
class RiskReport:
    overall_risk: str
    risk_score: int          # 0–100
    conditions: List[str]    # e.g. ["Diabetes Risk", "Anaemia"]
    markers: List[MarkerResult]
    summary: str             # Short plain-text paragraph
    recommendations: List[str]


# ── Individual marker analysis ───────────────────────────────────────────────
def _analyse_glucose(glucose: float, age: int) -> MarkerResult:
    if glucose < 70:
        return MarkerResult(
            "Glucose", glucose, "mg/dL",
            "Hypoglycaemia", HIGH,
            "Blood glucose critically low. Risk of hypoglycaemic episodes."
        )
    elif glucose <= 99:
        return MarkerResult(
            "Glucose", glucose, "mg/dL",
            "Normal", LOW,
            "Fasting glucose within normal range."
        )
    elif glucose <= 125:
        return MarkerResult(
            "Glucose", glucose, "mg/dL",
            "Pre-diabetic", MODERATE,
            "Elevated fasting glucose indicates pre-diabetes. Lifestyle modification advised."
        )
    elif glucose <= 200:
        return MarkerResult(
            "Glucose", glucose, "mg/dL",
            "Diabetic Range", HIGH,
            "Glucose consistent with diabetes mellitus. Formal HbA1c testing required."
        )
    else:
        return MarkerResult(
            "Glucose", glucose, "mg/dL",
            "Severely Elevated", CRITICAL,
            "Severely elevated glucose. Immediate clinical evaluation needed."
        )


def _analyse_haemoglobin(hb: float, age: int) -> MarkerResult:
    if hb < 8:
        return MarkerResult(
            "Haemoglobin", hb, "g/dL",
            "Severe Anaemia", CRITICAL,
            "Severely low haemoglobin. Transfusion may be required."
        )
    elif hb < 12:
        return MarkerResult(
            "Haemoglobin", hb, "g/dL",
            "Anaemia", HIGH,
            "Low haemoglobin indicates anaemia. Iron panel and further workup advised."
        )
    elif hb <= 17:
        return MarkerResult(
            "Haemoglobin", hb, "g/dL",
            "Normal", LOW,
            "Haemoglobin within normal range."
        )
    else:
        return MarkerResult(
            "Haemoglobin", hb, "g/dL",
            "Polycythaemia", MODERATE,
            "Elevated haemoglobin. Rule out dehydration or polycythaemia vera."
        )


def _analyse_cholesterol(chol: float, age: int) -> MarkerResult:
    if chol < 150:
        return MarkerResult(
            "Cholesterol", chol, "mg/dL",
            "Low", MODERATE,
            "Very low cholesterol may indicate malnutrition or liver disease."
        )
    elif chol < 200:
        return MarkerResult(
            "Cholesterol", chol, "mg/dL",
            "Optimal", LOW,
            "Total cholesterol within desirable range."
        )
    elif chol < 240:
        return MarkerResult(
            "Cholesterol", chol, "mg/dL",
            "Borderline High", MODERATE,
            "Borderline high cholesterol. Dietary review and lipid panel advised."
        )
    elif chol < 300:
        return MarkerResult(
            "Cholesterol", chol, "mg/dL",
            "High", HIGH,
            "High cholesterol significantly increases cardiovascular disease risk."
        )
    else:
        return MarkerResult(
            "Cholesterol", chol, "mg/dL",
            "Very High", CRITICAL,
            "Very high cholesterol. Statin therapy and specialist referral should be considered."
        )


# ── Risk score calculation ───────────────────────────────────────────────────
_LEVEL_WEIGHTS = {LOW: 0, MODERATE: 25, HIGH: 50, CRITICAL: 80}


def _compute_score(markers: List[MarkerResult], age: int) -> int:
    base = max(_LEVEL_WEIGHTS[m.risk_level] for m in markers)
    # Age modifies risk
    age_bonus = 5 if age > 50 else (3 if age > 35 else 0)
    # Multiple abnormal markers compound risk
    abnormal = sum(1 for m in markers if m.risk_level != LOW)
    compound = (abnormal - 1) * 8 if abnormal > 1 else 0
    return min(100, base + age_bonus + compound)


def _overall_from_score(score: int) -> str:
    if score < 20:
        return LOW
    elif score < 50:
        return MODERATE
    elif score < 75:
        return HIGH
    else:
        return CRITICAL


# ── Conditions detection ─────────────────────────────────────────────────────
def _detect_conditions(markers: List[MarkerResult]) -> List[str]:
    conds: List[str] = []
    status_map = {m.name: m.status for m in markers}
    if status_map.get("Glucose") in ("Pre-diabetic", "Diabetic Range", "Severely Elevated"):
        conds.append("Diabetes / Pre-Diabetes Risk")
    if status_map.get("Glucose") == "Hypoglycaemia":
        conds.append("Hypoglycaemia Risk")
    if status_map.get("Haemoglobin") in ("Anaemia", "Severe Anaemia"):
        conds.append("Anaemia")
    if status_map.get("Haemoglobin") == "Polycythaemia":
        conds.append("Polycythaemia")
    if status_map.get("Cholesterol") in ("Borderline High", "High", "Very High"):
        conds.append("Cardiovascular Disease Risk")
    return conds if conds else ["No immediate risk conditions detected"]


# ── Recommendations ──────────────────────────────────────────────────────────
def _recommendations(markers: List[MarkerResult], age: int) -> List[str]:
    recs: List[str] = []
    status_map = {m.name: (m.status, m.risk_level) for m in markers}

    g_stat, g_lvl = status_map.get("Glucose", ("Normal", LOW))
    hb_stat, hb_lvl = status_map.get("Haemoglobin", ("Normal", LOW))
    ch_stat, ch_lvl = status_map.get("Cholesterol", ("Normal", LOW))

    if g_lvl in (MODERATE, HIGH, CRITICAL):
        recs.append("Schedule HbA1c and fasting glucose repeat test within 4 weeks.")
        recs.append("Reduce refined sugar and carbohydrate intake.")
    if g_stat == "Hypoglycaemia":
        recs.append("Monitor blood glucose hourly; consider oral glucose or IV dextrose.")
    if hb_lvl in (HIGH, CRITICAL):
        recs.append("Order iron studies, B12, folate, and peripheral blood smear.")
    if hb_lvl == MODERATE and hb_stat == "Polycythaemia":
        recs.append("Check oxygen saturation; rule out secondary polycythaemia.")
    if ch_lvl in (MODERATE, HIGH, CRITICAL):
        recs.append("Initiate dietary fat reduction — increase fibre and omega-3 intake.")
        recs.append("Consider full lipid panel (HDL, LDL, TG) for cardiovascular risk stratification.")
    if ch_lvl in (HIGH, CRITICAL):
        recs.append("Evaluate statin therapy eligibility in consultation with a physician.")
    if age > 50:
        recs.append("Annual comprehensive metabolic panel recommended for patients over 50.")
    if not recs:
        recs.append("Continue healthy lifestyle — balanced diet and regular physical activity.")
        recs.append("Routine follow-up in 12 months.")
    return recs


# ── Main entry point ─────────────────────────────────────────────────────────
def analyse_patient(patient) -> RiskReport:
    """
    Run the local ML risk engine on a Patient model instance.
    Returns a RiskReport dataclass.
    """
    age = patient.age()
    markers = [
        _analyse_glucose(patient.glucose, age),
        _analyse_haemoglobin(patient.haemoglobin, age),
        _analyse_cholesterol(patient.cholesterol, age),
    ]
    score = _compute_score(markers, age)
    overall = _overall_from_score(score)
    conditions = _detect_conditions(markers)
    recs = _recommendations(markers, age)

    # Build a plain-text summary
    abnormal_parts = [f"{m.name} ({m.status})" for m in markers if m.risk_level != LOW]
    if abnormal_parts:
        summary = (
            f"Lab review for {patient.full_name} (age {age}) shows concern in: "
            + ", ".join(abnormal_parts)
            + ". Overall health risk is assessed as "
            + overall.upper()
            + f" (score {score}/100). Prompt clinical review advised."
        )
    else:
        summary = (
            f"All lab values for {patient.full_name} (age {age}) are within "
            "normal reference ranges. Overall health risk is LOW. "
            "Continue routine monitoring."
        )

    return RiskReport(
        overall_risk=overall,
        risk_score=score,
        conditions=conditions,
        markers=markers,
        summary=summary,
        recommendations=recs,
    )


def report_to_text(report: RiskReport) -> str:
    """Convert a RiskReport to a plain-text string for storing in remarks."""
    lines = [
        f"RISK LEVEL: {report.overall_risk} (Score: {report.risk_score}/100)",
        "",
        f"DETECTED CONDITIONS: {', '.join(report.conditions)}",
        "",
        "MARKER ANALYSIS:",
    ]
    for m in report.markers:
        lines.append(f"  • {m.name}: {m.value} {m.unit} — {m.status} [{m.risk_level}]")
        lines.append(f"    {m.note}")
    lines += ["", "SUMMARY:", report.summary, "", "RECOMMENDATIONS:"]
    for r in report.recommendations:
        lines.append(f"  • {r}")
    return "\n".join(lines)
