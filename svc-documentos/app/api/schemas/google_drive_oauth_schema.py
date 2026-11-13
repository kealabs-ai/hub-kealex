from pydantic import BaseModel, Field


class GoogleOAuthCompletionIn(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=1, max_length=2048)
