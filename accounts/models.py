import json

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class AccountUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_google_account = models.BooleanField(default=False)

    objects = AccountUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class UserSecret(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="secrets")
    encrypted_google_access_token = models.TextField(blank=True, default="")
    encrypted_google_refresh_token = models.TextField(blank=True, default="")
    encrypted_google_token_expiry = models.TextField(blank=True, default="")
    google_token_scopes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_scopes_list(self):
        if not self.google_token_scopes:
            return []
        try:
            return json.loads(self.google_token_scopes)
        except json.JSONDecodeError:
            return []

    def set_scopes_list(self, scopes):
        self.google_token_scopes = json.dumps(scopes) if scopes else ""
