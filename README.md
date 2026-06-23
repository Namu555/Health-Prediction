# 🏥 PatientManager — Flask Application

A secure, full-featured patient health record management system with AI-powered clinical insights, built with Flask 3, Bootstrap 5, and the Lovable AI Gateway.

---

## ✨ Features

- **Secure auth** — Registration, login, logout with Werkzeug password hashing & CSRF protection
- **Patient CRUD** — Add, edit, view, delete patient records with full validation
- **AI Clinical Remarks** — Automated lab assessment via Gemini AI (flagging abnormal values, risks, recommendations)
- **Search & Paginate** — Full-text search by name/email, 10 records/page
- **CSV Export** — One-click download of all patient data
- **Dashboard** — Stats overview, recent patients, quick actions
- **Responsive** — Mobile-friendly Bootstrap 5 grid

---

## 🛠 Prerequisites

- **Python 3.11+**
- **pip** (comes with Python)

---

## 🚀 Quick Start

### 1. Navigate to the flask_app directory

```bash
cd flask_app
```

### 2. Create & activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random secret (run `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `LOVABLE_API_KEY` | Your Lovable API key (see below) |
| `DATABASE_URL` | Optional — defaults to SQLite |

#### 🔑 Getting your Lovable API Key

1. Go to [https://lovable.dev](https://lovable.dev) and sign in
2. Navigate to **Settings → API Keys**
3. Create a new key and copy it into `.env` as `LOVABLE_API_KEY`

> Without a key, the app still works — patients save normally, and remarks will show "AI remarks unavailable — please regenerate."

### 5. Initialise the database

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

### 6. Seed sample patient data (Recommended)

To populate the database with a default doctor account (`doctor@example.com` / `password123`) and 6 realistic patient records (ranging from Low to Critical health risk profiles), run the database seeder:

```bash
python seed_db.py
```

### 7. Run the development server

```bash
flask --app app run --debug
```

Open **http://127.0.0.1:5000** in your browser.

---

## 🗄 Database

### SQLite (default)

No configuration needed. The database file is stored at `instance/patients.db`.

### PostgreSQL

Set `DATABASE_URL` in your `.env`:

```
DATABASE_URL=postgresql://username:password@localhost:5432/patientmanager
```

Then run `flask db upgrade` to apply migrations.

---

## 🌐 Production Deployment

### Option 1 — Render.com

1. Push `flask_app/` to a GitHub repository
2. Create a new **Web Service** on Render
3. Set Build Command: `pip install -r requirements.txt && flask db upgrade`
4. Set Start Command: `gunicorn app:app`
5. Add environment variables in Render dashboard (`SECRET_KEY`, `LOVABLE_API_KEY`, `DATABASE_URL`, `FLASK_ENV=production`)

### Option 2 — Railway.app

1. Create a new project → Deploy from GitHub
2. Add a PostgreSQL plugin
3. Set the same environment variables
4. Railway auto-detects Python and uses `gunicorn app:app`

### Option 3 — Gunicorn (VPS/Docker)

```bash
FLASK_ENV=production gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

---

## 📁 Project Structure

```
flask_app/
├── app.py              # App factory
├── config.py           # Dev/Prod configuration
├── extensions.py       # Flask extension singletons
├── models.py           # User & Patient ORM models
├── forms.py            # WTForms form classes
├── requirements.txt
├── .env.example
├── routes/
│   ├── auth.py         # /register /login /logout
│   ├── main.py         # / /dashboard /account
│   └── patients.py     # CRUD + export + AI regenerate
├── services/
│   └── ai.py           # Lovable AI Gateway integration
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── dashboard.html
│   ├── account.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── patients/
│   │   ├── list.html
│   │   ├── add.html
│   │   ├── edit.html
│   │   ├── detail.html
│   │   └── _form_fields.html
│   └── partials/
│       ├── flash.html
│       └── empty_state.html
├── static/
│   ├── css/style.css
│   └── js/validation.js
└── instance/           # SQLite DB (gitignored)
```

---

## 🔒 Security Notes

- All patient queries are filtered by `user_id == current_user.id` — users can only see their own data
- CSRF protection on every form via Flask-WTF
- Passwords hashed with Werkzeug's `pbkdf2:sha256`
- In production, `SESSION_COOKIE_SECURE=True` enforces HTTPS-only cookies

---

## 🤖 AI Remarks

The AI uses the **Lovable AI Gateway** (OpenAI-compatible endpoint):

- **Endpoint**: `https://ai.gateway.lovable.dev/v1/chat/completions`
- **Model**: `google/gemini-2.5-flash-preview` (configurable via `AI_MODEL`)
- **Prompt**: Patient name, age, glucose, haemoglobin, cholesterol
- **Output**: 3–5 sentence clinical assessment + disclaimer

The disclaimer `⚠️ MEDICAL DISCLAIMER: This AI-generated assessment is for informational purposes only...` is always appended.

---

## 🧪 Flask Shell

```bash
flask shell
>>> User.query.all()
>>> Patient.query.filter_by(user_id=1).count()
```

---

## 📄 License

MIT — free to use, modify, and distribute.
