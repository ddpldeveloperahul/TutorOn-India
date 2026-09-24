from rest_framework import generics, status, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.contrib.auth import get_user_model

from app.models import (
    StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, Bookmark, Enrollment,
    Attendance, ConnectionRequest, ContactAccess, Conversation, Message,
    MessageAttachment, Notification, Review, Report, UserBlock, Payment, AuditLog
)

from app.serializers import (
    UserSerializer, StudentRegistrationSerializer, TeacherRegistrationSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, TeacherProfileDetailSerializer,
    TeacherVerificationSerializer, BatchSerializer, BatchDetailSerializer,
    BatchAnnouncementSerializer, ClassContentSerializer, StudyMaterialSerializer,
    BookmarkSerializer, EnrollmentSerializer, AttendanceSerializer,
    ConnectionRequestSerializer, ContactAccessSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, ReviewSerializer, ReportSerializer,
    UserBlockSerializer, PaymentSerializer, AuditLogSerializer
)

from app.permissions import (
    IsAdminUserRole, IsStudent, IsTeacher, IsVerifiedTeacher,
    IsBatchTeacher, IsEnrolledStudent, IsConversationParticipant, IsConnectionParticipant
)

from app.utils import standard_response, log_audit_action

User = get_user_model()

# ==============================================================================
# AUTHENTICATION VIEWS
# ==============================================================================

