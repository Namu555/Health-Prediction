"""
routes/main.py
Main blueprint: landing page, dashboard, and account management.
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Patient
from forms import AccountForm

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    total = current_user.patients.count()
    recent = (
        current_user.patients.order_by(Patient.created_at.desc()).limit(5).all()
    )
    return render_template("dashboard.html", total=total, recent=recent)


@main_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = AccountForm(obj=current_user)
    if form.validate_on_submit():
        # Check email uniqueness if changed
        new_email = form.email.data.lower().strip()
        if new_email != current_user.email:
            from models import User
            conflict = User.query.filter_by(email=new_email).first()
            if conflict:
                flash("That email is already in use.", "danger")
                return render_template("account.html", form=form)
        current_user.full_name = form.full_name.data.strip()
        current_user.email = new_email
        db.session.commit()
        flash("Account updated successfully.", "success")
        return redirect(url_for("main.account"))
    return render_template("account.html", form=form)
