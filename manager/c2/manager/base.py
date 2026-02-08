from pydantic import BaseModel, Field
from secrets import token_hex

class Message(BaseModel):
    operation: str
    data: dict
    id:str = Field(default_factory=lambda : token_hex(16))