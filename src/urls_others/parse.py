import re

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
METHOD_PATH_RE = re.compile(
    r"(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/[^\s<>\"']*",
    re.IGNORECASE,
)
BARE_PATH_RE = re.compile(r"(?:/api/|/v\d+/)[^\s<>\"']+")
TRAILING_PUNCT = ".,;:!?)]}'\""


def _trim(value):
    return value.rstrip(TRAILING_PUNCT)


def _overlaps(start, end, occupied):
    for left, right in occupied:
        if start < right and end > left:
            return True
    return False


def parse_references(text):
    """Return (matches, note). matches is a list of (kind, value) in text order."""
    source = text or ""
    found = []
    occupied = []

    def add(kind, match):
        if _overlaps(match.start(), match.end(), occupied):
            return
        value = _trim(match.group(0))
        if kind == "endpoint":
            value = re.sub(r"\s+", " ", value)
        if not value:
            return
        found.append((match.start(), kind, value))
        occupied.append((match.start(), match.end()))

    for match in URL_RE.finditer(source):
        add("url", match)
    for match in METHOD_PATH_RE.finditer(source):
        add("endpoint", match)
    for match in BARE_PATH_RE.finditer(source):
        add("endpoint", match)

    found.sort(key=lambda item: item[0])
    occupied.sort()
    parts = []
    cursor = 0
    for start, end in occupied:
        parts.append(source[cursor:start])
        cursor = end
    parts.append(source[cursor:])
    note = re.sub(r"\s+", " ", "".join(parts)).strip()
    matches = [(kind, value) for _, kind, value in found]
    return matches, note
