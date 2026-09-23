# pyrefly: ignore [missing-import]
from rest_framework import serializers
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# pyrefly: ignore [missing-import]
from .models import (
    User, UserBlock, StudentProfile, TeacherProfile, TeacherVerification,
    Batch, BatchAnnouncement, Enrollment, ClassContent, Attendance,
    StudyMaterial, Bookmark, ConnectionRequest,
    Conversation, Message, MessageAttachment, Notification,
    Review, Report, Payment, AuditLog,
    validate_external_url, validate_video_file
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
    token = serializers.CharField(required=True)

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
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_photo = serializers.ImageField(source='user.profile_photo', required=False, allow_null=True)

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'profile_photo',
            'date_of_birth', 'gender', 'education_level', 'school_name',
            'city', 'state', 'preferred_language', 'subjects_of_interest', 'bio'
        )

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

class StudentSafePublicSerializer(serializers.ModelSerializer):
    user = UserSafePublicSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user', 'education_level', 'school_name',
            'city', 'state', 'preferred_language', 'subjects_of_interest', 'bio'
        )

class TeacherProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    profile_photo = serializers.ImageField(source='user.profile_photo', required=False, allow_null=True)

    class Meta:
        model = TeacherProfile
        fields = (
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'profile_photo',
            'display_name', 'bio', 'qualification', 'experience_years',
            'subjects', 'teaching_languages', 'exam_expertise', 'hourly_rate',
            'demo_video_url', 'verification_status', 'average_rating',
            'total_reviews', 'total_students', 'is_featured', 'created_at'
        )
        read_only_fields = (
            'id', 'verification_status', 'average_rating', 'total_reviews',
            'total_students', 'is_featured', 'created_at'
        )

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
    Public representation of teachers.
    STRICT PRIVACY: phone_number and email are completely omitted.
    """
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    profile_photo = serializers.ImageField(source='user.profile_photo', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = (
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'profile_photo', 'bio', 'qualification', 'experience_years',
            'subjects', 'teaching_languages', 'exam_expertise', 'hourly_rate',
            'demo_video_url', 'verification_status', 'average_rating',
            'total_reviews', 'total_students', 'is_featured'
        )
        read_only_fields = fields

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

    class Meta:
        model = Batch
        fields = (
            'id', 'title', 'slug', 'description', 'subject', 'grade_level',
            'language', 'start_date', 'end_date', 'capacity', 'price', 'is_free',
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

    class Meta:
        model = Batch
        fields = (
            'id', 'title', 'slug', 'description', 'subject', 'grade_level',
            'language', 'start_date', 'end_date', 'capacity', 'price', 'is_free',
            'status', 'thumbnail', 'enrolled_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')

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
            'id', 'batch', 'teacher', 'teacher_name', 'title', 'message',
            'attachment', 'published_at'
        )
        read_only_fields = ('id', 'batch', 'teacher', 'teacher_name', 'published_at')


# ==========================================
# 4. ENROLLMENT SERIALIZERS
# ==========================================

class EnrollmentSerializer(serializers.ModelSerializer):
    student = StudentSafePublicSerializer(read_only=True)
    batch = BatchPublicSerializer(read_only=True)
    batch_id = serializers.UUIDField(source='batch.id', read_only=True)
    batch_title = serializers.CharField(source='batch.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            'id', 'student', 'batch', 'batch_id', 'batch_title',
            'status', 'payment_status', 'requested_at', 'approved_at',
            'completed_at', 'cancelled_at'
        )
        read_only_fields = fields

class EnrollmentActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    reason = serializers.CharField(required=False, allow_blank=True)


# ==========================================
# 5. CLASS & ATTENDANCE SERIALIZERS
# ==========================================

class ClassContentSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = ClassContent
        fields = (
            'id', 'batch', 'batch_title', 'teacher', 'teacher_name',
            'title', 'description', 'class_type', 'video_file',
            'external_url', 'thumbnail', 'scheduled_date', 'duration',
            'order', 'is_published', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'teacher', 'created_at', 'updated_at')

    def validate(self, attrs):
        class_type = attrs.get('class_type', getattr(self.instance, 'class_type', None))
        video_file = attrs.get('video_file', getattr(self.instance, 'video_file', None))
        external_url = attrs.get('external_url', getattr(self.instance, 'external_url', None))

        if class_type == ClassContent.ClassType.RECORDED_VIDEO:
            if not video_file and not self.instance:
                raise serializers.ValidationError({"video_file": "Video file is required for RECORDED_VIDEO."})
            if attrs.get('video_file'):
                validate_video_file(attrs['video_file'])

        elif class_type in [ClassContent.ClassType.YOUTUBE, ClassContent.ClassType.ZOOM, ClassContent.ClassType.GOOGLE_MEET]:
            if not external_url:
                raise serializers.ValidationError({"external_url": f"External URL is required for {class_type}."})
            validate_external_url(external_url, class_type)

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
    batch_title = serializers.CharField(source='batch.title', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = StudyMaterial
        fields = (
            'id', 'batch', 'batch_title', 'teacher', 'teacher_name',
            'title', 'description', 'file', 'file_type', 'size',
            'is_downloadable', 'published_at'
        )
        read_only_fields = ('id', 'batch', 'teacher', 'teacher_name', 'file_type', 'size', 'published_at')

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

    class Meta:
        model = Review
        fields = (
            'id', 'student', 'student_name', 'teacher', 'teacher_name',
            'batch', 'batch_title', 'rating', 'teaching_quality',
            'doubt_solving', 'punctuality', 'notes_quality',
            'comment', 'status', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'student', 'teacher', 'batch', 'status', 'created_at', 'updated_at')

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

    class Meta:
        model = Report
        fields = (
            'id', 'reporter', 'reporter_email', 'target_type', 'target_id',
            'reason', 'description', 'status', 'admin_note',
            'resolved_by', 'resolved_by_email', 'resolved_at', 'created_at'
        )
        read_only_fields = ('id', 'reporter', 'status', 'admin_note', 'resolved_by', 'resolved_at', 'created_at')

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

    class Meta:
        model = AuditLog
        fields = (
            'id', 'actor', 'actor_email', 'actor_name', 'action',
            'object_type', 'object_id', 'description', 'metadata',
            'ip_address', 'user_agent', 'created_at'
        )
        read_only_fields = fields
