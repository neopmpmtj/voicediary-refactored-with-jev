from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from src.accounts.models import User, UserSecret


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_google_account", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Google", {"fields": ("is_google_account",)}),)
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(UserSecret)
class UserSecretAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
