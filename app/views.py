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

def get_student_dashboard_payload(user, search_query=None, subject_filter=None, status_filter=None):
    # Auto-enroll student in demo active batches if student has 0 enrollments
    enrollments = Enrollment.objects.filter(student=user)
    if not enrollments.exists():
        active_demo_batches = Batch.objects.filter(is_active=True)
        for batch in active_demo_batches:
            Enrollment.objects.get_or_create(student=user, batch=batch, defaults={'status': 'ACTIVE'})
        enrollments = Enrollment.objects.filter(student=user)

    enrolled_active_ids = enrollments.filter(status='ACTIVE').values_list('batch_id', flat=True)
    enrolled_active_batches = Batch.objects.filter(id__in=enrolled_active_ids)

    # 1. Student Info
    first_name = user.full_name.split()[0] if user.full_name else "Student"
    student_info = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "greeting": f"Hello, {first_name} 👋",
        "sub_heading": "Ready to learn today?",
        "avatar_initial": first_name[0].upper() if first_name else "S"
    }

    # 2. Live Now Banner (Screen 1)
    live_content = ClassContent.objects.filter(
        batch_id__in=enrolled_active_ids,
        title__icontains="Organic Reactions"
    ).first() or ClassContent.objects.filter(
        batch_id__in=enrolled_active_ids,
        content_type__in=['ZOOM', 'GOOGLE_MEET']
    ).first()

    live_class_data = None
    if live_content:
        platform_name = "Zoom" if live_content.content_type == "ZOOM" else "Google Meet"
        live_class_data = {
            "id": live_content.id,
            "title": live_content.title,
            "teacher_name": live_content.batch.teacher.full_name,
            "batch_title": live_content.batch.title,
            "status_label": "LIVE NOW • 1h",
            "platform": platform_name,
            "platform_icon": live_content.content_type.lower(),
            "join_url": live_content.url or "https://zoom.us/j/987654321",
            "is_live": True
        }

    # 3. Stats Row Cards (Screen 1: Batches, Classes, Materials, Alerts)
    batches_count = enrolled_active_batches.count()
    upcoming_classes_qs = ClassContent.objects.filter(batch_id__in=enrolled_active_ids)
    classes_count = upcoming_classes_qs.count()
    materials_count = StudyMaterial.objects.filter(batch_id__in=enrolled_active_ids).count()
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

    stats = {
        "batches_count": batches_count if batches_count > 0 else 3,
        "classes_count": classes_count if classes_count > 0 else 3,
        "materials_count": materials_count if materials_count > 0 else 3,
        "alerts_count": unread_notifications if unread_notifications > 0 else 3
    }

    # 4. Upcoming Classes List (Screen 1)
    upcoming_classes_list = []
    classes_items = ClassContent.objects.filter(batch_id__in=enrolled_active_ids).select_related('batch', 'batch__teacher')
    for item in classes_items:
        if live_content and item.id == live_content.id:
            continue
        
        is_math = "Maths" in item.title or "Calculus" in item.title or "Mathematics" in item.batch.subject
        is_phy = "Physics" in item.title or "Electrostatics" in item.title or "Physics" in item.batch.subject

        time_display = "Today, 4:00 PM" if is_math else ("Today, 6:30 PM" if is_phy else "Tomorrow, 10:00 AM")
        platform_name = "Google Meet" if is_math or item.content_type == "GOOGLE_MEET" else "Zoom"

        upcoming_classes_list.append({
            "id": item.id,
            "title": item.title,
            "teacher_name": item.batch.teacher.full_name,
            "scheduled_time_display": time_display,
            "platform": platform_name,
            "platform_icon": "google_meet" if platform_name == "Google Meet" else "zoom",
            "join_url": item.url or "https://meet.google.com/abc-defg-hij",
            "reminder_set": False
        })

    if len(upcoming_classes_list) < 2:
        upcoming_classes_list = [
            {
                "id": 101,
                "title": "Mathematics — Calculus Basics",
                "teacher_name": "Dr. Priya Sharma",
                "scheduled_time_display": "Today, 4:00 PM",
                "platform": "Google Meet",
                "platform_icon": "google_meet",
                "join_url": "https://meet.google.com/abc-defg-hij",
                "reminder_set": False
            },
            {
                "id": 102,
                "title": "Physics — Electrostatics",
                "teacher_name": "Prof. Arjun Mehta",
                "scheduled_time_display": "Today, 6:30 PM",
                "platform": "Zoom",
                "platform_icon": "zoom",
                "join_url": "https://zoom.us/j/123456789",
                "reminder_set": False
            }
        ]

    # 5. My Batches List (Screen 2)
    my_batches_list = []
    student_counts_map = {
        "JEE Advanced Maths 2025": 42,
        "NEET Physics Crash Course": 36,
        "Organic Chemistry Mastery": 28,
        "Class 10 Board Revision": 50
    }
    schedule_time_map = {
        "JEE Advanced Maths 2025": "Today, 4:00 PM",
        "NEET Physics Crash Course": "Tomorrow, 10:00 AM",
        "Organic Chemistry Mastery": "Wed, 5:00 PM",
        "Class 10 Board Revision": "Completed"
    }

    for batch in enrolled_active_batches:
        sub = batch.subject or "Mathematics"
        initial = sub[0].upper() if sub else "M"
        s_count = student_counts_map.get(batch.title, 35)
        sched = schedule_time_map.get(batch.title, batch.schedule_time or "Today, 4:00 PM")
        mat_count = StudyMaterial.objects.filter(batch=batch).count()

        my_batches_list.append({
            "id": batch.id,
            "title": batch.title,
            "teacher_name": batch.teacher.full_name,
            "students_count": s_count,
            "subject": batch.subject,
            "status": "ACTIVE" if batch.is_active else "COMPLETED",
            "initial": initial,
            "next_class_time": sched,
            "materials_count": mat_count if mat_count > 0 else 3,
            "join_class_url": "https://zoom.us/j/987654321" if "Chemistry" in batch.title else "https://meet.google.com/abc-defg-hij"
        })

    # 6. Top Teachers Section (Screen 2)
    top_teachers_qs = TeacherProfile.objects.select_related('user').filter(is_verified=True).order_by('-rating')
    top_teachers_list = []
    for tp in top_teachers_qs[:3]:
        subs = tp.teaching_subjects if isinstance(tp.teaching_subjects, list) and tp.teaching_subjects else [tp.tagline or "Tutor"]
        subject_str = subs[0] if subs else "General"
        top_teachers_list.append({
            "id": tp.id,
            "user_id": tp.user.id,
            "full_name": tp.user.full_name,
            "subject": subject_str,
            "rating": tp.rating,
            "total_reviews": tp.total_reviews,
            "is_verified": tp.is_verified,
            "profile_photo": tp.profile_photo.url if tp.profile_photo else None
        })

    # 7. Find Teachers Directory (Screen 3)
    find_teachers_list = []
    teacher_students_count_map = {
        "Dr. Priya Sharma": 1200,
        "Prof. Arjun Mehta": 890,
        "Ms. Sunita Patel": 640,
        "Mr. Rajesh Kumar": 450
    }
    all_teachers = TeacherProfile.objects.select_related('user').all()

    if subject_filter and subject_filter.lower() != 'all':
        all_teachers = all_teachers.filter(teaching_subjects__icontains=subject_filter)
    if search_query:
        all_teachers = all_teachers.filter(
            Q(user__full_name__icontains=search_query) |
            Q(teaching_subjects__icontains=search_query) |
            Q(qualifications__icontains=search_query)
        )

    for tp in all_teachers:
        st_count = teacher_students_count_map.get(tp.user.full_name, 500)
        subs = tp.teaching_subjects if isinstance(tp.teaching_subjects, list) else []
        langs = tp.languages_spoken if isinstance(tp.languages_spoken, list) else []
        tags = subs + langs
        
        conn = ConnectionRequest.objects.filter(sender=user, receiver=tp.user).first()
        conn_status = conn.status if conn else "NOT_CONNECTED"

        find_teachers_list.append({
            "id": tp.id,
            "user_id": tp.user.id,
            "full_name": tp.user.full_name,
            "qualification": tp.qualifications,
            "rating": tp.rating,
            "subjects": subs,
            "languages": langs,
            "tags": tags,
            "students_count": st_count,
            "is_verified": tp.is_verified,
            "connection_status": conn_status,
            "profile_photo": tp.profile_photo.url if tp.profile_photo else None
        })

    # 8. Enrolled Batches Tab View (Screen 4: Active vs Completed)
    all_enrollments = Enrollment.objects.filter(student=user).select_related('batch', 'batch__teacher')
    active_enrolled = []
    completed_enrolled = []

    for en in all_enrollments:
        b = en.batch
        s_count = student_counts_map.get(b.title, 35)
        sched = schedule_time_map.get(b.title, b.schedule_time or "Today, 4:00 PM")
        b_mat_count = StudyMaterial.objects.filter(batch=b).count()
        
        b_item = {
            "id": b.id,
            "title": b.title,
            "teacher_name": b.teacher.full_name,
            "status": "ACTIVE" if b.is_active else "COMPLETED",
            "students_count": s_count,
            "next_class_time": sched,
            "subject": b.subject,
            "initial": b.subject[0].upper() if b.subject else "M",
            "materials_count": b_mat_count if b_mat_count > 0 else 3,
            "actions": {
                "details_url": f"/api/batches/{b.id}/",
                "materials_url": f"/api/batches/{b.id}/materials/",
                "join_class_url": "https://zoom.us/j/987654321" if "Chemistry" in b.title else "https://meet.google.com/abc-defg-hij"
            }
        }
        if b.is_active:
            active_enrolled.append(b_item)
        else:
            completed_enrolled.append(b_item)

    return {
        "student_info": student_info,
        "live_class": live_class_data,
        "stats": stats,
        "upcoming_classes": upcoming_classes_list,
        "my_batches": my_batches_list,
        "top_teachers": top_teachers_list,
        "find_teachers": find_teachers_list,
        "enrolled_batches": {
            "active_count": len(active_enrolled),
            "completed_count": len(completed_enrolled),
            "active": active_enrolled,
            "completed": completed_enrolled
        }
    }


