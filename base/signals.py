from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from base.models import Booking, Rate, Slot


# Cache key helpers
def slot_cache_key(service_id, date, time_value):
    return f"slot-availability:{service_id}:{date}:{time_value}"


def avg_rating_cache_key(service_id):
    return f"service:{service_id}:avg_rating"


@receiver([post_save, post_delete], sender=Booking, dispatch_uid="booking_slot_cache_invalidation")
def invalidate_slot_cache_on_booking(sender, instance, **kwargs):
    cache.delete(slot_cache_key(instance.service_id, instance.date, instance.time))


@receiver([post_save, post_delete], sender=Slot, dispatch_uid="slot_cache_invalidation")
def invalidate_slot_cache_on_slot(sender, instance, **kwargs):
    cache.delete(slot_cache_key(instance.service_id, instance.date, instance.time))


@receiver([post_save, post_delete], sender=Rate, dispatch_uid="rate_avg_cache_invalidation")
def invalidate_average_rating_cache(sender, instance, **kwargs):
    service_id = instance.Service_id
    if service_id:
        cache.delete(avg_rating_cache_key(service_id))
