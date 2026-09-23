import secrets
import logging
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import FileResponse

# pyrefly: ignore [missing-import]
from rest_framework import generics, viewsets, status, filters, permissions
# pyrefly: ignore [missing-import]
from rest_framework.views import APIView
# pyrefly: ignore [missing-import]
from rest_framework.response import Response    
# pyrefly: ignore [missing-import]
from rest_framework.pagination import PageNumberPagination
# pyrefly: ignore [missing-import]
from rest_framework.views import exception_handler
# pyrefly: ignore [missing-import]
from rest_framework.permissions import AllowAny, IsAuthenticated
# pyrefly: ignore [missing-import]
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.tokens import RefreshToken
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

# pyrefly: ignore [missing-import]
from .models import (
    User, UserBlock, EmailVerificationToken, PasswordResetToken,
    StudentProfile, TeacherProfile, TeacherVerification,
    Batch, BatchAnnouncement, Enrollment, ClassContent, Attendance,
    StudyMaterial, Bookmark, ConnectionRequest, ContactAccess,
    Conversation, Message, MessageAttachment, Notification,
    Review, Report, Payment, AuditLog
)
# pyrefly: ignore [missing-import]
from .serializers import (
    UserDetailSerializer, UserSafePublicSerializer,
    StudentRegistrationSerializer, TeacherRegistrationSerializer,
    UnifiedRegistrationSerializer,
    CustomTokenObtainPairSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailVerificationSerializer, UserBlockSerializer,
    StudentProfileSerializer, StudentSafePublicSerializer,
    TeacherProfileSerializer, TeacherPublicSearchSerializer,
    TeacherVerificationSubmitSerializer, TeacherVerificationAdminSerializer,
    BatchPublicSerializer, BatchTeacherSerializer, BatchAnnouncementSerializer,
    EnrollmentSerializer, EnrollmentActionSerializer,
    ClassContentSerializer, AttendanceSerializer,
    StudyMaterialSerializer, BookmarkSerializer,
    MessageAttachmentSerializer, MessageSerializer,
    ConversationSerializer, SendMessageSerializer,
    ConnectionRequestSerializer, ConnectionRequestCreateSerializer, ContactDetailSerializer,
    NotificationSerializer, ReviewSerializer, ReviewCreateSerializer,
    ReportSerializer, ReportCreateSerializer,
    PaymentSerializer, PaymentInitiateSerializer, PaymentVerifySerializer,
    AuditLogSerializer
)

logger = logging.getLogger(__name__)

# ==========================================
# 0. API RESPONSE ENVELOPE, PAGINATION & EXCEPTIONS
# ==========================================

def api_response(success=True, message="Request successful", data=None, errors=None, status_code=200, pagination=None):
    payload = {
        "success": success,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    if errors is not None:
        payload["errors"] = errors
    if pagination is not None:
        payload["pagination"] = pagination
    return Response(payload, status=status_code)



# ==========================================
# 1. PERMISSIONS
# ==========================================

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role == User.Role.ADMIN or request.user.is_staff or request.user.is_superuser)
        )

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role == User.Role.STUDENT
        )

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role == User.Role.TEACHER
        )

def check_batch_access(user, batch):
    """
    Returns (has_access, is_teacher).
    """
    if user.is_staff or getattr(user, 'role', '') == 'ADMIN':
        return True, False
    teacher_profile = getattr(user, 'teacher_profile', None)
    if teacher_profile and batch.teacher == teacher_profile:
        return True, True
    student_profile = getattr(user, 'student_profile', None)
    if student_profile:
        is_enrolled = Enrollment.objects.filter(
            batch=batch,
            student=student_profile,
            status=Enrollment.Status.ACTIVE
        ).exists()
        if is_enrolled:
            return True, False
    return False, False


# ==========================================
# 2. CORE BUSINESS SERVICES
# ==========================================

class AuthService:
    @staticmethod
    @transaction.atomic
    def register_student(validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number', ''),
            profile_photo=validated_data.get('profile_photo'),
            role=User.Role.STUDENT,
            is_active=True,
            is_verified=False
        )
        StudentProfile.objects.create(
            user=user,
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender', ''),
            education_level=validated_data.get('education_level', ''),
            school_name=validated_data.get('school_name', ''),
            city=validated_data.get('city', ''),
            state=validated_data.get('state', ''),
            preferred_language=validated_data.get('preferred_language', ''),
            subjects_of_interest=validated_data.get('subjects_of_interest', []),
            bio=validated_data.get('bio', '')
        )
        AuthService.send_verification_email(user)
        return user

    @staticmethod
    @transaction.atomic
    def register_teacher(validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number', ''),
            profile_photo=validated_data.get('profile_photo'),
            role=User.Role.TEACHER,
            is_active=True,
            is_verified=False
        )
        TeacherProfile.objects.create(
            user=user,
            display_name=f"{user.first_name} {user.last_name}".strip(),
            bio=validated_data.get('bio', ''),
            qualification=validated_data.get('qualification', ''),
            experience_years=validated_data.get('experience_years', 0.0),
            subjects=validated_data.get('subjects', []),
            teaching_languages=validated_data.get('teaching_languages', []),
            exam_expertise=validated_data.get('exam_expertise', []),
            hourly_rate=validated_data.get('hourly_rate', 0.0),
            demo_video_url=validated_data.get('demo_video_url', ''),
            verification_status=TeacherProfile.VerificationStatus.PENDING_VERIFICATION
        )
        AuthService.send_verification_email(user)
        return user

    @staticmethod
    def send_verification_email(user):
        token_str = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=1)
        EmailVerificationToken.objects.create(user=user, token=token_str, expires_at=expires_at)
        subject = "Verify your TutorOn India Account"
        message = f"Hello {user.first_name},\n\nPlease verify your account with token:\n{token_str}\n\nTeam TutorOn India"
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:
            pass
        return token_str

    @staticmethod
    def verify_email(token_str):
        try:
            token = EmailVerificationToken.objects.select_related('user').get(token=token_str)
        except EmailVerificationToken.DoesNotExist:
            raise ValidationError("Invalid verification token.")
        if not token.is_valid():
            raise ValidationError("Verification token has expired or already been used.")
        token.is_used = True
        token.save()
        user = token.user
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        return user

    @staticmethod
    def request_password_reset(email):
        user = User.objects.filter(email=email.lower().strip(), is_active=True).first()
        if not user:
            return True
        token_str = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=2)
        PasswordResetToken.objects.create(user=user, token=token_str, expires_at=expires_at)
        subject = "Reset your TutorOn India Password"
        message = f"Hello {user.first_name},\n\nUse token below to reset password:\n{token_str}\n\nTeam TutorOn India"
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:
            pass
        return True

    @staticmethod
    def reset_password(token_str, new_password):
        try:
            token = PasswordResetToken.objects.select_related('user').get(token=token_str)
        except PasswordResetToken.DoesNotExist:
            raise ValidationError("Invalid reset token.")
        if not token.is_valid():
            raise ValidationError("Reset token has expired or already been used.")
        token.is_used = True
        token.save()
        user = token.user
        user.set_password(new_password)
        user.save()
        return user

    @staticmethod
    def is_user_blocked(user_a, user_b):
        return UserBlock.objects.filter(
            blocker__in=[user_a, user_b],
            blocked__in=[user_a, user_b]
        ).exists()

