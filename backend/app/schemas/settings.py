from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SettingsResponse(BaseModel):
    timezone: str
    base_currency: str


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str | None = None
    base_currency: str | None = None

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) > 64:
            raise ValueError("Timezone is too long")
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Timezone must be a valid IANA zone") from error
        return value

    @field_validator("base_currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Base currency must be three uppercase letters")
        return value

    @model_validator(mode="after")
    def nonempty_and_nonnull(self) -> SettingsUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one setting is required")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Settings cannot be null")
        return self
