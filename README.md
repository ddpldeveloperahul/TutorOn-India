# TUTORON INDIA — Complete Backend & API Documentation

**TutorOn India** is an enterprise-grade EdTech student-teacher marketplace and online coaching platform backend designed for India. It connects students with verified teachers while strictly protecting user privacy through admin-controlled contact unlocking.

---

# 📑 TABLE OF CONTENTS
1. [SECTION 1: Admin Control Panel & Web Dashboard APIs](#-section-1-admin-control-panel--web-dashboard-apis)
2. [SECTION 2: Mobile Application APIs (Student & Teacher Apps)](#-section-2-mobile-application-apis-student--teacher-apps)
3. [SECTION 3: Architecture, Credentials, Setup & Deployment Guide](#-section-3-architecture-credentials-setup--deployment-guide)

---

# 🛡️ SECTION 1: Admin Control Panel & Web Dashboard APIs

All endpoints in this section require an authenticated user with `role="ADMIN"` or `is_staff=True` passed in the `Authorization: Bearer <Admin_JWT>` header.

---

### 1.1 Admin Dashboard & Global Analytics

#### 🔹 1. Dashboard Comprehensive KPI Stats
- **URL**: `GET /api/v1/admin/dashboard/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Admin metrics loaded.",
    "data": {
      "operator": {
        "id": "e2a1b3c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
        "name": "Super Admin",
        "email": "admin@tutoron.in",
        "role": "SUPER_ADMIN"
      },
      "kpi_metrics": {
        "total_students": { "value": 1420, "growth_percentage": 8.4, "label": "vs last month" },
        "total_teachers": { "value": 85, "growth_percentage": 5.2, "label": "vs last month" },
        "pending_verifications": { "value": 6, "badge": "Needs Review" },
        "pending_connections": { "value": 14, "badge": "Action Required" },
        "pending_enrollments": { "value": 28, "badge": "Unpaid / Requested" },
        "total_revenue": { "value": 485000.00, "currency": "INR", "monthly": 125000.00 }
      },
      "secondary_metrics": {
        "active_students": 1280,
        "student_engagement_rate": "90.1%",
        "verified_teachers": 72,
        "teacher_verification_rate": "84.7%",
        "active_batches": 34,
        "unlocked_connections": 115
      }
    }
  }
  ```

#### 🔹 2. Dashboard Live Activity Feed
- **URL**: `GET /api/v1/admin/dashboard/activity/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Recent activity feed retrieved.",
    "data": [
      {
        "id": "act-1",
        "event_type": "TEACHER_VERIFIED",
        "description": "Dr. Rajesh Sharma was verified by Super Admin",
        "timestamp": "2026-09-30T10:14:32Z",
        "severity": "SUCCESS"
      },
      {
        "id": "act-2",
        "event_type": "ENROLLMENT_CONFIRMED",
        "description": "Student Aarav Kumar enrolled in Target JEE Advanced 2027",
        "timestamp": "2026-09-30T09:45:10Z",
        "severity": "INFO"
      }
    ]
  }
  ```

#### 🔹 3. Dashboard Global Search
- **URL**: `GET /api/v1/admin/dashboard/search/?q=rajesh`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Search results for 'rajesh'",
    "data": {
      "teachers": [
        { "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d", "name": "Dr. Rajesh Sharma", "subject": "Physics", "status": "VERIFIED" }
      ],
      "students": [],
      "batches": [
        { "id": "3c2b1a0f-9e8d-7c6b-5a4f-3e2d1c0b9a8f", "title": "Target JEE Advanced 2027 (Physics)", "teacher": "Dr. Rajesh Sharma" }
      ]
    }
  }
  ```

---

### 1.2 User & Profile Management

#### 🔹 4. Admin Users Directory
- **URL**: `GET /api/v1/admin/users/?role=TEACHER&is_active=true&search=rajesh`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "User directory fetched.",
    "data": {
      "count": 1,
      "results": [
        {
          "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
          "email": "rajesh.sharma@tutoron.in",
          "first_name": "Dr. Rajesh",
          "last_name": "Sharma",
          "phone": "+919876543210",
          "role": "TEACHER",
          "is_active": true,
          "is_verified": true,
          "date_joined": "2026-09-20T12:00:00Z"
        }
      ]
    }
  }
  ```

#### 🔹 5. Admin Teachers Directory & CRUD
- **URL**: `GET /api/v1/admin/teachers/?verification_status=VERIFIED&page=1`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Data fetched successfully",
    "total_count": 85,
    "verified_count": 72,
    "pending_count": 6,
    "data": [
      {
        "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
        "user_id": "7f8e9d0c-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "display_name": "Dr. Rajesh Sharma",
        "email": "rajesh.sharma@tutoron.in",
        "phone": "+919876543210",
        "headline": "IIT Delhi Physics Alum | 12+ Yrs Coaching",
        "subjects": ["Physics"],
        "verification_status": "VERIFIED",
        "hourly_rate": "1500.00",
        "rating": "4.90"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 85, "total_pages": 5 }
  }
  ```
- **Create Teacher**: `POST /api/v1/admin/teachers/`
- **Update Teacher**: `PATCH /api/v1/admin/teachers/{id}/`
- **Delete Teacher**: `DELETE /api/v1/admin/teachers/{id}/`

#### 🔹 6. Admin Students Directory & CRUD
- **URL**: `GET /api/v1/admin/students/?page=1&status=ACTIVE&board=CBSE&search=aarav`
- **Alternative URL**: `GET /api/v1/students/?page=1&status=ACTIVE&board=CBSE&search=aarav`
- **Method**: `GET`
- **Query Parameters**:
  - `page`: Page number (e.g. `1`)
  - `status`: Filter by status (`ACTIVE`, `PENDING`, `INACTIVE`)
  - `board`: Filter by board (`CBSE`, `ICSE`, `State Board`)
  - `search`: Search student by name, student code, email, phone, city, education level
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Students list retrieved successfully",
    "counts": {
      "total_students": 8452,
      "active_learners": 7890,
      "inactive_accounts": 220,
      "total_learners_badge": "8,452 Total Learners"
    },
    "total_count": 8452,
    "data": [
      {
        "id": "c1f3a2b4-7e89-4d12-9c34-89abcdef0123",
        "student_code": "STU-10021",
        "avatar_initial": "AS",
        "first_name": "Aarav",
        "last_name": "Sharma",
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma2026@gmail.com",
        "phone_number": "+91 98765 43210",
        "profile_photo": null,
        "joined": "14 Jul 2026",
        "date_joined": "2026-07-14T10:30:00+05:30",
        "enrollments": "3 Batches",
        "enrollments_count": 3,
        "status": "Active",
        "board": "CBSE",
        "grade_display": "Class XII (PCM) · CBSE",
        "date_of_birth": null,
        "gender": "MALE",
        "education_level": "Class XII (PCM)",
        "school_name": "Delhi Public School",
        "city": "New Delhi",
        "state": "Delhi",
        "preferred_language": "English / Hindi",
        "subjects_of_interest": ["Physics", "Chemistry", "Mathematics"],
        "bio": "Aspiring IIT JEE Aspirant"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 8452,
      "total_pages": 846
    }
  }
  ```
- **Create Student**: `POST /api/v1/admin/students/`
- **Update Student**: `PATCH /api/v1/admin/students/{id}/`
- **Delete Student**: `DELETE /api/v1/admin/students/{id}/`

---

### 1.3 Teacher Verification Workflow

#### 🔹 7. View Verification Requests Queue
- **URL**: `GET /api/v1/admin/teacher-verifications/?status=PENDING`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Teacher verifications retrieved.",
    "data": [
      {
        "id": "v-1001",
        "teacher": {
          "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
          "name": "Dr. Rajesh Sharma",
          "email": "rajesh.sharma@tutoron.in"
        },
        "document_type": "DEGREE",
        "document_file": "/media/verifications/phd_iit_delhi.pdf",
        "notes": "Ph.D Degree from IIT Delhi & Aadhaar Card",
        "status": "PENDING",
        "submitted_at": "2026-09-23T09:30:00Z"
      }
    ]
  }
  ```

#### 🔹 8. Approve Teacher Verification
- **URL**: `POST /api/v1/admin/teacher-verifications/{id}/approve/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Request Payload**:
  ```json
  {
    "admin_notes": "Verified Ph.D credentials from IIT Delhi, Aadhaar identity authenticated."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Teacher verification approved. Teacher is now verified and can publish batches.",
    "data": {
      "teacher_id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
      "verification_status": "VERIFIED",
      "approved_at": "2026-09-30T10:14:32Z"
    }
  }
  ```

#### 🔹 9. Reject Teacher Verification
- **URL**: `POST /api/v1/admin/teacher-verifications/{id}/reject/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Request Payload**:
  ```json
  {
    "rejection_reason": "Degree certificate blurred and unreadable. Please re-upload high resolution scan.",
    "admin_note": "Aadhaar verified, but IIT degree certificate illegible."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Teacher verification rejected.",
    "data": {
      "teacher_id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
      "verification_status": "REJECTED",
      "rejection_reason": "Degree certificate blurred and unreadable. Please re-upload high resolution scan."
    }
  }
  ```

---

### 1.4 Connections & Privacy Contact Sharing

#### 🔹 10. View Connection Requests Queue
- **URL**: `GET /api/v1/admin/connections/?status=PENDING`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Connection requests retrieved.",
    "data": [
      {
        "id": "c-901",
        "student": { "id": "c1f3a2b4-7e89-4d12-9c34-89abcdef0123", "name": "Aarav Kumar" },
        "teacher": { "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d", "name": "Dr. Rajesh Sharma" },
        "message": "Looking for 1-on-1 guidance in Mechanics.",
        "student_approved": true,
        "admin_approved": false,
        "status": "PENDING"
      }
    ]
  }
  ```

#### 🔹 11. Admin Approve Connection & Unlock Direct Contact
- **URL**: `POST /api/v1/admin/connections/{id}/approve/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Request Payload**:
  ```json
  {
    "admin_note": "Approved genuine 1-on-1 coaching inquiry. Contact shared."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Connection approved by Admin. Contact details are now accessible to both parties.",
    "data": {
      "connection_id": "c-901",
      "status": "APPROVED",
      "contact_unlocked": true
    }
  }
  ```

#### 🔹 12. Admin Reject Connection
- **URL**: `POST /api/v1/admin/connections/{id}/reject/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Request Payload**:
  ```json
  {
    "rejection_reason": "Commercial solicitation not permitted."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Connection request rejected.",
    "data": {
      "connection_id": "c-901",
      "status": "REJECTED"
    }
  }
  ```

---

### 1.5 Batches, Enrollments & Operations

#### 🔹 13. Admin Batches Directory
- **URL**: `GET /api/v1/admin/batches/?status=PUBLISHED`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Batches fetched successfully",
    "batch_count": 34,
    "status_counts": {
      "total": 42,
      "published": 34,
      "ongoing": 5,
      "completed": 2,
      "draft": 1
    },
    "data": [
      {
        "id": "3c2b1a0f-9e8d-7c6b-5a4f-3e2d1c0b9a8f",
        "title": "Target JEE Advanced 2027: Master Class in Physics",
        "teacher": "Dr. Rajesh Sharma",
        "subject": "Physics",
        "price": "14999.00",
        "enrolled_count": 28,
        "max_students": 30,
        "status": "PUBLISHED"
      }
    ]
  }
  ```

#### 🔹 14. Admin Enrollments Directory
- **URL**: `GET /api/v1/admin/enrollments/?status=PAYMENT_PENDING`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Enrollments retrieved successfully",
    "data": [
      {
        "id": "enr-7701",
        "student": { "name": "Nakul Kumar", "email": "nakul@example.com" },
        "batch": { "title": "Target JEE Advanced 2027", "price": "14999.00" },
        "status": "REQUESTED",
        "payment_status": "UNPAID",
        "requested_at": "2026-09-29T10:00:00Z"
      }
    ]
  }
  ```

