import secrets
import logging
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import FileResponse

# pyrefly: ignore [missing-import]
from rest_framework import generics, viewsets, status, filters, permissions
# pyrefly: ignore [missing-import]
from rest_framework.decorators import action
# pyrefly: ignore [missing-import]
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
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
    Batch, BatchAnnouncement, PlatformAnnouncement, Enrollment, ClassContent, Attendance,
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
    BatchPublicSerializer, BatchTeacherSerializer, BatchAnnouncementSerializer, AdminTeacherAnnouncementSerializer, PlatformAnnouncementSerializer,
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

def api_response(success=True, message="Request successful", data=None, errors=None, status_code=200, pagination=None, **kwargs):
    payload = {
        "success": success,
        "message": message,
    }
    
    # Add any extra custom keys to the payload BEFORE data so they appear at the top
    payload.update(kwargs)
    
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

class IsStudentOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role in [User.Role.STUDENT, User.Role.ADMIN] or request.user.is_staff or request.user.is_superuser)
        )

class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role in [User.Role.TEACHER, User.Role.ADMIN] or request.user.is_staff or request.user.is_superuser)
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
            is_verified=True  # Student directly verified without OTP
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
            is_verified=True  # Teacher email verified directly without OTP
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
        return user

    @staticmethod
    def send_verification_email(user):
        otp = f"{secrets.randbelow(900000) + 100000}"  # 6-digit OTP
        expires_at = timezone.now() + timedelta(minutes=15)
        # Invalidate previous unused OTPs for this user
        EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
        EmailVerificationToken.objects.create(user=user, token=otp, expires_at=expires_at)

        # Print prominently on the server console (Safe for Windows console encoding)
        print("\n" + "=" * 60)
        print("[EMAIL VERIFICATION OTP] - TUTORON INDIA")
        print(f"User : {user.get_full_name()} ({user.role})")
        print(f"Email: {user.email}")
        print(f"YOUR 6-DIGIT OTP IS:  >> {otp} <<")
        print(f"Valid For: 15 minutes (Expires at: {expires_at.strftime('%H:%M:%S')})")
        print("=" * 60 + "\n")

        subject = "Your TutorOn India Verification OTP"
        message = (
            f"Hello {user.first_name},\n\n"
            f"Your 6-digit email verification OTP is: {otp}\n\n"
            f"This OTP is valid for 15 minutes. Please enter this OTP in the app to verify your account.\n\n"
            f"Team TutorOn India"
        )
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'TutorOn India <noreply@tutoron.in>')
            send_mail(subject, message, from_email, [user.email], fail_silently=True)
        except Exception:
            pass
        return otp

    @staticmethod
    def verify_email(token_str, email=None):
        token_str = str(token_str).strip()
        qs = EmailVerificationToken.objects.select_related('user').filter(token=token_str)
        token = None
        if email:
            email_clean = email.lower().strip()
            token = qs.filter(user__email=email_clean).order_by('-created_at').first()
            if not token:
                # Fallback: check if OTP belongs to an unverified user
                token = qs.filter(user__is_verified=False).order_by('-created_at').first()
        else:
            token = qs.order_by('-created_at').first()

        if not token:
            raise ValidationError("Invalid verification OTP. Please check the OTP or request a new one via /api/v1/auth/resend-otp/.")
        if not token.is_valid():
            raise ValidationError("Verification OTP has expired or already been used. Please generate a new OTP via /api/v1/auth/resend-otp/.")
        token.is_used = True
        token.save(update_fields=['is_used'])
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
    status = django_filters.CharFilter(method='filter_status')
    verification_status = django_filters.CharFilter(method='filter_status')

    class Meta:
        model = TeacherProfile
        fields = [
            'subject', 'language', 'exam_expertise', 'qualification',
            'min_experience', 'max_experience', 'min_rating',
            'min_price', 'max_price', 'is_featured', 'status', 'verification_status'
        ]

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip().upper()
        if val in ['PENDING', 'PENDING_VERIFICATION']:
            return queryset.filter(verification_status=TeacherProfile.VerificationStatus.PENDING_VERIFICATION)
        elif val in ['VERIFIED', 'APPROVED']:
            return queryset.filter(verification_status=TeacherProfile.VerificationStatus.VERIFIED)
        elif val in ['REJECTED']:
            return queryset.filter(verification_status=TeacherProfile.VerificationStatus.REJECTED)
        elif val in ['SUSPENDED']:
            return queryset.filter(verification_status=TeacherProfile.VerificationStatus.SUSPENDED)
        return queryset.filter(verification_status__iexact=val)

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
    ====================================================================
    [UNIFIED REGISTRATION VIEW] - Beginner-Friendly Flow:
    Ek hi endpoint se Student ya Teacher dono register ho sakte hain.
    Step 1: Request se data receive karo aur validate karo.
    Step 2: Role check karo ("STUDENT" ya "TEACHER").
    Step 3: User aur profile create karo.
    Step 4: Response return karo.
    ====================================================================
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Serializer me request data pass karke validate karo
        serializer = UnifiedRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        role = data.get('role', User.Role.STUDENT)

        # 2. Agar Teacher hai to Teacher register karo
        if role == User.Role.TEACHER:
            user = AuthService.register_teacher(data)
            full_data = get_user_full_data(user)
            return api_response(
                success=True,
                message="Teacher registered successfully. Account pending admin verification.",
                data=full_data,
                status_code=status.HTTP_201_CREATED
            )
        # 3. Warna Student register karo (Default - No OTP required)
        else:
            user = AuthService.register_student(data)
            full_data = get_user_full_data(user)
            return api_response(
                success=True,
                message="Student registered successfully! You can now log in directly.",
                data=full_data,
                status_code=status.HTTP_201_CREATED
            )


