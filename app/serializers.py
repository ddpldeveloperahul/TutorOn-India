from rest_framework import serializers
from django.contrib.auth import get_user_model
from app.models import (
    StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, Bookmark, Enrollment,
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
        fields = ['id', 'email', 'phone_number', 'full_name', 'user_type', 'is_active', 'is_verified', 'created_at']
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
            user_type='STUDENT'
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
    Serializer matching exact 23 teacher registration fields from UI mockup.
    Supports parameter aliases for test payloads and postman consistency.
    """
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False)
    email_address = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    mobile_number = serializers.CharField(max_length=20, required=False)
    password = serializers.CharField(write_only=True, min_length=8)

    # 23 specific UI fields
    gender = serializers.ChoiceField(choices=['MALE', 'FEMALE', 'OTHER'], default='OTHER')
    dob = serializers.DateField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    qualifications = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(default=0)
    teaching_subjects = serializers.JSONField(required=False, default=list)
    classes_taught = serializers.JSONField(required=False, default=list)
    boards_catered = serializers.JSONField(required=False, default=list)
    mode_offered = serializers.ChoiceField(choices=['ONLINE', 'OFFLINE', 'BOTH'], default='BOTH')
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    city_location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pincode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    tagline = serializers.CharField(max_length=255, required=False, allow_blank=True)
    languages_spoken = serializers.JSONField(required=False, default=list)
    demo_class_available = serializers.BooleanField(default=True)

    # Document uploads (optional in test payloads)
    profile_photo = serializers.FileField(required=False, allow_null=True)
    id_proof_document = serializers.FileField(required=False, allow_null=True)
    qualification_certificate = serializers.FileField(required=False, allow_null=True)

    def to_internal_value(self, data):
        data = data.copy()
        # Alias mappings
        if 'email_address' in data and 'email' not in data:
            data['email'] = data['email_address']
        if 'mobile_number' in data and 'phone_number' not in data:
            data['phone_number'] = data['mobile_number']
        if 'date_of_birth' in data and 'dob' not in data:
            data['dob'] = data['date_of_birth']
        if 'city' in data and 'city_location' not in data:
            data['city_location'] = data['city']
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
        qualifications = validated_data.pop('qualifications', '')
        experience_years = validated_data.pop('experience_years', 0)
        teaching_subjects = validated_data.pop('teaching_subjects', [])
        classes_taught = validated_data.pop('classes_taught', [])
        boards_catered = validated_data.pop('boards_catered', [])
        mode_offered = validated_data.pop('mode_offered', 'BOTH')
        hourly_rate = validated_data.pop('hourly_rate', 0.00)
        monthly_fee = validated_data.pop('monthly_fee', 0.00)
        city_location = validated_data.pop('city_location', '')
        state = validated_data.pop('state', '')
        pincode = validated_data.pop('pincode', '')
        bio = validated_data.pop('bio', '')
        tagline = validated_data.pop('tagline', '')
        languages_spoken = validated_data.pop('languages_spoken', [])
        demo_class_available = validated_data.pop('demo_class_available', True)

        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            full_name=full_name,
            user_type='TEACHER'
        )

        teacher_profile = TeacherProfile.objects.create(
            user=user,
            gender=gender,
            dob=dob,
            qualifications=qualifications,
            experience_years=experience_years,
            teaching_subjects=teaching_subjects,
            classes_taught=classes_taught,
            boards_catered=boards_catered,
            mode_offered=mode_offered,
            hourly_rate=hourly_rate,
            monthly_fee=monthly_fee,
            city_location=city_location,
            state=state,
            pincode=pincode,
            bio=bio,
            tagline=tagline,
            languages_spoken=languages_spoken,
            demo_class_available=demo_class_available,
            profile_photo=profile_photo
        )

        # Create teacher verification record if documents provided
        if id_proof or qual_cert:
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
    class Meta:
        model = ClassContent
        fields = '__all__'
        read_only_fields = ['created_at']


class StudyMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyMaterial
        fields = '__all__'
        read_only_fields = ['uploaded_at']


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