#### 🔹 15. Admin Announcements & Promotional Updates
- **URL**: `GET /api/v1/admin/announcements/`
- **Create**: `POST /api/v1/admin/announcements/`
- **Request Payload**:
  ```json
  {
    "title": "Diwali Scholarship Test 2026",
    "content": "Participate in the nationwide scholarship test on October 20th. Up to 100% fee waivers for Top 100 students.",
    "target_audience": "ALL",
    "is_pinned": true
  }
  ```
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Announcement created successfully.",
    "data": {
      "id": "ann-101",
      "title": "Diwali Scholarship Test 2026",
      "target_audience": "ALL",
      "is_pinned": true,
      "created_at": "2026-09-30T11:00:00Z"
    }
  }
  ```

#### 🔹 16. Admin Promotional Banners
- **URL**: `GET /api/v1/admin/banners/`
- **Create**: `POST /api/v1/admin/banners/` (`multipart/form-data`)
  - `title`: `"IIT JEE Crash Course Banner"`
  - `image`: `[Image File - 1920x600 JPG/PNG]`
  - `target_url`: `"/batches/3c2b1a0f-9e8d-7c6b-5a4f-3e2d1c0b9a8f"`
  - `is_active`: `true`

---

### 1.6 Content Moderation, Reviews & Incident Reports

#### 🔹 17. Admin Study Materials Moderation
- **URL**: `GET /api/v1/admin/materials/?status=REPORTED`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Study materials retrieved successfully",
    "counts": { "all": 140, "published": 136, "reported": 2, "drafts": 2 },
    "data": [
      {
        "id": "mat-501",
        "title": "Copyrighted Test Series PDF",
        "batch_title": "NEET 2026 Organic Chemistry",
        "teacher": "Dr. Ananya Verma",
        "status": "REPORTED"
      }
    ]
  }
  ```
