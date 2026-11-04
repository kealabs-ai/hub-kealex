from typing import Optional

from pydantic import BaseModel, Field


class GoogleDriveCredentialIn(BaseModel):
    credential_json: Optional[str] = Field(default=None, max_length=16000)
    drive_folder_id: Optional[str] = Field(default=None, max_length=255)
