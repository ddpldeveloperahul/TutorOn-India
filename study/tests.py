from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import (
    User, StudentProfile, TeacherProfile, TeacherVerification,
    Batch, Enrollment, ClassContent, ConnectionRequest, ContactAccess,
    UserBlock, Review
)

class TutorOnIndiaBackendTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Admin
        self.admin = User.objects.create_superuser(
            email="testadmin@tutoron.in",
            password="AdminPassword123",
            first_name="Admin",
            last_name="User"
        )

        # 2. Verified Teacher
        self.v_teacher_user = User.objects.create_user(
            email="verified.teacher@tutoron.in",
            password="TeacherPassword123",
            first_name="Verified",
            last_name="Teacher",
            phone_number="+919876543210",
            role=User.Role.TEACHER,
            is_verified=True
        )
        self.v_teacher_profile = TeacherProfile.objects.create(
            user=self.v_teacher_user,
            display_name="Prof. Verified",
            qualification="M.Sc. Physics",
            experience_years=10.0,
            subjects=["Physics", "Maths"],
            teaching_languages=["English", "Hindi"],
            verification_status=TeacherProfile.VerificationStatus.VERIFIED,
            average_rating=4.9
        )

        # 3. Unverified Teacher
        self.u_teacher_user = User.objects.create_user(
            email="pending.teacher@tutoron.in",
            password="TeacherPassword123",
            first_name="Pending",
            last_name="Teacher",
            role=User.Role.TEACHER,
            is_verified=False
        )
        self.u_teacher_profile = TeacherProfile.objects.create(
            user=self.u_teacher_user,
            display_name="Pending Teacher",
            verification_status=TeacherProfile.VerificationStatus.PENDING_VERIFICATION
        )

        # 4. Student 1
        self.student1_user = User.objects.create_user(
            email="student1@tutoron.in",
            password="StudentPassword123",
            first_name="Student",
            last_name="One",
            phone_number="+919811122233",
            role=User.Role.STUDENT,
            is_verified=True
        )
        self.student1_profile = StudentProfile.objects.create(
            user=self.student1_user,
            education_level="Class 12"
        )

        # 5. Student 2 (Unenrolled)
        self.student2_user = User.objects.create_user(
            email="student2@tutoron.in",
            password="StudentPassword123",
            first_name="Student",
            last_name="Two",
            phone_number="+919811144455",
            role=User.Role.STUDENT,
            is_verified=True
        )
        self.student2_profile = StudentProfile.objects.create(
            user=self.student2_user,
            education_level="Class 11"
        )

        # 6. Published Batch
        self.batch = Batch.objects.create(
            teacher=self.v_teacher_profile,
            title="Comprehensive Physics for JEE",
            subject="Physics",
            capacity=2,
            price=1500.00,
            status=Batch.Status.PUBLISHED
        )

    # -----------------------------------------------------------
    # AUTH TESTS
    # -----------------------------------------------------------
    def test_student_registration_and_login(self):
        # Register
        data = {
            "first_name": "New",
            "last_name": "Student",
            "email": "newstudent@tutoron.in",
            "password": "StrongPassword123!",
            "phone_number": "+919999900001",
            "education_level": "Class 10"
        }
        res = self.client.post('/api/v1/auth/register/student/', data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['success'])
        # Verify complete response data
        self.assertIn('profile', res.data['data'])
        self.assertIn('tokens', res.data['data'])
        self.assertEqual(res.data['data']['email'], "newstudent@tutoron.in")

        # Login
        login_res = self.client.post('/api/v1/auth/login/', {
            "email": "newstudent@tutoron.in",
            "password": "StrongPassword123!"
        }, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_res.data['data'])
        self.assertIn('refresh', login_res.data['data'])

    def test_teacher_registration_starts_as_pending(self):
        data = {
            "first_name": "New",
            "last_name": "Teacher",
            "email": "newteacher@tutoron.in",
            "password": "StrongPassword123!",
            "phone_number": "+919999900002",
            "qualification": "Ph.D. Mathematics"
        }
        res = self.client.post('/api/v1/auth/register/teacher/', data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Verify complete response data
        self.assertIn('profile', res.data['data'])
        self.assertIn('tokens', res.data['data'])
        teacher_prof = TeacherProfile.objects.get(user__email="newteacher@tutoron.in")
        self.assertEqual(teacher_prof.verification_status, TeacherProfile.VerificationStatus.PENDING_VERIFICATION)

    def test_unified_registration_for_student_and_teacher(self):
        # 1. Register Student via unified endpoint
        student_data = {
            "role": "STUDENT",
            "first_name": "Unified",
            "last_name": "Student",
            "email": "unified.student@tutoron.in",
            "password": "Password123!",
            "phone_number": "+919876543299",
            "education_level": "Class 12"
        }
        res_stu = self.client.post('/api/v1/auth/register/', student_data, format='json')
        self.assertEqual(res_stu.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_stu.data['data']['role'], "STUDENT")
        self.assertIn('profile', res_stu.data['data'])
        self.assertIn('tokens', res_stu.data['data'])
        self.assertEqual(res_stu.data['data']['profile']['education_level'], "Class 12")

        # 2. Register Teacher via unified endpoint
        teacher_data = {
            "role": "TEACHER",
            "first_name": "Unified",
            "last_name": "Teacher",
            "email": "unified.teacher@tutoron.in",
            "password": "Password123!",
            "phone_number": "+919876543288",
            "qualification": "M.Sc. Chemistry",
            "subjects": ["Chemistry"]
        }
        res_tch = self.client.post('/api/v1/auth/register/', teacher_data, format='json')
        self.assertEqual(res_tch.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_tch.data['data']['role'], "TEACHER")
        self.assertIn('profile', res_tch.data['data'])
        self.assertIn('tokens', res_tch.data['data'])
        self.assertEqual(res_tch.data['data']['profile']['qualification'], "M.Sc. Chemistry")

    # -----------------------------------------------------------
    # PRIVACY & SEARCH TESTS
    # -----------------------------------------------------------
    def test_public_teacher_search_privacy(self):
        res = self.client.get('/api/v1/teachers/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['data']
        # Only verified teacher should be in results
        teacher_ids = [t['id'] for t in results]
        self.assertIn(str(self.v_teacher_profile.id), teacher_ids)
        self.assertNotIn(str(self.u_teacher_profile.id), teacher_ids)

        # STRICT PRIVACY: phone_number and email must NOT be present
        v_teacher_card = [t for t in results if t['id'] == str(self.v_teacher_profile.id)][0]
        self.assertNotIn('email', v_teacher_card)
        self.assertNotIn('phone_number', v_teacher_card)

    # -----------------------------------------------------------
    # BATCH & PERMISSION TESTS
    # -----------------------------------------------------------
    def test_unverified_teacher_cannot_publish_batch(self):
        self.client.force_authenticate(user=self.u_teacher_user)
        res = self.client.post('/api/v1/teacher/batches/', {
            "title": "Unverified Physics Batch",
            "description": "Desc",
            "subject": "Physics",
            "capacity": 30,
            "status": "PUBLISHED"
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data['success'])

    # -----------------------------------------------------------
    # ENROLLMENT & CAPACITY TESTS
    # -----------------------------------------------------------
    def test_student_enrollment_and_capacity(self):
        self.client.force_authenticate(user=self.student1_user)
        # Request enrollment
        res = self.client.post(f'/api/v1/batches/{self.batch.id}/enroll/')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        enrollment_id = res.data['data']['id']

        # Duplicate request rejected
        dup_res = self.client.post(f'/api/v1/batches/{self.batch.id}/enroll/')
        self.assertEqual(dup_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Teacher approves enrollment
        self.client.force_authenticate(user=self.v_teacher_user)
        approve_res = self.client.post(f'/api/v1/teacher/enrollments/{enrollment_id}/approve/')
        self.assertEqual(approve_res.status_code, status.HTTP_200_OK)

        enrollment = Enrollment.objects.get(id=enrollment_id)
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

    # -----------------------------------------------------------
    # CLASS URL SECURITY TESTS
    # -----------------------------------------------------------
    def test_class_url_validation(self):
        self.client.force_authenticate(user=self.v_teacher_user)

        # Valid Zoom URL
        res_zoom = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "Zoom Live Class",
            "class_type": "ZOOM",
            "external_url": "https://us04web.zoom.us/j/123456789"
        }, format='json')
        self.assertEqual(res_zoom.status_code, status.HTTP_201_CREATED)

        # Valid YouTube URL
        res_yt = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "YouTube Class",
            "class_type": "YOUTUBE",
            "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }, format='json')
        self.assertEqual(res_yt.status_code, status.HTTP_201_CREATED)

        # Valid Google Meet URL
        res_meet = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "Meet Class",
            "class_type": "GOOGLE_MEET",
            "external_url": "https://meet.google.com/abc-defg-hij"
        }, format='json')
        self.assertEqual(res_meet.status_code, status.HTTP_201_CREATED)

        # Insecure or spoofed domain rejected
        res_bad = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "Fake Zoom",
            "class_type": "ZOOM",
            "external_url": "https://evil-hacker.com/zoom"
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

        # Non-HTTPS rejected
        res_http = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "HTTP Zoom",
            "class_type": "ZOOM",
            "external_url": "http://zoom.us/j/123"
        }, format='json')
        self.assertEqual(res_http.status_code, status.HTTP_400_BAD_REQUEST)

    # -----------------------------------------------------------
    # CLASS CONTENT ACCESS CONTROL
    # -----------------------------------------------------------
    def test_class_access_control_enrolled_vs_unenrolled(self):
        class_obj = ClassContent.objects.create(
            batch=self.batch,
            teacher=self.v_teacher_profile,
            title="Private Physics Class",
            class_type=ClassContent.ClassType.ZOOM,
            external_url="https://zoom.us/j/123456789"
        )
        # 1. Enrolled student allowed
        Enrollment.objects.create(
            student=self.student1_profile,
            batch=self.batch,
            status=Enrollment.Status.ACTIVE
        )
        self.client.force_authenticate(user=self.student1_user)
        res_allowed = self.client.get(f'/api/v1/classes/{class_obj.id}/')
        self.assertEqual(res_allowed.status_code, status.HTTP_200_OK)

        # 2. Unenrolled student blocked (403 Forbidden)
        self.client.force_authenticate(user=self.student2_user)
        res_denied = self.client.get(f'/api/v1/classes/{class_obj.id}/')
        self.assertEqual(res_denied.status_code, status.HTTP_403_FORBIDDEN)

    # -----------------------------------------------------------
    # DEDICATED CONTACT PRIVACY WORKFLOW TESTS
    # -----------------------------------------------------------
    def test_contact_unlock_workflow(self):
        # Student initiates connection
        self.client.force_authenticate(user=self.student1_user)
        res_conn = self.client.post('/api/v1/connections/', {
            "teacher_id": str(self.v_teacher_profile.id),
            "message": "Can I connect?"
        }, format='json')
        self.assertEqual(res_conn.status_code, status.HTTP_201_CREATED)
        conn_id = res_conn.data['data']['id']

        # Attempt to access contact details BEFORE admin approval -> 403 Forbidden
        contact_attempt = self.client.get(f'/api/v1/connections/{conn_id}/contact/')
        self.assertEqual(contact_attempt.status_code, status.HTTP_403_FORBIDDEN)

        # Admin approves contact unlock
        self.client.force_authenticate(user=self.admin)
        admin_res = self.client.post(f'/api/v1/connections/{conn_id}/approve/', {"reason": "Verified"})
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)

        # Student accesses unlocked contact details -> 200 OK with teacher's phone & email
        self.client.force_authenticate(user=self.student1_user)
        contact_res = self.client.get(f'/api/v1/connections/{conn_id}/contact/')
        self.assertEqual(contact_res.status_code, status.HTTP_200_OK)
        self.assertEqual(contact_res.data['data']['phone_number'], "+919876543210")
        self.assertEqual(contact_res.data['data']['email'], "verified.teacher@tutoron.in")

    # -----------------------------------------------------------
    # USER BLOCKING TESTS
    # -----------------------------------------------------------
    def test_user_blocking_prevents_connection(self):
        # Teacher blocks Student 2
        UserBlock.objects.create(blocker=self.v_teacher_user, blocked=self.student2_user, reason="Spam")

        # Student 2 cannot initiate connection
        self.client.force_authenticate(user=self.student2_user)
        res = self.client.post('/api/v1/connections/', {
            "teacher_id": str(self.v_teacher_profile.id),
            "message": "Hello"
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # -----------------------------------------------------------
    # REVIEWS TESTS
    # -----------------------------------------------------------
    def test_review_eligibility(self):
        # Unenrolled student cannot review
        self.client.force_authenticate(user=self.student2_user)
        res_un = self.client.post(f'/api/v1/batches/{self.batch.id}/reviews/', {
            "rating": 5, "comment": "Good"
        }, format='json')
        self.assertEqual(res_un.status_code, status.HTTP_403_FORBIDDEN)

        # Enrolled student can review
        Enrollment.objects.create(student=self.student1_profile, batch=self.batch, status=Enrollment.Status.ACTIVE)
        self.client.force_authenticate(user=self.student1_user)
        res_ok = self.client.post(f'/api/v1/batches/{self.batch.id}/reviews/', {
            "rating": 5, "comment": "Excellent teaching!"
        }, format='json')
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    # -----------------------------------------------------------
    # ADMIN PERMISSION TESTS
    # -----------------------------------------------------------
    def test_admin_endpoints_require_admin_role(self):
        # Student receives 403 Forbidden
        self.client.force_authenticate(user=self.student1_user)
        res_student = self.client.get('/api/v1/admin/dashboard/')
        self.assertEqual(res_student.status_code, status.HTTP_403_FORBIDDEN)

        # Admin receives 200 OK
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/v1/admin/dashboard/')
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertIn('total_students', res_admin.data['data'])

    # -----------------------------------------------------------
    # CLASS REMINDERS TEST
    # -----------------------------------------------------------
    def test_class_reminder_dispatch(self):
        from django.utils import timezone
        from datetime import timedelta
        from .models import Notification

        # Create active enrollment
        Enrollment.objects.create(student=self.student1_profile, batch=self.batch, status=Enrollment.Status.ACTIVE)

        # Create scheduled class in next 30 minutes with Zoom URL
        class_obj = ClassContent.objects.create(
            batch=self.batch,
            teacher=self.v_teacher_profile,
            title="Scheduled Zoom Physics Class",
            class_type=ClassContent.ClassType.ZOOM,
            external_url="https://us04web.zoom.us/j/1234567890",
            scheduled_date=timezone.now() + timedelta(minutes=30),
            is_published=True
        )

        # Trigger reminders via admin endpoint
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/v1/admin/classes/send-reminders/', {"window_minutes": 60}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['success'])
        self.assertGreaterEqual(res.data['data']['reminders_sent'], 1)

        # Verify notification created for student with Zoom link
        notif = Notification.objects.filter(
            recipient=self.student1_user,
            notification_type=Notification.NotificationType.CLASS_REMINDER
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Scheduled Zoom Physics Class", notif.title)
        self.assertIn("https://us04web.zoom.us/j/1234567890", notif.message)

    # -----------------------------------------------------------
    # ADMIN CONNECTION APPROVE & REJECT REST ENDPOINT TESTS
    # -----------------------------------------------------------
    def test_admin_connection_endpoints(self):
        # Create connection request
        conn = ConnectionRequest.objects.create(
            student=self.student1_profile,
            teacher=self.v_teacher_profile,
            requested_by=self.student1_user,
            status=ConnectionRequest.Status.STUDENT_APPROVED,
            student_approved=True
        )
        ContactAccess.objects.create(
            connection=conn,
            student=self.student1_profile,
            teacher=self.v_teacher_profile,
            status=ContactAccess.Status.PENDING
        )

        # Admin approves connection via REST endpoint
        self.client.force_authenticate(user=self.admin)
        res_approve = self.client.post(f'/api/v1/admin/connections/{conn.id}/approve/', {"reason": "Verified credentials"}, format='json')
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        self.assertTrue(res_approve.data['data']['contact_unlocked'])

        # Create another connection and test reject endpoint
        conn2 = ConnectionRequest.objects.create(
            student=self.student2_profile,
            teacher=self.v_teacher_profile,
            requested_by=self.student2_user,
            status=ConnectionRequest.Status.STUDENT_APPROVED,
            student_approved=True
        )
        res_reject = self.client.post(f'/api/v1/admin/connections/{conn2.id}/reject/', {"reason": "Rejected by admin"}, format='json')
        self.assertEqual(res_reject.status_code, status.HTTP_200_OK)
        conn2.refresh_from_db()
        self.assertEqual(conn2.status, ConnectionRequest.Status.REJECTED)

    # -----------------------------------------------------------
    # EXTERNAL URL VALIDATION TESTS
    # -----------------------------------------------------------
    def test_external_url_security_validation(self):
        self.client.force_authenticate(user=self.v_teacher_user)

        # 1. Valid YouTube URL
        res_yt = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "YouTube Lecture",
            "class_type": "YOUTUBE",
            "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }, format='json')
        self.assertEqual(res_yt.status_code, status.HTTP_201_CREATED)

        # 2. Valid Google Meet URL
        res_meet = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "Google Meet Session",
            "class_type": "GOOGLE_MEET",
            "external_url": "https://meet.google.com/abc-defg-hij"
        }, format='json')
        self.assertEqual(res_meet.status_code, status.HTTP_201_CREATED)

        # 3. Invalid URL (dangerous scheme or non-allowed domain)
        res_bad = self.client.post(f'/api/v1/teacher/batches/{self.batch.id}/classes/', {
            "title": "Dangerous Class",
            "class_type": "YOUTUBE",
            "external_url": "javascript:alert(1)"
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

