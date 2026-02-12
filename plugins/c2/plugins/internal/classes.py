from typing import Any, Optional

from pydantic import BaseModel, Field
from secrets import token_hex


class PluginMessage(BaseModel):
    client_id: str
    id:str = Field(default_factory=lambda : token_hex(16))
    operation: str
    data:Optional[Any] = None
    args: list[Any] = []
    kwargs: dict[str, Any] = {}

class ClientMessage(BaseModel):
    operation: str
    data: dict[str, Any]
    id:str = Field(default_factory=lambda : token_hex(16))
