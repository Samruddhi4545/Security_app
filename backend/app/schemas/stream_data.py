from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class KeystrokeTelemetry(BaseModel):
    type: Literal["keystroke"]
    key: str
    press_time: float = Field(..., description="UNIX timestamp of key press")
    release_time: float = Field(..., description="UNIX timestamp of key release")
    hold_time: float = Field(..., ge=0, description="Duration key was held down in seconds")


class MouseClickTelemetry(BaseModel):
    type: Literal["mouse_click"]
    button: str
    x: float
    y: float
    timestamp: float = Field(..., description="UNIX timestamp of click event")


class MouseMoveTelemetry(BaseModel):
    type: Literal["mouse_move"]
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    duration: float = Field(..., gt=0, description="Duration of movement segment in seconds")
    velocity: float = Field(..., ge=0, description="Movement speed in pixels/sec")
    acceleration: float | None = Field(default=0.0, description="Rate of change of velocity")
    jerk: float | None = Field(default=0.0, description="Rate of change of acceleration")
    timestamp: float = Field(..., description="UNIX timestamp of movement completion")


# Tagged Discriminated Union for high-performance payload parsing
TelemetryPayload = Annotated[
    Union[KeystrokeTelemetry, MouseClickTelemetry, MouseMoveTelemetry],
    Field(discriminator="type"),
]