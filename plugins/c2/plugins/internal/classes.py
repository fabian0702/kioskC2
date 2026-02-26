from typing import Union, Optional, Any, Literal

from pydantic import BaseModel, Field
from secrets import token_hex

Argument = Union[str, int, float, bool]


class PluginMessage(BaseModel):
    client_id: str
    id:str = Field(default_factory=lambda : token_hex(16))
    operation: str
    state: Literal['pending', 'complete', 'error'] = 'pending'
    data:Optional[Any] = None
    args: list[Argument] = []
    kwargs: dict[str, Argument] = {}

class ClientMessage(BaseModel):
    operation: str
    data: dict[str, Any]
    id:str = Field(default_factory=lambda : token_hex(16))
