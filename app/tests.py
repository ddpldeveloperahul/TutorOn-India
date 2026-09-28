from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from app.models import TeacherProfile, StudentProfile, Batch, ContactAccess

User = get_user_model()

class TutorOnApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_student_registration(self):
        url = reverse('register-student')
        payload = {
            "full_name": "Test Student",
            "email_address": "student.test@tutoron.in",
            "mobile_number": "9811111111",
            "password": "Password123!",
            "class": "Class 10",
            "board_or_university": "CBSE",
            "city": "Delhi",
            "mode_preference": "ONLINE"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertTrue(User.objects.filter(email="student.test@tutoron.in").exists())

    def test_teacher_registration(self):
        url = reverse('register-teacher')
        payload = {
            "full_name": "Test Teacher 23 Fields",
            "email_address": "teacher.23@tutoron.in",
            "mobile_number": "9822222222",
            "password": "Password123!",
            "dob": "1990-05-15",
            "gender": "MALE",
            "state": "Maharashtra",
            "city": "Mumbai",
            "address": "123 Green Park, Bandra West",
            "highest_qualification": "M.Tech in Computer Science",
            "university_institute": "IIT Bombay",
            "qualification_year": 2014,
            "subjects": ["Physics", "Mathematics"],
            "exam_expertise": ["JEE Advanced", "NEET-UG"],
            "teaching_languages": ["English", "Hindi"],
            "short_bio": "Experienced Physics educator with 10+ years teaching experience.",
            "specialization": "Mechanics and Electrodynamics",
            "current_previous_institution": "Allen Career Institute",
            "id_proof_type": "Aadhar Card",
            "year_experience": 10
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        tp = TeacherProfile.objects.get(user__email="teacher.23@tutoron.in")
        self.assertEqual(tp.university_institute, "IIT Bombay")
        self.assertEqual(tp.id_proof_type, "Aadhar Card")

    def test_unverified_teacher_login_and_dashboard_blocking(self):
        # 1. Register Unverified Teacher
        reg_url = reverse('register-teacher')
        payload = {
            "full_name": "Unverified Teacher",
            "email_address": "unverified.teacher@tutoron.in",
            "mobile_number": "9899988877",
            "password": "Password123!",
            "highest_qualification": "M.Sc Physics"
        }
        self.client.post(reg_url, payload, format='json')

        # 2. Try Login -> Must be blocked (403 FORBIDDEN)
        login_url = reverse('login')
        login_res = self.client.post(login_url, {"email": "unverified.teacher@tutoron.in", "password": "Password123!"}, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(login_res.data['success'])
        self.assertIn("pending admin verification", login_res.data['message'])

        # 3. Admin Approves Verification
        admin_user = User.objects.create_user(email="admin.verify@tutoron.in", password="AdminPass!", full_name="Admin", user_type="ADMIN", is_staff=True)
        teacher_user = User.objects.get(email="unverified.teacher@tutoron.in")
        verification = teacher_user.teacher_profile.verifications.first()

        self.client.force_authenticate(user=admin_user)
        review_url = reverse('admin-verification-review', kwargs={'pk': verification.pk})
        review_res = self.client.post(review_url, {"status": "APPROVED"}, format='json')
        self.assertEqual(review_res.status_code, status.HTTP_200_OK)

        # 4. Try Login again -> Must succeed (200 OK)
        self.client.logout()
        login_res_2 = self.client.post(login_url, {"email": "unverified.teacher@tutoron.in", "password": "Password123!"}, format='json')
        self.assertEqual(login_res_2.status_code, status.HTTP_200_OK)
        self.assertTrue(login_res_2.data['success'])

    def test_login_and_token(self):
        # Create user
        user = User.objects.create_user(
            email="login.test@tutoron.in",
            phone_number="9833333333",
            password="Password123!",
            full_name="Login Test",
            role="STUDENT"
        )
        url = reverse('login')
        payload = {
            "email": "login.test@tutoron.in",
            "password": "Password123!"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data']['tokens'])

    def test_strict_role_based_login_prevention(self):
        # Create a Student
        student = User.objects.create_user(
            email="student.role@tutoron.in",
            phone_number="9800011122",
            password="Password123!",
            full_name="Role Student",
            role="STUDENT"
        )
        url = reverse('login')

        # 1. Student tries to login specifying role=TEACHER -> DENIED (403 FORBIDDEN)
        res_cross = self.client.post(url, {"email": "student.role@tutoron.in", "password": "Password123!", "role": "TEACHER"}, format='json')
        self.assertEqual(res_cross.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(res_cross.data['success'])
        self.assertIn("registered as a STUDENT", res_cross.data['message'])

        # 2. Student logs in specifying role=STUDENT -> SUCCESS (200 OK)
        res_valid = self.client.post(url, {"email": "student.role@tutoron.in", "password": "Password123!", "role": "STUDENT"}, format='json')
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)
        self.assertTrue(res_valid.data['success'])

    def test_contact_access_privacy_masking(self):
        teacher_user = User.objects.create_user(
            email="hidden.teacher@tutoron.in",
            phone_number="9844444444",
            password="Password123!",
            full_name="Hidden Contact Teacher",
            user_type="TEACHER"
        )
        tp = TeacherProfile.objects.create(
            user=teacher_user,
            city_location="Delhi",
            hourly_rate=600.00
        )

        student_user = User.objects.create_user(
            email="visitor.student@tutoron.in",
            phone_number="9855555555",
            password="Password123!",
            full_name="Visitor Student",
            user_type="STUDENT"
        )

        # Anonymous view of teacher detail
        detail_url = reverse('teacher-detail', kwargs={'pk': tp.id})
        res1 = self.client.get(detail_url)
        self.assertEqual(res1.data['email'], "Contact Hidden (Request Connection)")
        self.assertEqual(res1.data['phone_number'], "Contact Hidden (Request Connection)")

        # Grant contact access
        ContactAccess.objects.create(
            student=student_user,
            teacher=teacher_user,
            status='GRANTED'
        )

        # Authenticated student view after access grant
        self.client.force_authenticate(user=student_user)
        res2 = self.client.get(detail_url)
        self.assertEqual(res2.data['email'], "hidden.teacher@tutoron.in")
        self.assertEqual(res2.data['phone_number'], "9844444444")

    def test_admin_dashboard_api(self):
        admin_user = User.objects.create_user(
            email="admin.test@tutoron.in",
            phone_number="9990001111",
            password="AdminPassword123!",
            full_name="Super Admin",
            user_type="ADMIN",
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=admin_user)
        url = reverse('admin-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('overview_stats', response.data['data'])
        self.assertIn('charts', response.data['data'])
        self.assertIn('recent_activity', response.data['data'])

    def test_admin_user_management(self):
        admin_user = User.objects.create_user(
            email="admin.mgmt@tutoron.in",
            phone_number="9990002222",
            password="AdminPassword123!",
            full_name="Super Admin Mgmt",
            user_type="ADMIN",
            is_staff=True
        )
        target_user = User.objects.create_user(
            email="target.user@tutoron.in",
            phone_number="9877777777",
            password="Password123!",
            full_name="Target User",
            user_type="STUDENT",
            is_active=True
        )
        self.client.force_authenticate(user=admin_user)

        # List users
        list_url = reverse('admin-user-list')
        res_list = self.client.get(list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)

        # Toggle user active status
        toggle_url = reverse('admin-user-status-toggle', kwargs={'pk': target_user.pk})
        res_toggle = self.client.patch(toggle_url, {'is_active': False}, format='json')
        self.assertEqual(res_toggle.status_code, status.HTTP_200_OK)
        target_user.refresh_from_db()
        self.assertFalse(target_user.is_active)


class TeacherDashboardTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_user = User.objects.create_user(
            email="teacher.dash@tutoron.in",
            phone_number="9899999999",
            password="Password123!",
            full_name="Teacher Dash",
            user_type="TEACHER"
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            is_verified=True,
            rating=4.9
        )
        self.client.force_authenticate(user=self.teacher_user)

    def test_teacher_dashboard_get(self):
        url = reverse('teacher-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertIn('teacher_info', data)
        self.assertIn('live_class_now', data)
        self.assertIn('quick_actions', data)
        self.assertIn('stats', data)
        self.assertIn('todays_schedule', data)
        self.assertIn('my_batches', data)
        self.assertIn('student_updates', data)
        self.assertIn('uploaded_materials', data)
        self.assertIn('announcements', data)

    def test_teacher_batch_crud(self):
        # 1. Create Batch (POST)
        list_url = reverse('teacher-batch-list-create')
        post_data = {
            "title": "JEE Advanced Maths 2025",
            "description": "Calculus and Algebra",
            "subject": "Mathematics",
            "batch_type": "ONLINE",
            "fee": 4999.00
        }
        res_create = self.client.post(list_url, post_data, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        batch_id = res_create.data['id']

        # 2. Detail & Update Batch (PUT)
        detail_url = reverse('teacher-batch-detail', kwargs={'pk': batch_id})
        res_update = self.client.patch(detail_url, {"title": "JEE Advanced Maths 2025 (Updated)"}, format='json')
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data['title'], "JEE Advanced Maths 2025 (Updated)")

        # 3. Delete Batch (DELETE)
        res_delete = self.client.delete(detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)

    def test_teacher_class_schedule_and_toggle_live(self):
        # Create a batch first
        batch = Batch.objects.create(teacher=self.teacher_user, title="Physics Crash", subject="Physics")
        
        # 1. Schedule Class (POST)
        class_url = reverse('teacher-class-list-create')
        class_data = {
            "batch": batch.id,
            "title": "Electrostatics",
            "content_type": "ZOOM",
            "url": "https://zoom.us/j/123456",
            "duration_minutes": 60
        }
        res_class = self.client.post(class_url, class_data, format='json')
        self.assertEqual(res_class.status_code, status.HTTP_201_CREATED)
        class_id = res_class.data['id']

        # 2. Toggle Live (POST)
        live_url = reverse('teacher-class-toggle-live', kwargs={'pk': class_id})
        res_live = self.client.post(live_url, {"is_live": True, "status": "LIVE"}, format='json')
        self.assertEqual(res_live.status_code, status.HTTP_200_OK)
        self.assertTrue(res_live.data['data']['is_live'])

    def test_create_batch_wizard_flow(self):
        # 1. GET Wizard Options
        options_url = reverse('teacher-batch-wizard-options')
        res_options = self.client.get(options_url)
        self.assertEqual(res_options.status_code, status.HTTP_200_OK)
        self.assertIn('step_1_essentials', res_options.data['data'])
        self.assertIn('step_2_delivery_and_schedule', res_options.data['data'])
        self.assertIn('step_3_pricing_and_perks', res_options.data['data'])

        # 2. Save Draft (Step 1 & Step 2 auto-save)
        draft_url = reverse('teacher-batch-save-draft')
        draft_payload = {
            "title": "JEE Advanced 2026: Mechanics & Electrodynamics",
            "target_exam": "JEE Advanced",
            "subject": "Physics",
            "target_grade": "Class 12th & Droppers (Intensive)",
            "delivery_format": "LIVE_INTERACTIVE",
            "max_students_capacity": 150,
            "class_days": ["Mon", "Wed", "Fri"],
            "class_slot": "4:00 PM - 5:30 PM"
        }
        res_draft = self.client.post(draft_url, draft_payload, format='json')
        self.assertEqual(res_draft.status_code, status.HTTP_200_OK)
        self.assertTrue(res_draft.data['data']['is_draft'])
        draft_id = res_draft.data['data']['id']

        # 3. Complete Step 3 & Publish Batch
        publish_url = reverse('teacher-batch-list-create')
        publish_payload = {
            "title": "JEE Advanced 2026: Mechanics & Electrodynamics",
            "target_exam": "JEE Advanced",
            "subject": "Physics",
            "target_grade": "Class 12th & Droppers (Intensive)",
            "delivery_format": "LIVE_INTERACTIVE",
            "max_students_capacity": 150,
            "class_days": ["Mon", "Wed", "Fri"],
            "class_slot": "4:00 PM - 5:30 PM",
            "is_paid": True,
            "fee": 4999.00,
            "discounted_price": 4999.00,
            "original_price": 7999.00,
            "allow_installments": True,
            "installment_amount": 2600.00,
            "cohort_perks": [
                "Daily Live Interactive Sessions",
                "DPPs & Annotated PDF Class Notes",
                "Weekly AI-Proctored Mock Tests",
                "24/7 Dedicated Doubt Solving Room"
            ]
        }
        res_pub = self.client.post(publish_url, publish_payload, format='json')
        self.assertEqual(res_pub.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res_pub.data['is_draft'])
        self.assertEqual(len(res_pub.data['cohort_perks']), 4)



