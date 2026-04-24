from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from signature_pad import SignaturePadField
from .managers import CustomUserManager
from django.conf import settings


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPES = (
        (1, 'SuperAdmin'),
        (2, 'Admin'),
        (3, 'User'),
    )

    user_type = models.PositiveSmallIntegerField(
    choices=USER_TYPES,
    default=3
     )
    username = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True)
   

    verification_token = models.CharField(max_length=100, null=True, blank=True)

    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    

class PendingUser(models.Model):
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PendingUser: {self.email}"


class PDFReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    blood_group = models.CharField(max_length=3, null=True, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    signature = models.TextField(null=True, blank=True) 
   
    def __str__(self):
        return f"Report by {self.user.email} at {self.created_at}"


class Article(models.Model):
    author      = models.ForeignKey(User, on_delete=models.CASCADE)
    title       = models.CharField(max_length=300)
    content     = models.TextField()
    tags        = models.CharField(max_length=200, blank=True)  # comma separated
    price       = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    is_premium  = models.BooleanField(default=False)
    read_count  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)