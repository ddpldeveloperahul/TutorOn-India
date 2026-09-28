from rest_framework import serializers
from django.contrib.auth import get_user_model
from app.models import (
    StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, StudentUpdate, Bookmark, Enrollment,
    Attendance, ConnectionRequest, ContactAccess, Conversation, Message,
    MessageAttachment, Notification, Review, Report, UserBlock, Payment, AuditLog
)

User = get_user_model()

# ==============================================================================
# USER & REGISTRATION SERIALIZERS
# ==============================================================================

class UserSerializer(serializers.ModelSerializer):
    """
    Standard serializer for User model.
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'full_name', 'role', 'user_type', 'is_active', 'is_verified', 'created_at']
        read_only_fields = ['id', 'is_active', 'is_verified', 'created_at']


class StudentRegistrationSerializer(serializers.Serializer):
    """
    Serializer matching exact 12 student registration fields from UI mockup.
    Supports parameter aliases for test payloads and postman consistency.
    """
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False)
    email_address = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    mobile_number = serializers.CharField(max_length=20, required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    
    # 12 specific UI fields
    student_class = serializers.CharField(max_length=50, required=False, allow_blank=True)
    board_or_university = serializers.CharField(max_length=100, required=False, allow_blank=True)
    subjects_needed = serializers.JSONField(required=False, default=list)
    target_exams = serializers.JSONField(required=False, default=list)
    city_location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mode_preference = serializers.ChoiceField(choices=['ONLINE', 'OFFLINE', 'BOTH'], default='ONLINE')
    budget_range = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=['MALE', 'FEMALE', 'OTHER'], default='OTHER')

    def to_internal_value(self, data):
        data = data.copy()
        # Alias mappings
        if 'email_address' in data and 'email' not in data:
            data['email'] = data['email_address']
        if 'mobile_number' in data and 'phone_number' not in data:
            data['phone_number'] = data['mobile_number']
        if 'class' in data and 'student_class' not in data:
            data['student_class'] = data['class']
        if 'city' in data and 'city_location' not in data:
            data['city_location'] = data['city']
        return super().to_internal_value(data)

    def validate(self, data):
        email = data.get('email')
        phone_number = data.get('phone_number')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required for student registration.")

        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})

        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"phone_number": "User with this phone number already exists."})

        return data

    def create(self, validated_data):
        email = validated_data.get('email', '')
        phone_number = validated_data.get('phone_number', '')
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name')

        student_class = validated_data.pop('student_class', '')
        board_or_university = validated_data.pop('board_or_university', '')
        subjects_needed = validated_data.pop('subjects_needed', [])
        target_exams = validated_data.pop('target_exams', [])
        city_location = validated_data.pop('city_location', '')
        mode_preference = validated_data.pop('mode_preference', 'ONLINE')
        budget_range = validated_data.pop('budget_range', '')
        gender = validated_data.pop('gender', 'OTHER')

        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            full_name=full_name,
            role='STUDENT',
            is_verified=True
        )

        StudentProfile.objects.create(
            user=user,
            student_class=student_class,
            board_or_university=board_or_university,
            subjects_needed=subjects_needed,
            target_exams=target_exams,
            city_location=city_location,
            mode_preference=mode_preference,
            budget_range=budget_range,
            gender=gender
        )

        return user


class TeacherRegistrationSerializer(serializers.Serializer):
    """
    Serializer strictly matching exact 23 teacher registration fields from the UI spec table:
    1. Full Name
    2. Profile Photo
    3. Email Address
    4. Mobile Number
    5. Password
    6. Date of Birth
    7. Gender
    8. State
    9. City
    10. Address
    11. Highest Qualification
    12. University / Institute
    13. Qualification Year
    14. Subjects
    15. Exam Expertise
    16. Teaching Languages
    17. Short Professional Bio
    18. Specialization / Expertise
    19. Current / Previous Institution
    20. ID Proof Type
    21. ID Proof Document
    22. Qualification Certificate
    23. Year Experience
    """
    full_name = serializers.CharField(max_length=150)
    email_address = serializers.EmailField(required=False)
    email = serializers.EmailField(required=False)
    mobile_number = serializers.CharField(max_length=20, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    
    dob = serializers.DateField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=['MALE', 'FEMALE', 'OTHER'], default='OTHER')
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city_location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    
    highest_qualification = serializers.CharField(max_length=255, required=False, allow_blank=True)
    qualifications = serializers.CharField(required=False, allow_blank=True)
    university_institute = serializers.CharField(max_length=255, required=False, allow_blank=True)
    qualification_year = serializers.IntegerField(required=False, allow_null=True)
    
    subjects = serializers.JSONField(required=False, default=list)
    teaching_subjects = serializers.JSONField(required=False, default=list)
    exam_expertise = serializers.JSONField(required=False, default=list)
    teaching_languages = serializers.JSONField(required=False, default=list)
    languages_spoken = serializers.JSONField(required=False, default=list)
    
    short_bio = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    specialization = serializers.CharField(max_length=255, required=False, allow_blank=True)
    current_previous_institution = serializers.CharField(max_length=255, required=False, allow_blank=True)
    current_institution = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    id_proof_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    id_proof_document = serializers.FileField(required=False, allow_null=True)
    qualification_certificate = serializers.FileField(required=False, allow_null=True)
    profile_photo = serializers.FileField(required=False, allow_null=True)
    
    year_experience = serializers.IntegerField(required=False, default=0)
    experience_years = serializers.IntegerField(required=False, default=0)

    def to_internal_value(self, data):
        data = data.copy()
        # Full Alias mappings for all 23 fields
        if 'email_address' in data and 'email' not in data:
            data['email'] = data['email_address']
        if 'mobile_number' in data and 'phone_number' not in data:
            data['phone_number'] = data['mobile_number']
        if 'date_of_birth' in data and 'dob' not in data:
            data['dob'] = data['date_of_birth']
        if 'city' in data and 'city_location' not in data:
            data['city_location'] = data['city']
        if 'subjects' in data and 'teaching_subjects' not in data:
            data['teaching_subjects'] = data['subjects']
        if 'teaching_languages' in data and 'languages_spoken' not in data:
            data['languages_spoken'] = data['teaching_languages']
        if 'short_bio' in data and 'bio' not in data:
            data['bio'] = data['short_bio']
        if 'highest_qualification' in data and 'qualifications' not in data:
            data['qualifications'] = data['highest_qualification']
        if 'current_previous_institution' in data and 'current_institution' not in data:
            data['current_institution'] = data['current_previous_institution']
        if 'year_experience' in data and 'experience_years' not in data:
            data['experience_years'] = data['year_experience']
        return super().to_internal_value(data)

    def validate(self, data):
        email = data.get('email')
        phone_number = data.get('phone_number')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required for teacher registration.")

        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})

        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"phone_number": "User with this phone number already exists."})

        return data

    def create(self, validated_data):
        email = validated_data.get('email', '')
        phone_number = validated_data.get('phone_number', '')
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name')

        profile_photo = validated_data.pop('profile_photo', None)
        id_proof = validated_data.pop('id_proof_document', None)
        qual_cert = validated_data.pop('qualification_certificate', None)

        dob = validated_data.pop('dob', None) or validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', 'OTHER')
        state = validated_data.pop('state', '')
        city_location = validated_data.pop('city_location', '') or validated_data.pop('city', '')
        address = validated_data.pop('address', '')

        highest_qualification = validated_data.pop('highest_qualification', '') or validated_data.pop('qualifications', '')
        university_institute = validated_data.pop('university_institute', '')
        qualification_year = validated_data.pop('qualification_year', None)

        experience_years = validated_data.pop('experience_years', 0) or validated_data.pop('year_experience', 0)
        teaching_subjects = validated_data.pop('teaching_subjects', []) or validated_data.pop('subjects', [])
        exam_expertise = validated_data.pop('exam_expertise', [])
        languages_spoken = validated_data.pop('languages_spoken', []) or validated_data.pop('teaching_languages', [])

        bio = validated_data.pop('bio', '') or validated_data.pop('short_bio', '')
        specialization = validated_data.pop('specialization', '')
        current_institution = validated_data.pop('current_institution', '') or validated_data.pop('current_previous_institution', '')
        id_proof_type = validated_data.pop('id_proof_type', '')

        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            full_name=full_name,
            role='TEACHER',
            is_verified=False
        )

        teacher_profile = TeacherProfile.objects.create(
            user=user,
            gender=gender,
            dob=dob,
            state=state,
            city_location=city_location,
            address=address,
            highest_qualification=highest_qualification,
            qualifications=highest_qualification,
            university_institute=university_institute,
            qualification_year=qualification_year,
            experience_years=experience_years,
            teaching_subjects=teaching_subjects,
            exam_expertise=exam_expertise,
            languages_spoken=languages_spoken,
            bio=bio,
            specialization=specialization,
            current_institution=current_institution,
            id_proof_type=id_proof_type,
            profile_photo=profile_photo,
            id_proof_document=id_proof,
            qualification_certificate=qual_cert,
            is_verified=False
        )

        TeacherVerification.objects.create(
            teacher_profile=teacher_profile,
            id_proof_document=id_proof,
            qualification_certificate=qual_cert,
            status='PENDING'
        )

        return user


# ==============================================================================
# PROFILE SERIALIZERS
# ==============================================================================

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = '__all__'


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = '__all__'


class TeacherProfileDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    
    # Hidden contact details fields (only populated if unlocked via contact access)
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user_id', 'full_name', 'email', 'phone_number', 'gender',
            'qualifications', 'experience_years', 'teaching_subjects',
            'classes_taught', 'boards_catered', 'mode_offered', 'hourly_rate',
            'monthly_fee', 'city_location', 'state', 'pincode', 'bio',
            'tagline', 'languages_spoken', 'rating', 'total_reviews',
            'is_verified', 'demo_class_available', 'profile_photo'
        ]

    def get_email(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return "Contact Hidden (Request Connection)"
        
        # Admin or self can see full email
        if request.user.is_staff or request.user == obj.user:
            return obj.user.email

        # Check contact access grant
        granted = ContactAccess.objects.filter(
            student=request.user,
            teacher=obj.user,
            status='GRANTED'
        ).exists()

        if granted:
            return obj.user.email
        return "Contact Hidden (Request Connection)"

    def get_phone_number(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return "Contact Hidden (Request Connection)"

        # Admin or self can see full phone number
        if request.user.is_staff or request.user == obj.user:
            return obj.user.phone_number

        # Check contact access grant
        granted = ContactAccess.objects.filter(
            student=request.user,
            teacher=obj.user,
            status='GRANTED'
        ).exists()

        if granted:
            return obj.user.phone_number
        return "Contact Hidden (Request Connection)"


class TeacherVerificationSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher_profile.user.full_name', read_only=True)

    class Meta:
        model = TeacherVerification
        fields = '__all__'


# ==============================================================================
# BATCH & CONTENT SERIALIZERS
# ==============================================================================

class BatchSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    enrolled_count = serializers.IntegerField(source='enrollments.count', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at', 'updated_at']


class BatchAnnouncementSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='batch.teacher.full_name', read_only=True)

    class Meta:
        model = BatchAnnouncement
        fields = '__all__'
        read_only_fields = ['created_at']


class ClassContentSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    batch_subject = serializers.CharField(source='batch.subject', read_only=True)

    class Meta:
        model = ClassContent
        fields = '__all__'
        read_only_fields = ['created_at']


class StudyMaterialSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source='batch.title', read_only=True)

    class Meta:
        model = StudyMaterial
        fields = '__all__'
        read_only_fields = ['uploaded_at']


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentUpdate
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at']


class BatchDetailSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    announcements = BatchAnnouncementSerializer(many=True, read_only=True)
    class_contents = ClassContentSerializer(many=True, read_only=True)
    study_materials = StudyMaterialSerializer(many=True, read_only=True)
    enrolled_count = serializers.IntegerField(source='enrollments.count', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'


# ==============================================================================
# ENROLLMENT & CONNECTIONS
# ==============================================================================

class BookmarkSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher_profile.user.full_name', read_only=True)

    class Meta:
        model = Bookmark
        fields = '__all__'
        read_only_fields = ['student', 'created_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    batch_title = serializers.CharField(source='batch.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ['student', 'enrolled_at']


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    class_title = serializers.CharField(source='class_content.title', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'


class ConnectionRequestSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = '__all__'
        read_only_fields = ['sender', 'created_at', 'updated_at']


class ContactAccessSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = ContactAccess
        fields = '__all__'
        read_only_fields = ['student', 'requested_at', 'granted_at']


# ==============================================================================
# MESSAGING SERIALIZERS
# ==============================================================================

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'sent_at']


class ConversationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = '__all__'

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-sent_at').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None


# ==============================================================================
# REVIEWS, NOTIFICATIONS & AUDIT
# ==============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['student', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True)

    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['reporter', 'created_at']


class UserBlockSerializer(serializers.ModelSerializer):
    blocker_name = serializers.CharField(source='blocker.full_name', read_only=True)
    blocked_name = serializers.CharField(source='blocked.full_name', read_only=True)

    class Meta:
        model = UserBlock
        fields = '__all__'
        read_only_fields = ['blocker', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'


# ==============================================================================
# ADMIN DASHBOARD SERIALIZERS
# ==============================================================================

class AdminUserListSerializer(serializers.ModelSerializer):
    profile_details = serializers.SerializerMethodField()
    verifications_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'full_name', 'role', 'user_type', 'is_active', 'is_staff', 'is_verified', 'created_at', 'profile_details', 'verifications_count']

    def get_profile_details(self, obj):
        if obj.role == 'TEACHER' and hasattr(obj, 'teacher_profile'):
            tp = obj.teacher_profile
            return {
                "qualifications": tp.qualifications,
                "experience_years": tp.experience_years,
                "teaching_subjects": tp.teaching_subjects,
                "city": tp.city_location,
                "rating": tp.rating,
                "hourly_rate": float(tp.hourly_rate),
                "monthly_fee": float(tp.monthly_fee)
            }
        elif obj.role == 'STUDENT' and hasattr(obj, 'student_profile'):
            sp = obj.student_profile
            return {
                "student_class": sp.student_class,
                "board_or_university": sp.board_or_university,
                "subjects_needed": sp.subjects_needed,
                "city": sp.city_location
            }
        return None

    def get_verifications_count(self, obj):
        if obj.role == 'TEACHER' and hasattr(obj, 'teacher_profile'):
            return obj.teacher_profile.verifications.count()
        return 0

