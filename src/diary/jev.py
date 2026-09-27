import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from decouple import config

logger = logging.getLogger(__name__)

JEV_API_URL = "https://api.typesafe.ai/v1/systemone"

QUESTIONS = {
    "intent": {
        "type": "choice",
        "instructions": "What is the intent of this diary utterance?",
        "criteria": {
            "freeform": "a general note, reflection, or unstructured thought",
            "list": "a grouped set of items",
            "follow-up": "a reminder or follow-up tied to a specific day or time",
            "todo": "an action to do that has no specific day or time",
            "reschedule": "moving or changing an existing appointment",
        },
    },
    "subject": {
        "type": "choice",
        "instructions": "What is the subject of this diary utterance?",
        "criteria": {
            "diary": "a personal diary note",
            "finance": "money spent, received, owed, or paid",
            "appointment": "a meeting, booking, or visit at a place and time",
        },
    },
    "user_asked_for_diary": {
        "type": "noul",
        "instructions": "Does the speaker explicitly ask to add this to their diary?",
    },
    "continues_prior": {
        "type": "noul",
        "instructions": (
            "Does this utterance continue or complete one of the prior entries, "
            "judged by meaning rather than by comparing clocks?"
        ),
    },
}


class JevError(Exception):
    pass


def decide(state):
    api_key = config("JEV_API_KEY", default="")
    if not api_key:
        raise JevError("JEV_API_KEY is not set")
    body = json.dumps({
        "model": config("JEV_MODEL", default="jev-latest"),
        "state": state,
        "questions": QUESTIONS,
    }).encode("utf-8")
    req = Request(
        config("JEV_API_URL", default=JEV_API_URL),
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Jev request failed: %s", detail)
        raise JevError(detail) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Jev request error: %s", exc)
        raise JevError(str(exc)) from exc