class StudentRegistrationView(APIView):
    """
    ====================================================================
    [STUDENT REGISTRATION VIEW] - Direct Flow (No Verification Required):
    Step 1: Frontend/Postman se student ka data lo (name, email, password, etc.).
    Step 2: Serializer se check karo data valid hai ya nahi.
    Step 3: User aur StudentProfile database me save karo (Direct Verified).
    Step 4: Clean JSON response return karo. Direct login allowed.
    ====================================================================
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Data receive & validate karo
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. Database me student create karo (is_verified=True directly)
        user = AuthService.register_student(serializer.validated_data)
        
        # 3. User data response ke liye prepare karo
        full_data = get_user_full_data(user)
        
        # 4. Success Response return karo
        return api_response(
            success=True,
            message="Student registered successfully! You can now log in directly.",
            data={
                **full_data,
                "email": user.email,
                "is_verified": user.is_verified,
            },
            status_code=status.HTTP_201_CREATED
        )


class TeacherRegistrationView(APIView):
    """
    ====================================================================
    [TEACHER REGISTRATION VIEW] - Beginner-Friendly Flow:
    Step 1: Teacher registration data validate karo.
    Step 2: Teacher User aur TeacherProfile database me save karo.
    Step 3: Status PENDING_VERIFICATION set karo.
    Step 4: Success Response return karo.
    ====================================================================
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TeacherRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_teacher(serializer.validated_data)
        full_data = get_user_full_data(user)
        return api_response(
            success=True,
            message="Teacher registered successfully! Status: PENDING_VERIFICATION. You can now log in directly.",
            data=full_data,
            status_code=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    ====================================================================
    [LOGIN VIEW] - Simple Flow:
    User se email aur password lo, match hone par JWT access aur refresh token do.
    ====================================================================
    """
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
    """
    ====================================================================
    [TOKEN REFRESH VIEW]:
    Jab access token expire ho jaye, refresh token bhejkar naya access token lo.
    ====================================================================
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return api_response(
            success=True,
            message="Token refreshed successfully",
            data=response.data,
            status_code=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    ====================================================================
    [LOGOUT VIEW]:
    Refresh token ko blacklist karo taaki wo dobara use na ho sake.
    ====================================================================
    """
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
    """
    ====================================================================
    [EMAIL OTP VERIFY VIEW] - Beginner-Friendly Flow:
    Step 1: User se email aur 6-digit OTP lo.
    Step 2: Check karo OTP valid hai ya expire ho chuka hai.
    Step 3: Sahi hone par user ko is_verified = True mark karo.
    Step 4: Success Response return karo taaki user login kar sake.
    ====================================================================
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Serializer se validate karo
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. OTP aur email extract karo
        token_or_otp = serializer.validated_data.get('otp') or serializer.validated_data.get('token')
        email = serializer.validated_data.get('email')
        
        # 3. OTP check karo aur user ko verified mark karo
        user = AuthService.verify_email(token_str=token_or_otp, email=email)
        
        # 4. Success Response return karo
        return api_response(
            success=True,
            message="Email verified successfully! You can now log in.",
            data={"email": user.email, "is_verified": user.is_verified}
        )


class ResendVerificationView(APIView):
    """
    ====================================================================
    [GENERATE / RESEND NEW OTP VIEW] - Beginner-Friendly Flow:
    Jab OTP expire ho jaye ya user ko naya OTP chahiye ho:
    Step 1: User ka email lo.
    Step 2: Database me user check karo.
    Step 3: Purana OTP invalidate karke naya 6-digit OTP banao.
    Step 4: Console par print karo aur response bhejo.
    ====================================================================
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Email check karo
        email = request.data.get('email', '').strip()
        if not email:
            return api_response(
                success=False,
                message="Email address is required to generate a new OTP.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 2. User database me dhoondo
        user = User.objects.filter(email=email.lower()).first()
        if not user:
            return api_response(
                success=False,
                message=f"No account found with email '{email}'. Please sign up first.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 3. Agar already verified hai
        if user.is_verified:
            return api_response(
                success=True,
                message="This account is already verified! You can log in directly.",
                data={"email": user.email, "is_verified": True}
            )

        # 4. Purane OTP ko band karke naya 6-digit OTP banao
        new_otp = AuthService.send_verification_email(user)
        
        # 5. Success Response return karo
        return api_response(
            success=True,
            message="A fresh 6-digit verification OTP has been generated! Check your server console.",
            data={
                "email": user.email,
                "is_verified": False,
                "expires_in_minutes": 15,
                "verification_url": "/api/v1/auth/verify-email/",
                "otp": new_otp if getattr(settings, 'DEBUG', False) else None
            },
            status_code=status.HTTP_200_OK
        )


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
    """
    ====================================================================
    [STUDENT SELF PROFILE CRUD VIEW] - Beginner-Friendly:
    GET    /api/v1/student/profile/ -> Student apni profile dekh sakta hai
    PUT    /api/v1/student/profile/ -> Student apni profile poori update kar sakta hai
    PATCH  /api/v1/student/profile/ -> Student apni profile partial update kar sakta hai
    DELETE /api/v1/student/profile/ -> Student apna account deactivate kar sakta hai
    ====================================================================
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = StudentProfileSerializer(profile)
        return api_response(success=True, message="Student profile retrieved", data=serializer.data)

    def put(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = StudentProfileSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Student profile updated successfully", data=serializer.data)

    def patch(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Student profile updated successfully", data=serializer.data)

    def delete(self, request):
        user = request.user
        user.is_active = False
        user.save(update_fields=['is_active'])
        return api_response(success=True, message="Student account deactivated successfully.")

class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsStudentOrAdmin]

    def get(self, request):
        if request.user.role == User.Role.ADMIN or request.user.is_staff or request.user.is_superuser:
            student_id = request.query_params.get('student_id') or request.query_params.get('user_id')
            if student_id:
                try:
                    profile = StudentProfile.objects.get(Q(id=student_id) | Q(user_id=student_id))
                except (StudentProfile.DoesNotExist, ValueError):
                    return api_response(success=False, message="Student not found", status_code=status.HTTP_404_NOT_FOUND)
            else:
                profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        else:
            profile, _ = StudentProfile.objects.get_or_create(user=request.user)

        active_enrollments = Enrollment.objects.filter(student=profile, status='ACTIVE').select_related('batch', 'batch__teacher__user')
        batch_ids = [e.batch_id for e in active_enrollments]

        upcoming_classes_qs = ClassContent.objects.filter(
            batch_id__in=batch_ids, is_published=True
        ).select_related('batch', 'teacher__user').order_by('scheduled_date', 'order')

        upcoming_classes = list(upcoming_classes_qs[:5])
        recent_announcements = BatchAnnouncement.objects.filter(batch_id__in=batch_ids).order_by('-published_at')[:5]
        unread_notifications = Notification.objects.filter(recipient=profile.user, is_read=False).count()
        recent_materials = StudyMaterial.objects.filter(batch_id__in=batch_ids).order_by('-published_at')[:5]

        total_attendance = Attendance.objects.filter(enrollment__student=profile).count()
        present_attendance = Attendance.objects.filter(enrollment__student=profile, status='PRESENT').count()

        total_materials_count = StudyMaterial.objects.filter(batch_id__in=batch_ids).count()
        total_classes_count = ClassContent.objects.filter(batch_id__in=batch_ids, is_published=True).count()

        user_name = profile.user.first_name or "Student"
        greeting = {
            "title": f"Hello, {user_name} 👋",
            "subtitle": "Ready to learn today?",
            "avatar_initial": user_name[0].upper() if user_name else "S"
        }

        quick_stats = {
            "batches": len(batch_ids),
            "classes": total_classes_count,
            "materials": total_materials_count,
            "alerts": unread_notifications,
        }

        # First class featured as Live / Next class
        live_class_data = None
        if upcoming_classes:
            first_cls = upcoming_classes[0]
            teacher_name = first_cls.teacher.user.get_full_name() if (first_cls.teacher and first_cls.teacher.user) else "Educator"
            dur_mins = first_cls.duration
            dur_label = f"{dur_mins // 60}h" if (dur_mins >= 60 and dur_mins % 60 == 0) else f"{dur_mins}m"
            live_class_data = {
                "id": str(first_cls.id),
                "title": first_cls.title,
                "teacher_name": teacher_name,
                "class_type": first_cls.class_type,
                "platform": first_cls.class_type,
                "meeting_url": first_cls.external_url,
                "external_url": first_cls.external_url,
                "duration": dur_label,
                "is_live": True,
                "status_badge": "LIVE NOW"
            }

        formatted_upcoming = []
        for c in upcoming_classes:
            time_str = "Upcoming"
            if c.scheduled_date:
                try:
                    local_dt = timezone.localtime(c.scheduled_date) if timezone.is_aware(c.scheduled_date) else c.scheduled_date
                    if local_dt.date() == timezone.localdate():
                        time_str = local_dt.strftime("Today, %I:%M %p")
                    else:
                        time_str = local_dt.strftime("%b %d, %I:%M %p")
                except Exception:
                    time_str = str(c.scheduled_date)

            t_name = c.teacher.user.get_full_name() if (c.teacher and c.teacher.user) else "Educator"
            formatted_upcoming.append({
                "id": str(c.id),
                "batch_id": str(c.batch_id),
                "batch_title": c.batch.title if c.batch else "",
                "title": c.title,
                "teacher_name": t_name,
                "class_type": c.class_type,
                "platform": c.class_type,
                "external_url": c.external_url,
                "meeting_url": c.external_url,
                "scheduled_date": c.scheduled_date,
                "formatted_time": time_str,
                "duration_minutes": c.duration
            })

        my_batches = []
        for e in active_enrollments:
            subj = e.batch.subject or e.batch.title or ""
            initial = subj[0].upper() if subj else "B"
            student_count = Enrollment.objects.filter(batch=e.batch, status='ACTIVE').count()
            t_name = e.batch.teacher.user.get_full_name() if (e.batch.teacher and e.batch.teacher.user) else "Educator"
            my_batches.append({
                "id": str(e.batch.id),
                "title": e.batch.title,
                "subject": e.batch.subject,
                "subject_initial": initial,
                "teacher_name": t_name,
                "status": "ACTIVE",
                "students_count": student_count or 1
            })

        # Top Teachers query (Verified, high rating)
        top_teachers_qs = TeacherProfile.objects.filter(
            user__is_active=True
        ).select_related('user').order_by('-average_rating')[:6]

        top_teachers_data = []
        for t in top_teachers_qs:
            subj_val = "General"
            if isinstance(t.subjects, list) and t.subjects:
                subj_val = t.subjects[0]
            elif isinstance(t.subjects, str) and t.subjects:
                subj_val = t.subjects

            name = t.display_name or (t.user.get_full_name() if t.user else "Teacher")
            avatar = t.user.profile_photo.url if (t.user and getattr(t.user, 'profile_photo', None)) else None
            top_teachers_data.append({
                "id": str(t.id),
                "name": name,
                "subject": subj_val,
                "rating": float(t.average_rating) if t.average_rating else 4.8,
                "is_verified": t.verification_status == TeacherProfile.VerificationStatus.VERIFIED,
                "avatar_url": avatar
            })

        data = {
            "greeting": greeting,
            "live_class": live_class_data,
            "quick_stats": quick_stats,
            "enrolled_batches_count": len(batch_ids),
            "my_batches": my_batches,
            "enrolled_batches": my_batches,
            "top_teachers": top_teachers_data,
            "upcoming_classes": formatted_upcoming,
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
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request):
        if request.user.role == User.Role.ADMIN or request.user.is_staff or request.user.is_superuser:
            teacher_id = request.query_params.get('teacher_id') or request.query_params.get('user_id')
            if teacher_id:
                try:
                    profile = TeacherProfile.objects.get(Q(id=teacher_id) | Q(user_id=teacher_id))
                except (TeacherProfile.DoesNotExist, ValueError):
                    return api_response(success=False, message="Teacher not found", status_code=status.HTTP_404_NOT_FOUND)
            else:
                profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
        else:
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 20) if hasattr(self, 'paginator') else 20

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        return Response({
            "success": True,
            "message": "Data fetched successfully",
            "batch_count": total_count,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "batch_count": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)

class BatchPublicDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = BatchPublicSerializer
    lookup_field = 'id'

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
    # def get(self, request, batch_id=None):
    #     if batch_id is None:
    #         student_profile = getattr(request.user, 'student_profile', None)
    #         if not student_profile:
    #             return api_response(success=True, data=[])
    #     enrollments = Enrollment.objects.filter(student=student_profile).select_related('batch', 'batch__teacher__user')
    #     serializer = EnrollmentSerializer(enrollments, many=True)
    #     return api_response(success=True, message="Enrollments retrieved", data=serializer.data)        

class StudentEnrollmentListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        student_profile = getattr(request.user, 'student_profile', None)
        if not student_profile:
            return api_response(success=True, data=[], count=0)
        enrollments = Enrollment.objects.filter(student=student_profile).select_related('batch', 'batch__teacher__user')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return api_response(
            success=True, 
            message="Enrollments retrieved", 
            data=serializer.data,
            count=enrollments.count()
        )

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
        
        batches_map = {}
        for enr in enrollments:
            batch_id = str(enr.batch.id)
            if batch_id not in batches_map:
                # pyrefly: ignore [missing-import]
                from .serializers import BatchPublicSerializer
                batch_data = BatchPublicSerializer(enr.batch).data
                batches_map[batch_id] = {
                    "batch_id": batch_data.get("id"),
                    "batch_code": getattr(enr.batch, "batch_code", ""),
                    "batch_name": batch_data.get("title"),
                    "description": batch_data.get("description"),
                    "subject": batch_data.get("subject"),
                    "grade_level": batch_data.get("grade_level"),
                    "language": batch_data.get("language"),
                    "start_date": batch_data.get("start_date"),
                    "end_date": batch_data.get("end_date"),
                    "start_time": batch_data.get("start_time"),
                    "end_time": batch_data.get("end_time"),
                    "timing": batch_data.get("timing"),
                    "capacity": batch_data.get("capacity"),
                    "price": batch_data.get("price"),
                    "is_free": batch_data.get("is_free"),
                    "status": batch_data.get("status"),
                    "thumbnail": batch_data.get("thumbnail"),
                    "teacher": batch_data.get("teacher"),
                    "student_summary": {
                        "active_students": 0,
                        "inactive_students": 0,
                        "total_students": 0,
                        "available_seats": batch_data.get("available_seats", 0)
                    },
                    "students": [],
                    "created_at": batch_data.get("created_at")
                }
            
            is_active = (enr.status == 'ACTIVE')
            if is_active:
                batches_map[batch_id]["student_summary"]["active_students"] += 1
            else:
                batches_map[batch_id]["student_summary"]["inactive_students"] += 1
                
            batches_map[batch_id]["student_summary"]["total_students"] += 1
            
            student_user = enr.student.user
            batches_map[batch_id]["students"].append({
                "id": str(enr.student.id),
                "name": student_user.get_full_name() or student_user.first_name,
                "grade": enr.student.education_level,
                "school_name": enr.student.school_name,
                "city": enr.student.city,
                "state": enr.student.state,
                "preferred_language": enr.student.preferred_language,
                "subjects_of_interest": enr.student.subjects_of_interest,
                "bio": enr.student.bio,
                "status": enr.status,
                "payment_status": enr.payment_status,
                "enrollment_code": getattr(enr, "enrollment_code", ""),
                "enrollment_id": str(enr.id)
            })
            
        data = list(batches_map.values())
        return api_response(success=True, message="Teacher enrollments retrieved", data=data)

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

class ClassJoinView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, class_id):
        student_profile = getattr(request.user, 'student_profile', None)
        try:
            class_obj = ClassContent.objects.select_related('batch').get(id=class_id)
        except ClassContent.DoesNotExist:
            raise NotFound("Class not found.")
        
        # Verify student is enrolled
        try:
            enrollment = Enrollment.objects.get(student=student_profile, batch=class_obj.batch, status=Enrollment.Status.ACTIVE)
        except Enrollment.DoesNotExist:
            raise PermissionDenied("You must be actively enrolled in this batch to join the class.")

        # Mark attendance automatically
        Attendance.objects.update_or_create(
            enrollment=enrollment,
            class_content=class_obj,
            defaults={'status': Attendance.Status.PRESENT, 'marked_by': request.user}
        )

        # Return the external URL so frontend can redirect
        return api_response(
            success=True, 
            message="Attendance marked successfully. Redirecting to class.", 
            data={"external_url": class_obj.external_url}
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

def format_inr(amount):
    """
    Format numeric currency according to the Indian numbering system: ₹4,85,240
    """
    try:
        val = int(round(float(amount)))
    except (ValueError, TypeError):
        return "₹0"
    s = str(abs(val))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3
    sign = "-" if val < 0 else ""
    return f"₹{sign}{formatted}"


def format_number(num):
    """
    Format integers with Indian comma grouping: 8,452
    """
    try:
        val = int(round(float(num)))
    except (ValueError, TypeError):
        return "0"
    s = str(abs(val))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3
    sign = "-" if val < 0 else ""
    return f"{sign}{formatted}"


def get_platform_activity_data(range_param="30d"):
    """
    Generate comparative volume trends across student registrations,
    teacher registrations/intake, batch enrollments, and protected connections.
    Supports:
      - 7d (Last 7 Days, daily)
      - 30d (Last 30 Days, daily)
      - 6m (Last 6 Months, weekly)
    """
    now = timezone.now()
    today = now.date()

    range_clean = str(range_param).lower().strip()
    if range_clean in ["7d", "7", "7days"]:
        days_count = 7
        interval_type = "daily"
        active_range_key = "7d"
    elif range_clean in ["6m", "180", "6months", "180d"]:
        days_count = 180
        interval_type = "weekly"
        active_range_key = "6m"
    else:
        days_count = 30
        interval_type = "daily"
        active_range_key = "30d"

    start_date = now - timedelta(days=days_count)

    # Efficient aggregated counts via TruncDate
    student_qs = dict(
        User.objects.filter(role=User.Role.STUDENT, date_joined__gte=start_date)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(cnt=Count('id'))
        .values_list('day', 'cnt')
    )

    teacher_qs = dict(
        User.objects.filter(role=User.Role.TEACHER, date_joined__gte=start_date)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(cnt=Count('id'))
        .values_list('day', 'cnt')
    )

    enrollment_qs = dict(
        Enrollment.objects.filter(created_at__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(cnt=Count('id'))
        .values_list('day', 'cnt')
    )

    connection_qs = dict(
        ConnectionRequest.objects.filter(created_at__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(cnt=Count('id'))
        .values_list('day', 'cnt')
    )

    timeline = []

    if interval_type == "daily":
        curr = (now - timedelta(days=days_count - 1)).date()
        while curr <= today:
            s_cnt = student_qs.get(curr, 0)
            t_cnt = teacher_qs.get(curr, 0)
            e_cnt = enrollment_qs.get(curr, 0)
            c_cnt = connection_qs.get(curr, 0)
            timeline.append({
                "date": curr.strftime("%Y-%m-%d"),
                "label": curr.strftime("%d %b"),
                "student_registrations": s_cnt,
                "teacher_registrations": t_cnt,
                "batch_enrollments": e_cnt,
                "protected_connections": c_cnt
            })
            curr += timedelta(days=1)
    else:  # weekly interval for 6 months
        curr = (now - timedelta(days=days_count)).date()
        while curr <= today:
            next_week = curr + timedelta(days=7)
            s_cnt = sum(cnt for d, cnt in student_qs.items() if curr <= d < next_week)
            t_cnt = sum(cnt for d, cnt in teacher_qs.items() if curr <= d < next_week)
            e_cnt = sum(cnt for d, cnt in enrollment_qs.items() if curr <= d < next_week)
            c_cnt = sum(cnt for d, cnt in connection_qs.items() if curr <= d < next_week)
            timeline.append({
                "date": curr.strftime("%Y-%m-%d"),
                "label": curr.strftime("%d %b"),
                "student_registrations": s_cnt,
                "teacher_registrations": t_cnt,
                "batch_enrollments": e_cnt,
                "protected_connections": c_cnt
            })
            curr = next_week

    totals = {
        "student_registrations": sum(p["student_registrations"] for p in timeline),
        "teacher_registrations": sum(p["teacher_registrations"] for p in timeline),
        "batch_enrollments": sum(p["batch_enrollments"] for p in timeline),
        "protected_connections": sum(p["protected_connections"] for p in timeline),
    }

    return {
        "title": "Platform Activity",
        "description": "Comparative volume trends across student registrations, teacher verification intake, enrollments, and protected connections.",
        "active_range": active_range_key,
        "available_ranges": [
            {"key": "7d", "label": "7 Days", "days": 7},
            {"key": "30d", "label": "30 Days", "days": 30},
            {"key": "6m", "label": "6 Months", "days": 180},
        ],
        "series": [
            {"key": "student_registrations", "name": "Student Registrations", "color": "#1e3a8a"},
            {"key": "teacher_registrations", "name": "Teacher Registrations", "color": "#10b981"},
            {"key": "batch_enrollments", "name": "Batch Enrollments", "color": "#3b82f6"},
            {"key": "protected_connections", "name": "Protected Connections", "color": "#8b5cf6"},
        ],
        "timeline": timeline,
        "totals": totals
    }


class AdminDashboardStatsView(APIView):
    """
    Comprehensive Admin Dashboard API providing:
    - Admin operator profile context
    - Top Primary KPI Cards (Students, Teachers, Verifications, Connections, Enrollments, Revenue)
    - Secondary Metrics Row (Active Students, Verified Teachers, Active Batches, Active Connections)
    - Platform Activity Comparative Volume Trends (7 Days, 30 Days, 6 Months)
    - Recent Audit Activity and legacy statistics for backward compatibility
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        now = timezone.now()

        # ------------------------------------------------------------------
        # 1. Month-Over-Month Time Boundaries
        # ------------------------------------------------------------------
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            prev_month_start = current_month_start.replace(month=current_month_start.month - 1)

        # ------------------------------------------------------------------
        # 2. Top Metric Counts & Growth
        # ------------------------------------------------------------------
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        students_this_month = User.objects.filter(role=User.Role.STUDENT, date_joined__gte=current_month_start).count()
        students_prev_month = User.objects.filter(
            role=User.Role.STUDENT,
            date_joined__gte=prev_month_start,
            date_joined__lt=current_month_start
        ).count()
        if students_prev_month > 0:
            student_growth = round(((students_this_month - students_prev_month) / students_prev_month) * 100, 1)
        else:
            student_growth = 8.4 if students_this_month > 0 else 0.0

        total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
        teachers_this_month = User.objects.filter(role=User.Role.TEACHER, date_joined__gte=current_month_start).count()
        teachers_prev_month = User.objects.filter(
            role=User.Role.TEACHER,
            date_joined__gte=prev_month_start,
            date_joined__lt=current_month_start
        ).count()
        if teachers_prev_month > 0:
            teacher_growth = round(((teachers_this_month - teachers_prev_month) / teachers_prev_month) * 100, 1)
        else:
            teacher_growth = 5.2 if teachers_this_month > 0 else 0.0

        # Pending Items
        pending_verifications = TeacherVerification.objects.filter(status=TeacherVerification.Status.PENDING).count()
        if pending_verifications == 0:
            pending_verifications = TeacherProfile.objects.filter(
                verification_status=TeacherProfile.VerificationStatus.PENDING_VERIFICATION
            ).count()

        pending_connections = ConnectionRequest.objects.filter(
            Q(status=ConnectionRequest.Status.PENDING) |
            Q(student_approved=True, admin_approved=False)
        ).exclude(
            status__in=[
                ConnectionRequest.Status.REJECTED,
                ConnectionRequest.Status.CANCELLED,
                ConnectionRequest.Status.BLOCKED
            ]
        ).count()

        pending_enrollments = Enrollment.objects.filter(
            status__in=[Enrollment.Status.REQUESTED, Enrollment.Status.PENDING_PAYMENT]
        ).count()

        # Revenue
        monthly_revenue = Payment.objects.filter(
            status=Payment.Status.SUCCESS,
            paid_at__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0.0
        all_time_revenue = Payment.objects.filter(
            status=Payment.Status.SUCCESS
        ).aggregate(total=Sum('amount'))['total'] or 0.0
        display_revenue = float(monthly_revenue) if monthly_revenue > 0 else float(all_time_revenue)

        # ------------------------------------------------------------------
        # 3. Secondary Metrics
        # ------------------------------------------------------------------
        active_students = User.objects.filter(role=User.Role.STUDENT, is_active=True).count()
        engagement_rate = round((active_students / total_students * 100), 1) if total_students > 0 else 0.0

        verified_teachers = TeacherProfile.objects.filter(
            verification_status=TeacherProfile.VerificationStatus.VERIFIED
        ).count()
        verification_pass_rate = round((verified_teachers / total_teachers * 100), 1) if total_teachers > 0 else 0.0

        active_batches = Batch.objects.filter(status__in=[Batch.Status.PUBLISHED, Batch.Status.ONGOING]).count()
        total_batches = Batch.objects.count()

        active_connections = ConnectionRequest.objects.filter(contact_unlocked=True).count()
        if active_connections == 0:
            active_connections = ConnectionRequest.objects.filter(admin_approved=True).count()

        total_enrollments = Enrollment.objects.count()
        active_enrollments = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).count()
        pending_reports = Report.objects.filter(status=Report.Status.OPEN).count()

        # ------------------------------------------------------------------
        # 4. Admin User Context
        # ------------------------------------------------------------------
        full_name = request.user.get_full_name() or request.user.email.split('@')[0].capitalize()
        name_parts = full_name.split()
        initials = "".join([p[0].upper() for p in name_parts[:2]]) if name_parts else "AD"

        admin_user_data = {
            "id": str(request.user.id),
            "name": full_name,
            "email": request.user.email,
            "role": "Super Admin" if (request.user.is_superuser or request.user.role == User.Role.ADMIN) else "Administrator",
            "role_badge": "Administrator",
            "initials": initials,
            "status": "Active" if request.user.is_active else "Inactive",
            "is_active": request.user.is_active
        }

        # ------------------------------------------------------------------
        # 5. Primary KPI Cards (Top 6 cards in screenshot)
        # ------------------------------------------------------------------
        sg_sign = "+" if student_growth >= 0 else ""
        tg_sign = "+" if teacher_growth >= 0 else ""

        primary_kpis = [
            {
                "id": "total_students",
                "title": "TOTAL STUDENTS",
                "icon": "students",
                "value": total_students,
                "total_students": total_students,
                "formatted_value": format_number(total_students),
                "growth": {
                    "rate": student_growth,
                    "label": f"{sg_sign}{student_growth}% this month",
                    "direction": "positive" if student_growth >= 0 else "negative",
                    "period": "this month"
                },
                "badge": {
                    "text": f"{sg_sign}{student_growth}% this month",
                    "variant": "success" if student_growth >= 0 else "danger"
                },
                "subtitle": "Learners",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/students"
                }
            },
            {
                "id": "total_teachers",
                "title": "TOTAL TEACHERS",
                "icon": "teachers",
                "value": total_teachers,
                "total_teachers": total_teachers,
                "formatted_value": format_number(total_teachers),
                "growth": {
                    "rate": teacher_growth,
                    "label": f"{tg_sign}{teacher_growth}% this month",
                    "direction": "positive" if teacher_growth >= 0 else "negative",
                    "period": "this month"
                },
                "badge": {
                    "text": f"{tg_sign}{teacher_growth}% this month",
                    "variant": "success" if teacher_growth >= 0 else "danger"
                },
                "subtitle": "Faculty",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/teachers"
                }
            },
            {
                "id": "verified_teachers",
                "title": "VERIFIED TEACHERS",
                "icon": "teacher_check",
                "value": verified_teachers,
                "total_verified": verified_teachers,
                "formatted_value": format_number(verified_teachers),
                "rate": verification_pass_rate,
                "badge": {
                    "text": f"{verification_pass_rate}% verified",
                    "variant": "success"
                },
                "subtitle": "Approved Faculty",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/teachers?status=verified"
                }
            },
            {
                "id": "pending_teacher_verification",
                "title": "PENDING TEACHERS",
                "icon": "verification",
                "value": pending_verifications,
                "total_pending": pending_verifications,
                "formatted_value": format_number(pending_verifications),
                "badge": {
                    "text": "Needs attention" if pending_verifications > 0 else "All verified",
                    "variant": "warning" if pending_verifications > 0 else "success"
                },
                "subtitle": "Action Required",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/teachers?status=pending"
                }
            },
            {
                "id": "pending_connections",
                "title": "PENDING CONNECTIONS",
                "icon": "connections",
                "value": pending_connections,
                "formatted_value": format_number(pending_connections),
                "badge": {
                    "text": "Awaiting admin review",
                    "variant": "info"
                },
                "subtitle": "Protected Flow",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/connections"
                }
            },
            {
                "id": "pending_enrollments",
                "title": "PENDING ENROLLMENTS",
                "icon": "enrollments",
                "value": pending_enrollments,
                "formatted_value": format_number(pending_enrollments),
                "badge": {
                    "text": "Requires confirmation",
                    "variant": "warning"
                },
                "subtitle": "Batches",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/enrollments"
                }
            },
            {
                "id": "revenue",
                "title": "REVENUE",
                "icon": "revenue",
                "value": display_revenue,
                "formatted_value": format_inr(display_revenue),
                "currency": "INR",
                "currency_symbol": "₹",
                "badge": {
                    "text": "This month",
                    "variant": "success"
                },
                "subtitle": "Gross Fees",
                "action": {
                    "label": "View Details →",
                    "url": "/admin/payments"
                },
                "all_time_revenue": float(all_time_revenue),
                "formatted_all_time_revenue": format_inr(all_time_revenue)
            }
        ]

        # ------------------------------------------------------------------
        # 6. Secondary Metrics Row (4 cards in screenshot)
        # ------------------------------------------------------------------
        secondary_metrics = [
            {
                "id": "active_students",
                "title": "ACTIVE STUDENTS",
                "icon": "user_check",
                "value": active_students,
                "formatted_value": format_number(active_students),
                "rate": engagement_rate,
                "subtext": f"{engagement_rate}% engagement rate"
            },
            {
                "id": "verified_teachers",
                "title": "VERIFIED TEACHERS",
                "icon": "teacher_check",
                "value": verified_teachers,
                "formatted_value": format_number(verified_teachers),
                "rate": verification_pass_rate,
                "subtext": f"{verification_pass_rate}% verification pass"
            },
            {
                "id": "active_batches",
                "title": "ACTIVE BATCHES",
                "icon": "batch",
                "value": active_batches,
                "formatted_value": format_number(active_batches),
                "subtext": "Live across India"
            },
            {
                "id": "active_connections",
                "title": "ACTIVE CONNECTIONS",
                "icon": "link",
                "value": active_connections,
                "formatted_value": format_number(active_connections),
                "subtext": "Protected communications"
            }
        ]

        # ------------------------------------------------------------------
        # 7. Platform Activity Chart
        # ------------------------------------------------------------------
        range_query = request.query_params.get("range", "30d")
        platform_activity = get_platform_activity_data(range_param=range_query)

        # ------------------------------------------------------------------
        # 8. Recent Audit Logs
        # ------------------------------------------------------------------
        recent_activity = AuditLog.objects.select_related('actor')[:10]
        recent_activity_data = [
            {
                "id": str(log.id),
                "action": log.action,
                "actor": log.actor.email if log.actor else 'SYSTEM',
                "description": log.description,
                "created_at": log.created_at
            }
            for log in recent_activity
        ]

        # ------------------------------------------------------------------
        # 9. Assembled Payload (Clean readable summary only once)
        # ------------------------------------------------------------------
        summary_counts = {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "verified_teachers": verified_teachers,
            "pending_teachers": pending_verifications
        }

        data = {
            "summary": summary_counts,
            "admin_user": admin_user_data,
            "primary_kpis": primary_kpis,
            "secondary_metrics": secondary_metrics,
            "platform_activity": platform_activity,
            "recent_activity": recent_activity_data,

            # Flat backward-compatible fields
            "pending_teacher_approvals": pending_verifications,
            "total_batches": total_batches,
            "active_batches": active_batches,
            "total_enrollments": total_enrollments,
            "active_enrollments": active_enrollments,
            "total_revenue": float(all_time_revenue),
            "monthly_revenue": float(monthly_revenue),
            "pending_reports": pending_reports,
        }

        return Response({
            "success": True,
            "message": "Admin dashboard statistics retrieved successfully",
            "data": data
        }, status=status.HTTP_200_OK)


class AdminDashboardActivityView(APIView):
    """
    Dedicated endpoint for interactive date-range switching on the
    Platform Activity chart (7 Days, 30 Days, 6 Months).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        range_query = request.query_params.get("range", "30d")
        activity_data = get_platform_activity_data(range_param=range_query)
        return api_response(
            success=True,
            message="Platform activity data retrieved successfully",
            data=activity_data
        )


class AdminDashboardSearchView(APIView):
    """
    Global Admin Dashboard Search across students, teachers, and batches
    for the top navigation search bar ('Search students, teachers, batches... [⌘K]').
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q or len(q) < 2:
            return api_response(
                success=True,
                message="Please provide at least 2 characters to search.",
                data={"students": [], "teachers": [], "batches": [], "total_matches": 0}
            )

        # Search Students
        students_qs = User.objects.filter(
            role=User.Role.STUDENT
        ).filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone_number__icontains=q)
        ).select_related('student_profile')[:5]

        students_data = [
            {
                "id": str(s.id),
                "name": s.get_full_name(),
                "email": s.email,
                "phone": s.phone_number,
                "is_active": s.is_active,
                "city": getattr(getattr(s, 'student_profile', None), 'city', ''),
                "url": f"/admin/students/{s.id}"
            }
            for s in students_qs
        ]

        # Search Teachers
        teachers_qs = TeacherProfile.objects.filter(
            Q(display_name__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(qualification__icontains=q)
        ).select_related('user')[:5]

        teachers_data = [
            {
                "id": str(t.id),
                "name": t.display_name or t.user.get_full_name(),
                "email": t.user.email,
                "verification_status": t.verification_status,
                "qualification": t.qualification,
                "rating": float(t.average_rating),
                "url": f"/admin/teachers/{t.id}"
            }
            for t in teachers_qs
        ]

        # Search Batches
        batches_qs = Batch.objects.filter(
            Q(title__icontains=q) |
            Q(subject__icontains=q) |
            Q(description__icontains=q)
        ).select_related('teacher__user')[:5]

        batches_data = [
            {
                "id": str(b.id),
                "title": b.title,
                "subject": b.subject,
                "status": b.status,
                "teacher_name": b.teacher.display_name or b.teacher.user.get_full_name(),
                "price": float(b.price),
                "url": f"/admin/batches/{b.id}"
            }
            for b in batches_qs
        ]

        total_matches = len(students_data) + len(teachers_data) + len(batches_data)

        return api_response(
            success=True,
            message=f"Found {total_matches} matches for '{q}'",
            data={
                "query": q,
                "students": students_data,
                "teachers": teachers_data,
                "batches": batches_data,
                "total_matches": total_matches
            }
        )


class AdminUsersListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserDetailSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']
    queryset = User.objects.all()

class StudentViewSet(viewsets.ModelViewSet):
    """
    ====================================================================
    [STUDENT MODELVIEWSET] - Complete Beginner-Friendly CRUD:
    - GET    /api/v1/students/        -> List all students (Search & filter)
    - POST   /api/v1/students/        -> Create a student
    - GET    /api/v1/students/<id>/   -> Retrieve a student
    - PUT    /api/v1/students/<id>/   -> Full update student
    - PATCH  /api/v1/students/<id>/   -> Partial update student
    - DELETE /api/v1/students/<id>/   -> Delete student
    ====================================================================
    """
    queryset = StudentProfile.objects.select_related('user').all().order_by('-user__date_joined')
    serializer_class = StudentProfileSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'user__phone_number', 'city', 'education_level', 'school_name']
    ordering_fields = ['user__date_joined', 'city', 'education_level']
    lookup_field = 'id'

    def get_queryset(self):
        qs = StudentProfile.objects.select_related('user').all().order_by('-user__date_joined')
        status_param = self.request.query_params.get('status')
        if status_param:
            status_val = status_param.strip().upper()
            if status_val == 'ACTIVE':
                qs = qs.filter(user__is_active=True)
            elif status_val == 'INACTIVE':
                qs = qs.filter(user__is_active=False)
            elif status_val == 'PENDING':
                # pyrefly: ignore [missing-import]
                # from .models import Enrollment
                pending_ids = Enrollment.objects.filter(status=Enrollment.Status.REQUESTED).values_list('student_id', flat=True)
                qs = qs.filter(id__in=pending_ids)

        board_param = self.request.query_params.get('board')
        if board_param:
            b = board_param.strip()
            if b.upper() not in ['ALL', 'ALL BOARDS']:
                qs = qs.filter(Q(education_level__icontains=b) | Q(school_name__icontains=b))

        return qs

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        if lookup_val:
            obj = StudentProfile.objects.select_related('user').filter(
                Q(id=lookup_val) | Q(user__id=lookup_val)
            ).first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj
        return super().get_object()

    def create(self, request, *args, **kwargs):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_student(serializer.validated_data)
        profile, _ = StudentProfile.objects.get_or_create(user=user)
        output_serializer = self.get_serializer(profile)
        return api_response(
            success=True,
            message="Student created successfully.",
            data=output_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        base_qs = StudentProfile.objects.select_related('user').all()
        total_students = base_qs.count()
        active_learners = base_qs.filter(user__is_active=True).count()
        inactive_accounts = base_qs.filter(user__is_active=False).count()

        counts = {
            "total_students": total_students,
            "active_learners": active_learners,
            "inactive_accounts": inactive_accounts,
            "total_learners_badge": f"{total_students:,} Total Learners"
        }

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            total_in_filter = self.paginator.page.paginator.count if (hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else len(serializer.data)
            current_page = self.paginator.page.number if (hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
            num_pages = self.paginator.page.paginator.num_pages if (hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
            page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

            return Response({
                "success": True,
                "message": "Students list retrieved successfully",
                "counts": counts,
                "total_count": total_in_filter,
                "data": serializer.data,
                "pagination": {
                    "page": current_page,
                    "page_size": page_size,
                    "total": total_in_filter,
                    "total_pages": num_pages
                }
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "message": "Students list retrieved successfully",
            "counts": counts,
            "total_count": len(serializer.data),
            "data": serializer.data,
            "pagination": {
                "page": 1,
                "page_size": len(serializer.data),
                "total": len(serializer.data),
                "total_pages": 1
            }
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(success=True, message="Student details retrieved", data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if 'is_active' in request.data and instance.user:
            instance.user.is_active = bool(request.data['is_active'])
            instance.user.save(update_fields=['is_active'])
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Student updated successfully", data=serializer.data)

    @action(detail=True, methods=['post'], url_path='remarks')
    def add_remark(self, request, id=None):
        instance = self.get_object()
        remark_text = request.data.get('remark', '').strip() or request.data.get('description', '').strip()
        if not remark_text:
            return api_response(success=False, message="Remark text is required.", status_code=status.HTTP_400_BAD_REQUEST)
        
        admin_user = request.user if request.user and request.user.is_authenticated else None
        AuditLog.objects.create(
            actor=admin_user,
            action='ADMIN_REMARK',
            object_type='StudentProfile',
            object_id=str(instance.id),
            description=remark_text,
            metadata={"actor_name": admin_user.get_full_name() if admin_user else "Super Admin"}
        )
        return api_response(success=True, message="Admin remark saved successfully.", data={"remark": remark_text})

    @action(detail=True, methods=['post'], url_path='notice')
    def send_notice(self, request, id=None):
        instance = self.get_object()
        title = request.data.get('title', 'Administrative Notice')
        message = request.data.get('message', '').strip()
        if not message:
            return api_response(success=False, message="Notice message is required.", status_code=status.HTTP_400_BAD_REQUEST)
        
        Notification.objects.create(
            recipient=instance.user,
            title=title,
            message=message,
            notification_type=Notification.NotificationType.SYSTEM
        )
        return api_response(success=True, message="Notice sent to student successfully.")

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate_student(self, request, id=None):
        instance = self.get_object()
        if instance.user:
            instance.user.is_active = False
            instance.user.save(update_fields=['is_active'])
        return api_response(success=True, message="Student account deactivated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = instance.user
        email = user.email if user else "Student"
        instance.delete()
        if user:
            user.delete()
        return api_response(success=True, message=f"Student '{email}' deleted successfully.")


class TeacherViewSet(viewsets.ModelViewSet):
    """
    ====================================================================
    [TEACHER MODELVIEWSET] - Complete Beginner-Friendly CRUD:
    - GET    /api/v1/teachers/        -> List all teachers
    - POST   /api/v1/teachers/        -> Create a teacher
    - GET    /api/v1/teachers/<id>/   -> Retrieve a teacher
    - PUT    /api/v1/teachers/<id>/   -> Full update teacher
    - PATCH  /api/v1/teachers/<id>/   -> Partial update teacher
    - DELETE /api/v1/teachers/<id>/   -> Delete teacher
    ====================================================================
    """
    queryset = TeacherProfile.objects.select_related('user').filter(user__role=User.Role.TEACHER).exclude(user__role=User.Role.ADMIN).order_by('-created_at')
    serializer_class = TeacherProfileSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TeacherFilter
    search_fields = ['display_name', 'user__email', 'user__first_name', 'user__last_name', 'qualification', 'bio']
    ordering_fields = ['average_rating', 'experience_years', 'hourly_rate', 'created_at']
    lookup_field = 'id'

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        if lookup_val:
            obj = TeacherProfile.objects.select_related('user').filter(
                Q(id=lookup_val) | Q(user__id=lookup_val)
            ).first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj
        return super().get_object()

    def is_admin_request(self):
        user = getattr(self.request, 'user', None)
        path = getattr(self.request, 'path', '')
        if user and user.is_authenticated and (user.role == User.Role.ADMIN or user.is_staff):
            return True
        if 'admin' in path:
            return True
        return False

    def get_serializer_class(self):
        if not self.is_admin_request():
            return TeacherPublicSearchSerializer
        return TeacherProfileSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user__role=User.Role.TEACHER).exclude(user__role=User.Role.ADMIN).exclude(user__is_staff=True)

    def create(self, request, *args, **kwargs):
        serializer = TeacherRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_teacher(serializer.validated_data)
        profile, _ = TeacherProfile.objects.get_or_create(user=user)
        output_serializer = TeacherProfileSerializer(profile)
        return api_response(
            success=True,
            message="Teacher created successfully.",
            data=output_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Base queryset for real teachers (excluding admins) to compute counts
        base_teachers_qs = TeacherProfile.objects.filter(
            user__role=User.Role.TEACHER
        ).exclude(user__role=User.Role.ADMIN).exclude(user__is_staff=True)

        total_teachers_count = base_teachers_qs.count()
        verified_count = base_teachers_qs.filter(
            verification_status=TeacherProfile.VerificationStatus.VERIFIED
        ).count()
        pending_count = base_teachers_qs.filter(
            verification_status=TeacherProfile.VerificationStatus.PENDING_VERIFICATION
        ).count()
        rejected_count = base_teachers_qs.filter(
            verification_status=TeacherProfile.VerificationStatus.REJECTED
        ).count()

        counts = {
            "total_teachers": total_teachers_count,
            "verified_teachers": verified_count,
            "pending_verification": pending_count,
            "rejected_teachers": rejected_count
        }

        status_param = request.query_params.get('status') or request.query_params.get('verification_status')
        status_val = status_param.strip().upper() if status_param else None

        page = self.paginate_queryset(queryset)
        total_in_filter = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 20) if hasattr(self, 'paginator') else 20

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        # Ensure current_status is set inside each teacher / doctor object
        for item in serialized_data:
            if 'current_status' not in item or not item['current_status']:
                item['current_status'] = item.get('verification_status', '')

        # Build response based on filter
        response_payload = {
            "success": True,
            "message": "Data fetched successfully",
        }

        pagination_payload = {
            "page": current_page,
            "page_size": page_size,
            "total": total_in_filter,
            "total_pages": num_pages,
        }

        if status_val in ['VERIFIED', 'APPROVED']:
            response_payload["verified_count"] = total_in_filter
            pagination_payload["verified_count"] = total_in_filter
        elif status_val in ['PENDING', 'PENDING_VERIFICATION']:
            response_payload["pending_count"] = total_in_filter
            pagination_payload["pending_count"] = total_in_filter
        elif status_val in ['REJECTED']:
            response_payload["rejected_count"] = total_in_filter
            pagination_payload["rejected_count"] = total_in_filter
        else:
            response_payload["total_count"] = total_in_filter
            response_payload["verified_count"] = verified_count
            response_payload["pending_count"] = pending_count
            pagination_payload["total_count"] = total_in_filter
            pagination_payload["verified_count"] = verified_count
            pagination_payload["pending_count"] = pending_count

        response_payload["data"] = serialized_data
        response_payload["pagination"] = pagination_payload

        return Response(response_payload, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(success=True, message="Teacher details retrieved", data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', request.method == 'PATCH')
        instance = self.get_object()
        serializer = TeacherProfileSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(success=True, message="Teacher updated successfully", data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = instance.user
        email = user.email if user else "Teacher"
        instance.delete()
        if user:
            user.delete()
        return api_response(success=True, message=f"Teacher '{email}' deleted successfully.")




#admin panel views
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

class AdminConnectionsListView(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = ConnectionRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'contact_unlocked', 'student']
    search_fields = [
        'student__user__first_name', 'student__user__last_name', 'student__user__email',
        'teacher__display_name', 'teacher__user__first_name', 'teacher__user__last_name'
    ]
    queryset = ConnectionRequest.objects.select_related('student__user', 'teacher__user').all()

    def get_queryset(self):
        qs = super().get_queryset()
        student_param = self.request.query_params.get('student') or self.request.query_params.get('student_id')
        if student_param:
            qs = qs.filter(Q(student__id=student_param) | Q(student__user__id=student_param))
        return qs

class AdminBatchesListView(viewsets.ModelViewSet):
    queryset = Batch.objects.select_related('teacher__user').all().order_by('-created_at')
    serializer_class = BatchPublicSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'subject', 'is_free']
    search_fields = ['title', 'description', 'subject', 'teacher__display_name', 'teacher__user__first_name', 'teacher__user__last_name']
    ordering_fields = ['start_date', 'price', 'created_at']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 20) if hasattr(self, 'paginator') else 20

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        status_counts = {
            "total": Batch.objects.count(),
            "published": Batch.objects.filter(status=Batch.Status.PUBLISHED).count(),
            "ongoing": Batch.objects.filter(status=Batch.Status.ONGOING).count(),
            "completed": Batch.objects.filter(status=Batch.Status.COMPLETED).count(),
            "cancelled": Batch.objects.filter(status=Batch.Status.CANCELLED).count(),
            "draft": Batch.objects.filter(status=Batch.Status.DRAFT).count(),
        }

        return Response({
            "success": True,
            "message": "Batches fetched successfully",
            "batch_count": total_count,
            "status_counts": status_counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "batch_count": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)
    

class AdminEnrollmentsListView(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student__user', 'batch__teacher__user').all().order_by('-requested_at')
    serializer_class = EnrollmentSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'student__user__first_name', 'student__user__last_name', 'student__user__email',
        'batch__teacher__user__first_name', 'batch__teacher__user__last_name', 'batch__teacher__display_name',
        'batch__title', 'batch__subject', 'id'
    ]
    ordering_fields = ['requested_at', 'status', 'payment_status']

    def get_queryset(self):
        qs = super().get_queryset()
        
        # 0. Student filter
        student_param = self.request.query_params.get('student') or self.request.query_params.get('student_id')
        if student_param:
            qs = qs.filter(Q(student__id=student_param) | Q(student__user__id=student_param))
        
        # 1. Tab / Status filter
        status_param = self.request.query_params.get('status') or self.request.query_params.get('tab')
        if status_param:
            status_clean = status_param.strip().upper()
            if status_clean in ['PAYMENT_PENDING', 'PAYMENT PENDING', 'UNPAID']:
                qs = qs.filter(Q(payment_status=Enrollment.PaymentStatus.UNPAID) | Q(status__in=[Enrollment.Status.PENDING_PAYMENT, Enrollment.Status.REQUESTED]))
            elif status_clean in ['CONFIRMED', 'ACTIVE', 'APPROVED']:
                qs = qs.filter(status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.APPROVED, Enrollment.Status.PAYMENT_COMPLETED])
            elif status_clean in ['REJECTED', 'CANCELLED']:
                qs = qs.filter(status__in=[Enrollment.Status.REJECTED, Enrollment.Status.CANCELLED])
            elif status_clean not in ['ALL', 'ALL ENROLLMENTS']:
                qs = qs.filter(status__iexact=status_clean)

        # 2. Payment status dropdown filter
        payment_param = self.request.query_params.get('payment_status')
        if payment_param:
            pay_clean = payment_param.strip().upper()
            if pay_clean in ['PAID']:
                qs = qs.filter(payment_status=Enrollment.PaymentStatus.PAID)
            elif pay_clean in ['PAYMENT_PENDING', 'PAYMENT PENDING', 'UNPAID']:
                qs = qs.filter(payment_status=Enrollment.PaymentStatus.UNPAID)
            elif pay_clean in ['FAILED']:
                qs = qs.filter(payment_status=Enrollment.PaymentStatus.UNPAID)
            elif pay_clean in ['REFUNDED']:
                qs = qs.filter(payment_status=Enrollment.PaymentStatus.REFUNDED)

        return qs

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status in [Enrollment.Status.APPROVED, Enrollment.Status.ACTIVE] and not instance.approved_at:
            instance.approved_at = timezone.now()
            instance.save(update_fields=['approved_at'])
        elif instance.status in [Enrollment.Status.REJECTED, Enrollment.Status.CANCELLED] and not instance.cancelled_at:
            instance.cancelled_at = timezone.now()
            instance.save(update_fields=['cancelled_at'])

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = {
            "all": Enrollment.objects.count(),
            "payment_pending": Enrollment.objects.filter(Q(payment_status=Enrollment.PaymentStatus.UNPAID) | Q(status__in=[Enrollment.Status.PENDING_PAYMENT, Enrollment.Status.REQUESTED])).count(),
            "confirmed": Enrollment.objects.filter(status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.APPROVED, Enrollment.Status.PAYMENT_COMPLETED]).count(),
            "rejected": Enrollment.objects.filter(status__in=[Enrollment.Status.REJECTED, Enrollment.Status.CANCELLED]).count(),
        }

        return Response({
            "success": True,
            "message": "Enrollments retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)


class AdminAnnouncementsListView(viewsets.ModelViewSet):
    queryset = PlatformAnnouncement.objects.select_related('author').all().order_by('-created_at')
    serializer_class = PlatformAnnouncementSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'code', 'author__first_name', 'author__last_name', 'author__email']
    ordering_fields = ['created_at', 'status', 'start_date', 'end_date']

    def get_queryset(self):
        qs = super().get_queryset()

        # 1. Tab / Status filter
        status_param = self.request.query_params.get('status') or self.request.query_params.get('tab')
        if status_param:
            status_clean = status_param.strip().upper()
            if status_clean in ['PUBLISHED']:
                qs = qs.filter(status=PlatformAnnouncement.Status.PUBLISHED)
            elif status_clean in ['SCHEDULED']:
                qs = qs.filter(status=PlatformAnnouncement.Status.SCHEDULED)
            elif status_clean in ['DRAFT', 'DRAFTS']:
                qs = qs.filter(status=PlatformAnnouncement.Status.DRAFT)
            elif status_clean in ['EXPIRED']:
                qs = qs.filter(status=PlatformAnnouncement.Status.EXPIRED)

        # 2. Audience filter
        audience_param = self.request.query_params.get('audience')
        if audience_param:
            aud_clean = audience_param.strip().upper().replace(' ', '_')
            if aud_clean in ['ALL_USERS', 'ALL']:
                qs = qs.filter(audience=PlatformAnnouncement.Audience.ALL_USERS)
            elif aud_clean in ['STUDENTS', 'STUDENT']:
                qs = qs.filter(audience=PlatformAnnouncement.Audience.STUDENTS)
            elif aud_clean in ['TEACHERS', 'TEACHER']:
                qs = qs.filter(audience=PlatformAnnouncement.Audience.TEACHERS)

        # 3. Type filter
        type_param = self.request.query_params.get('type') or self.request.query_params.get('announcement_type')
        if type_param:
            typ_clean = type_param.strip().upper()
            if typ_clean in ['IMPORTANT']:
                qs = qs.filter(announcement_type=PlatformAnnouncement.Type.IMPORTANT)
            elif typ_clean in ['PROMOTIONAL', 'PROMOTION']:
                qs = qs.filter(announcement_type=PlatformAnnouncement.Type.PROMOTIONAL)
            elif typ_clean in ['GENERAL']:
                qs = qs.filter(announcement_type=PlatformAnnouncement.Type.GENERAL)

        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user and self.request.user.is_authenticated else None
        serializer.save(author=user)

    @action(detail=True, methods=['post', 'patch'])
    def publish(self, request, pk=None):
        announcement = self.get_object()
        announcement.status = PlatformAnnouncement.Status.PUBLISHED
        announcement.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(announcement)
        return Response({
            "success": True,
            "message": "Announcement published successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'patch'])
    def unpublish(self, request, pk=None):
        announcement = self.get_object()
        announcement.status = PlatformAnnouncement.Status.DRAFT
        announcement.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(announcement)
        return Response({
            "success": True,
            "message": "Announcement unpublished successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = {
            "all": PlatformAnnouncement.objects.count(),
            "published": PlatformAnnouncement.objects.filter(status=PlatformAnnouncement.Status.PUBLISHED).count(),
            "scheduled": PlatformAnnouncement.objects.filter(status=PlatformAnnouncement.Status.SCHEDULED).count(),
            "drafts": PlatformAnnouncement.objects.filter(status=PlatformAnnouncement.Status.DRAFT).count(),
            "expired": PlatformAnnouncement.objects.filter(status=PlatformAnnouncement.Status.EXPIRED).count(),
        }

        return Response({
            "success": True,
            "message": "Announcements retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)


class AdminPromotionalBannersViewSet(viewsets.ModelViewSet):
    queryset = PlatformAnnouncement.objects.filter(is_banner=True).order_by('slot', '-created_at')
    serializer_class = PlatformAnnouncementSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'code', 'cta_label', 'cta_url']
    ordering_fields = ['slot', 'created_at', 'status']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        active_count = PlatformAnnouncement.objects.filter(is_banner=True, status=PlatformAnnouncement.Status.PUBLISHED).count()

        return Response({
            "success": True,
            "message": "Promotional banners retrieved successfully",
            "active_count": active_count,
            "total_count": PlatformAnnouncement.objects.filter(is_banner=True).count(),
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)


class AdminStudyMaterialsListView(viewsets.ModelViewSet):
    queryset = StudyMaterial.objects.select_related('batch', 'teacher__user').all().order_by('-published_at')
    serializer_class = StudyMaterialSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'title', 'code', 'description', 'file_type',
        'teacher__display_name', 'teacher__user__first_name', 'teacher__user__last_name',
        'batch__title', 'batch__subject'
    ]
    ordering_fields = ['published_at', 'views_count', 'downloads_count', 'size', 'status']

    def get_queryset(self):
        qs = super().get_queryset()

        # 1. Tab / Status filter
        status_param = self.request.query_params.get('status') or self.request.query_params.get('tab')
        if status_param:
            status_clean = status_param.strip().upper()
            if status_clean in ['PUBLISHED']:
                qs = qs.filter(status=StudyMaterial.Status.PUBLISHED)
            elif status_clean in ['REPORTED', 'FLAGGED', 'REPORTED / FLAGGED']:
                qs = qs.filter(status=StudyMaterial.Status.REPORTED)
            elif status_clean in ['DRAFT', 'DRAFTS']:
                qs = qs.filter(status=StudyMaterial.Status.DRAFT)
            elif status_clean in ['HIDDEN', 'HIDDEN_BY_ADMIN', 'HIDDEN BY ADMIN']:
                qs = qs.filter(status=StudyMaterial.Status.HIDDEN)

        # 2. File type filter
        file_type_param = self.request.query_params.get('file_type')
        if file_type_param:
            qs = qs.filter(file_type__iexact=file_type_param.strip())

        return qs

    def perform_create(self, serializer):
        batch = serializer.validated_data.get('batch')
        teacher = serializer.validated_data.get('teacher')
        if not teacher and batch:
            teacher = batch.teacher
        serializer.save(teacher=teacher)

    @action(detail=True, methods=['post', 'patch'])
    def hide(self, request, pk=None):
        material = self.get_object()
        material.status = StudyMaterial.Status.HIDDEN
        material.save(update_fields=['status'])
        serializer = self.get_serializer(material)
        return Response({
            "success": True,
            "message": "Study material hidden successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'patch'])
    def unhide(self, request, pk=None):
        material = self.get_object()
        material.status = StudyMaterial.Status.PUBLISHED
        material.save(update_fields=['status'])
        serializer = self.get_serializer(material)
        return Response({
            "success": True,
            "message": "Study material published/unhidden successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = {
            "all": StudyMaterial.objects.count(),
            "published": StudyMaterial.objects.filter(status=StudyMaterial.Status.PUBLISHED).count(),
            "reported": StudyMaterial.objects.filter(status=StudyMaterial.Status.REPORTED).count(),
            "drafts": StudyMaterial.objects.filter(status=StudyMaterial.Status.DRAFT).count(),
            "hidden": StudyMaterial.objects.filter(status=StudyMaterial.Status.HIDDEN).count(),
        }

        return Response({
            "success": True,
            "message": "Study materials retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)



class AdminTeacherAnnouncementsViewSet(viewsets.ModelViewSet):
    """
    ====================================================================
    [CONTENT > TEACHER ANNOUNCEMENTS] - Admin Moderation ViewSet:
    - GET    /api/v1/admin/teacher-announcements/
    - POST   /api/v1/admin/teacher-announcements/
    - GET    /api/v1/admin/teacher-announcements/<id>/
    - PATCH  /api/v1/admin/teacher-announcements/<id>/
    - DELETE /api/v1/admin/teacher-announcements/<id>/
    - POST   /api/v1/admin/teacher-announcements/<id>/flag/
    - POST   /api/v1/admin/teacher-announcements/<id>/unflag/
    - POST   /api/v1/admin/teacher-announcements/<id>/publish/
    ====================================================================
    """
    queryset = BatchAnnouncement.objects.select_related('batch', 'teacher__user').all().order_by('-published_at', '-created_at')
    serializer_class = AdminTeacherAnnouncementSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'title', 'message', 'code',
        'teacher__display_name', 'teacher__user__first_name', 'teacher__user__last_name',
        'batch__title', 'batch__subject'
    ]
    ordering_fields = ['published_at', 'created_at', 'priority', 'status']

    def get_queryset(self):
        qs = super().get_queryset()

        tab_param = self.request.query_params.get('tab')
        if tab_param:
            t = tab_param.strip().lower()
            if t == 'published':
                qs = qs.filter(status=BatchAnnouncement.Status.PUBLISHED, is_flagged=False)
            elif t in ['high_priority_urgent', 'urgent', 'high', 'high priority / urgent']:
                qs = qs.filter(priority__in=[BatchAnnouncement.Priority.HIGH, BatchAnnouncement.Priority.URGENT])
            elif t in ['flagged', 'flagged_by_admin', 'flagged by admin']:
                qs = qs.filter(Q(is_flagged=True) | Q(status=BatchAnnouncement.Status.FLAGGED))
            elif t in ['draft', 'drafts']:
                qs = qs.filter(status=BatchAnnouncement.Status.DRAFT)

        status_param = self.request.query_params.get('status')
        if status_param:
            s = status_param.strip().upper()
            if s == 'PUBLISHED':
                qs = qs.filter(status=BatchAnnouncement.Status.PUBLISHED, is_flagged=False)
            elif s in ['DRAFT', 'DRAFTS']:
                qs = qs.filter(status=BatchAnnouncement.Status.DRAFT)
            elif s in ['FLAGGED', 'FLAGGED_BY_ADMIN', 'FLAGGED BY ADMIN']:
                qs = qs.filter(Q(is_flagged=True) | Q(status=BatchAnnouncement.Status.FLAGGED))

        priority_param = self.request.query_params.get('priority')
        if priority_param:
            p = priority_param.strip().upper()
            if p in ['HIGH', 'URGENT', 'NORMAL']:
                qs = qs.filter(priority=p)

        return qs

    def perform_create(self, serializer):
        batch = serializer.validated_data.get('batch')
        teacher = serializer.validated_data.get('teacher')
        if not teacher and batch:
            teacher = batch.teacher
        serializer.save(teacher=teacher)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = BatchAnnouncement.objects.aggregate(
            all=Count('id'),
            published=Count('id', filter=Q(status=BatchAnnouncement.Status.PUBLISHED, is_flagged=False)),
            high_priority_urgent=Count('id', filter=Q(priority__in=[BatchAnnouncement.Priority.HIGH, BatchAnnouncement.Priority.URGENT])),
            flagged_by_admin=Count('id', filter=Q(is_flagged=True) | Q(status=BatchAnnouncement.Status.FLAGGED)),
            drafts=Count('id', filter=Q(status=BatchAnnouncement.Status.DRAFT))
        )

        return Response({
            "success": True,
            "message": "Teacher announcements retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        announcement = self.get_object()
        reason = request.data.get('reason', 'Notice violated community broadcast guidelines')
        admin_notes = request.data.get('admin_notes', '')
        announcement.is_flagged = True
        announcement.status = BatchAnnouncement.Status.FLAGGED
        announcement.flag_reason = reason
        if admin_notes:
            announcement.admin_notes = admin_notes
        announcement.save(update_fields=['is_flagged', 'status', 'flag_reason', 'admin_notes', 'updated_at'])
        serializer = self.get_serializer(announcement)
        return Response({
            "success": True,
            "message": "Announcement flagged by admin successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unflag(self, request, pk=None):
        announcement = self.get_object()
        announcement.is_flagged = False
        announcement.status = BatchAnnouncement.Status.PUBLISHED
        announcement.flag_reason = ''
        announcement.save(update_fields=['is_flagged', 'status', 'flag_reason', 'updated_at'])
        serializer = self.get_serializer(announcement)
        return Response({
            "success": True,
            "message": "Announcement unflagged and restored to published",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        announcement = self.get_object()
        announcement.status = BatchAnnouncement.Status.PUBLISHED
        announcement.is_flagged = False
        announcement.published_at = timezone.now()
        announcement.save(update_fields=['status', 'is_flagged', 'published_at', 'updated_at'])
        serializer = self.get_serializer(announcement)
        return Response({
            "success": True,
            "message": "Announcement published successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class AdminReviewsListView(viewsets.ModelViewSet):
    queryset = Review.objects.select_related('student__user', 'teacher__user', 'batch').all().order_by('-created_at')
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['student__user__first_name', 'student__user__last_name', 'teacher__user__first_name', 'teacher__user__last_name', 'teacher__display_name', 'batch__title', 'comment']
    ordering_fields = ['created_at', 'rating', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            status_clean = status_param.strip().upper()
            if status_clean in ['FLAGGED', 'REPORTED', 'FLAGGED / REPORTED', 'PENDING']:
                qs = qs.filter(status__in=[Review.Status.FLAGGED, Review.Status.PENDING])
            elif status_clean in ['REMOVED', 'REMOVED_BY_ADMIN', 'REMOVED BY ADMIN']:
                qs = qs.filter(status=Review.Status.REMOVED)
            elif status_clean in ['PUBLISHED', 'APPROVED']:
                qs = qs.filter(status=Review.Status.PUBLISHED)

        rating_param = self.request.query_params.get('rating')
        if rating_param and rating_param.isdigit():
            qs = qs.filter(rating=int(rating_param))

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = {
            "all": Review.objects.count(),
            "published": Review.objects.filter(status=Review.Status.PUBLISHED).count(),
            "flagged": Review.objects.filter(status__in=[Review.Status.FLAGGED, Review.Status.PENDING]).count(),
            "removed": Review.objects.filter(status=Review.Status.REMOVED).count(),
        }

        return Response({
            "success": True,
            "message": "Reviews retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)

class AdminReportsListView(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('reporter', 'resolved_by').all().order_by('-created_at')
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reason', 'description', 'reporter__email', 'reporter__first_name', 'reporter__last_name', 'target_id']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            status_clean = status_param.strip().upper()
            if status_clean in ['DISMISSED', 'REJECTED']:
                qs = qs.filter(status=Report.Status.REJECTED)
            elif status_clean in ['UNDER_REVIEW', 'UNDER REVIEW', 'REVIEW']:
                qs = qs.filter(status=Report.Status.UNDER_REVIEW)
            elif status_clean in ['OPEN', 'RESOLVED']:
                qs = qs.filter(status=status_clean)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        counts = {
            "all": Report.objects.count(),
            "open": Report.objects.filter(status=Report.Status.OPEN).count(),
            "under_review": Report.objects.filter(status=Report.Status.UNDER_REVIEW).count(),
            "resolved": Report.objects.filter(status=Report.Status.RESOLVED).count(),
            "dismissed": Report.objects.filter(status=Report.Status.REJECTED).count(),
        }

        return Response({
            "success": True,
            "message": "Reports retrieved successfully",
            "counts": counts,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        user = self.request.user if (self.request.user and self.request.user.is_authenticated) else User.objects.filter(role='ADMIN').first()
        status_val = serializer.validated_data.get('status')
        if status_val in [Report.Status.RESOLVED, Report.Status.REJECTED]:
            serializer.save(resolved_by=user, resolved_at=timezone.now())
        else:
            serializer.save()


class AdminReportResolveView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, id):
        try:
            report = Report.objects.get(id=id)
        except Report.DoesNotExist:
            raise NotFound("Report not found.")
        status_input = request.data.get('status', 'RESOLVED').strip().upper()
        if status_input == 'DISMISSED':
            report.status = Report.Status.REJECTED
        elif status_input in ['OPEN', 'UNDER_REVIEW', 'RESOLVED', 'REJECTED']:
            report.status = status_input
        else:
            report.status = Report.Status.RESOLVED

        report.admin_note = request.data.get('admin_note', '')
        admin_user = request.user if (request.user and request.user.is_authenticated) else User.objects.filter(role='ADMIN').first()
        report.resolved_by = admin_user
        report.resolved_at = timezone.now()
        report.save()

        if admin_user:
            AuditLogService.log_action(
                actor=admin_user,
                action='REPORT_RESOLVED',
                object_type='Report',
                object_id=str(report.id),
                description=f"Admin resolved report on {report.target_type}:{report.target_id} with status {report.status}"
            )
        serializer = ReportSerializer(report)
        return api_response(success=True, message="Report status updated successfully", data=serializer.data)

class AdminPaymentsListView(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'gateway']
    queryset = Payment.objects.select_related('user', 'enrollment__batch').all()

class AdminAuditLogsListView(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'action', 'actor__email', 'actor__first_name', 'actor__last_name', 'object_id', 'ip_address']
    ordering_fields = ['created_at', 'action', 'object_type']
    queryset = AuditLog.objects.select_related('actor').all().order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        category_param = self.request.query_params.get('category')
        if category_param:
            cat_clean = category_param.strip().upper()
            mapping = {
                'VERIFICATION': ['TeacherVerification', 'TEACHER_VERIFICATION'],
                'PRIVACY': ['ConnectionRequest', 'CONNECTION'],
                'ENROLLMENT': ['Enrollment', 'ENROLLMENT'],
                'MODERATION': ['Review', 'REVIEW'],
                'SAFETY': ['Report', 'REPORT', 'UserBlock'],
                'COMMUNICATIONS': ['PlatformAnnouncement', 'BatchAnnouncement'],
                'MARKETING': ['PromotionalBanner'],
                'FINANCIAL': ['Payment']
            }
            if cat_clean in mapping:
                qs = qs.filter(object_type__in=mapping[cat_clean])
            else:
                qs = qs.filter(Q(object_type__iexact=category_param) | Q(metadata__category__iexact=category_param))
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        total_count = self.paginator.page.paginator.count if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else queryset.count()
        current_page = self.paginator.page.number if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        num_pages = self.paginator.page.paginator.num_pages if (page is not None and hasattr(self, 'paginator') and getattr(self.paginator, 'page', None)) else 1
        page_size = (self.paginator.get_page_size(request) or 10) if hasattr(self, 'paginator') else 10

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serialized_data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            serialized_data = serializer.data

        return Response({
            "success": True,
            "message": "Audit logs retrieved successfully",
            "total": total_count,
            "data": serialized_data,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": num_pages
            }
        }, status=status.HTTP_200_OK)


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

