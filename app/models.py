from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings

# ==============================================================================
# USER MANAGER & CUSTOM USER MODEL
# ==============================================================================

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError('Either Email or Phone Number is required.')
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('ADMIN', 'Admin'),
    )

    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=150)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='STUDENT')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.user_type})"


# ==============================================================================
# PROFILES & VERIFICATION
# ==============================================================================

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    gender = models.CharField(max_length=20, default='OTHER')
    dob = models.DateField(null=True, blank=True)
    student_class = models.CharField(max_length=50, blank=True)
    board_or_university = models.CharField(max_length=100, blank=True)
    subjects_needed = models.JSONField(default=list, blank=True)
    target_exams = models.JSONField(default=list, blank=True)
    city_location = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    mode_preference = models.CharField(max_length=20, default='ONLINE')
    budget_range = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StudentProfile: {self.user.full_name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    gender = models.CharField(max_length=20, default='OTHER')
    dob = models.DateField(null=True, blank=True)
    qualifications = models.TextField(blank=True)
    experience_years = models.IntegerField(default=0)
    teaching_subjects = models.JSONField(default=list, blank=True)
    classes_taught = models.JSONField(default=list, blank=True)
    boards_catered = models.JSONField(default=list, blank=True)
    mode_offered = models.CharField(max_length=20, default='BOTH')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    city_location = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    tagline = models.CharField(max_length=255, blank=True)
    languages_spoken = models.JSONField(default=list, blank=True)
    demo_class_available = models.BooleanField(default=True)
    profile_photo = models.FileField(upload_to='profiles/photos/', null=True, blank=True)
    rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TeacherProfile: {self.user.full_name}"


class TeacherVerification(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    teacher_profile = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='verifications')
    id_proof_document = models.FileField(upload_to='verifications/id/', null=True, blank=True)
    qualification_certificate = models.FileField(upload_to='verifications/certificates/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Verification for {self.teacher_profile.user.full_name} [{self.status}]"


# ==============================================================================
# BATCH & CONTENT
# ==============================================================================

class Batch(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255)
    description = models.TextField()
    subject = models.CharField(max_length=100)
    batch_type = models.CharField(max_length=20, default='ONLINE')
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    start_date = models.DateField(null=True, blank=True)
    schedule_time = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.subject})"


class BatchAnnouncement(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement: {self.title}"


class ClassContent(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('RECORDED_VIDEO', 'Recorded Video'),
        ('YOUTUBE', 'YouTube Video'),
        ('ZOOM', 'Zoom Link'),
        ('GOOGLE_MEET', 'Google Meet Link'),
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='class_contents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='YOUTUBE')
    url = models.URLField(max_length=500, blank=True)
    video_file = models.FileField(upload_to='classes/videos/', null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.content_type})"


class StudyMaterial(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='study_materials')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# ==============================================================================
# BOOKMARK, ENROLLMENT & ATTENDANCE
# ==============================================================================

class Bookmark(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    teacher_profile = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'teacher_profile')


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'batch')


class Attendance(models.Model):
    class_content = models.ForeignKey(ClassContent, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=20, default='PRESENT')
    marked_at = models.DateTimeField(auto_now_add=True)


# ==============================================================================
# CONNECTIONS & PRIVACY UNLOCK
# ==============================================================================

class ConnectionRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_connections')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_connections')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')


class ContactAccess(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('GRANTED', 'Granted'),
        ('REJECTED', 'Rejected'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_requests')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_grants')
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_at = models.DateTimeField(auto_now_add=True)
    granted_at = models.DateTimeField(null=True, blank=True)


# ==============================================================================
# MESSAGING & CHAT
# ==============================================================================

class Conversation(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_chats')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_chats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'teacher')


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='messages/attachments/')


# ==============================================================================
# REVIEWS, NOTIFICATIONS & SYSTEM
# ==============================================================================

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_reviews')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=100)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    ip_address = models.CharField(max_length=50, default='127.0.0.1')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
