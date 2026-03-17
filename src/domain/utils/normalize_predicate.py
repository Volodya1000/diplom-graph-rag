import re

_RE_NON_ALNUM = re.compile(r"[^A-Za-z0-9_]")


def normalize_predicate(predicate: str) -> str:
    result = re.sub(r"[\s\-]+", "_", predicate.strip())
    result = _RE_NON_ALNUM.sub("", result)
    return result.upper() or "RELATED_TO"
