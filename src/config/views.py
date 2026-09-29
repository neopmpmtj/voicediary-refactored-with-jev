from django.http import JsonResponse


def healthz(request):
    """Unauthenticated liveness probe.

    Deliberately cheap and side-effect free: no auth, no DB, no session writes.
    Used by uptime monitors and deploy checks.
    """
    return JsonResponse({"status": "ok"})
