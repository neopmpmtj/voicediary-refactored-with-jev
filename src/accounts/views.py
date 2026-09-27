import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from accounts.google import (
    FULL_SCOPES,
    SERVICE_SCOPES,
    GoogleAuthError,
    create_authorization_url,
    exchange_code_for_tokens,
    get_google_user_info,
)
from accounts.models import User, UserSecret
from accounts.services import create_google_user, revoke_user_tokens, store_user_tokens

logger = logging.getLogger(__name__)


def _clear_oauth_session(request):
    for key in ("oauth_state", "oauth_flow", "oauth_user_id"):
        request.session.pop(key, None)


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


class GoogleLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        try:
            auth_url, state = create_authorization_url(scopes=FULL_SCOPES)
        except Exception as exc:
            logger.error("Failed to create authorization URL: %s", exc)
            messages.error(request, "Unable to connect to Google. Please try again.")
            return redirect("accounts:login")
        request.session["oauth_state"] = state
        request.session["oauth_flow"] = "login"
        return redirect(auth_url)


class GoogleCallbackView(View):
    def get(self, request):
        if request.GET.get("error"):
            messages.error(request, "Google sign-in was cancelled or failed.")
            _clear_oauth_session(request)
            return redirect("accounts:login")

        state = request.GET.get("state")
        if not state or state != request.session.get("oauth_state"):
            messages.error(request, "Invalid authentication request. Please try again.")
            _clear_oauth_session(request)
            return redirect("accounts:login")

        code = request.GET.get("code")
        if not code:
            messages.error(request, "Invalid authentication response. Please try again.")
            _clear_oauth_session(request)
            return redirect("accounts:login")

        if request.session.get("oauth_flow") == "connect":
            return self._connect(request, code)

        try:
            tokens = exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")
            if not access_token:
                raise GoogleAuthError("No access token in response")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in")
            scopes = tokens.get("scope", "").split(" ")
            user_info = get_google_user_info(access_token)
            google_email = (user_info.get("email") or "").lower()
            if not google_email:
                raise GoogleAuthError("No email in user info")
            if not user_info.get("email_verified", False):
                messages.error(request, "Please verify your Google account email first.")
                return redirect("accounts:login")

            existing = User.objects.filter(email=google_email).first()
            if existing and existing.has_usable_password() and not existing.is_google_account:
                request.session["google_link_data"] = {
                    "email": google_email,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": expires_in,
                    "scopes": scopes,
                    "user_info": user_info,
                }
                return redirect("accounts:google_link_confirm")
            if existing:
                store_user_tokens(existing, access_token, refresh_token, expires_in, scopes)
                if not existing.first_name and user_info.get("given_name"):
                    existing.first_name = user_info["given_name"]
                if not existing.last_name and user_info.get("family_name"):
                    existing.last_name = user_info["family_name"]
                existing.save()
                login(request, existing)
                messages.success(request, "Welcome back.")
                return redirect(settings.LOGIN_REDIRECT_URL)

            user = create_google_user(user_info)
            store_user_tokens(user, access_token, refresh_token, expires_in, scopes)
            login(request, user)
            messages.success(request, "Account created. Welcome.")
            return redirect(settings.LOGIN_REDIRECT_URL)
        except GoogleAuthError as exc:
            logger.error("Google OAuth error: %s", exc)
            messages.error(request, "Google sign-in failed. Please try again.")
            return redirect("accounts:login")
        finally:
            request.session.pop("oauth_state", None)

    def _connect(self, request, code):
        if not request.user.is_authenticated or request.session.get("oauth_user_id") != request.user.id:
            _clear_oauth_session(request)
            messages.error(request, "Session invalid. Please try again.")
            target = "accounts:login" if not request.user.is_authenticated else "accounts:profile"
            return redirect(target)
        try:
            tokens = exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")
            if not access_token:
                raise GoogleAuthError("No access token in response")
            store_user_tokens(
                request.user,
                access_token,
                tokens.get("refresh_token"),
                tokens.get("expires_in"),
                tokens.get("scope", "").split(" "),
            )
            messages.success(request, "Google services connected.")
        except GoogleAuthError as exc:
            logger.error("Google connect error: %s", exc)
            messages.error(request, "Failed to connect Google services. Please try again.")
        finally:
            _clear_oauth_session(request)
        return redirect("accounts:profile")


