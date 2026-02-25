from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False) and getattr(request.user, "role", None) == "admin")
    
class IsBookingManager(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False) and getattr(request.user, "role", None) == "booking_manager")
