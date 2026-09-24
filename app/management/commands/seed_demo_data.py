from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app.models import (
    StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, ConnectionRequest,
    ContactAccess, Review
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds initial demo data for TutorOn India platform testing."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Seeding demo data..."))

        # 1. Superuser / Admin
        admin, created = User.objects.get_or_create(
            email="admin@tutoron.in",
            defaults={
                "phone_number": "9999999999",
                "full_name": "TutorOn Admin",
                "user_type": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True
            }
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin account: admin@tutoron.in / AdminPass123!"))

        # 2. Sample Teachers
        teachers_data = [
            {
                "email": "rahul.teacher@tutoron.in",
                "phone_number": "9876543210",
                "full_name": "Rahul Sharma",
                "city": "New Delhi",
                "subjects": ["Physics", "Mathematics"],
                "qualifications": "M.Tech IIT Delhi, 8 Years Teaching Exp.",
                "hourly_rate": 800.00,
                "monthly_fee": 5000.00,
                "tagline": "Top IIT-JEE Physics Specialist",
                "bio": "Expert in simplifying complex physics concepts for Class 11-12 and JEE aspirants.",
                "verified": True
            },
            {
                "email": "priya.singh@tutoron.in",
                "phone_number": "9876543211",
                "full_name": "Priya Singh",
                "city": "Mumbai",
                "subjects": ["Chemistry", "Biology"],
                "qualifications": "M.Sc Organic Chemistry, NEET Faculty",
                "hourly_rate": 700.00,
                "monthly_fee": 4500.00,
                "tagline": "NEET Chemistry Topper Faculty",
                "bio": "Specialized in Organic and Inorganic Chemistry with 100+ selections in NEET.",
                "verified": True
            }
        ]

        created_teachers = []
        for tdata in teachers_data:
            user, t_created = User.objects.get_or_create(
                email=tdata["email"],
                defaults={
                    "phone_number": tdata["phone_number"],
                    "full_name": tdata["full_name"],
                    "user_type": "TEACHER",
                    "is_verified": tdata["verified"]
                }
            )
            if t_created:
                user.set_password("Teacher123!")
                user.save()

            profile, _ = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    "gender": "MALE" if "Rahul" in user.full_name else "FEMALE",
                    "city_location": tdata["city"],
                    "teaching_subjects": tdata["subjects"],
                    "qualifications": tdata["qualifications"],
                    "hourly_rate": tdata["hourly_rate"],
                    "monthly_fee": tdata["monthly_fee"],
                    "tagline": tdata["tagline"],
                    "bio": tdata["bio"],
                    "is_verified": tdata["verified"],
                    "rating": 4.9
                }
            )
            created_teachers.append(user)
            self.stdout.write(self.style.SUCCESS(f"Teacher created: {user.email}"))

        # 3. Sample Students
        students_data = [
            {
                "email": "rohan.student@tutoron.in",
                "phone_number": "9123456789",
                "full_name": "Rohan Verma",
                "city": "New Delhi",
                "class": "Class 12",
                "target": ["JEE Mains", "CBSE Board"]
            },
            {
                "email": "ananya.student@tutoron.in",
                "phone_number": "9123456788",
                "full_name": "Ananya Patel",
                "city": "Mumbai",
                "class": "Class 11",
                "target": ["NEET"]
            }
        ]

        created_students = []
        for sdata in students_data:
            user, s_created = User.objects.get_or_create(
                email=sdata["email"],
                defaults={
                    "phone_number": sdata["phone_number"],
                    "full_name": sdata["full_name"],
                    "user_type": "STUDENT"
                }
            )
            if s_created:
                user.set_password("Student123!")
                user.save()

            StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "student_class": sdata["class"],
                    "city_location": sdata["city"],
                    "target_exams": sdata["target"]
                }
            )
            created_students.append(user)
            self.stdout.write(self.style.SUCCESS(f"Student created: {user.email}"))

        # 4. Sample Batches & Content
        if created_teachers:
            t1 = created_teachers[0]
            batch, b_created = Batch.objects.get_or_create(
                title="Class 12 Physics JEE Mains Masterclass 2026",
                teacher=t1,
                defaults={
                    "description": "Complete coverage of Electrostatics, Magnetism and Optics with problem solving.",
                    "subject": "Physics",
                    "batch_type": "ONLINE",
                    "fee": 5000.00
                }
            )
            if b_created:
                BatchAnnouncement.objects.create(
                    batch=batch,
                    title="Welcome to Physics Masterclass",
                    content="Classes will be conducted every Monday, Wednesday and Friday at 6 PM."
                )

                ClassContent.objects.create(
                    batch=batch,
                    title="Lecture 01: Coulomb's Law & Electric Field",
                    content_type="YOUTUBE",
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    description="Detailed explanation of Coulomb's inverse square law."
                )
                ClassContent.objects.create(
                    batch=batch,
                    title="Live Doubt Session 01",
                    content_type="ZOOM",
                    url="https://zoom.us/j/1234567890",
                    description="Interactive Zoom doubt discussion."
                )
                self.stdout.write(self.style.SUCCESS("Created demo batch and class contents."))

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete!"))
