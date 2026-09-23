from django.core.management.base import BaseCommand
from django.utils import timezone
from study.models import (
    User, StudentProfile, TeacherProfile, TeacherVerification,
    Batch, BatchAnnouncement, Enrollment, ClassContent, Attendance,
    StudyMaterial, Bookmark, ConnectionRequest, ContactAccess,
    Conversation, Message, Notification, Review
)

class Command(BaseCommand):
    help = "Seed demo data for TutorOn India platform"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding TutorOn India demo data..."))

        # 1. Admin
        admin, created = User.objects.get_or_create(
            email="admin@tutoron.in",
            defaults={
                "first_name": "TutorOn",
                "last_name": "Admin",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
                "phone_number": "+919876500000"
            }
        )
        if created:
            admin.set_password("Admin@12345")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created Admin: admin@tutoron.in (Admin@12345)"))

        # 2. Teachers
        teachers_data = [
            {
                "email": "rajesh.sharma@tutoron.in",
                "first_name": "Rajesh",
                "last_name": "Sharma",
                "phone_number": "+919876511111",
                "display_name": "Prof. Rajesh Sharma (IIT Delhi Alum)",
                "qualification": "M.Tech IIT Delhi, B.Tech IIT Roorkee",
                "experience_years": 12.5,
                "subjects": ["Physics", "Mathematics"],
                "teaching_languages": ["English", "Hindi"],
                "exam_expertise": ["IIT-JEE Main", "IIT-JEE Advanced", "KVPY"],
                "hourly_rate": 800.00,
                "verification_status": TeacherProfile.VerificationStatus.VERIFIED,
                "average_rating": 4.9,
                "total_reviews": 18,
                "total_students": 140,
                "is_featured": True,
                "bio": "Experienced IIT-JEE Physics mentor with 12+ years of track record producing Top 100 AIR ranks."
            },
            {
                "email": "ananya.verma@tutoron.in",
                "first_name": "Ananya",
                "last_name": "Verma",
                "phone_number": "+919876522222",
                "display_name": "Dr. Ananya Verma",
                "qualification": "Ph.D. in Organic Chemistry, AIIMS Research Fellow",
                "experience_years": 8.0,
                "subjects": ["Chemistry", "Biology"],
                "teaching_languages": ["English", "Hindi", "Bengali"],
                "exam_expertise": ["NEET", "AIIMS", "CBSE 12th"],
                "hourly_rate": 650.00,
                "verification_status": TeacherProfile.VerificationStatus.VERIFIED,
                "average_rating": 4.8,
                "total_reviews": 12,
                "total_students": 95,
                "is_featured": True,
                "bio": "Simplifying complex Organic Chemistry mechanisms for medical aspirants across India."
            },
            {
                "email": "amit.patel@tutoron.in",
                "first_name": "Amit",
                "last_name": "Patel",
                "phone_number": "+919876533333",
                "display_name": "Amit Patel",
                "qualification": "M.A. English Literature",
                "experience_years": 4.0,
                "subjects": ["English", "Social Science"],
                "teaching_languages": ["English", "Gujarati", "Hindi"],
                "exam_expertise": ["CBSE 10th", "ICSE"],
                "hourly_rate": 400.00,
                "verification_status": TeacherProfile.VerificationStatus.PENDING_VERIFICATION,
                "average_rating": 0.0,
                "total_reviews": 0,
                "total_students": 0,
                "is_featured": False,
                "bio": "Passionate language educator focusing on communicative fluency and board exam excellence."
            }
        ]

        created_teachers = []
        for tdata in teachers_data:
            user, created = User.objects.get_or_create(
                email=tdata["email"],
                defaults={
                    "first_name": tdata["first_name"],
                    "last_name": tdata["last_name"],
                    "phone_number": tdata["phone_number"],
                    "role": User.Role.TEACHER,
                    "is_verified": True
                }
            )
            if created:
                user.set_password("Teacher@12345")
                user.save()

            profile, _ = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    "display_name": tdata["display_name"],
                    "qualification": tdata["qualification"],
                    "experience_years": tdata["experience_years"],
                    "subjects": tdata["subjects"],
                    "teaching_languages": tdata["teaching_languages"],
                    "exam_expertise": tdata["exam_expertise"],
                    "hourly_rate": tdata["hourly_rate"],
                    "verification_status": tdata["verification_status"],
                    "average_rating": tdata["average_rating"],
                    "total_reviews": tdata["total_reviews"],
                    "total_students": tdata["total_students"],
                    "is_featured": tdata["is_featured"],
                    "bio": tdata["bio"]
                }
            )
            created_teachers.append(profile)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_teachers)} teachers."))

        # 3. Students
        students_data = [
            ("aarav.kumar@student.in", "Aarav", "Kumar", "+919811100001", "Class 12", "Delhi Public School", "New Delhi", "Delhi"),
            ("priya.singh@student.in", "Priya", "Singh", "+919811100002", "Class 12", "Kendriya Vidyalaya", "Patna", "Bihar"),
            ("rohit.sharma@student.in", "Rohit", "Sharma", "+919811100003", "Class 11", "DAV Model School", "Varanasi", "Uttar Pradesh"),
            ("sneha.gupta@student.in", "Sneha", "Gupta", "+919811100004", "Class 10", "St. Xavier's School", "Ranchi", "Jharkhand"),
            ("vikram.mehta@student.in", "Vikram", "Mehta", "+919811100005", "Class 12", "National High School", "Jaipur", "Rajasthan"),
            ("pooja.das@student.in", "Pooja", "Das", "+919811100006", "Class 11", "Salt Lake School", "Kolkata", "West Bengal")
        ]

        created_students = []
        for semail, fname, lname, phone, ed_level, school, city, state in students_data:
            user, created = User.objects.get_or_create(
                email=semail,
                defaults={
                    "first_name": fname,
                    "last_name": lname,
                    "phone_number": phone,
                    "role": User.Role.STUDENT,
                    "is_verified": True
                }
            )
            if created:
                user.set_password("Student@12345")
                user.save()

            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "education_level": ed_level,
                    "school_name": school,
                    "city": city,
                    "state": state,
                    "preferred_language": "Hindi / English",
                    "subjects_of_interest": ["Physics", "Mathematics", "Chemistry"]
                }
            )
            created_students.append(profile)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_students)} students."))

        # 4. Batches
        t_rajesh = created_teachers[0]
        t_ananya = created_teachers[1]

        b1, _ = Batch.objects.get_or_create(
            title="Target JEE Advanced 2027: Master Class in Physics",
            defaults={
                "teacher": t_rajesh,
                "description": "Comprehensive course covering Mechanics, Electrodynamics, Optics, and Modern Physics for JEE Advanced aspirants.",
                "subject": "Physics",
                "grade_level": "Class 11 & 12",
                "language": "Hinglish",
                "capacity": 60,
                "price": 2999.00,
                "is_free": False,
                "status": Batch.Status.PUBLISHED,
                "start_date": timezone.now().date(),
            }
        )

        b2, _ = Batch.objects.get_or_create(
            title="NEET 2026: Comprehensive Organic Chemistry",
            defaults={
                "teacher": t_ananya,
                "description": "Master reaction mechanisms, named reactions, and NCERT-based question patterns for full marks in Chemistry.",
                "subject": "Chemistry",
                "grade_level": "Class 12 & Droppers",
                "language": "English",
                "capacity": 45,
                "price": 1999.00,
                "is_free": False,
                "status": Batch.Status.PUBLISHED,
                "start_date": timezone.now().date(),
            }
        )

        b3, _ = Batch.objects.get_or_create(
            title="Foundation Mathematics for Class 10 CBSE",
            defaults={
                "teacher": t_rajesh,
                "description": "Free open bridge course covering Algebra, Geometry, and Trigonometry fundamentals.",
                "subject": "Mathematics",
                "grade_level": "Class 10",
                "language": "Hindi",
                "capacity": 100,
                "price": 0.00,
                "is_free": True,
                "status": Batch.Status.PUBLISHED,
                "start_date": timezone.now().date(),
            }
        )
        self.stdout.write(self.style.SUCCESS("Seeded 3 Batches."))

        # 5. Classes (YouTube, Zoom, Google Meet)
        c1, _ = ClassContent.objects.get_or_create(
            batch=b1,
            title="Session 01: Kinematics & Relative Motion in 2D",
            defaults={
                "teacher": t_rajesh,
                "description": "Understanding projectile trajectories and river-boat problems with problem solving.",
                "class_type": ClassContent.ClassType.ZOOM,
                "external_url": "https://zoom.us/j/98765432101",
                "scheduled_date": timezone.now() + timezone.timedelta(days=1),
                "duration": 90,
                "order": 1,
                "is_published": True
            }
        )

        c2, _ = ClassContent.objects.get_or_create(
            batch=b1,
            title="Session 02: Newton's Laws & Friction Concepts",
            defaults={
                "teacher": t_rajesh,
                "description": "Constraint equations and multi-block systems with friction.",
                "class_type": ClassContent.ClassType.GOOGLE_MEET,
                "external_url": "https://meet.google.com/abc-defg-hij",
                "scheduled_date": timezone.now() + timezone.timedelta(days=3),
                "duration": 90,
                "order": 2,
                "is_published": True
            }
        )

        c3, _ = ClassContent.objects.get_or_create(
            batch=b2,
            title="Organic Chemistry Module 1: Electrophilic Aromatic Substitution",
            defaults={
                "teacher": t_ananya,
                "description": "Watch lecture recording on Benzene reactions and activating/deactivating substituents.",
                "class_type": ClassContent.ClassType.YOUTUBE,
                "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "scheduled_date": timezone.now() + timezone.timedelta(days=2),
                "duration": 75,
                "order": 1,
                "is_published": True
            }
        )
        self.stdout.write(self.style.SUCCESS("Seeded 3 Classes (Zoom, Google Meet, YouTube)."))

        # 6. Enrollments
        s_aarav = created_students[0]
        s_priya = created_students[1]
        s_rohit = created_students[2]

        e1, _ = Enrollment.objects.get_or_create(
            student=s_aarav,
            batch=b1,
            defaults={"status": Enrollment.Status.ACTIVE, "payment_status": Enrollment.PaymentStatus.PAID, "approved_at": timezone.now()}
        )
        e2, _ = Enrollment.objects.get_or_create(
            student=s_priya,
            batch=b1,
            defaults={"status": Enrollment.Status.ACTIVE, "payment_status": Enrollment.PaymentStatus.PAID, "approved_at": timezone.now()}
        )
        e3, _ = Enrollment.objects.get_or_create(
            student=s_rohit,
            batch=b2,
            defaults={"status": Enrollment.Status.ACTIVE, "payment_status": Enrollment.PaymentStatus.PAID, "approved_at": timezone.now()}
        )
        self.stdout.write(self.style.SUCCESS("Seeded Enrollments."))

        # 7. Reviews
        Review.objects.get_or_create(
            student=s_aarav,
            batch=b1,
            defaults={
                "teacher": t_rajesh,
                "rating": 5,
                "teaching_quality": 5,
                "doubt_solving": 5,
                "punctuality": 5,
                "notes_quality": 5,
                "comment": "Sir's problem-solving methods for mechanics are unmatched! Best JEE teacher on the platform.",
                "status": Review.Status.PUBLISHED
            }
        )

        Review.objects.get_or_create(
            student=s_rohit,
            batch=b2,
            defaults={
                "teacher": t_ananya,
                "rating": 5,
                "teaching_quality": 5,
                "doubt_solving": 4,
                "punctuality": 5,
                "notes_quality": 5,
                "comment": "Mam explains mechanisms with such crystal clarity. Highly recommended for NEET aspirants.",
                "status": Review.Status.PUBLISHED
            }
        )
        self.stdout.write(self.style.SUCCESS("Seeded Reviews."))

        # 8. Connection Request & Unlocked Contact
        conn, created = ConnectionRequest.objects.get_or_create(
            student=s_aarav,
            teacher=t_rajesh,
            defaults={
                "requested_by": s_aarav.user,
                "message": "Hello Sir, I have joined your JEE batch and would like to ask questions regarding study schedule.",
                "status": ConnectionRequest.Status.ADMIN_APPROVED,
                "student_approved": True,
                "admin_approved": True,
                "contact_unlocked": True,
                "approved_at": timezone.now()
            }
        )
        if created:
            ContactAccess.objects.create(
                connection=conn,
                student=s_aarav,
                teacher=t_rajesh,
                status=ContactAccess.Status.APPROVED,
                approved_at=timezone.now(),
                approved_by=admin,
                reason="Admin verified connection request between student and teacher"
            )
            self.stdout.write(self.style.SUCCESS("Seeded ConnectionRequest with Unlocked ContactAccess."))

        self.stdout.write(self.style.SUCCESS("TutorOn India demo data seeded successfully!"))
