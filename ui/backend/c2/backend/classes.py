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