- **Takedown Material**: `PATCH /api/v1/admin/materials/{id}/` with `{"status": "HIDDEN"}`

#### 🔹 18. Admin Reviews Moderation
- **URL**: `GET /api/v1/admin/reviews/?status=FLAGGED`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Reviews retrieved successfully",
    "counts": { "all": 320, "published": 315, "flagged": 3, "removed": 2 },
    "data": [
      {
        "id": "rev-301",
        "student_name": "Anonymous Student",
        "teacher_name": "Dr. Rajesh Sharma",
        "rating": 1,
        "comment": "Abusive spam review containing offensive language.",
        "status": "FLAGGED",
        "created_at": "2026-09-29T14:20:00Z"
      }
    ]
  }
  ```
- **Remove Review**: `DELETE /api/v1/admin/reviews/{id}/` or `PATCH` with `{"status": "REMOVED"}`

#### 🔹 19. Admin Incident Reports & Resolution
- **URL**: `GET /api/v1/admin/reports/?status=OPEN`
- **Resolve Report**: `POST /api/v1/admin/reports/{id}/resolve/`
- **Request Payload**:
  ```json
  {
    "resolution_action": "CONTENT_REMOVED",
    "admin_notes": "Offensive review deleted and warning issued to student."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Report resolved successfully.",
    "data": {
      "report_id": "rep-401",
      "status": "RESOLVED",
      "resolved_by": "Super Admin",
      "resolution_action": "CONTENT_REMOVED"
    }
  }
  ```

---

### 1.7 Financial Transactions & Auditing

#### 🔹 20. Admin Financial Transactions / Payments
- **URL**: `GET /api/v1/admin/payments/?status=SUCCESS`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Payments list retrieved",
    "data": [
      {
        "id": "pay-8801",
        "transaction_id": "TXN_TUTORON_992144810",
        "student": "Aarav Kumar (aarav@student.in)",
        "batch": "Target JEE Advanced 2027",
        "amount": "14999.00",
        "currency": "INR",
        "status": "SUCCESS",
        "payment_method": "UPI",
        "paid_at": "2026-09-23T12:00:00Z"
      }
    ]
  }
  ```

