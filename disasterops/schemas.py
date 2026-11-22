from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .config import Phone

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=40,
        pattern=r"^[a-zA-Z0-9_-]+$",
    ),
]
Password = Annotated[str, Field(min_length=12, max_length=128)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Accuracy = Annotated[float, Field(ge=0, le=100000, allow_inf_nan=False)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: Username
    password: Annotated[str, Field(min_length=1, max_length=128)]


class Register(Input):
    username: Username
    password: Password
    phone: Phone | None = None


class SOS(Input):
    request_id: UUID
    source: Literal["BUTTON", "SHAKE_DEVICE"] = "BUTTON"
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    accuracy_meters: Accuracy | None = None
    battery_percentage: Annotated[int, Field(ge=0, le=100)] | None = None
    message: Annotated[str, Field(max_length=2000, pattern=r"^[^\x00]*$")] | None = None

    @model_validator(mode="after")
    def validate_location(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both coordinates or neither")
        if self.latitude is None and self.accuracy_meters is not None:
            raise ValueError("Accuracy requires coordinates")
        return self


class Safety(Input):
    status: Literal["SAFE", "NEEDS_HELP"]


class OpenIncident(Input):
    report_id: UUID


class Assign(Input):
    responder_username: Username


class ShareRequest(Input):
    report_id: UUID


class ShareSubmit(Input):
    token: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{43}$")]
    latitude: Latitude
    longitude: Longitude
    accuracy_meters: Accuracy | None = None


class GatewaySMS(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=12000)]
    sender: Annotated[str, Field(min_length=1, max_length=32)] | None = None
    phoneNumber: Annotated[str, Field(min_length=1, max_length=32)] | None = None


class GatewayEvent(BaseModel):
    id: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[^\x00]+$")]
    event: Literal["sms:received"]
    payload: GatewaySMS
