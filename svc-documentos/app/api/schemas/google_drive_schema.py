from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class GoogleDriveCredentialIn(BaseModel):
    credential_json: Optional[str] = Field(
        default=None,
        max_length=16000,
        validation_alias=AliasChoices("credential_json", "credentialJson"),
    )
    drive_folder_id: Optional[str] = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("drive_folder_id", "driveFolderId"),
    )
