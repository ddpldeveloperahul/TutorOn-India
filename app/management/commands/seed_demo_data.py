from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from app.models import (
    StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, ConnectionRequest,
    ContactAccess, Review, Enrollment, Notification
)

User = get_user_model()

def get_or_create_user(email, phone_number, full_name, user_type, is_verified=False):
    user = User.objects.filter(email=email).first()
    if not user and phone_number:
        user = User.objects.filter(phone_number=phone_number).first()
    
    if user:
        user.full_name = full_name
        user.user_type = user_type
        user.is_verified = is_verified
        user.save()
        return user, False
    else:
        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            full_name=full_name,
            user_type=user_type,
            is_verified=is_verified
        )
        return user, True

class Command(BaseCommand):
    help = "Seeds complete teacher dummy data & student dashboard data for TutorOn India."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Seeding demo data for Student Dashboard flow..."))

        # 1. Superuser / Admin
        admin, created = get_or_create_user(
            email="admin@tutoron.in",
            phone_number="9999999999",
            full_name="TutorOn Admin",
            user_type="ADMIN",
            is_verified=True
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("AdminPass123!")
        admin.save()
        self.stdout.write(self.style.SUCCESS("Admin ready: admin@tutoron.in"))

        # 2. Four Teachers from Screenshots
        teachers_data = [
            {
                "email": "priya.sharma@tutoron.in",
                "phone_number": "9876543201",
                "full_name": "Dr. Priya Sharma",
                "city": "New Delhi",
                "subjects": ["Mathematics"],
                "qualifications": "PhD — IIT Delhi",
                "hourly_rate": 900.00,
                "monthly_fee": 6000.00,
                "tagline": "Senior Mathematics Specialist",
                "bio": "PhD from IIT Delhi with over 10 years of experience coaching top rankers for JEE Advanced.",
                "languages": ["Hindi", "English"],
                "rating": 4.9,
                "total_reviews": 128,
                "verified": True
            },
            {
                "email": "arjun.mehta@tutoron.in",
                "phone_number": "9876543202",
                "full_name": "Prof. Arjun Mehta",
                "city": "Mumbai",
                "subjects": ["Physics"],
                "qualifications": "M.Sc — BITS Pilani",
                "hourly_rate": 850.00,
                "monthly_fee": 5500.00,
                "tagline": "Physics Faculty for NEET & JEE",
                "bio": "M.Sc from BITS Pilani. Simplified concept building approach for mechanics and electrodynamics.",
                "languages": ["Hindi", "English"],
                "rating": 4.7,
                "total_reviews": 95,
                "verified": True
            },
            {
                "email": "sunita.patel@tutoron.in",
                "phone_number": "9876543203",
                "full_name": "Ms. Sunita Patel",
                "city": "Ahmedabad",
                "subjects": ["Chemistry"],
                "qualifications": "M.Sc — DU",
                "hourly_rate": 800.00,
                "monthly_fee": 5000.00,
                "tagline": "Organic Chemistry Master",
                "bio": "M.Sc Delhi University. Specializing in Organic mechanisms and reaction tricks for Class 11 & 12.",
                "languages": ["Hindi", "Gujarati"],
                "rating": 4.8,
                "total_reviews": 84,
                "verified": True
            },
            {
                "email": "rajesh.kumar@tutoron.in",
                "phone_number": "9876543204",
                "full_name": "Mr. Rajesh Kumar",
                "city": "Jaipur",
                "subjects": ["Biology"],
                "qualifications": "MBBS — AIIMS",
                "hourly_rate": 750.00,
                "monthly_fee": 4500.00,
                "tagline": "NEET Biology Specialist",
                "bio": "AIIMS Graduate teaching Botany and Zoology with interactive visual diagrams and NCERT focus.",
                "languages": ["Hindi", "English"],
                "rating": 4.6,
                "total_reviews": 60,
                "verified": True
            }
        ]

        teacher_objs = {}
        for tdata in teachers_data:
            user, t_created = get_or_create_user(
                email=tdata["email"],
                phone_number=tdata["phone_number"],
                full_name=tdata["full_name"],
                user_type="TEACHER",
                is_verified=tdata["verified"]
            )
            if t_created:
                user.set_password("Teacher123!")
                user.save()

            profile, _ = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    "gender": "FEMALE" if "Ms." in user.full_name or "Priya" in user.full_name else "MALE",
                    "city_location": tdata["city"],
                    "teaching_subjects": tdata["subjects"],
                    "qualifications": tdata["qualifications"],
                    "hourly_rate": tdata["hourly_rate"],
                    "monthly_fee": tdata["monthly_fee"],
                    "tagline": tdata["tagline"],
                    "bio": tdata["bio"],
                    "languages_spoken": tdata["languages"],
                    "is_verified": tdata["verified"],
                    "rating": tdata["rating"],
                    "total_reviews": tdata["total_reviews"]
                }
            )
            profile.rating = tdata["rating"]
            profile.total_reviews = tdata["total_reviews"]
            profile.is_verified = tdata["verified"]
            profile.save()

            teacher_objs[tdata["full_name"]] = user
            self.stdout.write(self.style.SUCCESS(f"Teacher ready: {tdata['full_name']}"))

        # 3. Default Demo Student Account
        student_user, s_created = get_or_create_user(
            email="student@tutoron.in",
            phone_number="9123456700",
            full_name="Student",
            user_type="STUDENT",
            is_verified=True
        )
        if s_created:
            student_user.set_password("Student123!")
            student_user.save()

        student_profile, _ = StudentProfile.objects.get_or_create(
            user=student_user,
            defaults={
                "student_class": "Class 12",
                "city_location": "New Delhi",
                "target_exams": ["JEE Advanced", "NEET"],
                "subjects_needed": ["Mathematics", "Physics", "Chemistry"]
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Default Student ready: student@tutoron.in / Student123!"))

        # 4. Batches from Screenshots
        now = timezone.now()
        batches_info = [
            {
                "title": "JEE Advanced Maths 2025",
                "teacher": teacher_objs["Dr. Priya Sharma"],
                "subject": "Mathematics",
                "schedule_time": "Today, 4:00 PM",
                "is_active": True,
                "fee": 6000.00,
                "description": "Comprehensive course for JEE Advanced Mathematics 2025."
            },
            {
                "title": "NEET Physics Crash Course",
                "teacher": teacher_objs["Prof. Arjun Mehta"],
                "subject": "Physics",
                "schedule_time": "Tomorrow, 10:00 AM",
                "is_active": True,
                "fee": 4500.00,
                "description": "High-yield crash course for NEET Physics preparation."
            },
            {
                "title": "Organic Chemistry Mastery",
                "teacher": teacher_objs["Ms. Sunita Patel"],
                "subject": "Chemistry",
                "schedule_time": "Wed, 5:00 PM",
                "is_active": True,
                "fee": 5000.00,
                "description": "Master all organic mechanisms, conversions and reactions."
            },
            {
                "title": "Class 10 Board Revision",
                "teacher": teacher_objs["Dr. Priya Sharma"],
                "subject": "Mathematics",
                "schedule_time": "Completed",
                "is_active": False,
                "fee": 3000.00,
                "description": "Board revision module for Class 10 students."
            }
        ]

        batch_objs = {}
        for b_info in batches_info:
            batch, _ = Batch.objects.get_or_create(
                title=b_info["title"],
                teacher=b_info["teacher"],
                defaults={
                    "subject": b_info["subject"],
                    "schedule_time": b_info["schedule_time"],
                    "is_active": b_info["is_active"],
                    "fee": b_info["fee"],
                    "description": b_info["description"]
                }
            )
            batch_objs[b_info["title"]] = batch
            # Enroll demo student
            Enrollment.objects.get_or_create(student=student_user, batch=batch, defaults={"status": "ACTIVE" if b_info["is_active"] else "CANCELLED"})

        # 5. Live Class & Upcoming Classes
        # Live Class: Chemistry - Organic Reactions by Ms. Sunita Patel (LIVE NOW)
        ClassContent.objects.get_or_create(
            batch=batch_objs["Organic Chemistry Mastery"],
            title="Chemistry — Organic Reactions",
            defaults={
                "description": "Live session covering aromatic substitution and reaction mechanisms.",
                "content_type": "ZOOM",
                "url": "https://zoom.us/j/987654321",
                "scheduled_at": now - datetime.timedelta(minutes=15),
                "duration_minutes": 60
            }
        )

        # Upcoming Class 1: Mathematics - Calculus Basics by Dr. Priya Sharma
        ClassContent.objects.get_or_create(
            batch=batch_objs["JEE Advanced Maths 2025"],
            title="Mathematics — Calculus Basics",
            defaults={
                "description": "Introduction to limits, continuity and derivatives.",
                "content_type": "GOOGLE_MEET",
                "url": "https://meet.google.com/abc-defg-hij",
                "scheduled_at": now + datetime.timedelta(hours=2),
                "duration_minutes": 90
            }
        )

        # Upcoming Class 2: Physics - Electrostatics by Prof. Arjun Mehta
        ClassContent.objects.get_or_create(
            batch=batch_objs["NEET Physics Crash Course"],
            title="Physics — Electrostatics",
            defaults={
                "description": "Electric fields, potential and Gauss's law numericals.",
                "content_type": "ZOOM",
                "url": "https://zoom.us/j/123456789",
                "scheduled_at": now + datetime.timedelta(hours=4, minutes=30),
                "duration_minutes": 60
            }
        )

        # 6. Study Materials
        for b_name in ["JEE Advanced Maths 2025", "NEET Physics Crash Course", "Organic Chemistry Mastery"]:
            batch = batch_objs[b_name]
            StudyMaterial.objects.get_or_create(
                batch=batch,
                title=f"{batch.subject} Complete Notes & Formula Sheet",
                defaults={"file": "materials/sample_notes.pdf"}
            )

        # 7. Unread Notifications for Student
        notifs = [
            ("🔴 LIVE NOW", "Chemistry — Organic Reactions is live now on Zoom! Tap to join."),
            ("📅 Upcoming Class", "Mathematics — Calculus Basics starts today at 4:00 PM."),
            ("📁 New Material", "New study materials added to Organic Chemistry Mastery.")
        ]
        for title, msg in notifs:
            Notification.objects.get_or_create(
                user=student_user,
                title=title,
                message=msg,
                defaults={"is_read": False}
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded all teacher dummy data & student dashboard elements!"))