#### 🔹 21. Admin Audit Logs List (Category Filtered)
- **URL**: `GET /api/v1/admin/audit-logs/?category=Verification&search=AUD-10081`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Audit logs retrieved.",
    "data": {
      "count": 1,
      "results": [
        {
          "id": "e7c2a1b0-8f9d-4e3c-2b1a-0f9e8d7c6b5a",
          "audit_code": "AUD-10081",
          "category": "Verification",
          "action": "Teacher Verification Approved",
          "operator": "Super Admin (sudhanshu@tutoron.in)",
          "target_entity": "Faculty Profile: Dr. Rajesh Sharma (TCH-10248)",
          "timestamp": "2026-09-23 10:14:32 IST"
        }
      ]
    }
  }
  ```

#### 🔹 22. Admin Audit Inspection Details (Before vs After State Transition)
- **URL**: `GET /api/v1/admin/audit-logs/AUD-10081/` (or by UUID)
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Audit log detail retrieved.",
    "data": {
      "audit_code": "AUD-10081",
      "category": "Verification",
      "action": "Teacher Verification Approved",
      "operator": "Super Admin (sudhanshu@tutoron.in)",
      "target_user_id": "TCH-10248",
      "related_entity": "Faculty Profile: Dr. Rajesh Sharma",
      "originating_ip": "103.21.144.18 (New Delhi, India)",
      "timestamp": "2026-09-23 10:14:32 IST",
      "justification": "Verified Ph.D credentials from IIT Delhi, Aadhaar identity authenticated, and 12-year coaching track record confirmed.",
      "state_transition": {
        "previous_state": {
          "verificationStatus": "Pending Verification",
          "badge": "Unverified",
          "allowedToPublishBatches": false
        },
        "new_state": {
          "verificationStatus": "Verified",
          "badge": "Verified Educator",
          "allowedToPublishBatches": true
        }
      },
      "integrity_signature": "SHA256:7f83b1657ff1fc53b92dc18148a1d6650fc2e4b1fa3c677284adcd208126d9069"
    }
  }
  ```

#### 🔹 23. Trigger Scheduled Class Reminders (Celery Dispatch)
- **URL**: `POST /api/v1/admin/classes/send-reminders/`
- **Headers**: `Authorization: Bearer <Admin_JWT>`
- **Request Payload**:
  ```json
  {
    "window_minutes": 60
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Class reminders queued successfully via Celery.",
    "data": {
      "dispatched_at": "2026-09-30T14:30:00Z",
      "window_minutes": 60,
      "notifications_queued": 18
    }
  }
  ```

---

# 📱 SECTION 2: Mobile Application APIs (Student & Teacher Apps)

This section contains all client endpoints consumed by the Flutter/React Native/iOS/Android mobile apps for **Students** and **Teachers**.

---

### 2.1 Authentication & User Security (`/api/v1/auth/`)

