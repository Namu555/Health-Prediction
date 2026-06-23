"""
routes/patients.py
Patient CRUD blueprint: list/search/paginate, add, edit, detail,
delete, CSV export, and AI remarks regeneration.
"""
import csv
import io
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    Response,
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from models import Patient
from forms import PatientForm
from services.ai import generate_remarks, _GatewayError, DISCLAIMER
from services.ml_risk import analyse_patient, report_to_text

patients_bp = Blueprint("patients", __name__, url_prefix="/patients")

PER_PAGE = 10


def _get_patient_or_404(patient_id: int) -> Patient:
    """Fetch a patient belonging to the current user or 404."""
    patient = db.session.get(Patient, patient_id)
    if not patient or patient.user_id != current_user.id:
        abort(404)
    return patient


# ---------------------------------------------------------------------------
# List / Search
# ---------------------------------------------------------------------------

@patients_bp.route("/")
@login_required
def list_patients():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = current_user.patients
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Patient.full_name.ilike(like), Patient.email.ilike(like))
        )

    pagination = query.order_by(Patient.created_at.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    return render_template(
        "patients/list.html",
        pagination=pagination,
        patients=pagination.items,
        q=q,
    )


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

@patients_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient(
            user_id=current_user.id,
            full_name=form.full_name.data.strip(),
            date_of_birth=form.date_of_birth.data,
            email=form.email.data.lower().strip(),
            glucose=form.glucose.data,
            haemoglobin=form.haemoglobin.data,
            cholesterol=form.cholesterol.data,
        )
        db.session.add(patient)
        db.session.flush()  # get patient.id before AI call

        try:
            patient.remarks = generate_remarks(patient)
        except _GatewayError as e:
            if e.status_code == 429:
                flash(e.message, "warning")
            elif e.status_code == 402:
                flash(e.message, "danger")
            # Save local ML analysis fallback
            patient.remarks = (
                report_to_text(analyse_patient(patient))
                + f"\n\n⚠️ NOTE: AI narrative skipped ({e.message})\n\n"
                + DISCLAIMER
            )

        db.session.commit()
        flash(f"Patient '{patient.full_name}' added successfully.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))

    return render_template("patients/add.html", form=form)


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

@patients_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id: int):
    patient = _get_patient_or_404(patient_id)
    form = PatientForm(obj=patient)

    if form.validate_on_submit():
        patient.full_name = form.full_name.data.strip()
        patient.date_of_birth = form.date_of_birth.data
        patient.email = form.email.data.lower().strip()
        patient.glucose = form.glucose.data
        patient.haemoglobin = form.haemoglobin.data
        patient.cholesterol = form.cholesterol.data
        patient.updated_at = datetime.utcnow()

        try:
            patient.remarks = generate_remarks(patient)
        except _GatewayError as e:
            if e.status_code == 429:
                flash(e.message, "warning")
            elif e.status_code == 402:
                flash(e.message, "danger")
            # Update remarks using new lab values and local ML engine
            patient.remarks = (
                report_to_text(analyse_patient(patient))
                + f"\n\n⚠️ NOTE: AI narrative skipped ({e.message})\n\n"
                + DISCLAIMER
            )

        db.session.commit()
        flash("Patient record updated.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))

    return render_template("patients/edit.html", form=form, patient=patient)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@patients_bp.route("/<int:patient_id>")
@login_required
def detail(patient_id: int):
    patient = _get_patient_or_404(patient_id)
    return render_template("patients/detail.html", patient=patient)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@patients_bp.route("/<int:patient_id>/delete", methods=["POST"])
@login_required
def delete_patient(patient_id: int):
    patient = _get_patient_or_404(patient_id)
    name = patient.full_name
    db.session.delete(patient)
    db.session.commit()
    flash(f"Patient '{name}' deleted.", "info")
    return redirect(url_for("patients.list_patients"))


# ---------------------------------------------------------------------------
# Regenerate AI Remarks
# ---------------------------------------------------------------------------

@patients_bp.route("/<int:patient_id>/regenerate", methods=["POST"])
@login_required
def regenerate(patient_id: int):
    patient = _get_patient_or_404(patient_id)
    try:
        patient.remarks = generate_remarks(patient)
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        flash("AI remarks regenerated successfully.", "success")
    except _GatewayError as e:
        if e.status_code == 429:
            flash(e.message, "warning")
        elif e.status_code == 402:
            flash(e.message, "danger")
    return redirect(url_for("patients.detail", patient_id=patient.id))


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

@patients_bp.route("/export.csv")
@login_required
def export_csv():
    patients = current_user.patients.order_by(Patient.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "Full Name", "Date of Birth", "Email",
         "Glucose (mg/dL)", "Haemoglobin (g/dL)", "Cholesterol (mg/dL)",
         "Created At", "Updated At", "Remarks"]
    )
    for p in patients:
        writer.writerow(
            [
                p.id,
                p.full_name,
                p.date_of_birth.isoformat(),
                p.email,
                p.glucose,
                p.haemoglobin,
                p.cholesterol,
                p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                p.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                p.remarks or "",
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=patients_export.csv"
        },
    )