class TeacherVerificationService:
    @staticmethod
    @transaction.atomic
    def approve_verification(verification: TeacherVerification, admin_user, admin_note=""):
        if verification.status == TeacherVerification.Status.APPROVED:
            return verification
        verification.status = TeacherVerification.Status.APPROVED
        verification.reviewed_at = timezone.now()
        verification.reviewed_by = admin_user
        verification.admin_note = admin_note
        verification.save()

        profile = verification.teacher
        profile.verification_status = TeacherProfile.VerificationStatus.VERIFIED
        profile.save(update_fields=['verification_status', 'updated_at'])

        AuditLogService.log_action(
            actor=admin_user,
            action='TEACHER_VERIFICATION_APPROVED',
            object_type='TeacherVerification',
            object_id=str(verification.id),
            description=f"Approved verification for {profile.user.get_full_name()} ({profile.user.email})",
            metadata={'admin_note': admin_note}
        )
        NotificationService.create_notification(
            recipient=profile.user,
            title="Profile Verified!",
            message="Congratulations! Your teacher profile has been verified. You can now publish batches.",
            notification_type='SYSTEM',
            related_object_id=str(profile.id)
        )
        return verification

    @staticmethod
    @transaction.atomic
    def reject_verification(verification: TeacherVerification, admin_user, rejection_reason="", admin_note=""):
        verification.status = TeacherVerification.Status.REJECTED
        verification.reviewed_at = timezone.now()
        verification.reviewed_by = admin_user
        verification.rejection_reason = rejection_reason
        verification.admin_note = admin_note
        verification.save()

        profile = verification.teacher
        profile.verification_status = TeacherProfile.VerificationStatus.REJECTED
        profile.save(update_fields=['verification_status', 'updated_at'])

        AuditLogService.log_action(
            actor=admin_user,
            action='TEACHER_VERIFICATION_REJECTED',
            object_type='TeacherVerification',
            object_id=str(verification.id),
            description=f"Rejected verification for {profile.user.get_full_name()} ({profile.user.email})",
            metadata={'rejection_reason': rejection_reason, 'admin_note': admin_note}
        )
        NotificationService.create_notification(
            recipient=profile.user,
            title="Verification Rejected",
            message=f"Your teacher verification was rejected. Reason: {rejection_reason}",
            notification_type='SYSTEM',
            related_object_id=str(profile.id)
        )
        return verification

    @staticmethod
    def recalculate_rating(teacher_profile: TeacherProfile):
        stats = Review.objects.filter(
            teacher=teacher_profile,
            status=Review.Status.PUBLISHED
        ).aggregate(avg_rating=Avg('rating'), count=Count('id'))
        teacher_profile.average_rating = round(stats['avg_rating'] or 0.0, 2)
        teacher_profile.total_reviews = stats['count'] or 0
        teacher_profile.save(update_fields=['average_rating', 'total_reviews', 'updated_at'])

class EnrollmentService:
    @staticmethod
    def request_enrollment(student_profile, batch: Batch):
        if batch.status not in [Batch.Status.PUBLISHED, Batch.Status.ONGOING]:
            raise ValidationError("This batch is not open for enrollments.")

        existing = Enrollment.objects.filter(student=student_profile, batch=batch).first()
        if existing:
            if existing.status in [Enrollment.Status.ACTIVE, Enrollment.Status.APPROVED]:
                raise ValidationError("You are already actively enrolled in this batch.")
            if existing.status == Enrollment.Status.REQUESTED:
                raise ValidationError("You already have a pending enrollment request for this batch.")
            existing.status = Enrollment.Status.REQUESTED
            existing.requested_at = timezone.now()
            existing.save()
            enrollment = existing
        else:
            active_count = Enrollment.objects.filter(batch=batch, status=Enrollment.Status.ACTIVE).count()
            if active_count >= batch.capacity:
                raise ValidationError("This batch has reached maximum capacity.")
            enrollment = Enrollment.objects.create(
                student=student_profile,
                batch=batch,
                status=Enrollment.Status.REQUESTED,
                payment_status=Enrollment.PaymentStatus.PAID if batch.is_free else Enrollment.PaymentStatus.UNPAID
            )

        NotificationService.create_notification(
            recipient=batch.teacher.user,
            title="New Enrollment Request",
            message=f"{student_profile.user.get_full_name()} requested to join batch '{batch.title}'.",
            notification_type='ENROLLMENT_REQUEST',
            related_object_id=str(enrollment.id)
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def approve_enrollment(enrollment: Enrollment, approver):
        if enrollment.status == Enrollment.Status.ACTIVE:
            return enrollment
        batch = enrollment.batch
        active_count = Enrollment.objects.filter(batch=batch, status=Enrollment.Status.ACTIVE).count()
        if active_count >= batch.capacity:
            raise ValidationError("Batch is currently at full capacity.")

        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.approved_at = timezone.now()
        enrollment.approved_by = approver
        enrollment.save()

        # Update teacher total students
        teacher = batch.teacher
        total_unique = Enrollment.objects.filter(
            batch__teacher=teacher,
            status=Enrollment.Status.ACTIVE
        ).values('student').distinct().count()
        teacher.total_students = total_unique
        teacher.save(update_fields=['total_students', 'updated_at'])

        AuditLogService.log_action(
            actor=approver,
            action='ENROLLMENT_APPROVED',
            object_type='Enrollment',
            object_id=str(enrollment.id),
            description=f"Approved enrollment of {enrollment.student.user.get_full_name()} into {batch.title}"
        )
        NotificationService.create_notification(
            recipient=enrollment.student.user,
            title="Enrollment Approved!",
            message=f"You are now enrolled in '{batch.title}'.",
            notification_type='ENROLLMENT_APPROVED',
            related_object_id=str(batch.id)
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def reject_enrollment(enrollment: Enrollment, approver, reason=""):
        enrollment.status = Enrollment.Status.REJECTED
        enrollment.save()
        AuditLogService.log_action(
            actor=approver,
            action='ENROLLMENT_REJECTED',
            object_type='Enrollment',
            object_id=str(enrollment.id),
            description=f"Rejected enrollment of {enrollment.student.user.get_full_name()} into {enrollment.batch.title}"
        )
        NotificationService.create_notification(
            recipient=enrollment.student.user,
            title="Enrollment Update",
            message=f"Your request to join '{enrollment.batch.title}' was rejected.",
            notification_type='SYSTEM',
            related_object_id=str(enrollment.batch.id)
        )
        return enrollment

class ConnectionService:
    @staticmethod
    def create_connection_request(student_profile, teacher_profile, requested_by, message=""):
        if AuthService.is_user_blocked(student_profile.user, teacher_profile.user):
            raise ValidationError("Cannot initiate connection request with this user due to privacy/blocking settings.")

        existing = ConnectionRequest.objects.filter(
            student=student_profile,
            teacher=teacher_profile,
            status__in=[
                ConnectionRequest.Status.PENDING,
                ConnectionRequest.Status.STUDENT_APPROVED,
                ConnectionRequest.Status.ADMIN_APPROVED
            ]
        ).first()

        if existing:
            if existing.status == ConnectionRequest.Status.ADMIN_APPROVED:
                raise ValidationError("You are already connected and contact sharing is unlocked.")
            raise ValidationError("A pending connection request already exists between you and this teacher/student.")

        is_student_initiator = (requested_by == student_profile.user)
        with transaction.atomic():
            connection = ConnectionRequest.objects.create(
                student=student_profile,
                teacher=teacher_profile,
                requested_by=requested_by,
                message=message,
                status=ConnectionRequest.Status.STUDENT_APPROVED if is_student_initiator else ConnectionRequest.Status.PENDING,
                student_approved=is_student_initiator,
                admin_approved=False,
                contact_unlocked=False
            )
            ContactAccess.objects.create(
                connection=connection,
                student=student_profile,
                teacher=teacher_profile,
                status=ContactAccess.Status.PENDING
            )

        recipient = teacher_profile.user if is_student_initiator else student_profile.user
        sender_name = student_profile.user.get_full_name() if is_student_initiator else (teacher_profile.display_name or teacher_profile.user.get_full_name())
        NotificationService.create_notification(
            recipient=recipient,
            title="New Connection Request",
            message=f"{sender_name} sent you a connection request. Contact details remain locked until final admin approval.",
            notification_type='CONNECTION_REQUEST',
            related_object_id=str(connection.id)
        )
        return connection

    @staticmethod
    def student_approve(connection: ConnectionRequest, student_user):
        if connection.student.user != student_user:
            raise PermissionDenied("Only the invited student can approve this connection.")
        connection.student_approved = True
        connection.status = ConnectionRequest.Status.STUDENT_APPROVED
        connection.save(update_fields=['student_approved', 'status', 'updated_at'])

        NotificationService.create_notification(
            recipient=connection.teacher.user,
            title="Student Accepted Connection",
            message=f"{connection.student.user.get_full_name()} accepted your connection request. Waiting for admin contact unlock approval.",
            notification_type='SYSTEM',
            related_object_id=str(connection.id)
        )
        return connection

    @staticmethod
    @transaction.atomic
    def admin_approve(connection: ConnectionRequest, admin_user, reason="Admin verified connection"):
        connection.admin_approved = True
        connection.contact_unlocked = True
        connection.status = ConnectionRequest.Status.ADMIN_APPROVED
        connection.approved_at = timezone.now()
        connection.approved_by = admin_user
        connection.save()

        access, _ = ContactAccess.objects.get_or_create(
            connection=connection,
            defaults={'student': connection.student, 'teacher': connection.teacher}
        )
        access.status = ContactAccess.Status.APPROVED
        access.approved_at = timezone.now()
        access.approved_by = admin_user
        access.reason = reason
        access.save()

        AuditLogService.log_action(
            actor=admin_user,
            action='CONTACT_UNLOCK_APPROVED',
            object_type='ConnectionRequest',
            object_id=str(connection.id),
            description=f"Unlocked contact sharing between Student {connection.student.user.get_full_name()} and Teacher {connection.teacher.user.get_full_name()}",
            metadata={'reason': reason}
        )

        for user, title, msg in [
            (connection.student.user, "Contact Sharing Unlocked!", f"Connection with {connection.teacher.display_name or connection.teacher.user.get_full_name()} approved. Direct contact details are now unlocked."),
            (connection.teacher.user, "Contact Sharing Unlocked!", f"Connection with {connection.student.user.get_full_name()} approved by admin. Direct contact details are now unlocked.")
        ]:
            NotificationService.create_notification(
                recipient=user, title=title, message=msg,
                notification_type='CONNECTION_APPROVED', related_object_id=str(connection.id)
            )
        return connection

    @staticmethod
    @transaction.atomic
    def reject_connection(connection: ConnectionRequest, user, reason=""):
        connection.status = ConnectionRequest.Status.REJECTED
        connection.save()
        if hasattr(connection, 'contact_access'):
            connection.contact_access.status = ContactAccess.Status.REJECTED
            connection.contact_access.reason = reason
            connection.contact_access.save()
        if user.is_staff or getattr(user, 'role', '') == 'ADMIN':
            AuditLogService.log_action(
                actor=user,
                action='CONTACT_UNLOCK_REJECTED',
                object_type='ConnectionRequest',
                object_id=str(connection.id),
                description=f"Admin rejected connection request {connection.id}",
                metadata={'reason': reason}
            )
        return connection

class NotificationService:
    @staticmethod
    def create_notification(recipient, title, message, notification_type='SYSTEM', related_object_id=None, send_email=True):
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_id=str(related_object_id) if related_object_id else '',
            is_read=False
        )
        if send_email and recipient.email:
            try:
                subject = f"[TutorOn India] {title}"
                body = f"Hello {recipient.get_full_name()},\n\n{message}\n\nTeam TutorOn India"
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient.email], fail_silently=True)
            except Exception:
                pass
        return notification

    @staticmethod
    def send_upcoming_class_reminders(window_minutes=60):
        """
        Send CLASS_REMINDER notifications to all active enrolled students and teacher
        for classes scheduled within the next window_minutes.
        """
        now = timezone.now()
        upcoming_window = now + timedelta(minutes=window_minutes)
        upcoming_classes = ClassContent.objects.filter(
            is_published=True,
            scheduled_date__gte=now,
            scheduled_date__lte=upcoming_window
        ).select_related('batch', 'teacher__user')

        sent_count = 0
        for cls in upcoming_classes:
            link_info = f" Access Link: {cls.external_url}" if cls.external_url else ""
            msg = (
                f"Reminder: Class '{cls.title}' in batch '{cls.batch.title}' is scheduled for "
                f"{cls.scheduled_date.strftime('%Y-%m-%d %H:%M')}.{link_info}"
            )
            enrollments = Enrollment.objects.filter(
                batch=cls.batch,
                status=Enrollment.Status.ACTIVE
            ).select_related('student__user')

            recipients = [e.student.user for e in enrollments]
            if cls.teacher and cls.teacher.user:
                recipients.append(cls.teacher.user)

            for user in recipients:
                already_sent = Notification.objects.filter(
                    recipient=user,
                    notification_type=Notification.NotificationType.CLASS_REMINDER,
                    related_object_id=str(cls.id),
                    created_at__gte=now - timedelta(hours=2)
                ).exists()
                if not already_sent:
                    NotificationService.create_notification(
                        recipient=user,
                        title=f"Upcoming Class Reminder: {cls.title}",
                        message=msg,
                        notification_type=Notification.NotificationType.CLASS_REMINDER,
                        related_object_id=str(cls.id)
                    )
                    sent_count += 1
        return sent_count

