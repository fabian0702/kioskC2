from typing import Optional, Any, Union

from pydantic import BaseModel, Field, ConfigDict

from secrets import token_hex

Argument = Union[str, int, float, bool, bytes]

class PluginMessage(BaseModel):
    model_config = ConfigDict(ser_json_bytes='base64', val_json_bytes='base64')
    client_id: str
    id: str = Field(default_factory=lambda: token_hex(16))
    operation: str
    data: Optional[Any] = None
    args: list[Argument] = []
    kwargs: dict[str, Argument] = {}


def short(value: Any, limit: int = 100) -> str:
    """Caps a value's string form for logging - command args/results can be
    screenshots/audio/etc as base64, which must never hit the logs whole."""
    s = str(value)
    return s if len(s) <= limit else f"{s[:limit]}...<+{len(s) - limit} chars>"
