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
            "full_name": "Test Teacher",
            "email_address": "teacher.test@tutoron.in",
            "mobile_number": "9822222222",
            "password": "Password123!",
            "gender": "MALE",
            "qualifications": "B.Tech Computer Science",
            "experience_years": 5,
            "teaching_subjects": ["Physics"],
            "city": "Bangalore",
            "hourly_rate": 500.00
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertTrue(TeacherProfile.objects.filter(user__email="teacher.test@tutoron.in").exists())

    def test_login_and_token(self):
        # Create user
        user = User.objects.create_user(
            email="login.test@tutoron.in",
            phone_number="9833333333",
            password="Password123!",
            full_name="Login Test",
            user_type="STUDENT"
        )
        url = reverse('login')
        payload = {
            "email": "login.test@tutoron.in",
            "password": "Password123!"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data']['tokens'])

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
