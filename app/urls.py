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
    StudentTopTeachersView, StudentFindTeachersView, StudentEnrolledBatchesView,
    AdminDashboardView, AdminDashboardStatsView, AdminDashboardChartsView,
    AdminDashboardActivityView, AdminUserListView, AdminUserStatusToggleView,
    AdminVerificationListView, AdminContactAccessListView, AdminFinancialsView,
    AdminReportsListView,
    # Teacher Module Views
    TeacherBatchWizardOptionsView, TeacherBatchSaveDraftView, TeacherBatchListCreateView,
    TeacherBatchDetailView, TeacherBatchStudentsView, TeacherClassListCreateView,
    TeacherClassDetailView, TeacherClassToggleLiveView, TeacherAttendanceRecordView,
    TeacherAttendanceDetailView, TeacherStudyMaterialListCreateView,
    TeacherStudyMaterialDetailView, TeacherAnnouncementListCreateView,
    TeacherAnnouncementDetailView, TeacherStudentUpdateListCreateView,
    TeacherStudentUpdateDetailView
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

    # Super Admin Dashboard & Management Endpoints
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard-alias'),
    path('admin/dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/dashboard/charts/', AdminDashboardChartsView.as_view(), name='admin-dashboard-charts'),
    path('admin/dashboard/activity/', AdminDashboardActivityView.as_view(), name='admin-dashboard-activity'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:pk>/status/', AdminUserStatusToggleView.as_view(), name='admin-user-status-toggle'),
    path('admin/verifications/', AdminVerificationListView.as_view(), name='admin-verification-list'),
    path('admin/contact-access/', AdminContactAccessListView.as_view(), name='admin-contact-access-list'),
    path('admin/financials/', AdminFinancialsView.as_view(), name='admin-financials'),
    path('admin/reports/', AdminReportsListView.as_view(), name='admin-reports-list'),

    # User Dashboards & Student Dashboard Sub-Endpoints
    path('dashboard/student/', StudentDashboardView.as_view(), name='student-dashboard'),
    path('dashboard/student/live-class/', StudentLiveClassView.as_view(), name='student-live-class'),
    path('dashboard/student/upcoming-classes/', StudentUpcomingClassesView.as_view(), name='student-upcoming-classes'),
    path('dashboard/student/my-batches/', StudentMyBatchesView.as_view(), name='student-my-batches'),
    path('dashboard/student/top-teachers/', StudentTopTeachersView.as_view(), name='student-top-teachers'),
    path('dashboard/student/find-teachers/', StudentFindTeachersView.as_view(), name='student-find-teachers'),
    path('dashboard/student/enrolled-batches/', StudentEnrolledBatchesView.as_view(), name='student-enrolled-batches'),

    # Teacher Dashboard & Management Endpoints (Screenshot Accurate)
    path('dashboard/teacher/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
    path('teacher/dashboard/', TeacherDashboardView.as_view(), name='teacher-dashboard-alias'),

    # Teacher Batches Wizard & CRUD
    path('teacher/batches/options/', TeacherBatchWizardOptionsView.as_view(), name='teacher-batch-wizard-options'),
    path('teacher/batches/save-draft/', TeacherBatchSaveDraftView.as_view(), name='teacher-batch-save-draft'),
    path('teacher/batches/drafts/', TeacherBatchSaveDraftView.as_view(), name='teacher-batch-drafts-list'),
    path('teacher/batches/', TeacherBatchListCreateView.as_view(), name='teacher-batch-list-create'),
    path('teacher/batches/<int:pk>/', TeacherBatchDetailView.as_view(), name='teacher-batch-detail'),
    path('teacher/batches/<int:batch_id>/students/', TeacherBatchStudentsView.as_view(), name='teacher-batch-students'),
    path('teacher/batches/<int:batch_id>/students/<int:student_id>/', TeacherBatchStudentsView.as_view(), name='teacher-batch-student-remove'),

    # Teacher Classes & Schedule CRUD
    path('teacher/classes/', TeacherClassListCreateView.as_view(), name='teacher-class-list-create'),
    path('teacher/classes/<int:pk>/', TeacherClassDetailView.as_view(), name='teacher-class-detail'),
    path('teacher/classes/<int:pk>/toggle-live/', TeacherClassToggleLiveView.as_view(), name='teacher-class-toggle-live'),

    # Teacher Attendance CRUD
    path('teacher/classes/<int:class_id>/attendance/', TeacherAttendanceRecordView.as_view(), name='teacher-class-attendance'),
    path('teacher/attendance/<int:pk>/', TeacherAttendanceDetailView.as_view(), name='teacher-attendance-detail'),

    # Teacher Uploaded Materials CRUD
    path('teacher/materials/', TeacherStudyMaterialListCreateView.as_view(), name='teacher-material-list-create'),
    path('teacher/materials/<int:pk>/', TeacherStudyMaterialDetailView.as_view(), name='teacher-material-detail'),

    # Teacher Announcements CRUD
    path('teacher/announcements/', TeacherAnnouncementListCreateView.as_view(), name='teacher-announcement-list-create'),
    path('teacher/announcements/<int:pk>/', TeacherAnnouncementDetailView.as_view(), name='teacher-announcement-detail'),

    # Teacher Student Activity Updates CRUD
    path('teacher/student-updates/', TeacherStudentUpdateListCreateView.as_view(), name='teacher-student-update-list-create'),
    path('teacher/student-updates/<int:pk>/', TeacherStudentUpdateDetailView.as_view(), name='teacher-student-update-detail'),
]

