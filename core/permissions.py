from rest_framework import permissions
from profiles.models import Profile
class IsAccountAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only requests are allowed for any users (both authorized and anonymous).
    Write/Delete requests are allowed only to authorized Admin.
    """

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS or
            request.user and
            request.user.is_superuser
        )

class IsStudent(permissions.BasePermission):
    """
    Allows access only to student.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name == 'student')

class IsAdminUser(permissions.BasePermission):
    
    def has_permission(self, request, view):
        if request.user:
            return request.user.is_superuser
        return False

class IsStudentorInstituteStaff(permissions.BasePermission):
    """
    Allows access only to student or institutestaff.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['student', 'institutestaff'])

class IsStudentorInstituteStafforAdmin(permissions.BasePermission):
    """
    Allows access only to student or institutestaff or admin.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['student', 'institutestaff'] or request.user.is_staff)

class IsInstituteStaff(permissions.BasePermission):
    """
    Allows access only to institutestaff.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['institutestaff', 'organizationstaff'])

class IsInstituteStafforAdmin(permissions.BasePermission):
    """
    Allows access only to institutestaff.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['institutestaff', 'organizationstaff'] or request.user.is_superuser)

class IsQuestionAdminUser(permissions.BasePermission):
    """
    Allows access only to institutestaff.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['admin', 'content_manager'])

class IsMMPAdminUser(permissions.BasePermission):
    """
    Allows access only to MMPAdmin.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (Profile.objects.get(user=request.user).user_group.name in ['admin'])
    