class StudentRegisterView(APIView):
    """
    Register a new Student user with 12 profile fields.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            log_audit_action(user, "REGISTER_STUDENT", "User", user.id)
            return standard_response(
                success=True,
                message="Student registered successfully.",
                data={
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token)
                    }
                },
                status_code=status.HTTP_201_CREATED
            )
        return standard_response(
            success=False,
            message="Student registration failed.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class TeacherRegisterView(APIView):
    """
    Register a new Teacher user with 23 profile fields.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TeacherRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            log_audit_action(user, "REGISTER_TEACHER", "User", user.id)
            return standard_response(
                success=True,
                message="Teacher registered successfully.",
                data={
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token)
                    }
                },
                status_code=status.HTTP_201_CREATED
            )
        return standard_response(
            success=False,
            message="Teacher registration failed.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class CustomLoginView(APIView):
    """
    Authenticates user via email/phone and password, returning SimpleJWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = request.data.get('email') or request.data.get('phone_number') or request.data.get('username')
        password = request.data.get('password')

        if not identifier or not password:
            return standard_response(
                success=False,
                message="Email/phone number and password are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(Q(email=identifier) | Q(phone_number=identifier)).first()
        if user and user.check_password(password):
            if not user.is_active:
                return standard_response(
                    success=False,
                    message="User account is inactive.",
                    status_code=status.HTTP_403_FORBIDDEN
                )

            refresh = RefreshToken.for_user(user)
            log_audit_action(user, "LOGIN", "User", user.id)

            profile_data = {}
            if user.user_type == 'STUDENT' and hasattr(user, 'student_profile'):
                profile_data = StudentProfileSerializer(user.student_profile).data
            elif user.user_type == 'TEACHER' and hasattr(user, 'teacher_profile'):
                profile_data = TeacherProfileSerializer(user.teacher_profile).data

            return standard_response(
                success=True,
                message="Login successful.",
                data={
                    "user": UserSerializer(user).data,
                    "profile": profile_data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token)
                    }
                }
            )

        return standard_response(
            success=False,
            message="Invalid credentials.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    """
    Blacklist refresh token to logout user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_audit_action(request.user, "LOGOUT", "User", request.user.id)
            return standard_response(success=True, message="Logout successful.")
        except Exception as e:
            return standard_response(
                success=False,
                message="Invalid or expired token.",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(APIView):
    """
    Allows authenticated users to change password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return standard_response(
                success=False,
                message="Both old_password and new_password are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.check_password(old_password):
            return standard_response(
                success=False,
                message="Incorrect old password.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save()
        log_audit_action(request.user, "CHANGE_PASSWORD", "User", request.user.id)
        return standard_response(success=True, message="Password changed successfully.")


class UserProfileView(APIView):
    """
    Retrieve or update logged-in user profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile_data = {}
        if user.user_type == 'STUDENT' and hasattr(user, 'student_profile'):
            profile_data = StudentProfileSerializer(user.student_profile).data
        elif user.user_type == 'TEACHER' and hasattr(user, 'teacher_profile'):
            profile_data = TeacherProfileSerializer(user.teacher_profile).data

        return standard_response(
            success=True,
            data={
                "user": UserSerializer(user).data,
                "profile": profile_data
            }
        )

    def put(self, request):
        user = request.user
        full_name = request.data.get('full_name')
        if full_name:
            user.full_name = full_name
            user.save()

        if user.user_type == 'STUDENT' and hasattr(user, 'student_profile'):
            serializer = StudentProfileSerializer(user.student_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return standard_response(success=True, message="Profile updated.", data=serializer.data)
            return standard_response(success=False, errors=serializer.errors, status_code=400)

        elif user.user_type == 'TEACHER' and hasattr(user, 'teacher_profile'):
            serializer = TeacherProfileSerializer(user.teacher_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return standard_response(success=True, message="Profile updated.", data=serializer.data)
            return standard_response(success=False, errors=serializer.errors, status_code=400)

        return standard_response(success=True, message="User updated.", data=UserSerializer(user).data)


# ==============================================================================
# TEACHER MARKETPLACE VIEWS
# ==============================================================================

class TeacherSearchView(generics.ListAPIView):
    """
    Search and filter teachers based on subject, class, board, mode, city, rating, rate.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TeacherProfileDetailSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__full_name', 'tagline', 'bio', 'city_location', 'qualifications']
    ordering_fields = ['rating', 'hourly_rate', 'experience_years', 'created_at']

    def get_queryset(self):
        queryset = TeacherProfile.objects.select_related('user').filter(user__is_active=True)

        subject = self.request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(teaching_subjects__icontains=subject)

        mode = self.request.query_params.get('mode')
        if mode:
            queryset = queryset.filter(Q(mode_offered=mode) | Q(mode_offered='BOTH'))

        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city_location__icontains=city)

        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=float(min_rating))

        max_rate = self.request.query_params.get('max_rate')
        if max_rate:
            queryset = queryset.filter(hourly_rate__lte=float(max_rate))

        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() in ['true', '1'])

        return queryset


class TeacherDetailView(generics.RetrieveAPIView):
    """
    Detailed public profile view of a teacher (hides contact info unless unlocked).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TeacherProfileDetailSerializer
    queryset = TeacherProfile.objects.select_related('user').all()
    lookup_field = 'pk'


# ==============================================================================
# TEACHER VERIFICATION VIEWS
# ==============================================================================

class TeacherVerificationSubmitView(APIView):
    """
    Teacher endpoint to submit ID proof and qualification certificates.
    """
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request):
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        if not teacher_profile:
            return standard_response(success=False, message="Teacher profile not found.", status_code=400)

        verification, _ = TeacherVerification.objects.get_or_create(teacher_profile=teacher_profile)
        serializer = TeacherVerificationSerializer(verification, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(status='PENDING')
            return standard_response(
                success=True,
                message="Verification documents submitted for admin review.",
                data=serializer.data
            )
        return standard_response(success=False, errors=serializer.errors, status_code=400)


class AdminVerificationReviewView(APIView):
    """
    Admin endpoint to approve/reject teacher verification.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def post(self, request, pk):
        try:
            verification = TeacherVerification.objects.get(pk=pk)
        except TeacherVerification.DoesNotExist:
            return standard_response(success=False, message="Verification record not found.", status_code=404)

        status_action = request.data.get('status') # APPROVED or REJECTED
        notes = request.data.get('admin_notes', '')

        if status_action not in ['APPROVED', 'REJECTED']:
            return standard_response(success=False, message="Status must be APPROVED or REJECTED.", status_code=400)

        verification.status = status_action
        verification.admin_notes = notes
        verification.save()

        # If approved, update teacher profile status
        if status_action == 'APPROVED':
            verification.teacher_profile.is_verified = True
            verification.teacher_profile.save()

        log_audit_action(request.user, f"VERIFICATION_{status_action}", "TeacherVerification", verification.id)
        return standard_response(
            success=True,
            message=f"Teacher verification {status_action.lower()}.",
            data=TeacherVerificationSerializer(verification).data
        )


# ==============================================================================
# BATCH & CONTENT VIEWS
# ==============================================================================

class BatchListCreateView(generics.ListCreateAPIView):
    """
    List active batches or create a new batch (Teacher only).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'batch_type', 'is_active']
    search_fields = ['title', 'description', 'subject']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'TEACHER':
            return Batch.objects.filter(teacher=user)
        elif user.user_type == 'STUDENT':
            return Batch.objects.filter(enrollments__student=user, enrollments__status='ACTIVE')
        return Batch.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class BatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific batch.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BatchDetailSerializer
    queryset = Batch.objects.all()


class BatchAnnouncementListCreateView(generics.ListCreateAPIView):
    """
    List and create announcements for a batch.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BatchAnnouncementSerializer

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_id')
        return BatchAnnouncement.objects.filter(batch_id=batch_id).order_by('-created_at')

    def perform_create(self, serializer):
        batch_id = self.kwargs.get('batch_id')
        serializer.save(batch_id=batch_id)


class ClassContentListCreateView(generics.ListCreateAPIView):
    """
    List or add class contents (recorded videos, Youtube, Zoom, Google Meet links).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClassContentSerializer

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_id')
        return ClassContent.objects.filter(batch_id=batch_id).order_by('-scheduled_at')

    def perform_create(self, serializer):
        batch_id = self.kwargs.get('batch_id')
        serializer.save(batch_id=batch_id)


class ClassContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClassContentSerializer
    queryset = ClassContent.objects.all()


class StudyMaterialListCreateView(generics.ListCreateAPIView):
    """
    Upload and view study materials for a batch.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudyMaterialSerializer

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_id')
        return StudyMaterial.objects.filter(batch_id=batch_id).order_by('-uploaded_at')

    def perform_create(self, serializer):
        batch_id = self.kwargs.get('batch_id')
        serializer.save(batch_id=batch_id)


# ==============================================================================
# BOOKMARKS, ENROLLMENTS & ATTENDANCE
# ==============================================================================

class BookmarkListCreateView(generics.ListCreateAPIView):
    """
    Bookmark a teacher profile or list saved bookmarks.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        return Bookmark.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """
    Student enrolls into a batch or views current enrollments.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'STUDENT':
            return Enrollment.objects.filter(student=user)
        elif user.user_type == 'TEACHER':
            return Enrollment.objects.filter(batch__teacher=user)
        return Enrollment.objects.all()

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class AttendanceRecordView(generics.ListCreateAPIView):
    """
    Record student attendance for a class.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        return Attendance.objects.filter(class_content_id=class_id)


# ==============================================================================
# CONNECTION REQUESTS & CONTACT ACCESS PRIVACY
# ==============================================================================

class ConnectionRequestListCreateView(generics.ListCreateAPIView):
    """
    Send or view connection requests.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConnectionRequestSerializer

    def get_queryset(self):
        user = self.request.user
        return ConnectionRequest.objects.filter(Q(sender=user) | Q(receiver=user))

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class ConnectionRequestRespondView(APIView):
    """
    Accept or reject a connection request.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            conn = ConnectionRequest.objects.get(pk=pk, receiver=request.user)
        except ConnectionRequest.DoesNotExist:
            return standard_response(success=False, message="Connection request not found.", status_code=404)

        action = request.data.get('status') # ACCEPTED or REJECTED
        if action not in ['ACCEPTED', 'REJECTED']:
            return standard_response(success=False, message="Status must be ACCEPTED or REJECTED.", status_code=400)

        conn.status = action
        conn.save()

        # Create or update conversation if accepted
        if action == 'ACCEPTED':
            student = conn.sender if conn.sender.user_type == 'STUDENT' else conn.receiver
            teacher = conn.receiver if conn.receiver.user_type == 'TEACHER' else conn.sender
            Conversation.objects.get_or_create(student=student, teacher=teacher)

        return standard_response(
            success=True,
            message=f"Connection request {action.lower()}.",
            data=ConnectionRequestSerializer(conn).data
        )


class ContactAccessRequestView(APIView):
    """
    Request contact phone/email access unlock from admin.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        teacher_id = request.data.get('teacher_id')
        reason = request.data.get('reason', '')

        if not teacher_id:
            return standard_response(success=False, message="teacher_id is required.", status_code=400)

        try:
            teacher = User.objects.get(id=teacher_id, user_type='TEACHER')
        except User.DoesNotExist:
            return standard_response(success=False, message="Teacher not found.", status_code=404)

        # Check existing request
        access_req, created = ContactAccess.objects.get_or_create(
            student=request.user,
            teacher=teacher,
            defaults={'reason': reason, 'status': 'PENDING'}
        )

        return standard_response(
            success=True,
            message="Contact access request submitted to admin.",
            data=ContactAccessSerializer(access_req).data
        )


class ContactAccessUnlockView(APIView):
    """
    Admin endpoint to grant or reject contact access request.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def post(self, request, pk):
        try:
            access_req = ContactAccess.objects.get(pk=pk)
        except ContactAccess.DoesNotExist:
            return standard_response(success=False, message="Access request not found.", status_code=404)

        action = request.data.get('status') # GRANTED or REJECTED
        if action not in ['GRANTED', 'REJECTED']:
            return standard_response(success=False, message="Status must be GRANTED or REJECTED.", status_code=400)

        access_req.status = action
        if action == 'GRANTED':
            from django.utils import timezone
            access_req.granted_at = timezone.now()
        access_req.save()

        log_audit_action(request.user, f"CONTACT_ACCESS_{action}", "ContactAccess", access_req.id)
        return standard_response(
            success=True,
            message=f"Contact access {action.lower()}.",
            data=ContactAccessSerializer(access_req).data
        )


# ==============================================================================
# MESSAGING & CHAT VIEWS
# ==============================================================================

class ConversationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(Q(student=user) | Q(teacher=user))


class MessageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        conv_id = self.kwargs.get('conversation_id')
        return Message.objects.filter(conversation_id=conv_id).order_by('sent_at')

    def perform_create(self, serializer):
        conv_id = self.kwargs.get('conversation_id')
        serializer.save(sender=self.request.user, conversation_id=conv_id)


# ==============================================================================
# REVIEWS, NOTIFICATIONS & SYSTEM
# ==============================================================================

class ReviewListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return Review.objects.filter(teacher_id=teacher_id)
        return Review.objects.all()

    def perform_create(self, serializer):
        review = serializer.save(student=self.request.user)
        # Update teacher profile aggregate rating
        teacher_profile = getattr(review.teacher, 'teacher_profile', None)
        if teacher_profile:
            avg_rating = Review.objects.filter(teacher=review.teacher).aggregate(Avg('rating'))['rating__avg']
            count = Review.objects.filter(teacher=review.teacher).count()
            teacher_profile.rating = round(avg_rating or 0.0, 2)
            teacher_profile.total_reviews = count
            teacher_profile.save()


class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class ReportCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class UserBlockCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserBlockSerializer

    def get_queryset(self):
        return UserBlock.objects.filter(blocker=self.request.user)

    def perform_create(self, serializer):
        serializer.save(blocker=self.request.user)


class PaymentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AuditLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().order_by('-created_at')


# ==============================================================================
# DASHBOARD VIEWS
# ==============================================================================

class StudentDashboardView(APIView):
    """
    Overview stats and metrics for student dashboard.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        user = request.user
        active_enrollments = Enrollment.objects.filter(student=user, status='ACTIVE').count()
        saved_teachers = Bookmark.objects.filter(student=user).count()
        connection_requests = ConnectionRequest.objects.filter(sender=user).count()
        notifications_count = Notification.objects.filter(user=user, is_read=False).count()

        return standard_response(
            success=True,
            data={
                "student_name": user.full_name,
                "active_enrollments": active_enrollments,
                "saved_teachers": saved_teachers,
                "connection_requests_sent": connection_requests,
                "unread_notifications": notifications_count
            }
        )


class TeacherDashboardView(APIView):
    """
    Overview stats and metrics for teacher dashboard.
    """
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        user = request.user
        teacher_profile = getattr(user, 'teacher_profile', None)
        active_batches = Batch.objects.filter(teacher=user, is_active=True).count()
        total_students = Enrollment.objects.filter(batch__teacher=user, status='ACTIVE').count()
        pending_connections = ConnectionRequest.objects.filter(receiver=user, status='PENDING').count()
        rating = getattr(teacher_profile, 'rating', 0.0)
        is_verified = getattr(teacher_profile, 'is_verified', False)

        return standard_response(
            success=True,
            data={
                "teacher_name": user.full_name,
                "is_verified": is_verified,
                "active_batches": active_batches,
                "total_students": total_students,
                "pending_connections": pending_connections,
                "rating": rating
            }
        )
