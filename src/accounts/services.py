import logging
from datetime import datetime, timedelta, timezone

from src.accounts.crypto import decrypt_value, encrypt_value
from src.accounts.google import GoogleAuthError, refresh_access_token, revoke_access_token
from src.accounts.models import User, UserSecret

logger = logging.getLogger(__name__)


def account_list_item(user):
    return {
        "email": user.email,
        "is_google_account": user.is_google_account,
    }


def accounts_list():
    return [account_list_item(row) for row in User.objects.order_by("email")]


def store_user_tokens(user, access_token, refresh_token, expires_in, scopes):
    secret, _created = UserSecret.objects.get_or_create(user=user)
    secret.encrypted_google_access_token = encrypt_value(access_token)
    if refresh_token:
        secret.encrypted_google_refresh_token = encrypt_value(refresh_token)
    if expires_in:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        secret.encrypted_google_token_expiry = encrypt_value(expiry.isoformat())
    secret.set_scopes_list(scopes)
    secret.save()
    logger.info("Stored OAuth tokens for user %s", user.pk)


def create_google_user(user_info):
    email = (user_info.get("email") or "").lower()
    user = User.objects.create_user(email=email, password=None)
    user.first_name = user_info.get("given_name") or ""
    user.last_name = user_info.get("family_name") or ""
    user.is_google_account = True
    user.save()
    return user


def google_access_token(user):
    secret = UserSecret.objects.filter(user=user).first()
    if not secret or not secret.encrypted_google_access_token:
        raise GoogleAuthError("Google account is not linked")
    access_token = decrypt_value(secret.encrypted_google_access_token)
    expiry_raw = decrypt_value(secret.encrypted_google_token_expiry)
    expired = True
    if expiry_raw:
        try:
            expiry = datetime.fromisoformat(expiry_raw)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            expired = datetime.now(timezone.utc) >= expiry - timedelta(seconds=60)
        except ValueError:
            expired = True
    if access_token and not expired:
        return access_token
    refresh_token = decrypt_value(secret.encrypted_google_refresh_token)
    if not refresh_token:
        raise GoogleAuthError("Google access token expired")
    tokens = refresh_access_token(refresh_token)
    new_access = tokens.get("access_token")
    if not new_access:
        raise GoogleAuthError("Google token refresh returned no access token")
    store_user_tokens(
        user,
        new_access,
        tokens.get("refresh_token") or refresh_token,
        tokens.get("expires_in"),
        secret.get_scopes_list(),
    )
    return new_access


def revoke_user_tokens(user):
    secret = UserSecret.objects.filter(user=user).first()
    if not secret or not secret.encrypted_google_access_token:
        return True
    access_token = decrypt_value(secret.encrypted_google_access_token)
    ok = True
    if access_token:
        ok = revoke_access_token(access_token)
    secret.encrypted_google_access_token = ""
    secret.encrypted_google_refresh_token = ""
    secret.encrypted_google_token_expiry = ""
    secret.google_token_scopes = ""
    secret.save()
    return ok
