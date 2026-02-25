from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from base.models import (
    Booking,
    Comment,
    CommentImage,
    Rate,
    Review,
    ReviewImage,
    Service,
    ServiceImage,
    ServiceVideo,
    Slot,
)
from user.models import User


class FileUrlMixin:
    """Small helper to build absolute URLs for uploaded files."""

    def _file_url(self, file_field):
        request = self.context.get("request") if hasattr(self, "context") else None
        if file_field and hasattr(file_field, "url"):
            return request.build_absolute_uri(file_field.url) if request else file_field.url
        return None


class ServiceImageSerializer(FileUrlMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceImage
        fields = ["id", "image", "image_url"]
        read_only_fields = ["id", "image_url"]

    def get_image_url(self, obj):
        return self._file_url(obj.image)


class ServiceVideoSerializer(FileUrlMixin, serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceVideo
        fields = ["id", "video", "video_url"]
        read_only_fields = ["id", "video_url"]

    def get_video_url(self, obj):
        return self._file_url(obj.video)


class ReviewImageSerializer(FileUrlMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ReviewImage
        fields = ["id", "image", "image_url"]
        read_only_fields = ["id", "image_url"]

    def get_image_url(self, obj):
        return self._file_url(obj.image)


class CommentImageSerializer(FileUrlMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CommentImage
        fields = ["id", "image", "image_url"]
        read_only_fields = ["id", "image_url"]

    def get_image_url(self, obj):
        return self._file_url(obj.image)


class ServiceListSerializer(FileUrlMixin, serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField(read_only=True)
    logo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = ["id", "name", "category", "average_rating", "logo_url"]
        read_only_fields = ["id", "average_rating", "logo_url", "name", "category"]

    def get_average_rating(self, obj):
        cache_key = f"service:{obj.id}:avg_rating"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        rates = obj.rates.filter(deleted=False)
        if not rates.exists():
            avg = 0.0
        else:
            avg = round(rates.aggregate(average=Avg("rating"))["average"] or 0, 2)
        cache.set(cache_key, avg, 300)
        return avg

    def get_logo_url(self, obj):
        return self._file_url(obj.logo)


class ServiceDetailSerializer(FileUrlMixin, serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField(read_only=True)
    logo_url = serializers.SerializerMethodField(read_only=True)
    videos = serializers.SerializerMethodField(read_only=True)
    images = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "category",
            "average_rating",
            "logo_url",
            "videos",
            "images",
            "email",
            "phone_number",
            "is_active",
            "working_hours",
            "location",
            "price",
        ]
        read_only_fields = [
            "id",
            "average_rating",
            "logo_url",
            "name",
            "description",
            "category",
            "email",
            "phone_number",
            "is_active",
            "working_hours",
            "location",
            "price",
        ]

    def get_logo_url(self, obj):
        return self._file_url(obj.logo)

    def get_videos(self, obj):
        return [self._file_url(video.video) for video in obj.videos.all() if video.video]

    def get_images(self, obj):
        return [self._file_url(image.image) for image in obj.images.all() if image.image]

    def get_average_rating(self, obj):
        cache_key = f"service:{obj.id}:avg_rating"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        rates = obj.rates.filter(deleted=False)
        if not rates.exists():
            avg = 0.0
        else:
            avg = round(rates.aggregate(average=Avg("rating"))["average"] or 0, 2)
        cache.set(cache_key, avg, 300)
        return avg


class ServiceCreateUpdateSerializer(FileUrlMixin, serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "category",
            "logo",
            "logo_url",
            "email",
            "phone_number",
            "is_active",
            "working_hours",
            "location",
            "price",
        ]
        read_only_fields = ["id", "logo_url"]

    def get_logo_url(self, obj):
        return self._file_url(obj.logo)

    def validate_logo(self, value):
        if value and hasattr(value, "content_type") and not value.content_type.startswith("image/"):
            raise serializers.ValidationError("The uploaded file must be an image.")
        return value

    def validate_name(self, value):
        qs = Service.objects.filter(name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A service with this name already exists.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be a positive number.")
        return value

    def validate(self, data):
        if self.instance and self.instance.deleted:
            raise serializers.ValidationError("Cannot update a deleted service.")
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["logo_url"] = self._file_url(instance.logo)
        return representation

    def delete(self, instance):
        self._release_slot(instance.service, instance.date, instance.time, exclude_booking_id=instance.pk)
        instance.deleted = True
        instance.save()


class BookingSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(deleted=False, is_active=True))
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(deleted=False))

    class Meta:
        model = Booking
        fields = [
            "id",
            "service",
            "user",
            "date",
            "time",
            "status",
            "notes",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "price"]

    conflict_statuses = ("pending", "confirmed", "completed")

    def _release_slot(self, service, date, time, exclude_booking_id=None):
        slot = Slot.objects.filter(service=service, date=date, time=time).first()
        if not slot:
            return
        qs = Booking.objects.filter(
            service=service,
            date=date,
            time=time,
            deleted=False,
            status__in=self.conflict_statuses,
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        if not qs.exists():
            slot.is_booked = False
            slot.save(update_fields=["is_booked"])

    def validate(self, data):
        if self.instance and self.instance.deleted:
            raise serializers.ValidationError("Cannot update a deleted booking.")

        service = data.get("service") or (self.instance.service if self.instance else None)
        date = data.get("date") or (self.instance.date if self.instance else None)
        time_value = data.get("time") or (self.instance.time if self.instance else None)
        user = data.get("user") or (self.instance.user if self.instance else None)

        if user and user.deleted:
            raise serializers.ValidationError({"user": "Cannot book with a deleted user."})

        if service and (service.deleted or not service.is_active):
            raise serializers.ValidationError({"service": "This service is not available."})

        if date and time_value:
            today = timezone.localdate()
            now_time = timezone.localtime().time()
            if date < today or (date == today and time_value <= now_time):
                raise serializers.ValidationError({"time": "Cannot book a past time."})

            conflict_qs = Booking.objects.filter(
                service=service,
                date=date,
                time=time_value,
                deleted=False,
                status__in=self.conflict_statuses,
            )
            if self.instance:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)
            if conflict_qs.exists():
                raise serializers.ValidationError({"time": "This time slot is already booked."})

            slot = Slot.objects.filter(service=service, date=date, time=time_value).first()
            self._slot = slot
            if slot and slot.is_booked:
                is_same_as_instance = (
                    self.instance
                    and slot.service_id == self.instance.service_id
                    and slot.date == self.instance.date
                    and slot.time == self.instance.time
                )
                if not is_same_as_instance:
                    raise serializers.ValidationError({"time": "This time slot is already booked."})

        return data

    @transaction.atomic
    def create(self, validated_data):
        service = validated_data["service"]
        date = validated_data["date"]
        time_value = validated_data["time"]

        slot = getattr(self, "_slot", None)
        if slot is None:
            slot = Slot.objects.create(service=service, date=date, time=time_value, is_booked=False)
        if slot.is_booked:
            raise serializers.ValidationError({"time": "This time slot is already booked."})

        slot.is_booked = True
        slot.save(update_fields=["is_booked"])

        price = service.price
        booking = Booking.objects.create(**validated_data, price=price)
        return booking

    @transaction.atomic
    def update(self, instance, validated_data):
        original = (instance.service, instance.date, instance.time)

        new_service = validated_data.get("service", instance.service)
        new_date = validated_data.get("date", instance.date)
        new_time = validated_data.get("time", instance.time)
        new_status = validated_data.get("status", instance.status)

        cancelling = new_status == "cancelled"
        slot_changed = (new_service, new_date, new_time) != original

        if not cancelling and slot_changed:
            slot = getattr(self, "_slot", None) or Slot.objects.filter(
                service=new_service, date=new_date, time=new_time
            ).first()
            if slot is None:
                slot = Slot.objects.create(service=new_service, date=new_date, time=new_time, is_booked=False)
            if slot.is_booked and slot != Slot.objects.filter(
                service=original[0], date=original[1], time=original[2]
            ).first():
                raise serializers.ValidationError({"time": "This time slot is already booked."})
            slot.is_booked = True
            slot.save(update_fields=["is_booked"])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if slot_changed or "service" in validated_data:
            instance.price = new_service.price

        instance.save()

        if cancelling:
            self._release_slot(original[0], original[1], original[2], exclude_booking_id=instance.pk)
        elif slot_changed:
            self._release_slot(original[0], original[1], original[2], exclude_booking_id=instance.pk)

        return instance

    def delete(self, instance):
        instance.deleted = True
        instance.save()


class RateSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Rate
        fields = ["id", "Service", "user", "rating", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=Rate.objects.all(),
                fields=["Service", "user"],
                message="You have already rated this service.",
            )
        ]
         
    def validate(self, data):
        service = data.get("Service") or getattr(self.instance, "Service", None)
        if service and service.deleted:
            raise serializers.ValidationError("Cannot rate a deleted service.")
        return data


class ReviewSerializer(FileUrlMixin, serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "author",
            "service",
            "title",
            "description",
            "images",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at", "deleted"]

    def validate_service(self, value):
        if value.deleted:
            raise serializers.ValidationError("Cannot review a deleted service.")
        return value

    def validate(self, data):
        if self.instance and self.instance.deleted:
            raise serializers.ValidationError("Cannot update a deleted review.")
        return data


class CommentSerializer(FileUrlMixin, serializers.ModelSerializer):
    images = CommentImageSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "review",
            "parent",
            "text",
            "images",
            "created_at",
            "updated_at",
            "deleted",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at", "deleted"]

    def validate_review(self, value):
        if value.deleted:
            raise serializers.ValidationError("Cannot comment on a deleted review.")
        return value

    def validate(self, data):
        if self.instance and self.instance.deleted:
            raise serializers.ValidationError("Cannot update a deleted comment.")
        return data


class SlotSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(deleted=False))

    class Meta:
        model = Slot
        fields = ["id", "service", "date", "time", "is_booked"]
        read_only_fields = ["id"]

    def validate(self, data):
        if self.instance and self.instance.is_booked:
            raise serializers.ValidationError("Cannot modify an already booked slot.")
        service = data.get("service") or (self.instance.service if self.instance else None)
        date = data.get("date") or (self.instance.date if self.instance else None)
        time_value = data.get("time") or (self.instance.time if self.instance else None)

        if service and date and time_value:
            qs = Slot.objects.filter(service=service, date=date, time=time_value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"time": "A slot already exists for this time."})
        return data