import os
import unittest
from datetime import date, timedelta
from app import create_app
from extensions import db
from models import User, Patient

class PatientManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        self.app = create_app("testing")
        self.app.config["LOVABLE_API_KEY"] = ""  # empty so we use local ML fallback

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create all tables
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_auth_and_crud_flow(self):
        # 1. Test registration
        response = self.client.post("/register", data={
            "full_name": "Test Doctor",
            "email": "doctor@test.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account created! Please log in.", response.data)

        # 2. Test login
        response = self.client.post("/login", data={
            "email": "doctor@test.com",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back, Test Doctor!", response.data)

        # 3. Test patient CRUD
        # Add patient (valid data)
        response = self.client.post("/patients/add", data={
            "full_name": "John Doe",
            "date_of_birth": "1980-05-15",
            "email": "john.doe@example.com",
            "glucose": "110",
            "haemoglobin": "14.5",
            "cholesterol": "220"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Patient &#39;John Doe&#39; added successfully.", response.data)
        self.assertIn(b"John Doe", response.data)
        self.assertIn(b"Pre-diabetic", response.data)  # local ML engine output should be present

        # View patient list
        response = self.client.get("/patients/", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"John Doe", response.data)
        self.assertIn(b"john.doe@example.com", response.data)

        # Edit patient
        response = self.client.post("/patients/1/edit", data={
            "full_name": "John Doe Jr",
            "date_of_birth": "1980-05-15",
            "email": "john.doe@example.com",
            "glucose": "85",            # Changed from 110 to 85 (Normal)
            "haemoglobin": "14.5",
            "cholesterol": "180"         # Changed from 220 to 180 (Optimal)
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Patient record updated.", response.data)
        self.assertIn(b"John Doe Jr", response.data)
        self.assertIn(b"Normal", response.data)

        # Delete patient
        response = self.client.post("/patients/1/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Patient &#39;John Doe Jr&#39; deleted.", response.data)

        # Check list is empty
        response = self.client.get("/patients/")
        self.assertNotIn(b"John Doe Jr", response.data)

    def test_validation_rules(self):
        # Log in first
        self.client.post("/register", data={
            "full_name": "Test Doctor",
            "email": "doctor@test.com",
            "password": "password123",
            "confirm_password": "password123"
        })
        self.client.post("/login", data={
            "email": "doctor@test.com",
            "password": "password123"
        })

        # Test invalid email format
        response = self.client.post("/patients/add", data={
            "full_name": "Bad Email",
            "date_of_birth": "1990-01-01",
            "email": "not-an-email",
            "glucose": "100",
            "haemoglobin": "14",
            "cholesterol": "200"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email address.", response.data)

        # Test future DOB
        future_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.post("/patients/add", data={
            "full_name": "Future Baby",
            "date_of_birth": future_date,
            "email": "baby@example.com",
            "glucose": "100",
            "haemoglobin": "14",
            "cholesterol": "200"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Date of birth cannot be in the future.", response.data)

        # Test out of bounds/non-numeric values
        response = self.client.post("/patients/add", data={
            "full_name": "Bad Labs",
            "date_of_birth": "1995-05-20",
            "email": "labs@example.com",
            "glucose": "abc",  # non-numeric
            "haemoglobin": "14",
            "cholesterol": "200"
        })
        self.assertEqual(response.status_code, 200)
        # wtforms should reject non-numeric inputs
        self.assertTrue(
            b"Not a valid float value" in response.data or
            b"Glucose must be between" in response.data or
            b"Number must be between" in response.data
        )

if __name__ == "__main__":
    unittest.main()
