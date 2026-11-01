from typing import Optional
from pydantic import BaseModel, Field

class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    agente_id: Optional[str] = None


