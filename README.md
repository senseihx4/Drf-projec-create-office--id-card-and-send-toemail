# Drf-projec-create-office-id-card-and-send-toemail

A Django REST Framework API that allows office employees to fill in their details, draw a signature, and receive a generated PDF ID card directly to their email.

---

## 🚀 Features

- Admin creates user accounts (SuperAdmin / User roles)
- Users submit their info: name, job title, blood group, bio, joined date, and a hand-drawn signature
- A PDF ID card is generated using **Pillow**
- The ID card PDF is automatically sent to the user's email
- Token-based authentication via DRF

---

## 📋 Requirements

- Python 3.10+
- pip
- Git

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/senseihx4/Drf-projec-create-office--id-card-and-send-toemail.git
cd Drf-projec-create-office--id-card-and-send-toemail
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory and add your email settings:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True
```

> **Note:** If using Gmail, generate an [App Password](https://myaccount.google.com/apppasswords) instead of your regular password.

### 5. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser (Admin)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/` | GET | API root |
| `/api/users/` | GET / POST | List users / Admin creates a user |
| `/api/login/` | POST | Login and get auth token |
| `/api/pdfreports/` | GET / POST | Submit employee info + signature |
| `/api/generate-pdf/` | GET | Generate PDF ID card and send to email |

---

## 👤 How It Works

1. **Admin** logs in and creates a user account via `/api/users/` (sets email, username, user type, and profile picture).
2. **User** logs in via `/api/login/` to get their auth token.
3. **User** submits their details (name, job title, blood group, bio, joined date, and hand-drawn signature) via `/api/pdfreports/`.
4. **User** calls `/api/generate-pdf/` — the server generates a PDF ID card using Pillow and sends it to the user's registered email.

---

## 🗂️ Project Structure

```
├── idcard/           # ID card generation logic (Pillow)
├── pdfdownloder/     # PDF generation & email sending
├── manage.py
├── package.json
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django, Django REST Framework |
| Database | SQLite |
| PDF / ID Card | Pillow |
| Email | SMTP (Gmail) |
| Auth | DRF Token Authentication |

---

## 📝 Notes

- Only **Admin** users can create new accounts — self-registration is not supported.
- The signature field is a drawable canvas in the DRF browsable API (HTML form).
- Make sure `MEDIA_ROOT` and `MEDIA_URL` are configured in `settings.py` for profile pictures to be served correctly.
