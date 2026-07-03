from typing import Any

def short(value:Any, limit:int = 100) -> str:
    """Caps a value's string form for logging - command args/results can be
    screenshots/audio/etc as base64, which must never hit the logs whole."""
    s = str(value)
    return s if len(s) <= limit else f"{s[:limit]}...<+{len(s) - limit} chars>"
