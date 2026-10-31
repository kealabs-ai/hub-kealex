from datetime import date, datetime
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator

class ActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="todo", min_length=1, max_length=36, validation_alias=AliasChoices("status", "columnId", "column_id"))
    priority: Literal["baixa", "media", "alta"] = "media"
    dueDate: date | None = Field(default=None, validation_alias=AliasChoices("dueDate", "due_date"))

    @field_validator("dueDate", mode="before")
    @classmethod
    def parse_due_date(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return value


class ActivityUpdate(BaseModel):
    id: str = Field(validation_alias=AliasChoices("id", "activityId", "activity_id"))
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=36, validation_alias=AliasChoices("status", "columnId", "column_id"))
    priority: Literal["baixa", "media", "alta"] | None = None
    dueDate: date | None = Field(default=None, validation_alias=AliasChoices("dueDate", "due_date"))

    @field_validator("dueDate", mode="before")
    @classmethod
    def parse_due_date(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str) and "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return value


class ActivityColumnCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#087E96", pattern=r"^#[0-9A-Fa-f]{6}$")


class ActivityColumnUpdate(BaseModel):
    id: str = Field(validation_alias=AliasChoices("id", "columnId", "column_id"))
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ActivityDelete(BaseModel):
    id: str = Field(validation_alias=AliasChoices("id", "activityId", "activity_id"))


class ActivityColumnDelete(BaseModel):
    id: str = Field(validation_alias=AliasChoices("id", "columnId", "column_id"))
