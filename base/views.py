from django.utils import timezone
from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from base.models import Booking, Comment, Rate, Review, Service, Slot
from user.permissions import IsAdmin, IsBookingManager

from base.serializers import (
    BookingSerializer,
    CommentSerializer,
    RateSerializer,
    ReviewSerializer,
    ServiceCreateUpdateSerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
    SlotSerializer,
)

def _is_admin_or_manager(user):
    role = getattr(user, "role", None)
    return getattr(user, "is_staff", False) or getattr(user, "is_superuser", False) or role in {"admin", "booking_manager"}


class IsBookingOwnerOrAdmin(BasePermission):
    """
    Only booking owner, admin, or booking manager can mutate.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if _is_admin_or_manager(request.user):
            return True
        return obj.user_id == getattr(request.user, "id", None)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Exposes list/retrieve for browsing services and create/update for providers/admins.
    Uses soft-delete; deleted services are hidden from queries.
    """

    queryset = Service.objects.filter(deleted=False)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdmin | IsBookingManager]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        if self.action == "retrieve":
            return ServiceDetailSerializer
        return ServiceCreateUpdateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.is_active = False
        instance.save(update_fields=["deleted", "is_active"])


class BookingViewSet(viewsets.ModelViewSet):
    """
    Handles booking creation with conflict checks handled in the serializer.
    Supports soft-delete and simple filtering via query parameters.
    """

    permission_classes = [IsBookingOwnerOrAdmin]
    serializer_class = BookingSerializer

    def get_queryset(self):
        qs = Booking.objects.select_related("service", "user").filter(deleted=False)

        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)

        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)

        # If non-admin/manager, force to their own bookings regardless of query param
        if not _is_admin_or_manager(self.request.user):
            qs = qs.filter(user_id=self.request.user.id)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(date=date_param)

        upcoming = self.request.query_params.get("upcoming")
        if upcoming in {"1", "true", "True"}:
            today = timezone.localdate()
            qs = qs.filter(date__gte=today)

        return qs.order_by("date", "time")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        serializer = self.get_serializer(instance)
        serializer.delete(instance)

    @action(detail=False, methods=["get"], url_path="check-slot")
    def check_slot(self, request):
        """
        Endpoint to quickly check if a service/date/time is available.
        Expects ?service=<id>&date=YYYY-MM-DD&time=HH:MM
        """

        service_id = request.query_params.get("service")
        date = request.query_params.get("date")
        time_value = request.query_params.get("time")

        if not (service_id and date and time_value):
            return Response(
                {"detail": "service, date, and time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"slot-availability:{service_id}:{date}:{time_value}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"available": cached})

        conflict = Booking.objects.filter(
            service_id=service_id,
            date=date,
            time=time_value,
            deleted=False,
            status__in=BookingSerializer.conflict_statuses,
        ).exists()

        slot = Slot.objects.filter(service_id=service_id, date=date, time=time_value).first()
        slot_blocked = slot.is_booked if slot else False

        available = not (conflict or slot_blocked)
        cache.set(cache_key, available, 300)
        return Response({"available": available})


class SlotViewSet(viewsets.ModelViewSet):
    """
    Manage explicit slot objects (optional if bookings auto-create slots).
    Only admins/booking managers can change slots.
    """

    permission_classes = [IsAdmin | IsBookingManager]
    serializer_class = SlotSerializer
    queryset = Slot.objects.select_related("service").all()

    def perform_destroy(self, instance):
        if instance.is_booked:
            raise ValidationError({"detail": "Cannot delete a booked slot."})
        instance.delete()


class RateViewSet(viewsets.ModelViewSet):
    """
    Allows users to rate services once. Uses unique-together validator in serializer.
    Read open; writes require auth.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = RateSerializer

    def get_queryset(self):
        qs = Rate.objects.filter(deleted=False).select_related("Service", "user")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(Service_id=service_id)
        return qs.order_by("-created_at")

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save(update_fields=["deleted"])


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.filter(deleted=False).select_related("service", "author")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs.order_by("-created_at")

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save(update_fields=["deleted"])


class CommentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CommentSerializer

    def get_queryset(self):
        qs = Comment.objects.filter(deleted=False).select_related("review", "author")
        review_id = self.request.query_params.get("review")
        if review_id:
            qs = qs.filter(review_id=review_id)
        return qs.order_by("created_at")

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save(update_fields=["deleted"])
