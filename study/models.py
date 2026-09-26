import os
import uuid
import urllib.parse
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify

# ==========================================
# 0. BASE ABSTRACT MODEL
# ==========================================

class TimeStampedUUIDModel(models.Model):
    """
    Abstract base model providing UUID primary key and timestamp fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ==========================================
# 1. USER & AUTHENTICATION MODELS
# ==========================================

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin, TimeStampedUUIDModel):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'
        ADMIN = 'ADMIN', 'Admin'

    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, default='', db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_photo = models.ImageField(upload_to='profiles/%Y/%m/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email}) - {self.role}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()
        if self.phone_number:
            self.phone_number = self.phone_number.strip()

class UserBlock(TimeStampedUUIDModel):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_initiated')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_users')
    reason = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'User Block'
        verbose_name_plural = 'User Blocks'
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.blocker.email} blocked {self.blocked.email}"

    def clean(self):
        if self.blocker_id == self.blocked_id:
            raise ValidationError("You cannot block yourself.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class EmailVerificationToken(TimeStampedUUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

class PasswordResetToken(TimeStampedUUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at


# ==========================================
# 2. STUDENT & TEACHER PROFILES
# ==========================================

class StudentProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, default='')
    education_level = models.CharField(max_length=100, blank=True, default='')
    school_name = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='', db_index=True)
    state = models.CharField(max_length=100, blank=True, default='', db_index=True)
    preferred_language = models.CharField(max_length=50, blank=True, default='')
    subjects_of_interest = models.JSONField(default=list, blank=True)
    bio = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'

    def __str__(self):
        return f"Student: {self.user.get_full_name()}"

class TeacherProfile(TimeStampedUUIDModel):
    class VerificationStatus(models.TextChoices):
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    display_name = models.CharField(max_length=200, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    qualification = models.CharField(max_length=255, blank=True, default='', db_index=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, db_index=True)
    subjects = models.JSONField(default=list, blank=True)
    teaching_languages = models.JSONField(default=list, blank=True)
    exam_expertise = models.JSONField(default=list, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, db_index=True)
    demo_video_url = models.URLField(blank=True, default='')
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING_VERIFICATION,
        db_index=True
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, db_index=True)
    total_reviews = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'
        ordering = ['-average_rating', '-experience_years', '-created_at']

    def __str__(self):
        return f"Teacher: {self.display_name or self.user.get_full_name()} ({self.verification_status})"

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

class TeacherVerification(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.CharField(max_length=100, help_text="e.g. AADHAAR, PAN, DEGREE_CERTIFICATE")
    document_file = models.FileField(upload_to='verifications/%Y/%m/')
    certificate_file = models.FileField(upload_to='verifications/%Y/%m/', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications'
    )
    rejection_reason = models.TextField(blank=True, default='')
    admin_note = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Teacher Verification'
        verbose_name_plural = 'Teacher Verifications'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Verification for {self.teacher} - {self.status}"


# ==========================================
# 3. BATCHES & ANNOUNCEMENTS
# ==========================================

class Batch(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ONGOING = 'ONGOING', 'Ongoing'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField()
    subject = models.CharField(max_length=100, db_index=True)
    grade_level = models.CharField(max_length=100, blank=True, default='')
    language = models.CharField(max_length=50, blank=True, default='English')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_free = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    thumbnail = models.ImageField(upload_to='batches/%Y/%m/', null=True, blank=True)

    class Meta:
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.subject}) - {self.teacher.display_name or self.teacher.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'batch'
            unique_str = uuid.uuid4().hex[:6]
            self.slug = f"{base_slug}-{unique_str}"
        super().save(*args, **kwargs)

class BatchAnnouncement(TimeStampedUUIDModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='announcements')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    message = models.TextField()
    attachment = models.FileField(upload_to='announcements/%Y/%m/', null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Batch Announcement'
        verbose_name_plural = 'Batch Announcements'
        ordering = ['-published_at']

    def __str__(self):
        return f"Announcement: {self.title} ({self.batch.title})"


# ==========================================
# 4. ENROLLMENTS
# ==========================================

class Enrollment(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
        PAYMENT_COMPLETED = 'PAYMENT_COMPLETED', 'Payment Completed'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PAID = 'PAID', 'Paid'
        REFUNDED = 'REFUNDED', 'Refunded'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_enrollments'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        unique_together = ('student', 'batch')
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} -> {self.batch.title} ({self.status})"


# ==========================================
# 5. CLASSES & ATTENDANCE (EXTERNAL LINKS: YOUTUBE, ZOOM, GOOGLE_MEET ONLY)
# ==========================================

ALLOWED_YOUTUBE_DOMAINS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}
ALLOWED_ZOOM_DOMAINS = {'zoom.us', 'us04web.zoom.us', 'us05web.zoom.us', 'us02web.zoom.us'}
ALLOWED_MEET_DOMAINS = {'meet.google.com'}

def validate_external_url(url, class_type):
    if not url:
        raise ValidationError("External class link is required.")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != 'https':
        raise ValidationError("Only secure https:// URLs are allowed.")
    netloc = parsed.netloc.lower()
    if ':' in netloc:
        netloc = netloc.split(':')[0]

    if class_type == 'YOUTUBE':
        if netloc not in ALLOWED_YOUTUBE_DOMAINS:
            raise ValidationError(f"Invalid YouTube URL. Domain must be one of: {', '.join(ALLOWED_YOUTUBE_DOMAINS)}")
    elif class_type == 'ZOOM':
        is_zoom = (netloc == 'zoom.us' or netloc.endswith('.zoom.us'))
        if not is_zoom:
            raise ValidationError("Invalid Zoom URL. Domain must belong to zoom.us or its subdomains.")
    elif class_type == 'GOOGLE_MEET':
        if netloc != 'meet.google.com':
            raise ValidationError("Invalid Google Meet URL. Domain must be meet.google.com.")
    else:
        raise ValidationError(f"Invalid class type '{class_type}'. Platform only supports YOUTUBE, ZOOM, and GOOGLE_MEET links.")
    return url

class ClassContent(TimeStampedUUIDModel):
    class ClassType(models.TextChoices):
        YOUTUBE = 'YOUTUBE', 'YouTube Video/Stream'
        ZOOM = 'ZOOM', 'Zoom Meeting/Class'
        GOOGLE_MEET = 'GOOGLE_MEET', 'Google Meet'

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='classes')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='classes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    class_type = models.CharField(
        max_length=20,
        choices=ClassType.choices,
        default=ClassType.ZOOM,
        db_index=True
    )
    external_url = models.URLField(max_length=500, blank=True, default='', help_text="Direct link for YouTube, Zoom, or Google Meet class")
    video_file = models.FileField(upload_to='classes/videos/%Y/%m/', null=True, blank=True, editable=False)
    thumbnail = models.ImageField(upload_to='classes/thumbnails/%Y/%m/', null=True, blank=True)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Class Content'
        verbose_name_plural = 'Class Contents'
        ordering = ['order', 'scheduled_date', 'created_at']

    def __str__(self):
        return f"[{self.class_type}] {self.title} - {self.batch.title}"

    def clean(self):
        super().clean()
        if not self.external_url:
            raise ValidationError("Class link (external_url) is required. Live streaming or video hosting is not provided on-platform; provide a valid YouTube, Zoom, or Google Meet link.")
        validate_external_url(self.external_url, self.class_type)

class Attendance(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendances')
    class_content = models.ForeignKey(ClassContent, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ('enrollment', 'class_content')
        ordering = ['-marked_at']

    def __str__(self):
        return f"{self.enrollment.student.user.get_full_name()} - {self.class_content.title}: {self.status}"


# ==========================================
# 6. STUDY MATERIALS & BOOKMARKS
# ==========================================

class StudyMaterial(TimeStampedUUIDModel):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='materials')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='materials/%Y/%m/')
    file_type = models.CharField(max_length=50, blank=True, default='')
    size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    is_downloadable = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Study Material'
        verbose_name_plural = 'Study Materials'
        ordering = ['-published_at']

    def __str__(self):
        return f"{self.title} ({self.batch.title})"

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size') and not self.size:
            self.size = self.file.size
        if self.file and not self.file_type:
            ext = os.path.splitext(self.file.name)[1].lower().replace('.', '')
            self.file_type = ext.upper()
        super().save(*args, **kwargs)

class Bookmark(TimeStampedUUIDModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='bookmarks')
    material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE, related_name='bookmarks')

    class Meta:
        verbose_name = 'Bookmark'
        verbose_name_plural = 'Bookmarks'
        unique_together = ('student', 'material')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} bookmarked {self.material.title}"


# ==========================================
# 7. CONNECTIONS & CONTACT PRIVACY
# ==========================================

class ConnectionRequest(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        STUDENT_APPROVED = 'STUDENT_APPROVED', 'Student Approved'
        ADMIN_APPROVED = 'ADMIN_APPROVED', 'Admin Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'
        BLOCKED = 'BLOCKED', 'Blocked'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='connection_requests')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='connection_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_connections')
    message = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    student_approved = models.BooleanField(default=False)
    admin_approved = models.BooleanField(default=False)
    contact_unlocked = models.BooleanField(default=False, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_connections'
    )

    class Meta:
        verbose_name = 'Connection Request'
        verbose_name_plural = 'Connection Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Connection: {self.student.user.get_full_name()} <-> {self.teacher.display_name or self.teacher.user.get_full_name()} ({self.status})"

class ContactAccess(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        REVOKED = 'REVOKED', 'Revoked'

    connection = models.OneToOneField(ConnectionRequest, on_delete=models.CASCADE, related_name='contact_access')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='contact_accesses')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='contact_accesses')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    class Meta:
        verbose_name = 'Contact Access Approval'
        verbose_name_plural = 'Contact Access Approvals'
        ordering = ['-created_at']

    def __str__(self):
        return f"ContactAccess: {self.connection.id} - {self.status}"


# ==========================================
# 8. INTERNAL MESSAGING
# ==========================================

class Conversation(TimeStampedUUIDModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='conversations')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='conversations')

    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        unique_together = ('student', 'teacher')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat: {self.student.user.get_full_name()} & {self.teacher.display_name or self.teacher.user.get_full_name()}"

class Message(TimeStampedUUIDModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Msg from {self.sender.email} at {self.created_at}"

class MessageAttachment(TimeStampedUUIDModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='messages/%Y/%m/')
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'


# ==========================================
# 9. NOTIFICATIONS
# ==========================================

class Notification(TimeStampedUUIDModel):
    class NotificationType(models.TextChoices):
        CLASS_REMINDER = 'CLASS_REMINDER', 'Class Reminder'
        TEACHER_ANNOUNCEMENT = 'TEACHER_ANNOUNCEMENT', 'Teacher Announcement'
        CONNECTION_REQUEST = 'CONNECTION_REQUEST', 'Connection Request'
        CONNECTION_APPROVED = 'CONNECTION_APPROVED', 'Connection Approved'
        ENROLLMENT_REQUEST = 'ENROLLMENT_REQUEST', 'Enrollment Request'
        ENROLLMENT_APPROVED = 'ENROLLMENT_APPROVED', 'Enrollment Approved'
        MATERIAL_UPLOADED = 'MATERIAL_UPLOADED', 'Material Uploaded'
        NEW_MESSAGE = 'NEW_MESSAGE', 'New Message'
        PAYMENT_REMINDER = 'PAYMENT_REMINDER', 'Payment Reminder'
        PAYMENT_SUCCESS = 'PAYMENT_SUCCESS', 'Payment Success'
        PAYMENT_FAILED = 'PAYMENT_FAILED', 'Payment Failed'
        SYSTEM = 'SYSTEM', 'System'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True
    )
    related_object_id = models.CharField(max_length=128, blank=True, default='')
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.email}: [{self.notification_type}] {self.title}"


# ==========================================
# 10. REVIEWS & RATINGS
# ==========================================

class Review(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PUBLISHED = 'PUBLISHED', 'Published'
        PENDING = 'PENDING', 'Pending Moderation'
        HIDDEN = 'HIDDEN', 'Hidden'
        REMOVED = 'REMOVED', 'Removed by Admin'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reviews')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='reviews')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    teaching_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    doubt_solving = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    punctuality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    notes_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    comment = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PUBLISHED,
        db_index=True
    )

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ('student', 'batch')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.student.user.get_full_name()} for {self.teacher} ({self.rating}/5)"


# ==========================================
# 11. REPORTS & ABUSE MODERATION
# ==========================================

class Report(TimeStampedUUIDModel):
    class TargetType(models.TextChoices):
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        MESSAGE = 'MESSAGE', 'Message'
        REVIEW = 'REVIEW', 'Review'
        BATCH = 'BATCH', 'Batch'
        CLASS = 'CLASS', 'Class Content'
        MATERIAL = 'MATERIAL', 'Study Material'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        RESOLVED = 'RESOLVED', 'Resolved'
        REJECTED = 'REJECTED', 'Rejected'

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_submitted')
    target_type = models.CharField(max_length=20, choices=TargetType.choices, db_index=True)
    target_id = models.CharField(max_length=128, db_index=True)
    reason = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True
    )
    admin_note = models.TextField(blank=True, default='')
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Abuse Report'
        verbose_name_plural = 'Abuse Reports'
        ordering = ['-created_at']


# ==========================================
# 12. PAYMENTS (PHASE 2 ARCHITECTURE)
# ==========================================

class Payment(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        UPI = 'UPI', 'UPI'
        DEBIT_CARD = 'DEBIT_CARD', 'Debit Card'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        NET_BANKING = 'NET_BANKING', 'Net Banking'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    gateway = models.CharField(max_length=50, default='sandbox')
    transaction_id = models.CharField(max_length=255, unique=True, db_index=True)
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UPI
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    gateway_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.transaction_id} - {self.user.email} - ₹{self.amount} ({self.status})"


# ==========================================
# 13. AUDIT LOGS
# ==========================================

class AuditLog(TimeStampedUUIDModel):
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    action = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=128, db_index=True)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        actor_email = self.actor.email if self.actor else 'SYSTEM'
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {actor_email} -> {self.action} on {self.object_type}:{self.object_id}"