class GoogleLinkConfirmView(View):
    def get(self, request):
        link_data = request.session.get("google_link_data")
        if not link_data:
            messages.error(request, "No pending account link. Please try again.")
            return redirect("accounts:login")
        return render(request, "accounts/google_link_confirm.html", {"email": link_data["email"]})

    def post(self, request):
        link_data = request.session.get("google_link_data")
        if not link_data:
            messages.error(request, "No pending account link. Please try again.")
            return redirect("accounts:login")
        user = User.objects.filter(email=link_data["email"]).first()
        if not user or not user.check_password(request.POST.get("password", "")):
            messages.error(request, "Incorrect password. Please try again.")
            return render(request, "accounts/google_link_confirm.html", {"email": link_data["email"]})
        store_user_tokens(
            user,
            link_data["access_token"],
            link_data["refresh_token"],
            link_data["expires_in"],
            link_data["scopes"],
        )
        user_info = link_data.get("user_info") or {}
        if not user.first_name and user_info.get("given_name"):
            user.first_name = user_info["given_name"]
        if not user.last_name and user_info.get("family_name"):
            user.last_name = user_info["family_name"]
        user.save()
        request.session.pop("google_link_data", None)
        login(request, user)
        messages.success(request, "Your Google account has been linked.")
        return redirect(settings.LOGIN_REDIRECT_URL)


@method_decorator(login_required, name="dispatch")
class GoogleConnectView(View):
    def get(self, request):
        secret = UserSecret.objects.filter(user=request.user).first()
        if secret and secret.encrypted_google_access_token:
            granted = set(secret.get_scopes_list())
            if set(SERVICE_SCOPES).issubset(granted):
                messages.info(request, "Your Google account is already connected.")
                return redirect("accounts:profile")
        try:
            auth_url, state = create_authorization_url(
                scopes=FULL_SCOPES,
                login_hint=request.user.email,
            )
        except Exception as exc:
            logger.error("Failed to create connect URL: %s", exc)
            messages.error(request, "Unable to connect to Google. Please try again.")
            return redirect("accounts:profile")
        request.session["oauth_state"] = state
        request.session["oauth_flow"] = "connect"
        request.session["oauth_user_id"] = request.user.id
        return redirect(auth_url)


@method_decorator(login_required, name="dispatch")
class GoogleConnectCallbackView(View):
    def get(self, request):
        if request.session.get("oauth_flow") != "connect":
            return redirect("accounts:google_callback")
        if request.session.get("oauth_user_id") != request.user.id:
            messages.error(request, "Session mismatch. Please try again.")
            return redirect("accounts:profile")
        if request.GET.get("error"):
            _clear_oauth_session(request)
            messages.error(request, "Google connection was cancelled.")
            return redirect("accounts:profile")
        state = request.GET.get("state")
        if not state or state != request.session.get("oauth_state"):
            _clear_oauth_session(request)
            messages.error(request, "Invalid request. Please try again.")
            return redirect("accounts:profile")
        code = request.GET.get("code")
        if not code:
            _clear_oauth_session(request)
            messages.error(request, "Invalid response. Please try again.")
            return redirect("accounts:profile")
        try:
            tokens = exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")
            if not access_token:
                raise GoogleAuthError("No access token in response")
            store_user_tokens(
                request.user,
                access_token,
                tokens.get("refresh_token"),
                tokens.get("expires_in"),
                tokens.get("scope", "").split(" "),
            )
            messages.success(request, "Google services connected.")
        except GoogleAuthError as exc:
            logger.error("Google connection error: %s", exc)
            messages.error(request, "Failed to connect Google services. Please try again.")
        finally:
            _clear_oauth_session(request)
        return redirect("accounts:profile")


@method_decorator(login_required, name="dispatch")
class GoogleDisconnectView(View):
    def post(self, request):
        user = request.user
        if user.is_google_account and not user.has_usable_password():
            messages.error(request, "You cannot disconnect Google because it is your only login method.")
            return redirect("accounts:profile")
        if revoke_user_tokens(user):
            messages.success(request, "Google account disconnected.")
        else:
            messages.warning(request, "Google account may not have been fully disconnected.")
        return redirect("accounts:profile")


@login_required
def profile_view(request):
    secret = UserSecret.objects.filter(user=request.user).first()
    return render(request, "accounts/profile.html", {
        "scopes": secret.get_scopes_list() if secret else [],
        "connected": bool(secret and secret.encrypted_google_access_token),
    })
