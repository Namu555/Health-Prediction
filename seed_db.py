"""
seed_db.py
Seeds the Flask Patient Manager database with a default doctor user
and a realistic clinical dataset of 6 patients spanning various risk profiles.
"""
import sys
from datetime import date, timedelta
from app import create_app
from extensions import db
from models import User, Patient
from services.ai import generate_remarks

def seed():
    app = create_app("development")
    with app.app_context():
        print("Checking database for default seed data...")
        
        # 1. Create default doctor user if not present
        doctor_email = "doctor@example.com"
        doctor = User.query.filter_by(email=doctor_email).first()
        if not doctor:
            print("Creating default doctor account (doctor@example.com / password123)...")
            doctor = User(
                full_name="Dr. Sarah Carter",
                email=doctor_email
            )
            doctor.set_password("password123")
            db.session.add(doctor)
            db.session.commit()
        else:
            print("Default doctor account already exists.")

        # 2. Add sample patient dataset if the doctor has no patients
        if doctor.patients.count() == 0:
            print("Seeding sample patient dataset...")
            
            # Helper to calculate date of birth from age
            def dob_from_age(age: int) -> date:
                return date.today() - timedelta(days=int(age * 365.25))

            sample_patients = [
                {
                    "full_name": "Marcus Vance",
                    "date_of_birth": dob_from_age(52),
                    "email": "marcus.vance@example.com",
                    "glucose": 142.0,       # Diabetic range
                    "haemoglobin": 14.8,    # Normal
                    "cholesterol": 245.0,    # High cholesterol (CVD Risk)
                },
                {
                    "full_name": "Elena Rostova",
                    "date_of_birth": dob_from_age(28),
                    "email": "elena.rostova@example.com",
                    "glucose": 88.0,        # Normal
                    "haemoglobin": 9.2,     # Anaemia
                    "cholesterol": 170.0,    # Optimal
                },
                {
                    "full_name": "Arthur Pendelton",
                    "date_of_birth": dob_from_age(67),
                    "email": "arthur.p@example.com",
                    "glucose": 215.0,       # Severely Elevated (Critical)
                    "haemoglobin": 11.5,    # Mild Anaemia
                    "cholesterol": 310.0,    # Very High (Critical CVD)
                },
                {
                    "full_name": "Clara Higgins",
                    "date_of_birth": dob_from_age(34),
                    "email": "clara.h@example.com",
                    "glucose": 82.0,        # Normal
                    "haemoglobin": 13.5,    # Normal
                    "cholesterol": 182.0,    # Optimal (Low Risk)
                },
                {
                    "full_name": "David Miller",
                    "date_of_birth": dob_from_age(41),
                    "email": "d.miller@example.com",
                    "glucose": 61.0,        # Hypoglycaemia
                    "haemoglobin": 15.2,    # Normal
                    "cholesterol": 195.0,    # Optimal
                },
                {
                    "full_name": "Zoe Washburne",
                    "date_of_birth": dob_from_age(49),
                    "email": "zoe.w@example.com",
                    "glucose": 115.0,       # Pre-diabetic
                    "haemoglobin": 12.8,    # Normal
                    "cholesterol": 222.0,    # Borderline High
                }
            ]

            for p_data in sample_patients:
                patient = Patient(
                    user_id=doctor.id,
                    full_name=p_data["full_name"],
                    date_of_birth=p_data["date_of_birth"],
                    email=p_data["email"],
                    glucose=p_data["glucose"],
                    haemoglobin=p_data["haemoglobin"],
                    cholesterol=p_data["cholesterol"]
                )
                # Compute remarks (local engine fallback or remote gateway depending on API key config)
                patient.remarks = generate_remarks(patient)
                db.session.add(patient)
                print(f"  Added patient: {patient.full_name} ({p_data['glucose']} mg/dL Glucose, {p_data['haemoglobin']} g/dL Haemoglobin, {p_data['cholesterol']} mg/dL Cholesterol)")

            db.session.commit()
            print("Database seeding completed successfully!")
        else:
            print("Database already contains patients. Seeding skipped.")

if __name__ == "__main__":
    seed()
