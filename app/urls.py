from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from app.views import (
    StudentRegisterView, TeacherRegisterView, CustomLoginView, LogoutView,
    ChangePasswordView, UserProfileView, TeacherSearchView, TeacherDetailView,
    TeacherVerificationSubmitView, AdminVerificationReviewView, BatchListCreateView,
    BatchDetailView, BatchAnnouncementListCreateView, ClassContentListCreateView,
    ClassContentDetailView, StudyMaterialListCreateView, BookmarkListCreateView,
    EnrollmentListCreateView, AttendanceRecordView, ConnectionRequestListCreateView,
    ConnectionRequestRespondView, ContactAccessRequestView, ContactAccessUnlockView,
    ConversationListView, MessageListCreateView, ReviewListCreateView,
    NotificationListView, ReportCreateView, UserBlockCreateView, PaymentListCreateView,
    AuditLogListView, StudentDashboardView, TeacherDashboardView,
    StudentLiveClassView, StudentUpcomingClassesView, StudentMyBatchesView,
    StudentTopTeachersView, StudentFindTeachersView, StudentEnrolledBatchesView
)

urlpatterns = [
    # Auth Endpoints
    path('auth/register/student/', StudentRegisterView.as_view(), name='register-student'),
    path('auth/register/teacher/', TeacherRegisterView.as_view(), name='register-teacher'),
    path('auth/login/', CustomLoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),

    # Teacher Marketplace & Verification
    path('teachers/', TeacherSearchView.as_view(), name='teacher-search'),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='teacher-detail'),
    path('teacher/verification/submit/', TeacherVerificationSubmitView.as_view(), name='verification-submit'),
    path('admin/verification/<int:pk>/review/', AdminVerificationReviewView.as_view(), name='admin-verification-review'),

    # Batches & Class Content Management
    path('batches/', BatchListCreateView.as_view(), name='batch-list-create'),
    path('batches/<int:pk>/', BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<int:batch_id>/announcements/', BatchAnnouncementListCreateView.as_view(), name='batch-announcements'),
    path('batches/<int:batch_id>/classes/', ClassContentListCreateView.as_view(), name='class-content-list-create'),
    path('classes/<int:pk>/', ClassContentDetailView.as_view(), name='class-content-detail'),
    path('classes/<int:class_id>/attendance/', AttendanceRecordView.as_view(), name='class-attendance'),
    path('batches/<int:batch_id>/materials/', StudyMaterialListCreateView.as_view(), name='study-materials'),

    # Bookmarks & Enrollments
    path('bookmarks/', BookmarkListCreateView.as_view(), name='bookmark-list-create'),
    path('enrollments/', EnrollmentListCreateView.as_view(), name='enrollment-list-create'),

    # Connections & Contact Access Privacy Unlock
    path('connections/', ConnectionRequestListCreateView.as_view(), name='connection-list-create'),
    path('connections/<int:pk>/respond/', ConnectionRequestRespondView.as_view(), name='connection-respond'),
    path('contact-access/request/', ContactAccessRequestView.as_view(), name='contact-access-request'),
    path('admin/contact-access/<int:pk>/unlock/', ContactAccessUnlockView.as_view(), name='admin-contact-access-unlock'),

    # Conversations & Chat Messaging
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='message-list-create'),

    # Reviews, Notifications, Reports, Blocks & Audit
    path('reviews/', ReviewListCreateView.as_view(), name='review-list-create'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('reports/', ReportCreateView.as_view(), name='report-create'),
    path('blocks/', UserBlockCreateView.as_view(), name='block-create'),
    path('payments/', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('admin/audit-logs/', AuditLogListView.as_view(), name='audit-log-list'),

    # User Dashboards & Student Dashboard Sub-Endpoints
    path('dashboard/student/', StudentDashboardView.as_view(), name='student-dashboard'),
    path('dashboard/student/live-class/', StudentLiveClassView.as_view(), name='student-live-class'),
    path('dashboard/student/upcoming-classes/', StudentUpcomingClassesView.as_view(), name='student-upcoming-classes'),
    path('dashboard/student/my-batches/', StudentMyBatchesView.as_view(), name='student-my-batches'),
    path('dashboard/student/top-teachers/', StudentTopTeachersView.as_view(), name='student-top-teachers'),
    path('dashboard/student/find-teachers/', StudentFindTeachersView.as_view(), name='student-find-teachers'),
    path('dashboard/student/enrolled-batches/', StudentEnrolledBatchesView.as_view(), name='student-enrolled-batches'),
    path('dashboard/teacher/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
]