class AuditLogService:
    @staticmethod
    def log_action(actor, action, object_type, object_id, description, metadata=None, ip_address=None, user_agent=""):
        return AuditLog.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )

class PaymentProcessor:
    @staticmethod
    @transaction.atomic
    def process_successful_payment(payment: Payment, gateway_response=None):
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        if gateway_response:
            payment.gateway_response = gateway_response
        payment.save()

        if payment.enrollment:
            enrollment = payment.enrollment
            enrollment.payment_status = Enrollment.PaymentStatus.PAID
            if enrollment.status == Enrollment.Status.PENDING_PAYMENT:
                enrollment.status = Enrollment.Status.PAYMENT_COMPLETED
            enrollment.save(update_fields=['payment_status', 'status', 'updated_at'])

        AuditLogService.log_action(
            actor=payment.user,
            action='PAYMENT_SUCCESS',
            object_type='Payment',
            object_id=str(payment.id),
            description=f"Payment of ₹{payment.amount} successful for user {payment.user.email}",
            metadata={'transaction_id': payment.transaction_id, 'amount': float(payment.amount)}
        )
        NotificationService.create_notification(
            recipient=payment.user,
            title="Payment Received",
            message=f"Received payment of ₹{payment.amount}. Transaction ID: {payment.transaction_id}",
            notification_type='PAYMENT_SUCCESS',
            related_object_id=str(payment.id)
        )
        return payment


# ==========================================
# 3. FILTERS
# ==========================================

class TeacherFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(method='filter_subject')
    language = django_filters.CharFilter(method='filter_language')
    exam_expertise = django_filters.CharFilter(method='filter_exam_expertise')
    qualification = django_filters.CharFilter(field_name='qualification', lookup_expr='icontains')
    min_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    max_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    min_price = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')

    class Meta:
        model = TeacherProfile
        fields = [
            'subject', 'language', 'exam_expertise', 'qualification',
            'min_experience', 'max_experience', 'min_rating',
            'min_price', 'max_price', 'is_featured'
        ]

    def filter_subject(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(subjects__icontains=value) | Q(bio__icontains=value))

    def filter_language(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(teaching_languages__icontains=value)

    def filter_exam_expertise(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(exam_expertise__icontains=value)


# ==========================================
# 4. AUTH & USER VIEWS
# ==========================================

def get_user_full_data(user):
    """
    Returns complete user profile data along with authentication tokens.
    """
    user_data = UserDetailSerializer(user).data
    profile_data = {}
    if user.role == User.Role.STUDENT and hasattr(user, 'student_profile'):
        profile_data = StudentProfileSerializer(user.student_profile).data
    elif user.role == User.Role.TEACHER and hasattr(user, 'teacher_profile'):
        profile_data = TeacherProfileSerializer(user.teacher_profile).data

    refresh = RefreshToken.for_user(user)
    tokens = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }

    return {
        'user_id': str(user.id),
        **user_data,
        'profile': profile_data,
        'tokens': tokens
    }


class UnifiedRegistrationView(APIView):
    """
    Single Unified Registration Endpoint for both Students and Teachers.
    Accepts role="STUDENT" (default) or role="TEACHER".
    Returns complete response data.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UnifiedRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        role = data.get('role', User.Role.STUDENT)

        if role == User.Role.TEACHER:
            user = AuthService.register_teacher(data)
            full_data = get_user_full_data(user)
            return api_response(
                success=True,
                message="Teacher registered successfully. Account pending admin verification.",
                data=full_data,
                status_code=status.HTTP_201_CREATED
            )
        else:
            user = AuthService.register_student(data)
            full_data = get_user_full_data(user)
            return api_response(
                success=True,
                message="Student registered successfully. Please verify your email.",
                data=full_data,
                status_code=status.HTTP_201_CREATED
            )


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_student(serializer.validated_data)
        full_data = get_user_full_data(user)
        return api_response(
            success=True,
            message="Student registered successfully. Please verify your email.",
            data=full_data,
            status_code=status.HTTP_201_CREATED
        )

class TeacherRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TeacherRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_teacher(serializer.validated_data)
        full_data = get_user_full_data(user)
        return api_response(
            success=True,
            message="Teacher registered successfully. Status: PENDING_VERIFICATION.",
            data=full_data,
            status_code=status.HTTP_201_CREATED
        )

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return api_response(
            success=True,
            message="Login successful",
            data=serializer.validated_data,
            status_code=status.HTTP_200_OK
        )

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return api_response(
            success=True,
            message="Token refreshed successfully",
            data=response.data,
            status_code=status.HTTP_200_OK
        )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return api_response(
                success=False,
                message="Refresh token is required",
                errors={"refresh": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return api_response(success=True, message="Successfully logged out")
        except Exception:
            return api_response(
                success=False,
                message="Invalid or expired token",
                errors={"refresh": ["Token is invalid or already blacklisted."]},
                status_code=status.HTTP_400_BAD_REQUEST
            )

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_email(serializer.validated_data['token'])
        return api_response(
            success=True,
            message="Email verified successfully. You can now log in.",
            data={"email": user.email}
        )

class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return api_response(success=False, message="Email is required", status_code=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(email=email.lower().strip()).first()
        if user and not user.is_verified:
            AuthService.send_verification_email(user)
        return api_response(success=True, message="If an unverified account exists, verification email was sent.")

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data['email'])
        return api_response(success=True, message="If an account exists, password reset instructions were sent.")

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(serializer.validated_data['token'], serializer.validated_data['new_password'])
        return api_response(success=True, message="Password reset successfully. You may now log in.")

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return api_response(success=True, message="Profile fetched successfully", data=serializer.data)

    def patch(self, request):
        serializer = UserDetailSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Profile updated successfully", data=serializer.data)

class UserBlockViewSet(viewsets.ModelViewSet):
    serializer_class = UserBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBlock.objects.filter(blocker=self.request.user).select_related('blocked')

    def perform_create(self, serializer):
        blocked_user = serializer.validated_data.get('blocked')
        if blocked_user == self.request.user:
            raise ValidationError("You cannot block yourself.")
        serializer.save(blocker=self.request.user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return api_response(success=True, message="Blocked users retrieved", data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_response(
            success=True, message="User blocked successfully",
            data=serializer.data, status_code=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(success=True, message="User unblocked successfully")


# ==========================================
# 5. STUDENT & TEACHER PROFILE VIEWS
# ==========================================

class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = StudentProfileSerializer(profile)
        return api_response(success=True, message="Student profile retrieved", data=serializer.data)

    def patch(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Student profile updated", data=serializer.data)

class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        active_enrollments = Enrollment.objects.filter(student=profile, status='ACTIVE').select_related('batch', 'batch__teacher__user')
        batch_ids = [e.batch_id for e in active_enrollments]

        upcoming_classes = ClassContent.objects.filter(batch_id__in=batch_ids, is_published=True).order_by('scheduled_date', 'order')[:5]
        recent_announcements = BatchAnnouncement.objects.filter(batch_id__in=batch_ids).order_by('-published_at')[:5]
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()
        recent_materials = StudyMaterial.objects.filter(batch_id__in=batch_ids).order_by('-published_at')[:5]

        total_attendance = Attendance.objects.filter(enrollment__student=profile).count()
        present_attendance = Attendance.objects.filter(enrollment__student=profile, status='PRESENT').count()

        data = {
            "enrolled_batches_count": len(batch_ids),
            "enrolled_batches": [
                {
                    "id": str(e.batch.id),
                    "title": e.batch.title,
                    "slug": e.batch.slug,
                    "subject": e.batch.subject,
                    "teacher_name": e.batch.teacher.user.get_full_name(),
                    "status": e.batch.status
                }
                for e in active_enrollments
            ],
            "upcoming_classes": [
                {
                    "id": str(c.id),
                    "batch_id": str(c.batch_id),
                    "title": c.title,
                    "class_type": c.class_type,
                    "scheduled_date": c.scheduled_date
                }
                for c in upcoming_classes
            ],
            "recent_announcements": [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "message": a.message,
                    "published_at": a.published_at
                }
                for a in recent_announcements
            ],
            "recent_materials": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "file_type": m.file_type,
                    "is_downloadable": m.is_downloadable,
                    "published_at": m.published_at
                }
                for m in recent_materials
            ],
            "unread_notifications_count": unread_notifications,
            "attendance_summary": {
                "total_marked": total_attendance,
                "present": present_attendance,
                "percentage": round((present_attendance / total_attendance) * 100, 1) if total_attendance > 0 else 100.0
            }
        }
        return api_response(success=True, message="Student dashboard retrieved", data=data)

class TeacherListView(generics.ListAPIView):
    """
    Public Teacher Search & Discovery.
    Strictly returns only VERIFIED and ACTIVE teachers.
    Private phone numbers and emails are never exposed.
    """
    permission_classes = [AllowAny]
    serializer_class = TeacherPublicSearchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TeacherFilter
    search_fields = ['display_name', 'user__first_name', 'user__last_name', 'qualification', 'bio']
    ordering_fields = ['average_rating', 'experience_years', 'total_students', 'created_at', 'hourly_rate']
    ordering = ['-average_rating', '-experience_years']

    def get_queryset(self):
        return TeacherProfile.objects.filter(
            verification_status=TeacherProfile.VerificationStatus.VERIFIED,
            user__is_active=True
        ).select_related('user')

class TeacherDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = TeacherPublicSearchSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return TeacherProfile.objects.filter(
            verification_status=TeacherProfile.VerificationStatus.VERIFIED,
            user__is_active=True
        ).select_related('user')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(success=True, message="Teacher details fetched", data=serializer.data)

class TeacherBatchesListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        teacher = TeacherProfile.objects.filter(id=id, user__is_active=True).first()
        if not teacher:
            return api_response(success=False, message="Teacher not found", status_code=404)
        batches = Batch.objects.filter(teacher=teacher, status__in=['PUBLISHED', 'ONGOING']).order_by('-created_at')
        serializer = BatchPublicSerializer(batches, many=True)
        return api_response(success=True, message="Teacher batches retrieved", data=serializer.data)

class TeacherReviewsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        teacher = TeacherProfile.objects.filter(id=id).first()
        if not teacher:
            return api_response(success=False, message="Teacher not found", status_code=404)
        reviews = Review.objects.filter(teacher=teacher, status='PUBLISHED').select_related('student__user', 'batch').order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return api_response(success=True, message="Teacher reviews retrieved", data=serializer.data)

class TeacherProfileView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
        serializer = TeacherProfileSerializer(profile)
        return api_response(success=True, message="Teacher profile retrieved", data=serializer.data)

    def patch(self, request):
        profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
        serializer = TeacherProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Teacher profile updated", data=serializer.data)

class TeacherVerificationSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
        serializer = TeacherVerificationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = serializer.save(teacher=profile, status=TeacherVerification.Status.PENDING)
        return api_response(
            success=True,
            message="Verification document submitted successfully. Waiting for admin approval.",
            data={"verification_id": str(verification.id), "status": verification.status},
            status_code=status.HTTP_201_CREATED
        )

class TeacherDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
        total_batches = Batch.objects.filter(teacher=profile).count()
        active_batches = Batch.objects.filter(teacher=profile, status__in=['PUBLISHED', 'ONGOING']).count()
        pending_enrollments = Enrollment.objects.filter(batch__teacher=profile, status='REQUESTED').count()
        upcoming_classes = ClassContent.objects.filter(teacher=profile).order_by('scheduled_date', 'order')[:5]
        recent_reviews = Review.objects.filter(teacher=profile, status='PUBLISHED').select_related('student__user', 'batch')[:5]

        data = {
            "total_students": profile.total_students,
            "total_batches": total_batches,
            "active_batches": active_batches,
            "pending_enrollment_requests": pending_enrollments,
            "average_rating": float(profile.average_rating),
            "total_reviews": profile.total_reviews,
            "verification_status": profile.verification_status,
            "upcoming_classes": [
                {
                    "id": str(c.id),
                    "batch_id": str(c.batch_id),
                    "batch_title": c.batch.title,
                    "title": c.title,
                    "class_type": c.class_type,
                    "scheduled_date": c.scheduled_date
                }
                for c in upcoming_classes
            ],
            "recent_reviews": [
                {
                    "id": str(r.id),
                    "student_name": r.student.user.get_full_name(),
                    "batch_title": r.batch.title,
                    "rating": r.rating,
                    "comment": r.comment,
                    "created_at": r.created_at
                }
                for r in recent_reviews
            ]
        }
        return api_response(success=True, message="Teacher dashboard retrieved", data=data)


# ==========================================
# 6. BATCH VIEWS
# ==========================================

class BatchPublicListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BatchPublicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'language', 'grade_level', 'is_free']
    search_fields = ['title', 'description', 'subject', 'teacher__display_name', 'teacher__user__first_name', 'teacher__user__last_name']
    ordering_fields = ['start_date', 'price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Batch.objects.filter(
            status__in=[Batch.Status.PUBLISHED, Batch.Status.ONGOING]
        ).select_related('teacher', 'teacher__user')

class BatchPublicDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = BatchPublicSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Batch.objects.filter(
            status__in=[Batch.Status.PUBLISHED, Batch.Status.ONGOING]
        ).select_related('teacher', 'teacher__user')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(success=True, message="Batch details retrieved", data=serializer.data)

class TeacherBatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchTeacherSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        teacher_profile = getattr(self.request.user, 'teacher_profile', None)
        if not teacher_profile:
            return Batch.objects.none()
        return Batch.objects.filter(teacher=teacher_profile)

    def perform_create(self, serializer):
        teacher_profile = getattr(self.request.user, 'teacher_profile', None)
        if not teacher_profile:
            raise PermissionDenied("Teacher profile required.")
        serializer.save(teacher=teacher_profile)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return api_response(success=True, message="Batches retrieved", data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return api_response(success=True, message="Batch created successfully", data=serializer.data, status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(success=True, message="Batch retrieved", data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return api_response(success=True, message="Batch updated successfully", data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(success=True, message="Batch deleted successfully")

class BatchAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get_batch(self, batch_id):
        try:
            return Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")

    def get(self, request, batch_id):
        batch = self.get_batch(batch_id)
        has_access, _ = check_batch_access(request.user, batch)
        if not has_access:
            raise PermissionDenied("You must be enrolled in this batch to view its announcements.")

        announcements = BatchAnnouncement.objects.filter(batch=batch)
        serializer = BatchAnnouncementSerializer(announcements, many=True)
        return api_response(success=True, message="Announcements retrieved", data=serializer.data)

    def post(self, request, batch_id):
        batch = self.get_batch(batch_id)
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if not (teacher_profile and batch.teacher == teacher_profile) and not request.user.is_staff:
            raise PermissionDenied("Only the batch teacher can publish announcements.")

        serializer = BatchAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save(batch=batch, teacher=batch.teacher)

        enrolled = Enrollment.objects.filter(batch=batch, status='ACTIVE').select_related('student__user')
        for e in enrolled:
            NotificationService.create_notification(
                recipient=e.student.user,
                title=f"New Announcement: {batch.title}",
                message=announcement.title,
                notification_type='TEACHER_ANNOUNCEMENT',
                related_object_id=str(announcement.id)
            )
        return api_response(success=True, message="Announcement published", data=serializer.data, status_code=status.HTTP_201_CREATED)


# ==========================================
# 7. ENROLLMENT VIEWS
# ==========================================

class BatchEnrollRequestView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, batch_id):
        student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        try:
            batch = Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")

        enrollment = EnrollmentService.request_enrollment(student_profile, batch)
        serializer = EnrollmentSerializer(enrollment)
        return api_response(
            success=True,
            message="Enrollment request submitted successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class StudentEnrollmentListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        student_profile = getattr(request.user, 'student_profile', None)
        if not student_profile:
            return api_response(success=True, data=[])
        enrollments = Enrollment.objects.filter(student=student_profile).select_related('batch', 'batch__teacher__user')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return api_response(success=True, message="Enrollments retrieved", data=serializer.data)

class StudentEnrollmentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, id):
        student_profile = getattr(request.user, 'student_profile', None)
        try:
            enrollment = Enrollment.objects.select_related('batch', 'batch__teacher__user').get(id=id, student=student_profile)
        except Enrollment.DoesNotExist:
            raise NotFound("Enrollment not found.")
        serializer = EnrollmentSerializer(enrollment)
        return api_response(success=True, message="Enrollment details retrieved", data=serializer.data)

class TeacherEnrollmentListView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if not teacher_profile:
            return api_response(success=True, data=[])
        enrollments = Enrollment.objects.filter(batch__teacher=teacher_profile).select_related('student__user', 'batch')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return api_response(success=True, message="Teacher enrollments retrieved", data=serializer.data)

class TeacherEnrollmentApproveView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, id):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        try:
            enrollment = Enrollment.objects.select_related('batch', 'student__user').get(id=id)
        except Enrollment.DoesNotExist:
            raise NotFound("Enrollment not found.")
        if enrollment.batch.teacher != teacher_profile and not request.user.is_staff:
            raise PermissionDenied("You can only manage enrollments for your own batches.")
        approved = EnrollmentService.approve_enrollment(enrollment, request.user)
        serializer = EnrollmentSerializer(approved)
        return api_response(success=True, message="Enrollment approved.", data=serializer.data)

class TeacherEnrollmentRejectView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, id):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        try:
            enrollment = Enrollment.objects.select_related('batch', 'student__user').get(id=id)
        except Enrollment.DoesNotExist:
            raise NotFound("Enrollment not found.")
        if enrollment.batch.teacher != teacher_profile and not request.user.is_staff:
            raise PermissionDenied("You can only manage enrollments for your own batches.")
        reason = request.data.get('reason', '')
        rejected = EnrollmentService.reject_enrollment(enrollment, request.user, reason)
        serializer = EnrollmentSerializer(rejected)
        return api_response(success=True, message="Enrollment rejected.", data=serializer.data)


# ==========================================
# 8. CLASS & ATTENDANCE VIEWS
# ==========================================

class BatchClassListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
        try:
            batch = Batch.objects.select_related('teacher').get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")
        has_access, _ = check_batch_access(request.user, batch)
        if not has_access:
            raise PermissionDenied("You must be actively enrolled in this batch to access its classes.")
        classes = ClassContent.objects.filter(batch=batch, is_published=True).order_by('order', 'scheduled_date')
        serializer = ClassContentSerializer(classes, many=True)
        return api_response(success=True, message="Batch classes retrieved", data=serializer.data)

class TeacherBatchClassCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, batch_id):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        try:
            batch = Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")
        if batch.teacher != teacher_profile and not request.user.is_staff:
            raise PermissionDenied("You can only add classes to your own batch.")

        data = request.data.copy()
        data['batch'] = batch.id
        serializer = ClassContentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(teacher=teacher_profile)
        return api_response(success=True, message="Class created successfully", data=serializer.data, status_code=status.HTTP_201_CREATED)

class TeacherClassDetailView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self, id, user):
        try:
            obj = ClassContent.objects.select_related('batch', 'teacher').get(id=id)
        except ClassContent.DoesNotExist:
            raise NotFound("Class not found.")
        teacher_profile = getattr(user, 'teacher_profile', None)
        if obj.teacher != teacher_profile and not user.is_staff:
            raise PermissionDenied("You can only edit classes belonging to your own batch.")
        return obj

    def patch(self, request, id):
        instance = self.get_object(id, request.user)
        serializer = ClassContentSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Class updated successfully", data=serializer.data)

    def delete(self, request, id):
        instance = self.get_object(id, request.user)
        instance.delete()
        return api_response(success=True, message="Class deleted successfully")

class ClassDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            class_obj = ClassContent.objects.select_related('batch', 'teacher', 'teacher__user').get(id=id)
        except ClassContent.DoesNotExist:
            raise NotFound("Class not found.")
        has_access, _ = check_batch_access(request.user, class_obj.batch)
        if not has_access:
            raise PermissionDenied("You are not authorized to view this class content.")
        serializer = ClassContentSerializer(class_obj)
        return api_response(success=True, message="Class details retrieved", data=serializer.data)

class AttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        try:
            class_obj = ClassContent.objects.select_related('batch', 'teacher').get(id=class_id)
        except ClassContent.DoesNotExist:
            raise NotFound("Class not found.")
        has_access, is_teacher = check_batch_access(request.user, class_obj.batch)
        if not has_access:
            raise PermissionDenied("Unauthorized to view attendance.")

        if is_teacher or request.user.is_staff:
            attendances = Attendance.objects.filter(class_content=class_obj).select_related('enrollment__student__user', 'marked_by')
        else:
            student_profile = getattr(request.user, 'student_profile', None)
            attendances = Attendance.objects.filter(class_content=class_obj, enrollment__student=student_profile).select_related('enrollment__student__user', 'marked_by')

        serializer = AttendanceSerializer(attendances, many=True)
        return api_response(success=True, message="Attendance records retrieved", data=serializer.data)

    def post(self, request, class_id):
        try:
            class_obj = ClassContent.objects.select_related('batch', 'teacher').get(id=class_id)
        except ClassContent.DoesNotExist:
            raise NotFound("Class not found.")
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if class_obj.teacher != teacher_profile and not request.user.is_staff:
            raise PermissionDenied("Only the batch teacher or admin can mark attendance.")

        enrollment_id = request.data.get('enrollment_id')
        attendance_status = request.data.get('status', 'PRESENT')
        try:
            enrollment = Enrollment.objects.get(id=enrollment_id, batch=class_obj.batch)
        except Enrollment.DoesNotExist:
            raise ValidationError("Valid enrollment in this batch is required.")

        attendance, created = Attendance.objects.update_or_create(
            enrollment=enrollment,
            class_content=class_obj,
            defaults={'status': attendance_status, 'marked_by': request.user}
        )
        serializer = AttendanceSerializer(attendance)
        return api_response(
            success=True, message="Attendance marked successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        )


# ==========================================
# 9. STUDY MATERIAL & BOOKMARK VIEWS
# ==========================================

class BatchMaterialListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, batch_id):
        try:
            batch = Batch.objects.select_related('teacher').get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")
        has_access, _ = check_batch_access(request.user, batch)
        if not has_access:
            raise PermissionDenied("You must be enrolled in this batch to access study materials.")
        materials = StudyMaterial.objects.filter(batch=batch)
        serializer = StudyMaterialSerializer(materials, many=True)
        return api_response(success=True, message="Study materials retrieved", data=serializer.data)

class TeacherBatchMaterialCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, batch_id):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        try:
            batch = Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")
        if batch.teacher != teacher_profile and not request.user.is_staff:
            raise PermissionDenied("You can only add study materials to your own batch.")

        file = request.FILES.get('file')
        if not file:
            raise ValidationError({"file": "File is required."})
        title = request.data.get('title')
        if not title:
            raise ValidationError({"title": "Title is required."})

        material = StudyMaterial.objects.create(
            batch=batch,
            teacher=teacher_profile,
            title=title,
            description=request.data.get('description', ''),
            file=file,
            is_downloadable=request.data.get('is_downloadable', 'true').lower() in ('true', '1')
        )
        enrolled = Enrollment.objects.filter(batch=batch, status='ACTIVE').select_related('student__user')
        for e in enrolled:
            NotificationService.create_notification(
                recipient=e.student.user,
                title=f"New Study Material: {material.title}",
                message=f"New material uploaded for batch '{batch.title}'.",
                notification_type='MATERIAL_UPLOADED',
                related_object_id=str(material.id)
            )
        serializer = StudyMaterialSerializer(material)
        return api_response(success=True, message="Material uploaded successfully", data=serializer.data, status_code=status.HTTP_201_CREATED)

class TeacherMaterialDetailView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self, id, user):
        try:
            obj = StudyMaterial.objects.select_related('batch', 'teacher').get(id=id)
        except StudyMaterial.DoesNotExist:
            raise NotFound("Study material not found.")
        teacher_profile = getattr(user, 'teacher_profile', None)
        if obj.teacher != teacher_profile and not user.is_staff:
            raise PermissionDenied("You can only edit study materials belonging to your own batch.")
        return obj

    def patch(self, request, id):
        material = self.get_object(id, request.user)
        serializer = StudyMaterialSerializer(material, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Material updated successfully", data=serializer.data)

    def delete(self, request, id):
        material = self.get_object(id, request.user)
        material.delete()
        return api_response(success=True, message="Material deleted successfully")

class MaterialDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            material = StudyMaterial.objects.select_related('batch').get(id=id)
        except StudyMaterial.DoesNotExist:
            raise NotFound("Study material not found.")
        has_access, is_teacher = check_batch_access(request.user, material.batch)
        if not has_access:
            raise PermissionDenied("You are not authorized to access this material.")
        if not material.is_downloadable and not (is_teacher or request.user.is_staff):
            raise PermissionDenied("This study material is restricted for online view only and cannot be downloaded.")
        if not material.file:
            raise NotFound("File not found on server.")
        return FileResponse(material.file.open(), as_attachment=True, filename=material.file.name.split('/')[-1])

class MaterialBookmarkView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, id):
        student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        try:
            material = StudyMaterial.objects.get(id=id)
        except StudyMaterial.DoesNotExist:
            raise NotFound("Study material not found.")
        bookmark, created = Bookmark.objects.get_or_create(student=student_profile, material=material)
        return api_response(
            success=True,
            message="Material bookmarked successfully." if created else "Material is already bookmarked.",
            data={"bookmark_id": str(bookmark.id)}
        )

    def delete(self, request, id):
        student_profile = getattr(request.user, 'student_profile', None)
        if student_profile:
            Bookmark.objects.filter(student=student_profile, material_id=id).delete()
        return api_response(success=True, message="Bookmark removed successfully.")

class StudentBookmarkListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        student_profile = getattr(request.user, 'student_profile', None)
        if not student_profile:
            return api_response(success=True, data=[])
        bookmarks = Bookmark.objects.filter(student=student_profile).select_related('material', 'material__batch', 'material__teacher__user')
        serializer = BookmarkSerializer(bookmarks, many=True)
        return api_response(success=True, message="Bookmarks retrieved", data=serializer.data)


# ==========================================
# 10. CONNECTIONS & STRICT CONTACT PRIVACY VIEWS
# ==========================================

class ConnectionRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        query = Q()
        if hasattr(user, 'student_profile'):
            query |= Q(student=user.student_profile)
        if hasattr(user, 'teacher_profile'):
            query |= Q(teacher=user.teacher_profile)

        if not query and not user.is_staff:
            return api_response(success=True, data=[])
        connections = ConnectionRequest.objects.filter(query).select_related(
            'student__user', 'teacher__user', 'requested_by'
        )
        serializer = ConnectionRequestSerializer(connections, many=True)
        return api_response(success=True, message="Connection requests retrieved", data=serializer.data)

    def post(self, request):
        serializer = ConnectionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        message = serializer.validated_data.get('message', '')

        if user.role == User.Role.STUDENT:
            student_profile, _ = StudentProfile.objects.get_or_create(user=user)
            teacher_id = serializer.validated_data.get('teacher_id')
            try:
                teacher_profile = TeacherProfile.objects.get(id=teacher_id)
            except TeacherProfile.DoesNotExist:
                raise NotFound("Teacher not found.")
        elif user.role == User.Role.TEACHER:
            teacher_profile, _ = TeacherProfile.objects.get_or_create(user=user)
            student_id = serializer.validated_data.get('student_id')
            try:
                student_profile = StudentProfile.objects.get(id=student_id)
            except StudentProfile.DoesNotExist:
                raise NotFound("Student not found.")
        else:
            raise ValidationError("Admins cannot initiate connections as a participant.")

        connection = ConnectionService.create_connection_request(
            student_profile=student_profile,
            teacher_profile=teacher_profile,
            requested_by=user,
            message=message
        )
        res_serializer = ConnectionRequestSerializer(connection)
        return api_response(
            success=True,
            message="Connection request submitted. Contact sharing remains hidden until approved.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class ConnectionApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            connection = ConnectionRequest.objects.select_related('student__user', 'teacher__user').get(id=id)
        except ConnectionRequest.DoesNotExist:
            raise NotFound("Connection request not found.")

        user = request.user
        if user.is_staff or getattr(user, 'role', '') == 'ADMIN':
            reason = request.data.get('reason', 'Admin verified connection')
            ConnectionService.admin_approve(connection, user, reason=reason)
            return api_response(success=True, message="Admin approved contact unlock for this connection.", data={"contact_unlocked": True, "status": connection.status})

        if hasattr(user, 'student_profile') and connection.student == user.student_profile:
            ConnectionService.student_approve(connection, user)
            return api_response(success=True, message="Student accepted connection. Waiting for admin contact unlock approval.", data={"student_approved": True, "status": connection.status})

        raise PermissionDenied("You are not authorized to approve this connection.")

class ConnectionRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            connection = ConnectionRequest.objects.select_related('student__user', 'teacher__user').get(id=id)
        except ConnectionRequest.DoesNotExist:
            raise NotFound("Connection request not found.")

        user = request.user
        student_user = connection.student.user
        teacher_user = connection.teacher.user
        if user not in [student_user, teacher_user] and not user.is_staff:
            raise PermissionDenied("You are not authorized to reject this connection.")

        reason = request.data.get('reason', '')
        ConnectionService.reject_connection(connection, user, reason)
        return api_response(success=True, message="Connection rejected.", data={"status": connection.status})

class ConnectionContactDetailView(APIView):
    """
    DEDICATED SECURE CONTACT UNLOCK ENDPOINT.
    Returns personal contact information (email, phone) ONLY after:
    1. Authentication
    2. Connection participant verification
    3. ContactAccess status is APPROVED
    4. No active block between participants
    5. Active account status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            connection = ConnectionRequest.objects.select_related('student__user', 'teacher__user', 'contact_access').get(id=id)
        except ConnectionRequest.DoesNotExist:
            raise NotFound("Connection not found.")

        user = request.user
        student_user = connection.student.user
        teacher_user = connection.teacher.user

        if user not in [student_user, teacher_user] and not user.is_staff:
            raise PermissionDenied("You are not a participant of this connection.")

        access = getattr(connection, 'contact_access', None)
        if not (connection.contact_unlocked and access and access.status == ContactAccess.Status.APPROVED):
            return api_response(
                success=False,
                message="Contact information is not unlocked for this connection. Both parties and admin approval are required.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if AuthService.is_user_blocked(student_user, teacher_user):
            raise PermissionDenied("Contact information is restricted due to a user block.")

        if user == student_user:
            target_user = teacher_user
        elif user == teacher_user:
            target_user = student_user
        else:
            return api_response(
                success=True,
                message="Admin contact overview",
                data={
                    "student": {"name": student_user.get_full_name(), "email": student_user.email, "phone_number": student_user.phone_number},
                    "teacher": {"name": teacher_user.get_full_name(), "email": teacher_user.email, "phone_number": teacher_user.phone_number}
                }
            )

        if not target_user.is_active:
            raise PermissionDenied("Target account is inactive or suspended.")

        data = {
            "user_id": target_user.id,
            "full_name": target_user.get_full_name(),
            "role": target_user.role,
            "email": target_user.email,
            "phone_number": target_user.phone_number,
            "contact_unlocked_at": access.approved_at
        }
        serializer = ContactDetailSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return api_response(success=True, message="Contact details unlocked and fetched successfully.", data=serializer.data)


# ==========================================
# 11. INTERNAL MESSAGING VIEWS
# ==========================================

class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        query = Q()
        if hasattr(user, 'student_profile'):
            query |= Q(student=user.student_profile)
        if hasattr(user, 'teacher_profile'):
            query |= Q(teacher=user.teacher_profile)

        if not query and not user.is_staff:
            return api_response(success=True, data=[])

        conversations = Conversation.objects.filter(query).select_related('student__user', 'teacher__user').prefetch_related('messages')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return api_response(success=True, message="Conversations retrieved", data=serializer.data)

    def post(self, request):
        user = request.user
        teacher_id = request.data.get('teacher_id')
        student_id = request.data.get('student_id')

        if user.role == User.Role.STUDENT:
            student_profile, _ = StudentProfile.objects.get_or_create(user=user)
            if not teacher_id:
                raise ValidationError({"teacher_id": "Teacher ID is required to start a conversation."})
            try:
                teacher_profile = TeacherProfile.objects.get(id=teacher_id)
            except TeacherProfile.DoesNotExist:
                raise NotFound("Teacher not found.")
        elif user.role == User.Role.TEACHER:
            teacher_profile, _ = TeacherProfile.objects.get_or_create(user=user)
            if not student_id:
                raise ValidationError({"student_id": "Student ID is required to start a conversation."})
            try:
                student_profile = StudentProfile.objects.get(id=student_id)
            except StudentProfile.DoesNotExist:
                raise NotFound("Student not found.")
        else:
            raise ValidationError("Admins cannot start private conversations as a student or teacher.")

        if AuthService.is_user_blocked(student_profile.user, teacher_profile.user):
            raise PermissionDenied("Cannot start conversation due to blocking settings.")

        conversation, created = Conversation.objects.get_or_create(student=student_profile, teacher=teacher_profile)
        serializer = ConversationSerializer(conversation, context={'request': request})
        return api_response(
            success=True, message="Conversation initialized",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            conv = Conversation.objects.select_related('student__user', 'teacher__user').get(id=id)
        except Conversation.DoesNotExist:
            raise NotFound("Conversation not found.")
        if request.user not in [conv.student.user, conv.teacher.user] and not request.user.is_staff:
            raise PermissionDenied("You are not a participant in this conversation.")

        messages = conv.messages.all().select_related('sender').prefetch_related('attachments').order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return api_response(success=True, message="Messages retrieved", data=serializer.data)

class ConversationMessageSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            conv = Conversation.objects.select_related('student__user', 'teacher__user').get(id=id)
        except Conversation.DoesNotExist:
            raise NotFound("Conversation not found.")

        user = request.user
        if user not in [conv.student.user, conv.teacher.user] and not user.is_staff:
            raise PermissionDenied("You are not a participant in this conversation.")

        counter_user = conv.teacher.user if user == conv.student.user else conv.student.user
        if AuthService.is_user_blocked(user, counter_user):
            raise PermissionDenied("Cannot send message: communications between these users are blocked.")

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            conversation=conv,
            sender=user,
            content=serializer.validated_data['content']
        )
        attachment_file = request.FILES.get('attachment')
        if attachment_file:
            MessageAttachment.objects.create(
                message=message,
                file=attachment_file,
                file_name=attachment_file.name,
                file_size=attachment_file.size
            )
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])

        NotificationService.create_notification(
            recipient=counter_user,
            title=f"New Message from {user.get_full_name()}",
            message=message.content[:80] + ("..." if len(message.content) > 80 else ""),
            notification_type='NEW_MESSAGE',
            related_object_id=str(conv.id)
        )
        res_serializer = MessageSerializer(message)
        return api_response(success=True, message="Message sent successfully", data=res_serializer.data, status_code=status.HTTP_201_CREATED)

class MessageMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            message = Message.objects.select_related('conversation').get(id=id)
        except Message.DoesNotExist:
            raise NotFound("Message not found.")

        if message.sender == request.user:
            return api_response(success=True, message="Sender already read their own message.")

        conv = message.conversation
        if request.user not in [conv.student.user, conv.teacher.user] and not request.user.is_staff:
            raise PermissionDenied("Unauthorized to mark this message as read.")

        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=['is_read', 'read_at'])
        return api_response(success=True, message="Message marked as read.")


# ==========================================
# 12. NOTIFICATION VIEWS
# ==========================================

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        unread_count = notifications.filter(is_read=False).count()
        serializer = NotificationSerializer(notifications[:50], many=True)
        return api_response(
            success=True,
            message="Notifications retrieved",
            data={"unread_count": unread_count, "notifications": serializer.data}
        )

class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            notification = Notification.objects.get(id=id, recipient=request.user)
        except Notification.DoesNotExist:
            raise NotFound("Notification not found.")
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return api_response(success=True, message="Notification marked as read.")

class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return api_response(success=True, message=f"{updated_count} notifications marked as read.")


# ==========================================
# 13. REVIEW VIEWS
# ==========================================

class BatchReviewCreateView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, batch_id):
        student_profile = getattr(request.user, 'student_profile', None)
        if not student_profile:
            raise PermissionDenied("Student profile required.")
        try:
            batch = Batch.objects.select_related('teacher').get(id=batch_id)
        except Batch.DoesNotExist:
            raise NotFound("Batch not found.")

        is_enrolled = Enrollment.objects.filter(
            batch=batch, student=student_profile, status__in=['ACTIVE', 'COMPLETED']
        ).exists()
        if not is_enrolled:
            raise PermissionDenied("Only students enrolled in this batch can submit a review.")

        if Review.objects.filter(student=student_profile, batch=batch).exists():
            raise ValidationError("You have already submitted a review for this batch.")

        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(
            student=student_profile,
            teacher=batch.teacher,
            batch=batch,
            status=Review.Status.PUBLISHED
        )
        TeacherVerificationService.recalculate_rating(batch.teacher)
        res_serializer = ReviewSerializer(review)
        return api_response(success=True, message="Review submitted successfully", data=res_serializer.data, status_code=status.HTTP_201_CREATED)

