from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from app.models import (
    User, StudentProfile, TeacherProfile, TeacherVerification, Batch,
    BatchAnnouncement, ClassContent, StudyMaterial, Bookmark, Enrollment,
    Attendance, ConnectionRequest, ContactAccess, Conversation, Message,
    MessageAttachment, Notification, Review, Report, UserBlock, Payment, AuditLog
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'email', 'phone_number', 'full_name', 'user_type', 'is_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_active')
    search_fields = ('email', 'phone_number', 'full_name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'phone_number', 'password')}),
        ('Personal info', {'fields': ('full_name', 'user_type', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    readonly_fields = ('created_at',)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'student_class', 'city_location', 'mode_preference', 'gender')
    search_fields = ('user__full_name', 'user__email', 'city_location')
    list_filter = ('mode_preference', 'gender')

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'city_location', 'experience_years', 'hourly_rate', 'rating', 'is_verified')
    list_filter = ('is_verified', 'mode_offered', 'gender')
    search_fields = ('user__full_name', 'user__email', 'city_location', 'qualifications')

@admin.register(TeacherVerification)
class TeacherVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher_profile', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status',)
    actions = ['approve_verifications', 'reject_verifications']

    def approve_verifications(self, request, queryset):
        for obj in queryset:
            obj.status = 'APPROVED'
            obj.save()
            obj.teacher_profile.is_verified = True
            obj.teacher_profile.save()
        self.message_user(request, f"{queryset.count()} verification requests approved.")

    def reject_verifications(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, f"{queryset.count()} verification requests rejected.")

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'subject', 'batch_type', 'fee', 'is_active')
    list_filter = ('batch_type', 'is_active', 'subject')
    search_fields = ('title', 'teacher__full_name', 'subject')

@admin.register(ClassContent)
class ClassContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'batch', 'content_type', 'scheduled_at', 'duration_minutes')
    list_filter = ('content_type',)
    search_fields = ('title', 'batch__title')

@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(ContactAccess)
class ContactAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'teacher', 'status', 'requested_at', 'granted_at')
    list_filter = ('status',)
    actions = ['grant_contact_access']

    def grant_contact_access(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='GRANTED', granted_at=timezone.now())
        self.message_user(request, f"Contact access granted for {queryset.count()} requests.")

admin.site.register(BatchAnnouncement)
admin.site.register(StudyMaterial)
admin.site.register(Bookmark)
admin.site.register(Enrollment)
admin.site.register(Attendance)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(MessageAttachment)
admin.site.register(Notification)
admin.site.register(Review)
admin.site.register(Report)
admin.site.register(UserBlock)
admin.site.register(Payment)
admin.site.register(AuditLog)
