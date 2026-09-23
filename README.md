# TUTORON INDIA — Production Backend (Django 5 + Django REST Framework)

**TutorOn India** is an EdTech student-teacher marketplace and online coaching platform backend designed for India. It connects students with verified teachers while strictly protecting user privacy through admin-controlled contact unlocking.

---

## 🌟 Core Business Rules & Architectural Highlights

1. **NO Live Class Hosting**:
   - The platform does not host live video conferencing internally (No WebRTC/Zoom native SDK).
   - Supported class formats:
     - `RECORDED_VIDEO`: Validated video file uploads (size, extension, MIME).
     - `YOUTUBE`: External YouTube URL (domain and HTTPS whitelisted).
     - `ZOOM`: External Zoom meeting URL (domain and HTTPS whitelisted).
     - `GOOGLE_MEET`: External Google Meet URL (domain and HTTPS whitelisted).
2. **Contact Privacy By Design**:
   - Phone numbers and emails are strictly **HIDDEN** across all public teacher/student profiles, searches, batches, and messaging.
   - Contact details are unlocked ONLY via a formal connection workflow (`ConnectionRequest` + `ContactAccess`) approved by Admin and accessed via a dedicated secure endpoint: `GET /api/v1/connections/{id}/contact/`.
3. **Consolidated App Structure**:
   - All models consolidated in [study/models.py](file:///c:/Users/Dell%20Pc/Desktop/Learning/my_learning_project/study/models.py).
   - All serializers consolidated in [study/serializers.py](file:///c:/Users/Dell%20Pc/Desktop/Learning/my_learning_project/study/serializers.py).
   - All views and business logic consolidated in [study/views.py](file:///c:/Users/Dell%20Pc/Desktop/Learning/my_learning_project/study/views.py).
4. **Standardized API Response**:
   - Every response follows a unified JSON envelope:
     ```json
     {
       "success": true,
       "message": "...",
       "data": { ... }
     }
     ```

---

## 🔑 Demo Credentials (from `seed_demo_data`)

| Role | Email | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@tutoron.in` | `Admin@12345` | Full admin privileges |
| **Teacher** | `rajesh.sharma@tutoron.in` | `Teacher@12345` | Physics / Maths, **VERIFIED** |
| **Teacher** | `ananya.verma@tutoron.in` | `Teacher@12345` | Chemistry / Biology, **VERIFIED** |
| **Teacher** | `amit.patel@tutoron.in` | `Teacher@12345` | English, **PENDING_VERIFICATION** |
| **Student** | `aarav.kumar@student.in` | `Student@12345` | Enrolled in JEE Batch |
| **Student** | `priya.singh@student.in` | `Student@12345` | Enrolled in JEE Batch |
| **Student** | `rohit.sharma@student.in` | `Student@12345` | Enrolled in NEET Batch |

---

## 🚀 Getting Started

### 1. Migrations & Seeding
```bash
python manage.py makemigrations study
python manage.py migrate
python manage.py seed_demo_data
```

### 2. Running Automated Tests
```bash
python manage.py test study
```

### 3. Running the Server
```bash
python manage.py runserver
```

### 4. Interactive API Documentation
- **Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc**: [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI Schema**: [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 📚 API Endpoints Summary

### Authentication (`/api/v1/auth/`)
- `POST /api/v1/auth/register/student/` - Student registration
- `POST /api/v1/auth/register/teacher/` - Teacher registration (starts as `PENDING_VERIFICATION`)
- `POST /api/v1/auth/login/` - JWT Obtain (email + password)
- `POST /api/v1/auth/token/refresh/` - JWT Refresh token
- `POST /api/v1/auth/logout/` - Blacklist refresh token
- `POST /api/v1/auth/verify-email/` - Verify email token
- `POST /api/v1/auth/forgot-password/` & `POST /api/v1/auth/reset-password/`
- `GET /api/v1/auth/me/` & `PATCH /api/v1/auth/me/`

### Teachers (`/api/v1/teachers/`)
- `GET /api/v1/teachers/` - Public search & filter (only `VERIFIED` & `ACTIVE` teachers, contact hidden)
- `GET /api/v1/teachers/{id}/` - Teacher public details
- `GET /api/v1/teachers/{id}/batches/` - Teacher public batches
- `GET /api/v1/teachers/{id}/reviews/` - Teacher public reviews
- `GET|PATCH /api/v1/teacher/profile/` - Own teacher profile
- `POST /api/v1/teacher/verification/` - Submit verification document
- `GET /api/v1/teacher/dashboard/` - Teacher personal dashboard stats

### Batches (`/api/v1/batches/`)
- `GET /api/v1/batches/` - Public published batches
- `GET /api/v1/batches/{slug}/` - Batch detail by slug
- `POST /api/v1/batches/{id}/enroll/` - Student enrollment request
- `GET|POST /api/v1/batches/{id}/announcements/` - Batch announcements
- `GET|POST|PATCH|DELETE /api/v1/teacher/batches/` - Teacher batch management

### Classes & Attendance (`/api/v1/`)
- `GET /api/v1/batches/{batch_id}/classes/` - View batch classes (enrolled only)
- `POST /api/v1/teacher/batches/{batch_id}/classes/` - Create class (Zoom/Meet/YouTube/Recorded)
- `GET /api/v1/classes/{id}/` - View class content (enrolled only)
- `GET|POST /api/v1/classes/{id}/attendance/` - Manual attendance tracking

### Materials & Bookmarks (`/api/v1/`)
- `GET /api/v1/batches/{batch_id}/materials/` - Batch study materials
- `POST /api/v1/teacher/batches/{batch_id}/materials/` - Upload study material
- `GET /api/v1/materials/{id}/download/` - Download (enforces `is_downloadable`)
- `POST|DELETE /api/v1/materials/{id}/bookmark/` - Bookmark material

### Connections & Contact Privacy (`/api/v1/connections/`)
- `POST /api/v1/connections/` - Request connection
- `POST /api/v1/connections/{id}/approve/` - Student or Admin approval
- `POST /api/v1/connections/{id}/reject/` - Reject connection
- `GET /api/v1/connections/{id}/contact/` - **Dedicated secure contact unlock** (checks approval + block status)

### Messaging (`/api/v1/conversations/`)
- `GET|POST /api/v1/conversations/` - List/start conversations
- `GET /api/v1/conversations/{id}/` - Message history
- `POST /api/v1/conversations/{id}/messages/` - Send message (with attachment support & block protection)

### Reviews, Reports, Blocks & Notifications
- `POST /api/v1/batches/{batch_id}/reviews/` - Submit review (enrolled only)
- `POST /api/v1/reports/` - Submit report
- `POST|DELETE /api/v1/blocks/` - User block protection
- `GET /api/v1/notifications/` - In-app notifications
- `POST /api/v1/notifications/{id}/read/` - Mark notification read

### Admin Panel (`/api/v1/admin/`)
- `GET /api/v1/admin/dashboard/` - Platform statistics
- `GET /api/v1/admin/users/` - User directory
- `GET /api/v1/admin/teacher-verifications/` - Review queue
- `POST /api/v1/admin/teacher-verifications/{id}/approve/` - Verify teacher
- `POST /api/v1/admin/teacher-verifications/{id}/reject/` - Reject teacher
- `GET /api/v1/admin/connections/` - View all connection requests
- `POST /api/v1/admin/connections/{id}/approve/` - Admin approves connection and unlocks direct contact sharing
- `POST /api/v1/admin/connections/{id}/reject/` - Admin rejects connection request
- `POST /api/v1/admin/classes/send-reminders/` - Dispatch scheduled class reminder notifications
- `GET /api/v1/admin/batches/`, `/admin/enrollments/`, `/admin/reports/`, `/admin/audit-logs/`, `/admin/payments/`

---

## 🐳 Docker & Celery Architecture

### Running with Docker Compose
```bash
docker compose up --build
```
This boots up:
1. `web`: Django backend API on `http://localhost:8000`
2. `db`: PostgreSQL 16 database
3. `redis`: Redis cache & message broker
4. `celery`: Background asynchronous worker (email delivery, notifications)
5. `celery-beat`: Scheduler for recurring jobs (e.g., class reminders dispatched every 15 mins)

### Running Celery Locally (Manual)
```bash
# Terminal 1: Celery Worker
celery -A my_learning_project worker --loglevel=info

# Terminal 2: Celery Beat (Periodic reminders)
celery -A my_learning_project beat --loglevel=info
```

