from django.db import models
from user.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class Service(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    count = models.IntegerField(default=0)
    location = models.CharField(max_length=255, blank=True)

    working_hours = models.CharField(max_length=255, blank=True)

    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='services'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    deleted = models.BooleanField(default=False)

    logo = models.ImageField(upload_to='service_logos/', null=True, blank=True)

    def __str__(self):
        return self.name
    
class Booking(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='books'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='books'
    )
    date = models.DateField()
    time = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('confirmed', _('Confirmed')),
            ('completed', _('Completed')),
            ('cancelled', _('Cancelled')),
        ],
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.service.name} ({self.date})"



class Rate(models.Model):
    Service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='rates'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rates'
    )
    rating = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    deleted = models.BooleanField(default=False)

class Review(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    title = models.CharField(max_length=250, blank=True)   

    description = models.CharField(max_length=10000, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    deleted = models.BooleanField(default=False)
class Comment(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    text = models.CharField(max_length=10000, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    deleted = models.BooleanField(default=False)


class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="review_images/", null=True, blank=True)

    def __str__(self) -> str:
        return f"Image for {self.review_id}"



class CommentImage(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="comment_images/", null=True, blank=True)

    def __str__(self) -> str:
        return f"Image for {self.comment_id}"
    
class Slot(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    date = models.DateField()
    time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Slot for {self.service.name} on {self.date} at {self.time}"
    
class ServiceVideo(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="videos",
    )
    video = models.FileField(upload_to="service_videos/", null=True, blank=True)

    def __str__(self) -> str:
        return f"Video for {self.service.name}"

class ServiceImage(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="service_images/", null=True, blank=True)

    def __str__(self) -> str:
        return f"Image for {self.service.name}"
    