"""
forms.py
WTForms form definitions with server-side validators mirroring client-side rules.
"""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    EmailField,
    DateField,
    FloatField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    ValidationError,
    Optional,
)


# ---------------------------------------------------------------------------
# Helper validators
# ---------------------------------------------------------------------------

def _dob_after_1900(form, field):
    if field.data and field.data <= date(1900, 1, 1):
        raise ValidationError("Date of birth must be after 1900-01-01.")


def _dob_not_future(form, field):
    if field.data and field.data > date.today():
        raise ValidationError("Date of birth cannot be in the future.")


# ---------------------------------------------------------------------------
# Auth forms
# ---------------------------------------------------------------------------

class RegisterForm(FlaskForm):
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )
    submit = SubmitField("Sign In")


# ---------------------------------------------------------------------------
# Patient form
# ---------------------------------------------------------------------------

class PatientForm(FlaskForm):
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    date_of_birth = DateField(
        "Date of Birth",
        validators=[InputRequired(message="Date of birth is required."), _dob_after_1900, _dob_not_future],
        format="%Y-%m-%d",
    )
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    glucose = FloatField(
        "Glucose (mg/dL)",
        validators=[InputRequired(message="Glucose is required."), NumberRange(min=20, max=800, message="Glucose must be between 20 and 800 mg/dL.")],
    )
    haemoglobin = FloatField(
        "Haemoglobin (g/dL)",
        validators=[InputRequired(message="Haemoglobin is required."), NumberRange(min=2, max=25, message="Haemoglobin must be between 2 and 25 g/dL.")],
    )
    cholesterol = FloatField(
        "Cholesterol (mg/dL)",
        validators=[InputRequired(message="Cholesterol is required."), NumberRange(min=50, max=500, message="Cholesterol must be between 50 and 500 mg/dL.")],
    )
    submit = SubmitField("Save Patient")


# ---------------------------------------------------------------------------
# Account form
# ---------------------------------------------------------------------------

class AccountForm(FlaskForm):
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    submit = SubmitField("Update Account")
