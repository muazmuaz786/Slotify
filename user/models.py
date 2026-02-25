from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    role_choices = [
        ("admin", "Admin"),
        ("booking_manager", "Booking Manager"),
        ("user", "User"),
    ]

    bio = models.TextField(blank=True)
    
    phone_number = models.CharField(max_length=20, blank=True)
    
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    role = models.CharField(max_length=20, choices=role_choices, default="user")
    
    last_name = models.CharField(max_length=255, blank=True)
    
    first_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', null=True, blank=True
    )

    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)

    last_login = models.DateTimeField(blank=True, null=True)

    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.username