DEFAULT_TIMEZONE = "Europe/Lisbon"
DEFAULT_DURATION_MINUTES = 30
DEFAULT_REMINDERS = [
    {"method": "popup", "minutes": 10},
    {"method": "popup", "minutes": 1440},
]

BATCH_PROMPT_TEMPLATE = (
    "IMPORTANT: Respond in the same language as the input text below. "
    "Do not translate; preserve the language of the input.\n\n"
    "You are an assistant specialized in extracting MULTIPLE calendar events from natural language requests.\n"
    "Your task is to transform the given text into a list of calendar events in Google Calendar API format.\n\n"
    "System date (reference for 'today'): {system_date}\n"
    "System time (reference for 'now'): {system_time}\n"
    "Default timezone: {default_timezone}\n"
    "Default duration (minutes): {default_duration_minutes}\n\n"
    "Text to analyze:\n"
    "{content_text}\n\n"
    "Extract and return ALL events implied by the text. Examples of multi-event patterns:\n"
    "- 'Monday through Friday at 5pm' -> 5 events (one per weekday)\n"
    "- 'every Tuesday and Thursday at 10am for the next 3 weeks' -> 6 events\n"
    "- 'physiotherapy on Feb 24, 25, 26 at 17:00' -> 3 events\n"
    "- 'daily at 9am from tomorrow for 5 days' -> 5 events\n\n"
    "Each event must have:\n"
    "- summary: Brief title (in the same language as the input)\n"
    "- description: Optional detailed description\n"
    "- location: If mentioned\n"
    '- start: {{dateTime: ISO 8601, timeZone: "{default_timezone}"}}\n'
    '- end: {{dateTime: ISO 8601, timeZone: "{default_timezone}"}}\n'
    "- reminders: {{useDefault: false, overrides: {reminders_json_example}}}\n\n"
    "DATE/TIME RULES (critical):\n"
    "1) Relative dates ('tomorrow', 'next Monday') must be converted to absolute dates using system date/time.\n"
    "2) Never schedule in the past relative to system date/time.\n"
    "3) If date is not mentioned, choose the next valid occurrence.\n"
    "4) If time is not mentioned, use 09:00.\n"
    "5) For ambiguous times without AM/PM, infer the NEXT future occurrence from system time.\n"
    "6) If inferred time for today has passed, advance to the next logical day.\n"
    "7) If duration is not mentioned, use {default_duration_minutes} minutes.\n\n"
    "REMINDERS:\n"
    "A) Identify explicitly mentioned reminders in the text.\n"
    "B) Convert to minutes: 1 hour=60, 1 day=1440, etc.\n"
    "C) If none mentioned, use: {reminders_description}\n"
    "D) For medical appointments without reminders: add 1 day before (1440).\n\n"
    "Respond ONLY with valid JSON (no markdown, no extra text).\n"
    "Exact format:\n"
    "{{\n"
    '  "events": [\n'
    "    {{\n"
    '      "summary": "event title",\n'
    '      "description": "optional",\n'
    '      "location": "optional",\n'
    '      "start": {{"dateTime": "{example_date}T17:00:00", "timeZone": "{default_timezone}"}},\n'
    '      "end": {{"dateTime": "{example_date}T18:00:00", "timeZone": "{default_timezone}"}},\n'
    '      "reminders": {{"useDefault": false, "overrides": {reminders_json_example}}}\n'
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "If there is insufficient information to create at least one event, return exactly:\n"
    '{{"error": "Insufficient information to create calendar events"}}'
)


def reminder_description(reminders):
    parts = []
    for item in reminders:
        minutes = item.get("minutes", 0)
        if minutes < 60:
            parts.append(f"{minutes} minutes before")
        elif minutes == 60:
            parts.append("1 hour before")
        elif minutes < 1440:
            parts.append(f"{minutes // 60} hours before")
        elif minutes == 1440:
            parts.append("1 day before")
        else:
            parts.append(f"{minutes // 1440} days before")
    return ", ".join(parts)


def extraction_prompt(content_text, system_date, system_time, timezone=DEFAULT_TIMEZONE):
    import json

    reminders_json = json.dumps(DEFAULT_REMINDERS, ensure_ascii=False)
    return BATCH_PROMPT_TEMPLATE.format(
        system_date=system_date,
        system_time=system_time,
        example_date=system_date,
        default_timezone=timezone or DEFAULT_TIMEZONE,
        default_duration_minutes=DEFAULT_DURATION_MINUTES,
        reminders_description=reminder_description(DEFAULT_REMINDERS),
        reminders_json_example=reminders_json,
        content_text=content_text or "",
    )
