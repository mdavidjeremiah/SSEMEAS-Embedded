"""Request bodies (validated by Pydantic)."""
from pydantic import BaseModel, Field, model_validator


class Credentials(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6)


class EmailBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    password: str = Field(min_length=6)


class Reading(BaseModel):
    distance_cm: float
    ts: int | None = None      # epoch milliseconds; only used for buffered (batch) readings
    rssi: int | None = None    # Wi-Fi signal strength in dBm


class PhoneBody(BaseModel):
    number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")   # international format, e.g. +256772123456


class CodeBody(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class Prefs(BaseModel):
    warning: bool = True
    danger: bool = True
    recovery: bool = True
    offline: bool = False
    quiet_on: bool = False
    quiet_from: int = Field(22, ge=0, le=23)
    quiet_to: int = Field(6, ge=0, le=23)


class TankIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    location: str = Field("", max_length=120)
    depth_cm: float = Field(gt=10, le=1000)
    sensor_offset_cm: float = Field(ge=0)
    warn_pct: float = Field(gt=0, lt=100)
    danger_pct: float = Field(gt=0, le=100)
    hysteresis_pct: float = Field(3, ge=0, le=20)
    offline_after_s: int = Field(120, ge=10)

    @model_validator(mode="after")
    def check_limits(self):
        if self.warn_pct >= self.danger_pct or self.sensor_offset_cm >= self.depth_cm:
            raise ValueError("Warning must be below Danger, and the sensor offset must be smaller than the depth")
        return self


class UserPatch(BaseModel):
    role: str | None = Field(None, pattern="^(user|admin)$")
    active: bool | None = None
    tanks: list[int] | None = None
