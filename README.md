# TUTORON INDIA - EdTech Backend REST API

Production-ready Django & Django REST Framework (DRF) backend for **TutorOn India** - a student-teacher marketplace and online coaching management platform designed for India.

---

## 🌟 Product Highlights & Business Rules

1. **Student Registration**: Supports 12 exact fields from UI design (including `student_class`, `board_or_university`, `subjects_needed`, `target_exams`, `budget_range`, `mode_preference`, etc.).
2. **Teacher Registration**: Supports 23 exact fields from UI design (including `qualifications`, `experience_years`, `teaching_subjects`, `classes_taught`, `boards_catered`, `hourly_rate`, `monthly_fee`, `mode_offered`, document uploads, etc.).
3. **Contact Privacy Control**: Phone numbers and email addresses of teachers and students are **hidden by default** in API responses (`"Contact Hidden (Request Connection)"`). They are unlocked only when a connection request is accepted and `ContactAccess` is granted by admin/system.
4. **Class Content & Recording Management**:
   - Supports Recorded Video links/files
   - Supports YouTube video links
   - Supports Zoom live class links
   - Supports Google Meet links
5. **OpenAPI & Swagger UI**: Integrated `drf-spectacular` for interactive API testing and documentation.

---

## 🛠️ Architecture & Tech Stack

- **Framework**: Django 5.x + Django REST Framework (DRF)
- **Authentication**: SimpleJWT (Access + Refresh tokens with Blacklisting)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Documentation**: Swagger UI (`/api/docs/`), ReDoc (`/api/redoc/`), Schema (`/api/schema/`)
- **Background Tasks**: Celery + Redis
- **Security & Logging**: Role-based permissions, custom exception handlers, audit logging

---

## 🚀 Quick Start Guide

### 1. Requirements & Virtual Environment Setup

```bash
cd Edu
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply Migrations & Seed Demo Data

```bash
python manage.py makemigrations app
python manage.py migrate
python manage.py seed_demo_data
```

### 4. Run Development Server

```bash
python manage.py runserver
```

Server will start on `http://127.0.0.1:8000/`.

---

## 🔑 Demo Login Credentials

- **Admin Account**:
  - Email: `admin@tutoron.in`
  - Password: `AdminPass123!`

- **Teacher Account**:
  - Email: `rahul.teacher@tutoron.in`
  - Password: `Teacher123!`

- **Student Account**:
  - Email: `rohan.student@tutoron.in`
  - Password: `Student123!`

---

## 📡 API Endpoints Summary

Base URL: `http://127.0.0.1:8000/api/v1/`

### 🔒 Authentication
- `POST /api/v1/auth/register/student/` - Register student (12 UI fields supported)
- `POST /api/v1/auth/register/teacher/` - Register teacher (23 UI fields supported)
- `POST /api/v1/auth/login/` - Login & obtain JWT tokens
- `POST /api/v1/auth/logout/` - Logout & blacklist refresh token
- `POST /api/v1/auth/token/refresh/` - Refresh JWT access token
- `POST /api/v1/auth/change-password/` - Change password
- `GET/PUT /api/v1/auth/profile/` - View/update logged-in user profile

### 👨‍🏫 Teacher Marketplace & Search
- `GET /api/v1/teachers/` - Search/filter teachers (by subject, city, mode, rate, rating)
- `GET /api/v1/teachers/{id}/` - Detailed profile (contact details hidden unless unlocked)
- `POST /api/v1/teacher/verification/submit/` - Submit verification documents
- `POST /api/v1/admin/verification/{id}/review/` - Admin approve/reject verification

### 📚 Batches & Class Content
- `GET/POST /api/v1/batches/` - List/create batches
- `GET/PUT/DELETE /api/v1/batches/{id}/` - View/update/delete batch
- `GET/POST /api/v1/batches/{id}/announcements/` - Batch announcements
- `GET/POST /api/v1/batches/{id}/classes/` - Add class (Recorded Video, YouTube, Zoom, Google Meet)
- `GET/POST /api/v1/classes/{id}/attendance/` - Record student attendance
- `GET/POST /api/v1/batches/{id}/materials/` - Study material uploads

### 🤝 Connections & Contact Access Unlock
- `GET/POST /api/v1/connections/` - Send/list connection requests
- `POST /api/v1/connections/{id}/respond/` - Accept/reject connection request
- `POST /api/v1/contact-access/request/` - Request contact detail unlock
- `POST /api/v1/admin/contact-access/{id}/unlock/` - Admin grant/reject contact access

### 💬 Messaging & Dashboards
- `GET /api/v1/conversations/` - List active chat conversations
- `GET/POST /api/v1/conversations/{id}/messages/` - View/send messages
- `GET /api/v1/dashboard/student/` - Student dashboard stats
- `GET /api/v1/dashboard/teacher/` - Teacher dashboard stats

---

## 🧪 Running Automated Tests

```bash
python manage.py test app
```