#### 🔹 1. Student Registration
- **URL**: `POST /api/v1/auth/register/student/`
- **Request Payload**:
  ```json
  {
    "email": "student.aarav@example.com",
    "password": "Student@12345",
    "first_name": "Aarav",
    "last_name": "Kumar",
    "phone": "+919876543210",
    "grade_target": "Class 12 - IIT JEE 2027"
  }
  ```
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Student registered successfully.",
    "data": {
      "user_id": "c1f3a2b4-7e89-4d12-9c34-89abcdef0123",
      "email": "student.aarav@example.com",
      "role": "STUDENT",
      "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsIn...",
        "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
      }
    }
  }
  ```

#### 🔹 2. Teacher Registration (Pending Review)
- **URL**: `POST /api/v1/auth/register/teacher/`
- **Request Payload**:
  ```json
  {
    "email": "teacher.rajesh@tutoron.in",
    "password": "Teacher@12345",
    "first_name": "Dr. Rajesh",
    "last_name": "Sharma",
    "phone": "+919811122233",
    "headline": "IIT Delhi Physics Alum | 12+ Yrs Coaching",
    "bio": "Mentored 50+ Top 100 AIR rankers in IIT-JEE Advanced.",
    "subjects": ["Physics"],
    "qualifications": "Ph.D IIT Delhi, B.Tech IIT Roorkee",
    "experience_years": 12,
    "hourly_rate": 1500.00
  }
  ```
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Teacher registered successfully. Account is pending verification.",
    "data": {
      "user_id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
      "email": "teacher.rajesh@tutoron.in",
      "role": "TEACHER",
      "verification_status": "PENDING_VERIFICATION",
      "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsIn...",
        "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
      }
    }
  }
  ```

#### 🔹 3. Unified User Login (JWT)
- **URL**: `POST /api/v1/auth/login/`
- **Request Payload**:
  ```json
  {
    "email": "student.aarav@example.com",
    "password": "Student@12345"
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Login successful.",
    "data": {
      "access": "eyJhbGciOiJIUzI1NiIsIn...",
      "refresh": "eyJhbGciOiJIUzI1NiIsIn...",
      "user": {
        "id": "c1f3a2b4-7e89-4d12-9c34-89abcdef0123",
        "email": "student.aarav@example.com",
        "first_name": "Aarav",
        "last_name": "Kumar",
        "role": "STUDENT",
        "is_verified": true
      }
    }
  }
  ```

#### 🔹 4. Refresh Access Token
- **URL**: `POST /api/v1/auth/token/refresh/`
- **Request Payload**:
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```

#### 🔹 5. User Logout (Blacklist Refresh Token)
- **URL**: `POST /api/v1/auth/logout/`
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Payload**:
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Successfully logged out."
  }
  ```

#### 🔹 6. Forgot Password & Reset Password
- **Forgot Password**: `POST /api/v1/auth/forgot-password/`
  ```json
  {
    "email": "student.aarav@example.com"
  }
  ```
- **Reset Password**: `POST /api/v1/auth/reset-password/`
  ```json
  {
    "token": "reset-uuid-token-from-email",
    "new_password": "NewSecurePassword@123"
  }
  ```

#### 🔹 7. Get / Update Current User Profile (`/auth/me/`)
- **URL**: `GET /api/v1/auth/me/` & `PATCH /api/v1/auth/me/`
- **Headers**: `Authorization: Bearer <JWT>`
- **Patch Request Payload**:
  ```json
  {
    "first_name": "Aarav",
    "last_name": "Sharma"
  }
  ```

#### 🔹 8. Block / Unblock User
- **Block**: `POST /api/v1/blocks/`
  ```json
  {
    "blocked_user_id": "user-uuid-to-block",
    "reason": "Harassment in chat"
  }
  ```
- **Unblock**: `DELETE /api/v1/blocks/{blocked_user_id}/`

---

### 2.2 Student Mobile Module (`/api/v1/student/`)

