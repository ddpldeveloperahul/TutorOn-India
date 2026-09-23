from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Auth
    StudentRegistrationView, TeacherRegistrationView, UnifiedRegistrationView,
    CustomTokenObtainPairView, CustomTokenRefreshView, LogoutView,
    VerifyEmailView, ResendVerificationView, ForgotPasswordView, ResetPasswordView,
    MeView, UserBlockViewSet,

    # Students & Teachers
    StudentProfileView, StudentDashboardView,
    TeacherListView, TeacherDetailView, TeacherBatchesListView,
    TeacherReviewsListView, TeacherProfileView, TeacherVerificationSubmitView,
    TeacherDashboardView,

    # Batches & Announcements
    BatchPublicListView, BatchPublicDetailView, TeacherBatchViewSet,
    BatchAnnouncementView,

    # Enrollments
    BatchEnrollRequestView, StudentEnrollmentListView, StudentEnrollmentDetailView,
    TeacherEnrollmentListView, TeacherEnrollmentApproveView, TeacherEnrollmentRejectView,

    # Classes & Attendance
    BatchClassListView, TeacherBatchClassCreateView, TeacherClassDetailView,
    ClassDetailView, AttendanceView,

    # Materials & Bookmarks
    BatchMaterialListView, TeacherBatchMaterialCreateView, TeacherMaterialDetailView,
    MaterialDownloadView, MaterialBookmarkView, StudentBookmarkListView,

    # Connections & Contact Privacy
    ConnectionRequestListView, ConnectionApproveView, ConnectionRejectView,
    ConnectionContactDetailView,

    # Messaging
    ConversationListView, ConversationDetailView, ConversationMessageSendView,
    MessageMarkReadView,

    # Notifications
    NotificationListView, NotificationMarkReadView, NotificationMarkAllReadView,

    # Reviews
    BatchReviewCreateView, ReviewDetailView,

    # Reports
    ReportCreateView, MyReportsListView,

    # Payments
    PaymentInitiateView, PaymentVerifyView, StudentPaymentHistoryView,

    # Admin Panel
    AdminDashboardStatsView, AdminUsersListView, AdminTeachersListView,
    AdminStudentsListView, AdminTeacherVerificationsListView,
    AdminTeacherVerificationDetailView, AdminTeacherVerificationApproveView,
    AdminTeacherVerificationRejectView, AdminConnectionsListView,
    AdminBatchesListView, AdminEnrollmentsListView, AdminReviewsListView,
    AdminReportsListView, AdminReportResolveView, AdminPaymentsListView,
    AdminAuditLogsListView, AdminConnectionApproveView, AdminConnectionRejectView,
    AdminSendClassRemindersView
)

router = DefaultRouter()
router.register(r'blocks', UserBlockViewSet, basename='user-blocks')
router.register(r'teacher/batches', TeacherBatchViewSet, basename='teacher-batches')