class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, id):
        try:
            return Review.objects.select_related('student__user', 'teacher').get(id=id)
        except Review.DoesNotExist:
            raise NotFound("Review not found.")

    def patch(self, request, id):
        review = self.get_object(id)
        user = request.user
        is_owner = (hasattr(user, 'student_profile') and review.student == user.student_profile)

        if not is_owner and not user.is_staff:
            raise PermissionDenied("Unauthorized to edit this review.")

        if user.is_staff and 'status' in request.data:
            review.status = request.data['status']
            review.save(update_fields=['status'])
            AuditLogService.log_action(
                actor=user, action='REVIEW_MODERATED', object_type='Review',
                object_id=str(review.id), description=f"Admin set review status to {review.status}"
            )
            TeacherVerificationService.recalculate_rating(review.teacher)

        if is_owner:
            serializer = ReviewCreateSerializer(review, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            TeacherVerificationService.recalculate_rating(review.teacher)

        res_serializer = ReviewSerializer(review)
        return api_response(success=True, message="Review updated successfully", data=res_serializer.data)

    def delete(self, request, id):
        review = self.get_object(id)
        user = request.user
        is_owner = (hasattr(user, 'student_profile') and review.student == user.student_profile)
        if not is_owner and not user.is_staff:
            raise PermissionDenied("Unauthorized to delete this review.")

        teacher = review.teacher
        review.delete()
        TeacherVerificationService.recalculate_rating(teacher)
        return api_response(success=True, message="Review deleted successfully.")


# ==========================================
# 14. REPORT VIEWS
# ==========================================

class ReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(reporter=request.user, status=Report.Status.OPEN)
        res_serializer = ReportSerializer(report)
        return api_response(
            success=True,
            message="Report submitted successfully. Our safety and moderation team will review it.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class MyReportsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.filter(reporter=request.user)
        serializer = ReportSerializer(reports, many=True)
        return api_response(success=True, message="Your reports retrieved", data=serializer.data)


# ==========================================
# 15. PAYMENT VIEWS (PHASE 2 ARCHITECTURE)
# ==========================================

class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrollment_id = serializer.validated_data['enrollment_id']
        payment_method = serializer.validated_data['payment_method']
        try:
            enrollment = Enrollment.objects.select_related('batch').get(id=enrollment_id, student__user=request.user)
        except Enrollment.DoesNotExist:
            raise NotFound("Enrollment not found.")

        if enrollment.payment_status == Enrollment.PaymentStatus.PAID:
            raise ValidationError("Payment is already completed for this enrollment.")

        amount = enrollment.batch.price
        transaction_id = f"order_{secrets.token_hex(8)}"
        payment = Payment.objects.create(
            user=request.user,
            enrollment=enrollment,
            amount=amount,
            currency='INR',
            gateway='sandbox',
            transaction_id=transaction_id,
            payment_method=payment_method,
            status=Payment.Status.PENDING
        )
        return api_response(
            success=True,
            message="Payment initiated successfully",
            data={
                "payment_id": str(payment.id),
                "transaction_id": transaction_id,
                "amount": float(amount),
                "currency": "INR",
                "status": "PENDING"
            },
            status_code=status.HTTP_201_CREATED
        )

class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_id = serializer.validated_data['transaction_id']
        payment_id = serializer.validated_data['payment_id']
        signature = serializer.validated_data['signature']

        try:
            payment = Payment.objects.select_related('enrollment', 'user').get(transaction_id=transaction_id, user=request.user)
        except Payment.DoesNotExist:
            raise NotFound("Payment transaction not found.")

        if not payment_id or not signature:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=['status'])
            return api_response(success=False, message="Payment verification failed", status_code=status.HTTP_400_BAD_REQUEST)

        updated_payment = PaymentProcessor.process_successful_payment(
            payment=payment,
            gateway_response={"payment_id": payment_id, "signature": signature}
        )
        res_serializer = PaymentSerializer(updated_payment)
        return api_response(success=True, message="Payment verified successfully.", data=res_serializer.data)

class StudentPaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).select_related('enrollment__batch')
        serializer = PaymentSerializer(payments, many=True)
        return api_response(success=True, message="Payment history retrieved", data=serializer.data)


