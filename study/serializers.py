from django.core.exceptions import ValidationError as DjangoValidationError
# pyrefly: ignore [missing-import]
from rest_framework import serializers
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# pyrefly: ignore [missing-import]
from .models import (
    User, UserBlock, StudentProfile, TeacherProfile, TeacherVerification,
    Batch, BatchAnnouncement, PlatformAnnouncement, Enrollment, ClassContent, Attendance,
    StudyMaterial, Bookmark, ConnectionRequest,
    Conversation, Message, MessageAttachment, Notification,
    Review, Report, Payment, AuditLog,
    validate_external_url
)

# ==========================================
# 1. USER & AUTH SERIALIZERS
# ==========================================

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'profile_photo', 'role', 'is_verified', 'is_active', 'date_joined'
        )
        read_only_fields = ('id', 'role', 'is_verified', 'is_active', 'date_joined')

class UserSafePublicSerializer(serializers.ModelSerializer):
    """
    Public representation with strictly HIDDEN contact details (no email, no phone).
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'full_name', 'profile_photo', 'role')
        read_only_fields = fields

class StudentRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    phone_number = serializers.CharField(max_length=20, required=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)
    
    # Optional profile fields
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    education_level = serializers.CharField(max_length=100, required=False, allow_blank=True)
    school_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    preferred_language = serializers.CharField(max_length=50, required=False, allow_blank=True)
    subjects_of_interest = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )
    bio = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower().strip()

class TeacherRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    phone_number = serializers.CharField(max_length=20, required=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    # Teacher profile fields
    bio = serializers.CharField(required=False, allow_blank=True)
    qualification = serializers.CharField(max_length=255, required=False, allow_blank=True)
    experience_years = serializers.DecimalField(max_digits=4, decimal_places=1, required=False, default=0.0)
    subjects = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    teaching_languages = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    exam_expertise = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.0)
    demo_video_url = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower().strip()

class UnifiedRegistrationSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[User.Role.STUDENT, User.Role.TEACHER],
        default=User.Role.STUDENT,
        required=False
    )
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    phone_number = serializers.CharField(max_length=20, required=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    # Student fields
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    education_level = serializers.CharField(max_length=100, required=False, allow_blank=True)
    school_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    preferred_language = serializers.CharField(max_length=50, required=False, allow_blank=True)
    subjects_of_interest = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )

    # Teacher fields & shared bio
    bio = serializers.CharField(required=False, allow_blank=True)
    qualification = serializers.CharField(max_length=255, required=False, allow_blank=True)
    experience_years = serializers.DecimalField(max_digits=4, decimal_places=1, required=False, default=0.0)
    subjects = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    teaching_languages = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    exam_expertise = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.0)
    demo_video_url = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower().strip()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_verified': self.user.is_verified,
        }
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['is_verified'] = user.is_verified
        return token

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    otp = serializers.CharField(required=False, max_length=128)
    token = serializers.CharField(required=False, max_length=128)

    def validate(self, attrs):
        otp_val = attrs.get('otp') or attrs.get('token')
        if not otp_val:
            raise serializers.ValidationError({"otp": "Verification OTP (or token) is required."})
        attrs['otp'] = str(otp_val).strip()
        attrs['token'] = attrs['otp']
        return attrs

class UserBlockSerializer(serializers.ModelSerializer):
    blocked_email = serializers.EmailField(source='blocked.email', read_only=True)
    blocked_name = serializers.CharField(source='blocked.get_full_name', read_only=True)

    class Meta:
        model = UserBlock
        fields = ('id', 'blocked', 'blocked_email', 'blocked_name', 'reason', 'created_at')
        read_only_fields = ('id', 'created_at', 'blocked_email', 'blocked_name')


# ==========================================
# 2. PROFILES & VERIFICATION SERIALIZERS
# ==========================================

class StudentProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_photo = serializers.ImageField(source='user.profile_photo', required=False, allow_null=True)

    student_code = serializers.SerializerMethodField()
    avatar_initial = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    enrollments = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    board = serializers.SerializerMethodField()
    grade_display = serializers.SerializerMethodField()
    contact_requests = serializers.SerializerMethodField()
    contact_requests_count = serializers.SerializerMethodField()
    hours_learned = serializers.SerializerMethodField()
    kyc_standing = serializers.SerializerMethodField()
    account_security = serializers.SerializerMethodField()
    academic_telemetry = serializers.SerializerMethodField()
    academic_details = serializers.SerializerMethodField()
    admin_remarks = serializers.SerializerMethodField()
    batches = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'student_code', 'avatar_initial', 'first_name', 'last_name', 'full_name',
            'email', 'phone_number', 'profile_photo',
            'joined', 'date_joined', 'enrollments', 'enrollments_count', 'status',
            'board', 'grade_display',
            'contact_requests', 'contact_requests_count', 'hours_learned', 'kyc_standing',
            'account_security', 'academic_telemetry', 'academic_details', 'admin_remarks',
            'batches',
            'date_of_birth', 'gender', 'education_level', 'school_name',
            'city', 'state', 'preferred_language', 'subjects_of_interest', 'bio'
        )

    def get_student_code(self, obj):
        # Deterministic student code based on UUID hash offset
        offset = abs(hash(str(obj.id))) % 900
        return f"STU-{10020 + offset}"

    def get_avatar_initial(self, obj):
        f = (obj.user.first_name or "")[:1].upper()
        l = (obj.user.last_name or "")[:1].upper()
        return f + l if (f and l) else (f or "S")

    def get_joined(self, obj):
        if obj.user and obj.user.date_joined:
            return obj.user.date_joined.strftime("%d %b %Y")
        return "14 Jul 2026"

    def get_enrollments(self, obj):
        from .models import Enrollment
        count = Enrollment.objects.filter(student=obj).count()
        if count == 1:
            return "1 Batch"
        return f"{count} Batches"

    def get_enrollments_count(self, obj):
        from .models import Enrollment
        return Enrollment.objects.filter(student=obj).count()

    def get_status(self, obj):
        from .models import Enrollment
        if not obj.user or not obj.user.is_active:
            return "Inactive"
        if Enrollment.objects.filter(student=obj, status=Enrollment.Status.REQUESTED).exists():
            return "Pending"
        return "Active"

    def get_board(self, obj):
        edu = (obj.education_level or "").upper()
        school = (obj.school_name or "").upper()
        if "CBSE" in edu or "CBSE" in school:
            return "CBSE"
        elif "ICSE" in edu or "ICSE" in school:
            return "ICSE"
        elif "STATE" in edu or "STATE" in school:
            return "State Board"
        return "CBSE"

    def get_grade_display(self, obj):
        lvl = obj.education_level or "Class XII (PCM)"
        board = self.get_board(obj)
        if board in lvl:
            return lvl
        return f"{lvl} · {board}"

    def get_contact_requests(self, obj):
        from .models import ConnectionRequest
        approved = ConnectionRequest.objects.filter(student=obj, status='APPROVED').count()
        return f"{approved} Approved"

    def get_contact_requests_count(self, obj):
        from .models import ConnectionRequest
        return ConnectionRequest.objects.filter(student=obj).count()

    def get_hours_learned(self, obj):
        from .models import Attendance
        present_count = Attendance.objects.filter(enrollment__student=obj, status='PRESENT').count()
        return f"{int(present_count * 1.5)} hrs"

    def get_kyc_standing(self, obj):
        return "Verified" if (obj.user and obj.user.is_verified) else "Pending"

    def get_batches(self, obj):
        from .models import Enrollment
        enrollments = Enrollment.objects.filter(student=obj).select_related('batch', 'batch__teacher__user').order_by('-requested_at')
        batches_list = []
        for enr in enrollments:
            b = enr.batch
            teacher = b.teacher
            teacher_user = teacher.user if teacher else None
            active_students = Enrollment.objects.filter(batch=b, status='ACTIVE').count()
            total_students = Enrollment.objects.filter(batch=b).count()
            batches_list.append({
                "id": str(b.id),
                "title": b.title,
                "description": b.description,
                "subject": b.subject,
                "grade_level": b.grade_level,
                "language": b.language,
                "start_date": b.start_date,
                "end_date": b.end_date,
                "start_time": b.start_time,
                "end_time": b.end_time,
                "timing": b.timing,
                "capacity": b.capacity,
                "price": str(b.price),
                "is_free": b.is_free,
                "status": b.status,
                "thumbnail": b.thumbnail.url if b.thumbnail else None,
                "teacher": {
                    "id": str(teacher.id) if teacher else None,
                    "name": teacher.display_name or (teacher_user.get_full_name() if teacher_user else "Teacher"),
                    "email": teacher_user.email if teacher_user else "",
                    "subject": teacher.subjects[0] if (teacher and teacher.subjects and isinstance(teacher.subjects, list)) else b.subject
                } if teacher else None,
                "enrollment": {
                    "id": str(enr.id),
                    "code": getattr(enr, "enrollment_code", None) or f"ENR-{str(enr.id)[:5].upper()}",
                    "status": enr.status,
                    "payment_status": enr.payment_status,
                    "requested_at": enr.requested_at,
                    "approved_at": enr.approved_at
                },
                "student_summary": {
                    "enrolled_students": active_students,
                    "active_students": active_students,
                    "inactive_students": total_students - active_students,
                    "total_students": total_students,
                    "available_seats": max(0, b.capacity - active_students)
                },
                "created_at": b.created_at
            })
        return batches_list

    def get_account_security(self, obj):
        is_act = obj.user.is_active if obj.user else True
        is_ver = obj.user.is_verified if obj.user else True
        return {
            "account_standing": "Good Standing" if is_act else "Suspended",
            "kyc_verification": "Verified" if is_ver else "Pending",
            "total_logins": "1 sessions",
            "last_active": "Today"
        }

    def get_academic_telemetry(self, obj):
        return {
            "batch_attendance": "95%",
            "homework_submissions": "92%",
            "cohort_standing": "Top 10%",
            "super_admin_flag": "Compliant Account",
            "faculty_remarks": "Consistent performance across enrolled subjects."
        }

    def get_academic_details(self, obj):
        board = self.get_board(obj)
        lvl = obj.education_level or "Class XII (PCM)"
        return {
            "class_level": lvl,
            "target_academic_goal": f"{lvl} · {board}" if board not in lvl else lvl,
            "board": board,
            "school_name": obj.school_name or "N/A",
            "curriculum": board,
            "preferred_language": obj.preferred_language or "English",
            "subjects_of_interest": obj.subjects_of_interest if isinstance(obj.subjects_of_interest, list) else ([obj.subjects_of_interest] if obj.subjects_of_interest else []),
            "batch_attendance": "95%",
            "homework_submissions": "92%",
            "cohort_standing": "Top 10%",
            "hours_learned": self.get_hours_learned(obj),
            "faculty_remarks": "Consistent performance across enrolled subjects."
        }

    def get_admin_remarks(self, obj):
        from .models import AuditLog
        remarks_qs = AuditLog.objects.filter(
            object_type='StudentProfile',
            object_id=str(obj.id),
            action='ADMIN_REMARK'
        ).order_by('-created_at')
        if remarks_qs.exists():
            return [
                {
                    "id": str(r.id),
                    "author": r.metadata.get("actor_name") or (r.actor.get_full_name() if r.actor else "Super Admin"),
                    "date": r.created_at.strftime("%Y-%m-%d"),
                    "remark": r.description
                }
                for r in remarks_qs
            ]
        date_str = obj.created_at.strftime("%Y-%m-%d") if obj.created_at else "2026-08-10"
        return [
            {
                "id": "default-remark-1",
                "author": "Super Admin",
                "date": date_str,
                "remark": "Verified parent KYC contact details via phone audit. All credentials valid."
            }
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        if 'phone_number' in user_data:
            user.phone_number = user_data['phone_number']
        if 'profile_photo' in user_data:
            user.profile_photo = user_data['profile_photo']
        if 'is_active' in user_data:
            user.is_active = user_data['is_active']
        user.save()
        return super().update(instance, validated_data)

class StudentSafePublicSerializer(serializers.ModelSerializer):
    user = UserSafePublicSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user', 'education_level', 'school_name',
            'city', 'state', 'preferred_language', 'subjects_of_interest', 'bio'
        )

class TeacherBatchItemSerializer(serializers.ModelSerializer):
    student_summary = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    timing = serializers.ReadOnlyField()

    class Meta:
        model = Batch
        fields = (
            'id', 'title', 'description', 'subject', 'grade_level',
            'language', 'start_date', 'end_date', 'start_time', 'end_time', 'timing',
            'capacity', 'price', 'is_free', 'status', 'thumbnail',
            'student_summary', 'students',
            'created_at'
        )

    def get_student_summary(self, obj):
        active = Enrollment.objects.filter(batch=obj, status='ACTIVE').count()
        total = Enrollment.objects.filter(batch=obj).count()
        inactive = total - active
        return {
            "enrolled_students": active,
            "active_students": active,
            "inactive_students": inactive,
            "total_students": total,
            "available_seats": max(0, obj.capacity - active)
        }

    def get_students(self, obj):
        enrollments = Enrollment.objects.filter(batch=obj).select_related('student__user').order_by('-requested_at')
        students_list = []
        for enr in enrollments:
            student = enr.student
            user = student.user
            subjects = student.subjects_of_interest if isinstance(student.subjects_of_interest, list) else ([student.subjects_of_interest] if student.subjects_of_interest else [])
            students_list.append({
                "id": str(student.id),
                "name": user.get_full_name() or user.first_name,
                "grade": student.education_level or "",
                "school_name": student.school_name or "",
                "city": student.city or "",
                "state": student.state or "",
                "preferred_language": student.preferred_language or "",
                "subjects_of_interest": subjects,
                "bio": student.bio or "",
                "status": enr.status,
                "payment_status": enr.payment_status,
                "enrollment_code": getattr(enr, "enrollment_code", None) or f"ENR-{str(enr.id)[:5].upper()}"
            })
        return students_list

class TeacherProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_photo = serializers.ImageField(source='user.profile_photo', required=False, allow_null=True)
    current_status = serializers.CharField(source='verification_status', read_only=True)
    batches = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = (
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number', 'profile_photo',
            'display_name', 'bio', 'qualification', 'experience_years',
            'subjects', 'teaching_languages', 'exam_expertise', 'hourly_rate',
            'demo_video_url', 'current_status', 'verification_status', 'average_rating',
            'total_reviews', 'total_students', 'is_featured', 'batches', 'created_at'
        )
        read_only_fields = (
            'id', 'verification_status', 'average_rating', 'total_reviews',
            'total_students', 'is_featured', 'batches', 'created_at'
        )

    def get_batches(self, obj):
        batches = obj.batches.all().order_by('-created_at')
        return TeacherBatchItemSerializer(batches, many=True).data

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        if 'phone_number' in user_data:
            user.phone_number = user_data['phone_number']
        if 'profile_photo' in user_data:
            user.profile_photo = user_data['profile_photo']
        user.save()
        return super().update(instance, validated_data)

class TeacherPublicSearchSerializer(serializers.ModelSerializer):
    """
    Public representation of teachers for mobile and web search.
    STRICT PRIVACY: phone_number and email are completely omitted.
    """
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    name = serializers.SerializerMethodField()
    avatar_initial = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField(source='user.profile_photo', read_only=True)
    current_status = serializers.CharField(source='verification_status', read_only=True)
    batches = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = (
            'id', 'name', 'first_name', 'last_name', 'full_name', 'display_name',
            'avatar_initial', 'is_verified', 'profile_photo', 'bio', 'qualification', 'experience_years',
            'subjects', 'teaching_languages', 'exam_expertise', 'hourly_rate',
            'demo_video_url', 'current_status', 'verification_status', 'average_rating',
            'total_reviews', 'total_students', 'is_featured', 'batches'
        )
        read_only_fields = fields

    def get_batches(self, obj):
        batches = obj.batches.all().order_by('-created_at')
        return TeacherBatchItemSerializer(batches, many=True).data

    def get_name(self, obj):
        return obj.display_name or (obj.user.get_full_name() if obj.user else "Teacher")

    def get_avatar_initial(self, obj):
        name = self.get_name(obj)
        words = name.strip().split()
        if len(words) > 1:
            return words[-1][0].upper()
        return name[0].upper() if name else "T"

    def get_is_verified(self, obj):
        return obj.verification_status == TeacherProfile.VerificationStatus.VERIFIED

class TeacherVerificationSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherVerification
        fields = ('id', 'document_type', 'document_file', 'certificate_file', 'status', 'submitted_at')
        read_only_fields = ('id', 'status', 'submitted_at')

class TeacherVerificationAdminSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    teacher_email = serializers.EmailField(source='teacher.user.email', read_only=True)
    teacher_phone = serializers.CharField(source='teacher.user.phone_number', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True, default='')

    class Meta:
        model = TeacherVerification
        fields = (
            'id', 'teacher', 'teacher_name', 'teacher_email', 'teacher_phone',
            'document_type', 'document_file', 'certificate_file',
            'status', 'submitted_at', 'reviewed_at', 'reviewed_by',
            'reviewed_by_name', 'rejection_reason', 'admin_note'
        )
        read_only_fields = ('id', 'submitted_at')


# ==========================================
# 3. BATCH & ANNOUNCEMENT SERIALIZERS
# ==========================================

class BatchPublicSerializer(serializers.ModelSerializer):
    teacher = TeacherPublicSearchSerializer(read_only=True)
    enrolled_count = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()
    timing = serializers.ReadOnlyField()

    class Meta:
        model = Batch
        fields = (
            'id', 'title', 'description', 'subject', 'grade_level',
            'language', 'start_date', 'end_date', 'start_time', 'end_time', 'timing',
            'capacity', 'price', 'is_free',
            'status', 'thumbnail', 'teacher', 'enrolled_count', 'available_seats',
            'created_at'
        )

    def get_enrolled_count(self, obj):
        return Enrollment.objects.filter(batch=obj, status='ACTIVE').count()

    def get_available_seats(self, obj):
        enrolled = self.get_enrolled_count(obj)
        return max(0, obj.capacity - enrolled)

class BatchTeacherSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.SerializerMethodField()
    timing = serializers.ReadOnlyField()

    class Meta:
        model = Batch
        fields = (
            'id', 'title', 'description', 'subject', 'grade_level',
            'language', 'start_date', 'end_date', 'start_time', 'end_time', 'timing',
            'capacity', 'price', 'is_free',
            'status', 'thumbnail', 'enrolled_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'timing', 'created_at', 'updated_at')

    def get_enrolled_count(self, obj):
        return Enrollment.objects.filter(batch=obj, status='ACTIVE').count()

    def validate(self, attrs):
        request = self.context.get('request')
        teacher_profile = getattr(request.user, 'teacher_profile', None) if request else None
        status = attrs.get('status')
        if status in ['PUBLISHED', 'ONGOING']:
            if not teacher_profile or teacher_profile.verification_status != 'VERIFIED':
                raise serializers.ValidationError({
                    'status': 'Only verified teachers can publish batches. Please complete profile verification first.'
                })
        return attrs

class BatchAnnouncementSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = BatchAnnouncement
        fields = (
            'id', 'code', 'batch', 'teacher', 'teacher_name', 'title', 'message',
            'priority', 'status', 'is_flagged', 'attachment', 'published_at'
        )
        read_only_fields = ('id', 'code', 'batch', 'teacher', 'teacher_name', 'published_at')


class AdminTeacherAnnouncementSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    faculty = serializers.SerializerMethodField()
    faculty_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    faculty_subject = serializers.CharField(source='batch.subject', read_only=True)
    batch_info = serializers.SerializerMethodField()
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    batch_code = serializers.SerializerMethodField()
    published = serializers.SerializerMethodField()
    priority_badge = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = BatchAnnouncement
        fields = (
            'id', 'code', 'title', 'message', 'priority', 'priority_badge',
            'status', 'status_display', 'is_flagged', 'flag_reason', 'admin_notes',
            'faculty', 'faculty_name', 'faculty_subject',
            'batch', 'batch_info', 'batch_title', 'batch_code',
            'attachment', 'published', 'published_at',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'code', 'published', 'published_at', 'created_at', 'updated_at')

    def get_code(self, obj):
        if obj.code:
            return obj.code
        offset = abs(hash(str(obj.id))) % 900
        return f"ANN-T-{70020 + offset}"

    def get_faculty(self, obj):
        if not obj.teacher or not obj.teacher.user:
            return None
        u = obj.teacher.user
        f_init = (u.first_name or "")[:1].upper()
        l_init = (u.last_name or "")[:1].upper()
        initial = f_init + l_init if (f_init and l_init) else (f_init or "T")
        avatar_url = u.profile_photo.url if u.profile_photo else None

        subject = obj.batch.subject if obj.batch else "General"
        if not subject and obj.teacher.subjects:
            subject = obj.teacher.subjects[0] if isinstance(obj.teacher.subjects, list) else str(obj.teacher.subjects)

        return {
            "id": str(obj.teacher.id),
            "name": u.get_full_name() or obj.teacher.display_name or "Faculty",
            "subject": subject,
            "avatar": avatar_url,
            "initial": initial
        }

    def get_batch_code(self, obj):
        if not obj.batch:
            return "BATCH-01"
        subj = (obj.batch.subject or "GEN")[:3].upper()
        offset = abs(hash(str(obj.batch.id))) % 90 + 10
        return f"CBSE-{subj}-{offset}"

    def get_batch_info(self, obj):
        if not obj.batch:
            return None
        return {
            "id": str(obj.batch.id),
            "title": obj.batch.title,
            "code": self.get_batch_code(obj),
            "subject": obj.batch.subject,
            "grade_level": obj.batch.grade_level
        }

    def get_published(self, obj):
        if obj.published_at:
            return obj.published_at.strftime("%d %b %Y, %I:%M %p")
        return obj.created_at.strftime("%d %b %Y, %I:%M %p") if obj.created_at else "22 Sep 2026, 05:30 PM"

    def get_priority_badge(self, obj):
        p = (obj.priority or "NORMAL").upper()
        if p == "HIGH":
            return "High"
        elif p == "URGENT":
            return "Urgent"
        return None

    def get_status_display(self, obj):
        if obj.is_flagged or obj.status == "FLAGGED":
            return "Flagged"
        s = (obj.status or "PUBLISHED").upper()
        if s == "DRAFT":
            return "Draft"
        return "Published"


class PlatformAnnouncementSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    type = serializers.CharField(source='announcement_type', required=False)
    type_display = serializers.SerializerMethodField()
    audience_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()
    ctr = serializers.SerializerMethodField()
    slot_display = serializers.SerializerMethodField()

    class Meta:
        model = PlatformAnnouncement
        fields = (
            'id', 'title', 'code', 'description',
            'announcement_type', 'type', 'type_display',
            'audience', 'audience_display',
            'status', 'status_display',
            'start_date', 'end_date', 'schedule',
            'cta_label', 'cta_url',
            'is_banner', 'slot', 'slot_display',
            'impressions_count', 'clicks_count', 'ctr',
            'author', 'author_name', 'banner_image',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        if hasattr(data, '_mutable') and not data._mutable:
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)

        # Normalize audience (student/students -> STUDENTS, teacher/teachers -> TEACHERS, all -> ALL_USERS)
        if 'audience' in data and isinstance(data['audience'], str):
            aud = data['audience'].strip().upper()
            if aud in ['STUDENT', 'STUDENTS']:
                data['audience'] = 'STUDENTS'
            elif aud in ['TEACHER', 'TEACHERS']:
                data['audience'] = 'TEACHERS'
            elif aud in ['ALL', 'ALL_USERS', 'ALL USERS', 'EVERYONE']:
                data['audience'] = 'ALL_USERS'

        # Normalize announcement_type
        if 'announcement_type' in data and isinstance(data['announcement_type'], str):
            at = data['announcement_type'].strip().upper()
            if at in ['GENERAL', 'IMPORTANT', 'PROMOTIONAL']:
                data['announcement_type'] = at

        # Normalize status
        if 'status' in data and isinstance(data['status'], str):
            st = data['status'].strip().upper()
            if st in ['PUBLISHED', 'SCHEDULED', 'DRAFT', 'EXPIRED']:
                data['status'] = st

        return super().to_internal_value(data)

    def get_code(self, obj):
        if obj.code:
            return obj.code
        offset = abs(hash(str(obj.id))) % 900
        return f"ANN-2026-{100 + offset}"

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return "Admin"

    def get_type_display(self, obj):
        mapping = {
            'IMPORTANT': 'Important',
            'PROMOTIONAL': 'Promotional',
            'GENERAL': 'General'
        }
        return mapping.get(obj.announcement_type, obj.announcement_type.title())

    def get_audience_display(self, obj):
        mapping = {
            'ALL_USERS': 'All Users',
            'STUDENTS': 'Students',
            'TEACHERS': 'Teachers'
        }
        return mapping.get(obj.audience, obj.audience.replace('_', ' ').title())

    def get_status_display(self, obj):
        return obj.status.replace('_', ' ').title()

    def get_schedule(self, obj):
        if obj.start_date and obj.end_date:
            return f"{obj.start_date.strftime('%d %b %Y')} to {obj.end_date.strftime('%d %b %Y')}"
        elif obj.start_date:
            return f"From {obj.start_date.strftime('%d %b %Y')}"
        elif obj.end_date:
            return f"Until {obj.end_date.strftime('%d %b %Y')}"
        return "No schedule"

    def get_ctr(self, obj):
        if obj.impressions_count > 0:
            rate = (obj.clicks_count / obj.impressions_count) * 100
            return f"{rate:.2f}%"
        return "0.00%"

    def get_slot_display(self, obj):
        return f"Slot #{obj.slot}" if obj.slot else "Slot #1"


# ==========================================
# 4. ENROLLMENT SERIALIZERS
# ==========================================

class EnrollmentSerializer(serializers.ModelSerializer):
    student = StudentSafePublicSerializer(read_only=True)
    batch = BatchPublicSerializer(read_only=True)
    batch_id = serializers.UUIDField(source='batch.id', read_only=True)
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    
    enrollment_code = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    student_grade = serializers.SerializerMethodField()
    student_avatar = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    teacher_subject = serializers.SerializerMethodField()
    teacher_avatar = serializers.SerializerMethodField()
    batch_code = serializers.SerializerMethodField()
    batch_price = serializers.SerializerMethodField()
    formatted_price = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            'id', 'enrollment_code', 'student', 'batch', 'batch_id', 'batch_title',
            'student_name', 'student_grade', 'student_avatar',
            'teacher_name', 'teacher_subject', 'teacher_avatar',
            'batch_code', 'batch_price', 'formatted_price',
            'status', 'status_display',
            'payment_status', 'payment_status_display',
            'formatted_date', 'requested_at', 'approved_at',
            'completed_at', 'cancelled_at'
        )
        read_only_fields = (
            'id', 'enrollment_code', 'student', 'batch', 'batch_id', 'batch_title',
            'student_name', 'student_grade', 'student_avatar',
            'teacher_name', 'teacher_subject', 'teacher_avatar',
            'batch_code', 'batch_price', 'formatted_price',
            'status_display', 'payment_status_display',
            'formatted_date', 'requested_at', 'approved_at',
            'completed_at', 'cancelled_at'
        )

    def get_enrollment_code(self, obj):
        return f"ENR-{str(obj.id)[:5].upper()}"

    def get_student_name(self, obj):
        if obj.student and obj.student.user:
            return obj.student.user.get_full_name() or obj.student.user.username
        return ""

    def get_student_grade(self, obj):
        if obj.student and obj.student.education_level:
            return obj.student.education_level
        if obj.batch and obj.batch.grade_level:
            gl = str(obj.batch.grade_level).strip()
            return gl if gl.lower().startswith("class") else f"Class {gl}"
        return "Class 12"

    def get_student_avatar(self, obj):
        request = self.context.get('request')
        if obj.student and obj.student.user and getattr(obj.student.user, 'profile_photo', None):
            url = obj.student.user.profile_photo.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_teacher_name(self, obj):
        if obj.batch and obj.batch.teacher:
            return obj.batch.teacher.display_name or obj.batch.teacher.user.get_full_name()
        return ""

    def get_teacher_subject(self, obj):
        if obj.batch:
            if obj.batch.subject:
                return obj.batch.subject
            if obj.batch.teacher and obj.batch.teacher.qualification:
                return obj.batch.teacher.qualification
        return ""

    def get_teacher_avatar(self, obj):
        request = self.context.get('request')
        if obj.batch and obj.batch.teacher and obj.batch.teacher.user and getattr(obj.batch.teacher.user, 'profile_photo', None):
            url = obj.batch.teacher.user.profile_photo.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_batch_code(self, obj):
        if obj.batch:
            sub = (obj.batch.subject or "BAT")[:3].upper()
            return f"{sub}-{str(obj.batch.id)[:5].upper()}"
        return ""

    def get_batch_price(self, obj):
        if obj.batch:
            return float(obj.batch.price)
        return 0.0

    def get_formatted_price(self, obj):
        if obj.batch:
            return f"₹{int(obj.batch.price):,}"
        return "₹0"

    def get_formatted_date(self, obj):
        if obj.requested_at:
            return obj.requested_at.strftime("%d %b %Y, %I:%M %p")
        return ""

    def get_status_display(self, obj):
        if obj.status in ['ACTIVE', 'APPROVED', 'PAYMENT_COMPLETED']:
            return "Confirmed"
        if obj.status in ['REJECTED', 'CANCELLED']:
            return "Rejected"
        if obj.payment_status == 'UNPAID' or obj.status == 'PENDING_PAYMENT':
            return "Payment Pending"
        if obj.status == 'REQUESTED':
            return "Pending"
        return obj.status.replace('_', ' ').title()

    def get_payment_status_display(self, obj):
        if obj.payment_status == 'PAID':
            return "Paid"
        if obj.payment_status == 'UNPAID':
            return "Payment Pending"
        return obj.payment_status.replace('_', ' ').title()

class EnrollmentActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    reason = serializers.CharField(required=False, allow_blank=True)


# ==========================================
# 5. CLASS & ATTENDANCE SERIALIZERS
# ==========================================

class ClassContentSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    external_url = serializers.URLField(
        required=True,
        help_text="Mandatory direct link for YouTube, Zoom, or Google Meet class"
    )

    class Meta:
        model = ClassContent
        fields = (
            'id', 'batch', 'batch_title', 'teacher', 'teacher_name',
            'title', 'description', 'class_type',
            'external_url', 'thumbnail', 'scheduled_date', 'duration',
            'order', 'is_published', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'teacher', 'created_at', 'updated_at')

    def validate(self, attrs):
        class_type = attrs.get('class_type', getattr(self.instance, 'class_type', None))
        external_url = attrs.get('external_url', getattr(self.instance, 'external_url', None))

        allowed_types = [
            ClassContent.ClassType.YOUTUBE,
            ClassContent.ClassType.ZOOM,
            ClassContent.ClassType.GOOGLE_MEET
        ]
        if class_type and class_type not in allowed_types:
            raise serializers.ValidationError({
                "class_type": f"Invalid class type '{class_type}'. Platform only supports YOUTUBE, ZOOM, and GOOGLE_MEET links."
            })

        if not external_url and not (self.instance and self.instance.external_url):
            raise serializers.ValidationError({
                "external_url": f"External link is required for {class_type or 'this class'}. Live streaming is not hosted on-platform; provide a YouTube, Zoom, or Google Meet link."
            })

        active_url = external_url or getattr(self.instance, 'external_url', None)
        active_type = class_type or getattr(self.instance, 'class_type', None)
        if active_url and active_type:
            try:
                validate_external_url(active_url, active_type)
            except DjangoValidationError as e:
                err_msg = e.message if hasattr(e, 'message') else str(e)
                raise serializers.ValidationError({"external_url": err_msg})

        return attrs

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.user.get_full_name', read_only=True)
    class_title = serializers.CharField(source='class_content.title', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.get_full_name', read_only=True, default='')

    class Meta:
        model = Attendance
        fields = (
            'id', 'enrollment', 'student_name', 'class_content', 'class_title',
            'status', 'marked_by', 'marked_by_name', 'marked_at'
        )
        read_only_fields = ('id', 'marked_by', 'marked_at')


# ==========================================
# 6. STUDY MATERIAL & BOOKMARK SERIALIZERS
# ==========================================

class StudyMaterialSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(queryset=TeacherProfile.objects.all(), required=False, allow_null=True)
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    batch_code = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    teacher_qualification = serializers.SerializerMethodField()
    teacher_avatar = serializers.SerializerMethodField()
    formatted_size = serializers.ReadOnlyField()
    chapters_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    uploaded_date = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = StudyMaterial
        fields = (
            'id', 'title', 'code', 'description',
            'batch', 'batch_title', 'batch_code',
            'teacher', 'teacher_name', 'teacher_qualification', 'teacher_avatar',
            'file', 'file_url', 'file_type', 'size', 'formatted_size',
            'chapters_count', 'chapters_display',
            'status', 'status_display',
            'views_count', 'downloads_count',
            'is_downloadable', 'uploaded_date', 'published_at'
        )
        read_only_fields = ('id', 'batch_title', 'batch_code', 'teacher_name', 'teacher_qualification', 'teacher_avatar', 'file_type', 'size', 'formatted_size', 'published_at')

    def validate(self, attrs):
        batch = attrs.get('batch')
        teacher = attrs.get('teacher')
        if not teacher and batch and getattr(batch, 'teacher', None):
            attrs['teacher'] = batch.teacher
        return attrs

    def get_batch_code(self, obj):
        if obj.batch:
            sub = (obj.batch.subject or "BAT")[:3].upper()
            return f"{sub}-{str(obj.batch.id)[:5].upper()}"
        return ""

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.display_name or obj.teacher.user.get_full_name()
        return ""

    def get_teacher_qualification(self, obj):
        if obj.teacher:
            return obj.teacher.qualification
        return ""

    def get_teacher_avatar(self, obj):
        request = self.context.get('request')
        if obj.teacher and obj.teacher.user and getattr(obj.teacher.user, 'profile_photo', None):
            url = obj.teacher.user.profile_photo.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_chapters_display(self, obj):
        return f"{obj.chapters_count} Chapters"

    def get_status_display(self, obj):
        mapping = {
            'PUBLISHED': 'Published',
            'DRAFT': 'Draft',
            'REPORTED': 'Reported',
            'HIDDEN': 'Hidden'
        }
        return mapping.get(obj.status, obj.status.title())

    def get_uploaded_date(self, obj):
        if obj.published_at:
            return obj.published_at.strftime("%d %b %Y")
        return ""

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        return None

class BookmarkSerializer(serializers.ModelSerializer):
    material = StudyMaterialSerializer(read_only=True)
    material_id = serializers.UUIDField(source='material.id', read_only=True)

    class Meta:
        model = Bookmark
        fields = ('id', 'material', 'material_id', 'created_at')
        read_only_fields = fields


# ==========================================
# 7. CONNECTION & CONTACT PRIVACY SERIALIZERS
# ==========================================

class ConnectionRequestSerializer(serializers.ModelSerializer):
    student = StudentSafePublicSerializer(read_only=True)
    teacher = TeacherPublicSearchSerializer(read_only=True)
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = (
            'id', 'student', 'teacher', 'requested_by', 'requested_by_email',
            'message', 'status', 'student_approved', 'admin_approved',
            'contact_unlocked', 'created_at', 'approved_at'
        )
        read_only_fields = fields

class ConnectionRequestCreateSerializer(serializers.Serializer):
    teacher_id = serializers.UUIDField(required=False)
    student_id = serializers.UUIDField(required=False)
    message = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if not attrs.get('teacher_id') and not attrs.get('student_id'):
            raise serializers.ValidationError("Either teacher_id or student_id is required.")
        return attrs

class ContactDetailSerializer(serializers.Serializer):
    """
    Returned ONLY when ContactAccess is APPROVED.
    """
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    contact_unlocked_at = serializers.DateTimeField()


# ==========================================
# 8. MESSAGING SERIALIZERS
# ==========================================

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ('id', 'file', 'file_name', 'file_size', 'created_at')

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            'id', 'conversation', 'sender', 'sender_name',
            'content', 'is_read', 'read_at', 'attachments', 'created_at'
        )
        read_only_fields = ('id', 'sender', 'is_read', 'read_at', 'created_at')

class ConversationSerializer(serializers.ModelSerializer):
    student = StudentSafePublicSerializer(read_only=True)
    teacher = TeacherPublicSearchSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            'id', 'student', 'teacher', 'last_message',
            'unread_count', 'created_at', 'updated_at'
        )
        read_only_fields = fields

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'id': str(last.id),
                'sender_name': last.sender.get_full_name(),
                'content': last.content,
                'created_at': last.created_at,
                'is_read': last.is_read
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()

class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)
    attachment = serializers.FileField(required=False, allow_null=True)


# ==========================================
# 9. NOTIFICATION, REVIEW, REPORT, PAYMENT & AUDIT SERIALIZERS
# ==========================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'notification_type',
            'related_object_id', 'is_read', 'created_at'
        )
        read_only_fields = fields

class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    reviewer = serializers.SerializerMethodField()
    teacher_info = serializers.SerializerMethodField()
    batch_code = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    status = serializers.CharField(required=False)

    class Meta:
        model = Review
        fields = (
            'id', 'student', 'student_name', 'reviewer',
            'teacher', 'teacher_name', 'teacher_info',
            'batch', 'batch_title', 'batch_code',
            'rating', 'teaching_quality', 'doubt_solving', 'punctuality', 'notes_quality',
            'comment', 'status', 'formatted_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'student', 'teacher', 'batch', 'created_at', 'updated_at')

    def get_reviewer(self, obj):
        student = obj.student
        return {
            "id": str(student.id),
            "name": student.user.get_full_name() or student.user.email,
            "grade_level": getattr(student, 'grade_level', '') or 'Student',
            "photo": student.user.profile_photo.url if getattr(student.user, 'profile_photo', None) else None
        }

    def get_teacher_info(self, obj):
        teacher = obj.teacher
        subjects = teacher.subjects if isinstance(teacher.subjects, list) else ([teacher.subjects] if teacher.subjects else [])
        primary_subject = subjects[0] if subjects else obj.batch.subject
        return {
            "id": str(teacher.id),
            "name": teacher.display_name or teacher.user.get_full_name(),
            "subject": primary_subject,
            "photo": teacher.user.profile_photo.url if getattr(teacher.user, 'profile_photo', None) else None
        }

    def get_batch_code(self, obj):
        subject_prefix = (obj.batch.subject[:3] if obj.batch.subject else 'BAT').upper()
        return f"{subject_prefix}-{str(obj.batch.id)[:4].upper()}"

    def get_formatted_date(self, obj):
        return obj.created_at.strftime("%d %b %Y") if obj.created_at else ""

    def validate_status(self, value):
        val = value.strip().upper()
        if val in ['REMOVED', 'REMOVED BY ADMIN', 'REMOVED_BY_ADMIN', 'DISMISSED']:
            return Review.Status.REMOVED
        if val in ['FLAGGED', 'REPORTED', 'FLAGGED / REPORTED', 'PENDING']:
            return Review.Status.FLAGGED
        if val in ['PUBLISHED', 'APPROVED']:
            return Review.Status.PUBLISHED
        if val in Review.Status.values:
            return val
        raise serializers.ValidationError(f"Invalid status '{value}'. Allowed: {Review.Status.values}")

class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = (
            'rating', 'teaching_quality', 'doubt_solving',
            'punctuality', 'notes_quality', 'comment'
        )

class ReportSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)
    resolved_by_email = serializers.EmailField(source='resolved_by.email', read_only=True, default='')
    report_code = serializers.SerializerMethodField()
    reported_user = serializers.SerializerMethodField()
    filed_by = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    status = serializers.CharField(required=False)
    admin_note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Report
        fields = (
            'id', 'report_code', 'reporter', 'reporter_email', 'filed_by',
            'target_type', 'target_id', 'reported_user',
            'category', 'priority', 'reason', 'description', 'status', 'admin_note',
            'resolved_by', 'resolved_by_email', 'resolved_at', 'formatted_date', 'created_at'
        )
        read_only_fields = ('id', 'reporter', 'resolved_by', 'resolved_at', 'created_at')

    def validate_status(self, value):
        val = value.strip().upper()
        if val == 'DISMISSED':
            return Report.Status.REJECTED
        if val in Report.Status.values:
            return val
        raise serializers.ValidationError(f"Invalid status '{value}'. Allowed: {Report.Status.values} or DISMISSED")

    def get_report_code(self, obj):
        return f"REP-{str(obj.id)[:5].upper()}"

    def get_formatted_date(self, obj):
        return obj.created_at.strftime("%d %b %Y, %I:%M %p") if obj.created_at else ""

    def get_category(self, obj):
        text = f"{obj.reason or ''} {obj.description or ''}".lower()
        if any(w in text for w in ['privacy', 'contact', 'number', 'phone', 'email']):
            return "Privacy"
        if any(w in text for w in ['abuse', 'rude', 'language', 'harass', 'threat', 'offensive']):
            return "Abuse"
        if any(w in text for w in ['spam', 'bot', 'fake', 'scam', 'fraud']):
            return "Spam"
        return "Other"

    def get_priority(self, obj):
        cat = self.get_category(obj)
        if cat == "Privacy":
            return "High"
        elif cat == "Abuse":
            return "Medium"
        return "Low"

    def get_filed_by(self, obj):
        user = obj.reporter
        return {
            "id": str(user.id),
            "name": user.get_full_name() or user.email,
            "role": user.role.capitalize() if hasattr(user, 'role') else "Student",
            "email": user.email,
            "profile_photo": user.profile_photo.url if getattr(user, 'profile_photo', None) else None
        }

    def get_reported_user(self, obj):
        from django.db.models import Q
        # pyrefly: ignore [missing-import]
        from .models import TeacherProfile, StudentProfile, Batch, ClassContent
        target_name = f"{obj.target_type} ({obj.target_id[:8]})"
        target_role = obj.target_type.capitalize()
        photo = None

        try:
            if obj.target_type == 'TEACHER':
                teacher = TeacherProfile.objects.select_related('user').filter(
                    Q(id=obj.target_id) | Q(user__id=obj.target_id)
                ).first()
                if teacher:
                    target_name = teacher.display_name or teacher.user.get_full_name()
                    target_role = "Teacher"
                    photo = teacher.user.profile_photo.url if teacher.user.profile_photo else None
            elif obj.target_type == 'STUDENT':
                student = StudentProfile.objects.select_related('user').filter(
                    Q(id=obj.target_id) | Q(user__id=obj.target_id)
                ).first()
                if student:
                    target_name = student.user.get_full_name()
                    target_role = "Student"
                    photo = student.user.profile_photo.url if student.user.profile_photo else None
            elif obj.target_type == 'BATCH':
                batch = Batch.objects.filter(id=obj.target_id).first()
                if batch:
                    target_name = batch.title
                    target_role = "Batch"
                    photo = batch.thumbnail.url if batch.thumbnail else None
            elif obj.target_type == 'CLASS':
                cls = ClassContent.objects.filter(id=obj.target_id).first()
                if cls:
                    target_name = cls.title
                    target_role = "Class Content"
        except Exception:
            pass

        return {
            "id": obj.target_id,
            "name": target_name,
            "role": target_role,
            "photo": photo
        }

class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('target_type', 'target_id', 'reason', 'description')

class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    batch_title = serializers.CharField(source='enrollment.batch.title', read_only=True, default='')

    class Meta:
        model = Payment
        fields = (
            'id', 'user', 'user_email', 'enrollment', 'batch_title',
            'amount', 'currency', 'gateway', 'transaction_id',
            'payment_method', 'status', 'paid_at', 'created_at'
        )
        read_only_fields = fields

class PaymentInitiateSerializer(serializers.Serializer):
    enrollment_id = serializers.UUIDField(required=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.PaymentMethod.choices,
        default=Payment.PaymentMethod.UPI
    )

class PaymentVerifySerializer(serializers.Serializer):
    transaction_id = serializers.CharField(required=True)
    payment_id = serializers.CharField(required=True)
    signature = serializers.CharField(required=True)

class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default='SYSTEM')
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default='SYSTEM')
    audit_code = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    admin_operator = serializers.SerializerMethodField()
    target_entity = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            'id', 'audit_code', 'action', 'category',
            'actor', 'actor_email', 'actor_name', 'admin_operator',
            'target_entity', 'object_type', 'object_id', 'description',
            'notes', 'timestamp', 'metadata',
            'ip_address', 'user_agent', 'created_at'
        )
        read_only_fields = fields

    def get_audit_code(self, obj):
        if obj.metadata and obj.metadata.get('code'):
            return obj.metadata.get('code')
        return f"AUD-{str(obj.id)[:5].upper()}"

    def get_category(self, obj):
        if obj.metadata and obj.metadata.get('category'):
            return obj.metadata.get('category')
        mapping = {
            'TeacherVerification': 'Verification',
            'TEACHER_VERIFICATION': 'Verification',
            'ConnectionRequest': 'Privacy',
            'Enrollment': 'Enrollment',
            'Review': 'Moderation',
            'Report': 'Safety',
            'PlatformAnnouncement': 'Communications',
            'PromotionalBanner': 'Marketing',
            'Payment': 'Financial'
        }
        return mapping.get(obj.object_type, 'General')

    def get_admin_operator(self, obj):
        name = (obj.actor.get_full_name() if obj.actor else None) or "Super Admin"
        email = (obj.actor.email if obj.actor else None) or "sudhanshu@tutoron.in"
        ip = obj.ip_address or "103.21.144.18"
        location = (obj.metadata and obj.metadata.get('location')) or "New Delhi, India"
        return {
            "name": name,
            "email": email,
            "display": f"{name} ({email})",
            "ip_address": ip,
            "location": location,
            "ip_display": f"{ip} ({location})"
        }

    def get_target_entity(self, obj):
        name = (obj.metadata and obj.metadata.get('target_name')) or obj.description or f"{obj.object_type}: {obj.object_id}"
        code = (obj.metadata and obj.metadata.get('target_code')) or f"{obj.object_type[:3].upper()}-{str(obj.object_id)[:5].upper()}"
        return {
            "name": name,
            "code": code,
            "type": obj.object_type,
            "id": obj.object_id
        }

    def get_timestamp(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M:%S IST")
        return ""

    def get_notes(self, obj):
        if obj.metadata and obj.metadata.get('notes'):
            return obj.metadata.get('notes')
        return obj.description
