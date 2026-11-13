from pydantic import BaseModel, Field


class GoogleOAuthCompletionIn(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=1, max_length=2048)


class GoogleUploadOAuthStartIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=1024)
    client_secret: str = Field(min_length=1, max_length=1024)


class GoogleUploadOAuthCompletionIn(GoogleOAuthCompletionIn):
    client_id: str = Field(min_length=1, max_length=1024)
    client_secret: str = Field(min_length=1, max_length=1024)