# ==========================================
# 16. ADMIN MANAGEMENT PANEL REST VIEWS
# ==========================================

class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
        verified_teachers = TeacherProfile.objects.filter(verification_status=TeacherProfile.VerificationStatus.VERIFIED).count()
        pending_teacher_approvals = TeacherVerification.objects.filter(status=TeacherVerification.Status.PENDING).count()

        total_batches = Batch.objects.count()
        active_batches = Batch.objects.filter(status__in=[Batch.Status.PUBLISHED, Batch.Status.ONGOING]).count()
        total_enrollments = Enrollment.objects.count()
        active_enrollments = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).count()

        total_revenue = Payment.objects.filter(status=Payment.Status.SUCCESS).aggregate(total=Sum('amount'))['total'] or 0.0
        pending_reports = Report.objects.filter(status=Report.Status.OPEN).count()
        recent_activity = AuditLog.objects.select_related('actor')[:10]

        data = {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "verified_teachers": verified_teachers,
            "pending_teacher_approvals": pending_teacher_approvals,
            "total_batches": total_batches,
            "active_batches": active_batches,
            "total_enrollments": total_enrollments,
            "active_enrollments": active_enrollments,
            "total_revenue": float(total_revenue),
            "pending_reports": pending_reports,
            "recent_activity": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "actor": log.actor.email if log.actor else 'SYSTEM',
                    "description": log.description,
                    "created_at": log.created_at
                }
                for log in recent_activity
            ]
        }
        return api_response(success=True, message="Admin dashboard statistics retrieved", data=data)

class AdminUsersListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserDetailSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']
    queryset = User.objects.all()

class AdminTeachersListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = TeacherProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['verification_status']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'display_name']
    queryset = TeacherProfile.objects.select_related('user').all()

class AdminStudentsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = StudentProfileSerializer
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'city']
    queryset = StudentProfile.objects.select_related('user').all()

class AdminTeacherVerificationsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = TeacherVerificationAdminSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    queryset = TeacherVerification.objects.select_related('teacher__user', 'reviewed_by').all()

class AdminTeacherVerificationDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]
    serializer_class = TeacherVerificationAdminSerializer
    lookup_field = 'id'
    queryset = TeacherVerification.objects.select_related('teacher__user', 'reviewed_by').all()

class AdminTeacherVerificationApproveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        try:
            verification = TeacherVerification.objects.select_related('teacher__user').get(id=id)
        except TeacherVerification.DoesNotExist:
            raise NotFound("Teacher verification not found.")
        admin_note = request.data.get('admin_note', '')
        approved = TeacherVerificationService.approve_verification(verification=verification, admin_user=request.user, admin_note=admin_note)
        serializer = TeacherVerificationAdminSerializer(approved)
        return api_response(success=True, message="Teacher verification approved. Teacher status set to VERIFIED.", data=serializer.data)

class AdminTeacherVerificationRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        try:
            verification = TeacherVerification.objects.select_related('teacher__user').get(id=id)
        except TeacherVerification.DoesNotExist:
            raise NotFound("Teacher verification not found.")
        rejection_reason = request.data.get('rejection_reason', 'Documents did not meet criteria')
        admin_note = request.data.get('admin_note', '')
        rejected = TeacherVerificationService.reject_verification(
            verification=verification, admin_user=request.user,
            rejection_reason=rejection_reason, admin_note=admin_note
        )
        serializer = TeacherVerificationAdminSerializer(rejected)
        return api_response(success=True, message="Teacher verification rejected.", data=serializer.data)

class AdminConnectionsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = ConnectionRequestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'contact_unlocked']
    queryset = ConnectionRequest.objects.select_related('student__user', 'teacher__user').all()

class AdminBatchesListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = BatchPublicSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'subject']
    queryset = Batch.objects.select_related('teacher__user').all()

class AdminEnrollmentsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payment_status']
    queryset = Enrollment.objects.select_related('student__user', 'batch').all()

class AdminReviewsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    queryset = Review.objects.select_related('student__user', 'teacher__user', 'batch').all()

class AdminReportsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = ReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'target_type']
    queryset = Report.objects.select_related('reporter', 'resolved_by').all()

class AdminReportResolveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        try:
            report = Report.objects.get(id=id)
        except Report.DoesNotExist:
            raise NotFound("Report not found.")
        report.status = request.data.get('status', Report.Status.RESOLVED)
        report.admin_note = request.data.get('admin_note', '')
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        AuditLogService.log_action(
            actor=request.user,
            action='REPORT_RESOLVED',
            object_type='Report',
            object_id=str(report.id),
            description=f"Admin resolved report on {report.target_type}:{report.target_id} with status {report.status}"
        )
        serializer = ReportSerializer(report)
        return api_response(success=True, message="Report status updated successfully", data=serializer.data)

class AdminPaymentsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'gateway']
    queryset = Payment.objects.select_related('user', 'enrollment__batch').all()

class AdminAuditLogsListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['action', 'object_type']
    search_fields = ['description', 'actor__email', 'object_id']
    queryset = AuditLog.objects.select_related('actor').all()


class AdminConnectionApproveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        try:
            connection = ConnectionRequest.objects.select_related('student__user', 'teacher__user').get(id=id)
        except ConnectionRequest.DoesNotExist:
            raise NotFound("Connection request not found.")
        reason = request.data.get('reason', 'Admin verified and approved contact unlock')
        approved = ConnectionService.admin_approve(connection=connection, admin_user=request.user, reason=reason)
        serializer = ConnectionRequestSerializer(approved)
        return api_response(
            success=True,
            message="Connection and contact sharing unlocked successfully.",
            data=serializer.data
        )


class AdminConnectionRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        try:
            connection = ConnectionRequest.objects.select_related('student__user', 'teacher__user').get(id=id)
        except ConnectionRequest.DoesNotExist:
            raise NotFound("Connection request not found.")
        reason = request.data.get('reason', 'Admin rejected connection')
        rejected = ConnectionService.reject_connection(connection=connection, user=request.user, reason=reason)
        serializer = ConnectionRequestSerializer(rejected)
        return api_response(
            success=True,
            message="Connection rejected.",
            data=serializer.data
        )


class AdminSendClassRemindersView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        window_minutes = int(request.data.get('window_minutes', 60))
        sent_count = NotificationService.send_upcoming_class_reminders(window_minutes=window_minutes)
        return api_response(
            success=True,
            message=f"Dispatched {sent_count} class reminders for classes in the next {window_minutes} minutes.",
            data={"reminders_sent": sent_count, "window_minutes": window_minutes}
        )

