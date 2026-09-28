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
        if 'user_type' in extra_fields and 'role' not in extra_fields:
            extra_fields['role'] = extra_fields.pop('user_type')
        elif 'user_type' in extra_fields:
            extra_fields.pop('user_type')

        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError('Superuser must have an email address.')
        extra_fields.setdefault('role', 'ADMIN')
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
    role = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='STUDENT')
    
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

    @property
    def user_type(self):
        return self.role

    @user_type.setter
    def user_type(self, value):
        self.role = value

    def __str__(self):
        return f"{self.full_name} ({self.role})"


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
    
    # 23-field Teacher Registration fields
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    city_location = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    
    highest_qualification = models.CharField(max_length=255, blank=True)
    qualifications = models.TextField(blank=True)
    university_institute = models.CharField(max_length=255, blank=True)
    qualification_year = models.IntegerField(null=True, blank=True)
    
    experience_years = models.IntegerField(default=0)
    teaching_subjects = models.JSONField(default=list, blank=True)
    exam_expertise = models.JSONField(default=list, blank=True)
    languages_spoken = models.JSONField(default=list, blank=True)
    classes_taught = models.JSONField(default=list, blank=True)
    boards_catered = models.JSONField(default=list, blank=True)
    
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    current_institution = models.CharField(max_length=255, blank=True)
    tagline = models.CharField(max_length=255, blank=True)
    
    # Verification & Profile Documents
    profile_photo = models.FileField(upload_to='profiles/photos/', null=True, blank=True)
    id_proof_type = models.CharField(max_length=100, blank=True)
    id_proof_document = models.FileField(upload_to='verifications/id/', null=True, blank=True)
    qualification_certificate = models.FileField(upload_to='verifications/certificates/', null=True, blank=True)
    
    mode_offered = models.CharField(max_length=20, default='BOTH')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    demo_class_available = models.BooleanField(default=True)
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
    DELIVERY_FORMAT_CHOICES = (
        ('LIVE_INTERACTIVE', 'Live Interactive Classes'),
        ('PRERECORDED_DOUBTS', 'Pre-recorded + Live Doubts'),
        ('SELF_PACED', 'Self-paced Complete Course'),
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100)
    target_exam = models.CharField(max_length=100, blank=True, default='JEE Advanced')
    target_grade = models.CharField(max_length=150, blank=True, default='Class 12th & Droppers (Intensive)')
    
    # Step 2: Delivery Format & Capacity & Timings
    batch_type = models.CharField(max_length=20, default='ONLINE')
    delivery_format = models.CharField(max_length=30, choices=DELIVERY_FORMAT_CHOICES, default='LIVE_INTERACTIVE')
    is_unlimited_capacity = models.BooleanField(default=False)
    max_students_capacity = models.IntegerField(default=150)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    class_days = models.JSONField(default=list, blank=True)  # e.g. ["Mon", "Wed", "Fri"]
    class_slot = models.CharField(max_length=100, blank=True, default='4:00 PM - 5:30 PM')
    language = models.CharField(max_length=50, default='Hinglish')
    schedule_time = models.CharField(max_length=100, blank=True)
    
    # Step 3: Pricing & Perks
    is_paid = models.BooleanField(default=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=4999.00)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, default=4999.00)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=7999.00)
    allow_installments = models.BooleanField(default=True)
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2600.00)
    installment_months = models.IntegerField(default=2)
    cohort_perks = models.JSONField(default=list, blank=True)
    
    is_draft = models.BooleanField(default=False)
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
    STATUS_CHOICES = (
        ('UPCOMING', 'Upcoming'),
        ('LIVE', 'Live Now'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='class_contents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='YOUTUBE')
    url = models.URLField(max_length=500, blank=True)
    video_file = models.FileField(upload_to='classes/videos/', null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    is_live = models.BooleanField(default=False)
    joined_students_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.content_type})"


class StudyMaterial(models.Model):
    ACCESS_TYPE_CHOICES = (
        ('DOWNLOADABLE', 'Downloadable'),
        ('PROTECTED', 'Protected'),
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='study_materials')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='materials/')
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES, default='DOWNLOADABLE')
    file_size_display = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class StudentUpdate(models.Model):
    UPDATE_TYPE_CHOICES = (
        ('JOINED_BATCH', 'Joined batch'),
        ('SENT_DOUBT', 'Sent doubt query'),
        ('ATTENDED_SESSION', 'Attended session'),
        ('SUBMITTED_ASSIGNMENT', 'Submitted assignment'),
        ('OTHER', 'Other'),
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_updates')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updates_created', null=True, blank=True)
    student_name = models.CharField(max_length=150)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='student_updates', null=True, blank=True)
    batch_title = models.CharField(max_length=255, blank=True)
    update_type = models.CharField(max_length=30, choices=UPDATE_TYPE_CHOICES, default='JOINED_BATCH')
    update_text = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.update_type} ({self.batch_title})"


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
