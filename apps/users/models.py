from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import hashlib
from phonenumber_field.modelfields import PhoneNumberField
from utils.timestamped import TimeStampedModel

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    #fintech E.164 format storing
    phone = PhoneNumberField(unique=True)
    #raw phone number
    raw_phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    #kyc verify fields
    is_varified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["email", "raw_phone_number"]
    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"])
        ]
        constraints = [
            models.UniqueConstraint(fields=["phone"], name="unique_phone")
        ]

    def __str__(self):
        return f"{self.username} {self.phone}"
        

class UserProfile(TimeStampedModel):
    '''One-to-One extension of User.
    Keeps the User model lean. Holds supplementary personal/KYC data.
    '''
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank = True)
    country = models.CharField(max_length=100, default="BANGLADESH")
    postal_code = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = "user_profiles"
    
    def __str__(self):
        return f"Profile of {self.user.username}"