#### 🔹 9. Student Mobile Home Dashboard (Main Screen)
- **URL**: `GET /api/v1/student/dashboard/`
- **Headers**: `Authorization: Bearer <Student_JWT>`
- **Request Payload**: None *(GET request)*
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Student dashboard retrieved",
    "data": {
      "greeting": {
        "title": "Hello, Student 👋",
        "subtitle": "Ready to learn today?",
        "avatar_initial": "S"
      },
      "live_class": {
        "id": "c-7701",
        "title": "Chemistry — Organic Reactions",
        "teacher_name": "Ms. Sunita Patel",
        "class_type": "YOUTUBE",
        "platform": "YouTube",
        "meeting_url": "https://www.youtube.com/watch?v=live_stream_id",
        "external_url": "https://www.youtube.com/watch?v=live_stream_id",
        "duration": "1h",
        "is_live": true,
        "status_badge": "LIVE NOW"
      },
      "quick_stats": {
        "batches": 3,
        "classes": 3,
        "materials": 3,
        "alerts": 3
      },
      "upcoming_classes": [
        {
          "id": "cls-101",
          "batch_id": "b-1",
          "batch_title": "Class 12 Advanced Mathematics",
          "title": "Mathematics — Calculus Basics",
          "teacher_name": "Dr. Priya Sharma",
          "class_type": "GOOGLE_MEET",
          "platform": "Google Meet",
          "meeting_url": "https://meet.google.com/abc-defg-hij",
          "scheduled_date": "2026-09-30T10:30:00Z",
          "formatted_time": "Today, 4:00 PM",
          "duration_minutes": 60
        },
        {
          "id": "cls-102",
          "batch_id": "b-2",
          "batch_title": "Target JEE Advanced Physics",
          "title": "Physics — Electrostatics",
          "teacher_name": "Prof. Arjun Mehta",
          "class_type": "ZOOM",
          "platform": "Zoom",
          "meeting_url": "https://zoom.us/j/98765432101",
          "scheduled_date": "2026-09-30T13:00:00Z",
          "formatted_time": "Today, 6:30 PM",
          "duration_minutes": 90
        }
      ],
      "enrolled_batches_count": 3,
      "my_batches": [
        {
          "id": "b-1",
          "title": "JEE Advanced Maths 2025",
          "subject": "Mathematics",
          "subject_initial": "M",
          "teacher_name": "Dr. Priya Sharma",
          "status": "ACTIVE",
          "students_count": 42
        },
        {
          "id": "b-2",
          "title": "NEET Physics Crash Course",
          "subject": "Physics",
          "subject_initial": "P",
          "teacher_name": "Prof. Arjun Mehta",
          "status": "ACTIVE",
          "students_count": 36
        },
        {
          "id": "b-3",
          "title": "Organic Chemistry Mastery",
          "subject": "Chemistry",
          "subject_initial": "C",
          "teacher_name": "Ms. Sunita Patel",
          "status": "ACTIVE",
          "students_count": 28
        }
      ],
      "top_teachers": [
        {
          "id": "tch-1",
          "name": "Ms. Sunita Patel",
          "subject": "Chemistry",
          "rating": 4.8,
          "is_verified": true,
          "avatar_url": "/media/profiles/sunita.jpg"
        },
        {
          "id": "tch-2",
          "name": "Mr. Rajesh Kumar",
          "subject": "Biology",
          "rating": 4.6,
          "is_verified": true,
          "avatar_url": "/media/profiles/rajesh.jpg"
        }
      ],
      "unread_notifications_count": 3,
      "attendance_summary": {
        "total_marked": 10,
        "present": 9,
        "percentage": 90.0
      }
    }
  }
  ```

#### 🔹 10. Student My Enrollments
- **URL**: `GET /api/v1/student/enrollments/`
- **Detail**: `GET /api/v1/student/enrollments/{id}/`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "enr-101",
        "batch": {
          "id": "batch-1",
          "title": "Target JEE Advanced 2027",
          "subject": "Physics",
          "teacher_name": "Dr. Rajesh Sharma"
        },
        "status": "ACTIVE",
        "payment_status": "PAID",
        "enrolled_at": "2026-09-25T10:00:00Z"
      }
    ]
  }
  ```

#### 🔹 11. Student Bookmarked Study Materials
- **URL**: `GET /api/v1/student/bookmarks/`
- **Headers**: `Authorization: Bearer <Student_JWT>`

#### 🔹 12. Student Fee Payment History
- **URL**: `GET /api/v1/student/payments/`
- **Headers**: `Authorization: Bearer <Student_JWT>`

---

### 2.3 Teacher Mobile Module (`/api/v1/teacher/`)

#### 🔹 13. Teacher Mobile Dashboard Stats
- **URL**: `GET /api/v1/teacher/dashboard/`
- **Headers**: `Authorization: Bearer <Teacher_JWT>`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Teacher dashboard loaded.",
    "data": {
      "verification_status": "VERIFIED",
      "total_batches": 3,
      "total_students_enrolled": 48,
      "pending_enrollment_requests": 2,
      "upcoming_classes_today": 1,
      "monthly_earnings": 45000.00
    }
  }
  ```

#### 🔹 14. Submit Teacher Verification Documents
- **URL**: `POST /api/v1/teacher/verification/`
- **Headers**: `Authorization: Bearer <Teacher_JWT>`
- **Content-Type**: `multipart/form-data`
- **Form Data**:
  - `document_type`: `"AADHAAR"` *(options: `AADHAAR`, `PAN`, `DEGREE`, `EXPERIENCE_CERTIFICATE`)*
  - `document_file`: `[File Attachment - PDF / JPG]`
  - `notes`: `"Submitting IIT Delhi Ph.D degree and Aadhaar card."`
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Verification documents uploaded successfully.",
    "data": {
      "id": "v-101",
      "status": "PENDING",
      "document_type": "AADHAAR"
    }
  }
  ```

#### 🔹 15. Teacher Batch Management (CRUD)
- **List Batches**: `GET /api/v1/teacher/batches/`
- **Create Batch**: `POST /api/v1/teacher/batches/`
  ```json
  {
    "title": "Target JEE Advanced 2027: Master Class in Physics",
    "subject": "Physics",
    "target_exam": "IIT JEE Advanced",
    "start_date": "2026-10-01",
    "end_date": "2027-04-30",
    "max_students": 30,
    "price": "14999.00",
    "is_published": true,
    "schedule_description": "Mon, Wed, Fri: 6:00 PM - 7:30 PM IST"
  }
  ```
- **Update Batch**: `PATCH /api/v1/teacher/batches/{id}/`
- **Delete Batch**: `DELETE /api/v1/teacher/batches/{id}/`