urlpatterns = [
    # Auth
    path('auth/register/', UnifiedRegistrationView.as_view(), name='register-unified'),
    path('auth/register/student/', StudentRegistrationView.as_view(), name='register-student'),
    path('auth/register/teacher/', TeacherRegistrationView.as_view(), name='register-teacher'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/me/', MeView.as_view(), name='auth-me'),

    # Student Area
    path('student/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('student/dashboard/', StudentDashboardView.as_view(), name='student-dashboard'),
    path('student/enrollments/', StudentEnrollmentListView.as_view(), name='student-enrollments-list'),
    path('student/enrollments/<uuid:id>/', StudentEnrollmentDetailView.as_view(), name='student-enrollment-detail'),
    path('student/bookmarks/', StudentBookmarkListView.as_view(), name='student-bookmarks'),
    path('student/payments/', StudentPaymentHistoryView.as_view(), name='student-payments'),

    # Teacher Area & Public Search
    path('teachers/', TeacherListView.as_view(), name='teacher-list'),
    path('teachers/<uuid:id>/', TeacherDetailView.as_view(), name='teacher-detail'),
    path('teachers/<uuid:id>/batches/', TeacherBatchesListView.as_view(), name='teacher-batches'),
    path('teachers/<uuid:id>/reviews/', TeacherReviewsListView.as_view(), name='teacher-reviews'),
    path('teacher/profile/', TeacherProfileView.as_view(), name='teacher-profile'),
    path('teacher/verification/', TeacherVerificationSubmitView.as_view(), name='teacher-verification-submit'),
    path('teacher/dashboard/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
    path('teacher/enrollments/', TeacherEnrollmentListView.as_view(), name='teacher-enrollments-list'),
    path('teacher/enrollments/<uuid:id>/approve/', TeacherEnrollmentApproveView.as_view(), name='teacher-enrollment-approve'),
    path('teacher/enrollments/<uuid:id>/reject/', TeacherEnrollmentRejectView.as_view(), name='teacher-enrollment-reject'),

    # Batches
    path('batches/', BatchPublicListView.as_view(), name='batch-public-list'),
    path('batches/<slug:slug>/', BatchPublicDetailView.as_view(), name='batch-public-detail'),
    path('batches/<uuid:batch_id>/announcements/', BatchAnnouncementView.as_view(), name='batch-announcements'),
    path('batches/<uuid:batch_id>/enroll/', BatchEnrollRequestView.as_view(), name='batch-enroll'),

    # Classes & Attendance
    path('batches/<uuid:batch_id>/classes/', BatchClassListView.as_view(), name='batch-classes-list'),
    path('teacher/batches/<uuid:batch_id>/classes/', TeacherBatchClassCreateView.as_view(), name='teacher-batch-class-create'),
    path('teacher/classes/<uuid:id>/', TeacherClassDetailView.as_view(), name='teacher-class-detail'),
    path('classes/<uuid:id>/', ClassDetailView.as_view(), name='class-detail'),
    path('classes/<uuid:class_id>/attendance/', AttendanceView.as_view(), name='class-attendance'),

    # Materials
    path('batches/<uuid:batch_id>/materials/', BatchMaterialListView.as_view(), name='batch-materials-list'),
    path('teacher/batches/<uuid:batch_id>/materials/', TeacherBatchMaterialCreateView.as_view(), name='teacher-batch-material-create'),
    path('teacher/materials/<uuid:id>/', TeacherMaterialDetailView.as_view(), name='teacher-material-detail'),
    path('materials/<uuid:id>/download/', MaterialDownloadView.as_view(), name='material-download'),
    path('materials/<uuid:id>/bookmark/', MaterialBookmarkView.as_view(), name='material-bookmark'),

    # Connections & Contact Unlock
    path('connections/', ConnectionRequestListView.as_view(), name='connection-list-create'),
    path('connections/<uuid:id>/approve/', ConnectionApproveView.as_view(), name='connection-approve'),
    path('connections/<uuid:id>/reject/', ConnectionRejectView.as_view(), name='connection-reject'),
    path('connections/<uuid:id>/contact/', ConnectionContactDetailView.as_view(), name='connection-contact-detail'),

    # Messaging
    path('conversations/', ConversationListView.as_view(), name='conversation-list-create'),
    path('conversations/<uuid:id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:id>/messages/', ConversationMessageSendView.as_view(), name='conversation-send-message'),
    path('messages/<uuid:id>/read/', MessageMarkReadView.as_view(), name='message-mark-read'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<uuid:id>/read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/read-all/', NotificationMarkAllReadView.as_view(), name='notification-read-all'),

    # Reviews
    path('batches/<uuid:batch_id>/reviews/', BatchReviewCreateView.as_view(), name='batch-review-create'),
    path('reviews/<uuid:id>/', ReviewDetailView.as_view(), name='review-detail'),

    # Reports
    path('reports/', ReportCreateView.as_view(), name='report-create'),
    path('reports/my/', MyReportsListView.as_view(), name='my-reports'),

    # Payments
    path('payments/initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
    path('payments/verify/', PaymentVerifyView.as_view(), name='payment-verify'),

    # Admin REST APIs
    path('admin/dashboard/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/users/', AdminUsersListView.as_view(), name='admin-users-list'),
    path('admin/teachers/', AdminTeachersListView.as_view(), name='admin-teachers-list'),
    path('admin/students/', AdminStudentsListView.as_view(), name='admin-students-list'),
    path('admin/teacher-verifications/', AdminTeacherVerificationsListView.as_view(), name='admin-teacher-verifications-list'),
    path('admin/teacher-verifications/<uuid:id>/', AdminTeacherVerificationDetailView.as_view(), name='admin-teacher-verification-detail'),
    path('admin/teacher-verifications/<uuid:id>/approve/', AdminTeacherVerificationApproveView.as_view(), name='admin-teacher-verification-approve'),
    path('admin/teacher-verifications/<uuid:id>/reject/', AdminTeacherVerificationRejectView.as_view(), name='admin-teacher-verification-reject'),
    path('admin/connections/', AdminConnectionsListView.as_view(), name='admin-connections-list'),
    path('admin/connections/<uuid:id>/approve/', AdminConnectionApproveView.as_view(), name='admin-connection-approve'),
    path('admin/connections/<uuid:id>/reject/', AdminConnectionRejectView.as_view(), name='admin-connection-reject'),
    path('admin/classes/send-reminders/', AdminSendClassRemindersView.as_view(), name='admin-send-class-reminders'),
    path('admin/batches/', AdminBatchesListView.as_view(), name='admin-batches-list'),
    path('admin/enrollments/', AdminEnrollmentsListView.as_view(), name='admin-enrollments-list'),
    path('admin/reviews/', AdminReviewsListView.as_view(), name='admin-reviews-list'),
    path('admin/reports/', AdminReportsListView.as_view(), name='admin-reports-list'),
    path('admin/reports/<uuid:id>/resolve/', AdminReportResolveView.as_view(), name='admin-report-resolve'),
    path('admin/payments/', AdminPaymentsListView.as_view(), name='admin-payments-list'),
    path('admin/audit-logs/', AdminAuditLogsListView.as_view(), name='admin-audit-logs-list'),

    # Routers
    path('', include(router.urls)),
]
