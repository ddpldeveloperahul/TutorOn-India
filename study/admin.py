from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, UserBlock, EmailVerificationToken, PasswordResetToken,
    StudentProfile, TeacherProfile, TeacherVerification,
    Batch, BatchAnnouncement, Enrollment, ClassContent, Attendance,
    StudyMaterial, Bookmark, ConnectionRequest, ContactAccess,
    Conversation, Message, MessageAttachment, Notification,
    Review, Report, Payment, AuditLog
)
from .views import TeacherVerificationService, ConnectionService, EnrollmentService

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_photo')}),
        ('Role & Verification', {'fields': ('role', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined', 'last_login')

@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__email', 'blocked__email')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'education_level', 'school_name', 'city', 'state', 'created_at')
    list_filter = ('education_level', 'state', 'preferred_language')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'school_name', 'city')

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'qualification', 'experience_years', 'verification_status', 'average_rating', 'total_students', 'is_featured')
    list_filter = ('verification_status', 'is_featured')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'display_name', 'qualification')
    readonly_fields = ('average_rating', 'total_reviews', 'total_students', 'created_at', 'updated_at')

@admin.register(TeacherVerification)
class TeacherVerificationAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'document_type', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status', 'document_type')
    search_fields = ('teacher__user__email', 'teacher__user__first_name', 'teacher__user__last_name', 'document_type')
    readonly_fields = ('submitted_at', 'reviewed_at', 'reviewed_by')
    actions = ['approve_verifications', 'reject_verifications']

    def approve_verifications(self, request, queryset):
        for verification in queryset:
            TeacherVerificationService.approve_verification(
                verification=verification,
                admin_user=request.user,
                admin_note="Approved via Django admin action"
            )
        self.message_user(request, f"{queryset.count()} verification(s) approved.")
    approve_verifications.short_description = "Approve selected teacher verifications"

    def reject_verifications(self, request, queryset):
        for verification in queryset:
            TeacherVerificationService.reject_verification(
                verification=verification,
                admin_user=request.user,
                rejection_reason="Rejected via Django admin action"
            )
        self.message_user(request, f"{queryset.count()} verification(s) rejected.")
    reject_verifications.short_description = "Reject selected teacher verifications"

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'subject', 'price', 'is_free', 'status', 'capacity', 'start_date', 'created_at')
    list_filter = ('status', 'subject', 'is_free')
    search_fields = ('title', 'teacher__user__first_name', 'teacher__user__last_name', 'subject')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(BatchAnnouncement)
class BatchAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'teacher', 'published_at')
    list_filter = ('published_at',)
    search_fields = ('title', 'batch__title', 'teacher__user__first_name')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch', 'status', 'payment_status', 'requested_at', 'approved_at')
    list_filter = ('status', 'payment_status')
    search_fields = ('student__user__email', 'batch__title')
    actions = ['approve_enrollments']

    def approve_enrollments(self, request, queryset):
        for enrollment in queryset:
            EnrollmentService.approve_enrollment(enrollment, request.user)
        self.message_user(request, f"{queryset.count()} enrollment(s) approved.")
    approve_enrollments.short_description = "Approve selected enrollments"

@admin.register(ClassContent)
class ClassContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'teacher', 'class_type', 'scheduled_date', 'order', 'is_published')
    list_filter = ('class_type', 'is_published')
    search_fields = ('title', 'batch__title', 'teacher__user__first_name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'class_content', 'status', 'marked_by', 'marked_at')
    list_filter = ('status', 'marked_at')
    search_fields = ('enrollment__student__user__email', 'class_content__title')

@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'batch', 'teacher', 'file_type', 'is_downloadable', 'published_at')
    list_filter = ('file_type', 'is_downloadable')
    search_fields = ('title', 'batch__title')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'material', 'created_at')
    search_fields = ('student__user__email', 'material__title')

@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'status', 'contact_unlocked', 'student_approved', 'admin_approved', 'created_at')
    list_filter = ('status', 'contact_unlocked', 'student_approved', 'admin_approved')
    search_fields = ('student__user__email', 'teacher__user__email')
    actions = ['approve_contact_unlock']

    def approve_contact_unlock(self, request, queryset):
        for connection in queryset:
            ConnectionService.admin_approve(connection, request.user, reason="Approved via Django admin action")
        self.message_user(request, f"{queryset.count()} connection(s) contact sharing unlocked.")
    approve_contact_unlock.short_description = "Approve and unlock contact sharing"

@admin.register(ContactAccess)
class ContactAccessAdmin(admin.ModelAdmin):
    list_display = ('connection', 'student', 'teacher', 'status', 'approved_by', 'approved_at')
    list_filter = ('status',)
    search_fields = ('student__user__email', 'teacher__user__email')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'updated_at', 'created_at')
    search_fields = ('student__user__email', 'teacher__user__email')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'content', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__email', 'content')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__email', 'title', 'message')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'batch', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating')
    search_fields = ('student__user__email', 'teacher__user__email', 'batch__title')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'target_type', 'target_id', 'status', 'resolved_by', 'created_at')
    list_filter = ('status', 'target_type')
    search_fields = ('reporter__email', 'reason', 'target_id')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'currency', 'status', 'payment_method', 'paid_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('transaction_id', 'user__email')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'object_type', 'object_id', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('actor__email', 'description', 'object_id')
    readonly_fields = ('actor', 'action', 'object_type', 'object_id', 'description', 'metadata', 'ip_address', 'user_agent', 'created_at')