#### 🔹 16. Teacher Manage Enrollment Requests
- **List Requests**: `GET /api/v1/teacher/enrollments/`
- **Approve**: `POST /api/v1/teacher/enrollments/{id}/approve/`
- **Reject**: `POST /api/v1/teacher/enrollments/{id}/reject/`

---

### 2.4 Marketplace, Discovery & Batches

#### 🔹 17. Find a Teacher (Mobile Search & Subject Filters)
- **URL**: `GET /api/v1/teachers/`
- **Query Parameters**:
  - `subject`: `Maths` | `Physics` | `Chemistry` | `Biology` (Subject filter chips)
  - `search`: e.g. `Priya`, `Sharma` (Search by teacher name, subject, qualification)
- **Headers**: *(Public, No token required)*
- **Request Payload**: None *(GET request)*
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "message": "Data fetched successfully",
    "total_count": 4,
    "data": [
      {
        "id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
        "name": "Dr. Priya Sharma",
        "avatar_initial": "S",
        "is_verified": true,
        "qualification": "PhD — IIT Delhi",
        "subjects": ["Mathematics"],
        "teaching_languages": ["Hindi", "English"],
        "total_students": 1200,
        "average_rating": "4.90",
        "hourly_rate": "1500.00",
        "profile_photo": null
      },
      {
        "id": "9b8c7d6e-5f4a-3210-fedc-ba9876543210",
        "name": "Prof. Arjun Mehta",
        "avatar_initial": "M",
        "is_verified": true,
        "qualification": "M.Sc — BITS Pilani",
        "subjects": ["Physics"],
        "teaching_languages": ["Hindi", "English"],
        "total_students": 890,
        "average_rating": "4.70",
        "hourly_rate": "1200.00",
        "profile_photo": null
      },
      {
        "id": "1c2d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
        "name": "Ms. Sunita Patel",
        "avatar_initial": "P",
        "is_verified": true,
        "qualification": "M.Sc — DU",
        "subjects": ["Chemistry"],
        "teaching_languages": ["Hindi", "Gujarati"],
        "total_students": 640,
        "average_rating": "4.80",
        "hourly_rate": "1000.00",
        "profile_photo": null
      },
      {
        "id": "3d4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a",
        "name": "Mr. Rajesh Kumar",
        "avatar_initial": "K",
        "is_verified": true,
        "qualification": "MBBS — AIIMS",
        "subjects": ["Biology"],
        "teaching_languages": ["Hindi", "English"],
        "total_students": 520,
        "average_rating": "4.60",
        "hourly_rate": "1100.00",
        "profile_photo": null
      }
    ]
  }
  ```

#### 🔹 17.1 "Connect" Action (Send Connection Request from Teacher Card)
- **URL**: `POST /api/v1/connections/`
- **Headers**:
  ```http
  Authorization: Bearer <Student_JWT>
  Content-Type: application/json
  ```
- **Request Payload**:
  ```json
  {
    "teacher_id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
    "message": "Hello, I want to connect for 1-on-1 coaching."
  }
  ```
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Connection request submitted. Contact sharing remains hidden until approved.",
    "data": {
      "id": "d232e600-f533-4c70-b630-e1eafcd0c609",
      "status": "STUDENT_APPROVED",
      "student_approved": true,
      "admin_approved": false,
      "contact_unlocked": false,
      "created_at": "2026-10-01T15:11:38Z"
    }
  }
  ```
  *(Note: Phone numbers and emails are strictly hidden).*

#### 🔹 18. Teacher Public Profile & Batches
- **Profile Detail**: `GET /api/v1/teachers/{id}/`
- **Teacher Batches**: `GET /api/v1/teachers/{id}/batches/`
- **Teacher Reviews**: `GET /api/v1/teachers/{id}/reviews/`

#### 🔹 19. Public Batches Directory
- **List Batches**: `GET /api/v1/batches/?subject=Physics`
- **Batch Detail**: `GET /api/v1/batches/{id}/`
- **Request Enrollment**: `POST /api/v1/batches/{id}/enroll/`
  ```json
  {
    "notes": "Enrolling for JEE Advanced physics."
  }
  ```
- **Batch Announcements**: `GET|POST /api/v1/batches/{id}/announcements/`

