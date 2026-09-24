from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """
    Permission check for Admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.user_type == 'ADMIN')
        )

class IsStudent(permissions.BasePermission):
    """
    Permission check for Student users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'STUDENT'
        )

class IsTeacher(permissions.BasePermission):
    """
    Permission check for Teacher users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'TEACHER'
        )

class IsVerifiedTeacher(permissions.BasePermission):
    """
    Permission check for verified Teacher users.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.user_type == 'TEACHER'):
            return False
        return getattr(getattr(request.user, 'teacher_profile', None), 'is_verified', False)

class IsBatchTeacher(permissions.BasePermission):
    """
    Permission check to ensure object belongs to the teacher who created the batch.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        if hasattr(obj, 'batch'):
            return obj.batch.teacher == request.user
        return False

class IsEnrolledStudent(permissions.BasePermission):
    """
    Permission check to ensure student is enrolled in the batch.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated and request.user.user_type == 'STUDENT'):
            return False
        batch = getattr(obj, 'batch', obj)
        return batch.enrollments.filter(student=request.user, status='ACTIVE').exists()

class IsConversationParticipant(permissions.BasePermission):
    """
    Permission check to ensure user is part of the conversation.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user == obj.student or request.user == obj.teacher

class IsConnectionParticipant(permissions.BasePermission):
    """
    Permission check to ensure user is sender or receiver of connection request.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user == obj.sender or request.user == obj.receiver

class IsSelfOrAdmin(permissions.BasePermission):
    """
    Permission check allowing users to access their own object or admins.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff or request.user.user_type == 'ADMIN':
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user