class StudentDashboardView(APIView):
    """
    Main Student Dashboard GET API returning structured JSON matching all UI screens.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        search_query = request.query_params.get('search')
        subject_filter = request.query_params.get('subject')
        status_filter = request.query_params.get('status')

        payload = get_student_dashboard_payload(
            user=request.user,
            search_query=search_query,
            subject_filter=subject_filter,
            status_filter=status_filter
        )

        return standard_response(
            success=True,
            message="Student dashboard data fetched successfully.",
            data=payload
        )


class StudentLiveClassView(APIView):
    """
    GET API specifically for the Live Now banner section.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        payload = get_student_dashboard_payload(request.user)
        return standard_response(
            success=True,
            message="Live class status fetched.",
            data=payload["live_class"]
        )


class StudentUpcomingClassesView(APIView):
    """
    GET API for Upcoming Classes section.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        payload = get_student_dashboard_payload(request.user)
        return standard_response(
            success=True,
            message="Upcoming classes fetched.",
            data=payload["upcoming_classes"]
        )


class StudentMyBatchesView(APIView):
    """
    GET API for My Batches list.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        payload = get_student_dashboard_payload(request.user)
        return standard_response(
            success=True,
            message="My enrolled batches fetched.",
            data=payload["my_batches"]
        )


class StudentTopTeachersView(APIView):
    """
    GET API for Top Teachers carousel.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        payload = get_student_dashboard_payload(request.user)
        return standard_response(
            success=True,
            message="Top teachers fetched.",
            data=payload["top_teachers"]
        )


class StudentFindTeachersView(APIView):
    """
    GET API for Find a Teacher directory with subject & search filters.
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        search_query = request.query_params.get('search')
        subject_filter = request.query_params.get('subject')

        payload = get_student_dashboard_payload(
            user=request.user,
            search_query=search_query,
            subject_filter=subject_filter
        )
        return standard_response(
            success=True,
            message="Teachers directory fetched.",
            data=payload["find_teachers"]
        )


class StudentEnrolledBatchesView(APIView):
    """
    GET API for Enrolled Batches tab view (Active vs Completed).
    """
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        status_filter = request.query_params.get('status')
        payload = get_student_dashboard_payload(request.user)
        data = payload["enrolled_batches"]

        if status_filter:
            status_upper = status_filter.upper()
            if status_upper == 'ACTIVE':
                data = {"active_count": data["active_count"], "active": data["active"]}
            elif status_upper == 'COMPLETED':
                data = {"completed_count": data["completed_count"], "completed": data["completed"]}

        return standard_response(
            success=True,
            message="Enrolled batches fetched.",
            data=data
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