#### 🔹 20. Public Promotional Banners (App Carousel)
- **URL**: `GET /api/v1/banners/`
- **Response Payload (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "b-1",
        "title": "IIT JEE 2027 Admissions Open",
        "image_url": "/media/banners/jee2027.jpg",
        "target_url": "/batches/3c2b1a0f-9e8d-7c6b-5a4f-3e2d1c0b9a8f"
      }
    ]
  }
  ```

---

### 2.5 Classes, Attendance & Study Materials

#### 🔹 21. Create Class (Zoom / Google Meet / YouTube / Recorded Video)
- **URL**: `POST /api/v1/teacher/batches/{batch_id}/classes/`
- **Headers**: `Authorization: Bearer <Teacher_JWT>`
- **Request Payload**:
  ```json
  {
    "title": "Session 01: Rotational Mechanics Fundamentals",
    "description": "Moment of Inertia and Parallel Axis Theorem.",
    "content_type": "GOOGLE_MEET",
    "meeting_url": "https://meet.google.com/abc-defg-hij",
    "scheduled_at": "2026-10-05T18:00:00+05:30",
    "duration_minutes": 90
  }
  ```
- **Response Payload (`201 Created`)**:
  ```json
  {
    "success": true,
    "message": "Class scheduled successfully.",
    "data": {
      "id": "cls-101",
      "title": "Session 01: Rotational Mechanics Fundamentals",
      "content_type": "GOOGLE_MEET",
      "meeting_url": "https://meet.google.com/abc-defg-hij"
    }
  }
  ```

#### 🔹 22. View Batch Classes & Single Class
- **Batch Classes**: `GET /api/v1/batches/{batch_id}/classes/` *(Enrolled students & teacher only)*
- **Class Detail**: `GET /api/v1/classes/{id}/`

#### 🔹 23. Class Attendance
- **View Attendance**: `GET /api/v1/classes/{class_id}/attendance/`
- **Mark Attendance**: `POST /api/v1/classes/{class_id}/attendance/`
  ```json
  {
    "student_id": "c1f3a2b4-7e89-4d12-9c34-89abcdef0123",
    "status": "PRESENT"
  }
  ```

#### 🔹 24. Study Materials Upload & Download
- **Upload Material**: `POST /api/v1/teacher/batches/{batch_id}/materials/` (`multipart/form-data`)
  - `title`: `"Formula Sheet: Electrostatics & Magnetism"`
  - `material_type`: `"DOCUMENT"`
  - `file`: `[PDF File]`
  - `is_downloadable`: `true`
- **Batch Materials**: `GET /api/v1/batches/{batch_id}/materials/`
- **Download Material**: `GET /api/v1/materials/{id}/download/`
- **Bookmark Material**: `POST|DELETE /api/v1/materials/{id}/bookmark/`

---

### 2.6 Connections, Messaging, Reviews & Payments

#### 🔹 25. Privacy Connections & Contact Unlock
- **Send Connection Request**: `POST /api/v1/connections/`
  ```json
  {
    "teacher_id": "8a7b6c5d-4e3f-2a1b-0c9d-8e7f6a5b4c3d",
    "message": "Hi Sir, looking for 1-on-1 coaching."
  }
  ```
- **Approve Request**: `POST /api/v1/connections/{id}/approve/`
- **Reject Request**: `POST /api/v1/connections/{id}/reject/`
- **Secure Contact Unlock**: `GET /api/v1/connections/{id}/contact/`
  ```json
  {
    "success": true,
    "message": "Contact details unlocked securely.",
    "data": {
      "teacher_name": "Dr. Rajesh Sharma",
      "phone": "+919876543210",
      "email": "rajesh.sharma@tutoron.in"
    }
  }
  ```

#### 🔹 26. In-App Messaging / Chat (`/api/v1/conversations/`)
- **List / Start Conversations**: `GET|POST /api/v1/conversations/`
- **View Messages**: `GET /api/v1/conversations/{id}/`
- **Send Message**: `POST /api/v1/conversations/{id}/messages/`
  ```json
  {
    "content": "Sir, when is the next doubt-clearing session scheduled?"
  }
  ```
- **Mark Message Read**: `POST /api/v1/messages/{id}/read/`

#### 🔹 27. In-App Notifications
- **List Notifications**: `GET /api/v1/notifications/`
- **Mark Read**: `POST /api/v1/notifications/{id}/read/`
- **Mark All Read**: `POST /api/v1/notifications/read-all/`

#### 🔹 28. Reviews, Ratings & Incident Reports
- **Submit Batch Review**: `POST /api/v1/batches/{batch_id}/reviews/`
  ```json
  {
    "rating": 5,
    "comment": "Outstanding teaching methodology!"
  }
  ```
- **Submit Incident Report**: `POST /api/v1/reports/`
  ```json
  {
    "target_type": "USER",
    "target_id": "user-uuid-to-report",
    "reason": "SPAM",
    "description": "Sending unwanted promotional messages."
  }
  ```
- **My Reports**: `GET /api/v1/reports/my/`

#### 🔹 29. Payment Gateway & Checkout
- **Initiate Payment**: `POST /api/v1/payments/initiate/`
  ```json
  {
    "batch_id": "3c2b1a0f-9e8d-7c6b-5a4f-3e2d1c0b9a8f"
  }
  ```
  *Response*:
  ```json
  {
    "success": true,
    "data": {
      "payment_id": "pay_xyz123",
      "amount": "14999.00",
      "currency": "INR",
      "razorpay_order_id": "order_abc123"
    }
  }
  ```
- **Verify Payment**: `POST /api/v1/payments/verify/`
  ```json
  {
    "payment_id": "pay_xyz123",
    "razorpay_payment_id": "pay_98765",
    "razorpay_signature": "signature_hash"
  }
  ```

---
