import json
import logging
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

OPENID_SCOPE = "openid"
EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
PROFILE_SCOPE = "https://www.googleapis.com/auth/userinfo.profile"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_LABELS_SCOPE = "https://www.googleapis.com/auth/gmail.labels"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"

LOGIN_SCOPES = [OPENID_SCOPE, EMAIL_SCOPE, PROFILE_SCOPE]
SERVICE_SCOPES = [GMAIL_SCOPE, GMAIL_LABELS_SCOPE, DRIVE_SCOPE, CALENDAR_SCOPE]
FULL_SCOPES = LOGIN_SCOPES + SERVICE_SCOPES

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_REVOKE_URI = "https://oauth2.googleapis.com/revoke"


class GoogleAuthError(Exception):
    pass


def redirect_uri():
    return getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "") or config("GOOGLE_OAUTH_REDIRECT_URI")


def create_authorization_url(scopes=None, login_hint=None):
    client_id = config("GOOGLE_CLIENT_ID")
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(scopes or FULL_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{GOOGLE_AUTH_URI}?{urlencode(params)}", state


def exchange_code_for_tokens(code):
    token_data = urlencode({
        "code": code,
        "client_id": config("GOOGLE_CLIENT_ID"),
        "client_secret": config("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }).encode("utf-8")
    req = Request(GOOGLE_TOKEN_URI, data=token_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Token exchange failed: %s", body)
        raise GoogleAuthError(body) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Token exchange error: %s", exc)
        raise GoogleAuthError(str(exc)) from exc


def get_google_user_info(access_token):
    req = Request(GOOGLE_USERINFO_URI)
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("User info failed: %s", body)
        raise GoogleAuthError(body) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("User info error: %s", exc)
        raise GoogleAuthError(str(exc)) from exc


def revoke_access_token(access_token):
    data = urlencode({"token": access_token}).encode("utf-8")
    req = Request(GOOGLE_REVOKE_URI, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=30):
            return True
    except HTTPError as exc:
        if exc.code == 400:
            return True
        logger.warning("Token revocation returned HTTP %s", exc.code)
        return False
    except (URLError, TimeoutError) as exc:
        logger.error("Token revocation error: %s", exc)
        return False
