import math
from collections import deque
from typing import Any

from app.schemas.stream_data import (
    KeystrokeTelemetry,
    MouseClickTelemetry,
    MouseMoveTelemetry,
    TelemetryPayload,
)


class BiometricFeatureExtractor:
    """Extracts statistical and temporal behavioral features from raw telemetry streams.

    NOTE: Instantiated per WebSocket session to isolate user state.
    """

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.last_release_time: float | None = None
        self.hold_times: deque[float] = deque(maxlen=window_size)
        self.flight_times: deque[float] = deque(maxlen=window_size)
        self.mouse_velocities: deque[float] = deque(maxlen=window_size)

    def process_telemetry(self, event: TelemetryPayload) -> dict[str, Any] | None:
        if isinstance(event, KeystrokeTelemetry):
            return self._process_keystroke(event)
        elif isinstance(event, MouseMoveTelemetry):
            return self._process_mouse_move(event)
        elif isinstance(event, MouseClickTelemetry):
            return self._process_mouse_click(event)
        return None

    def _process_keystroke(self, event: KeystrokeTelemetry) -> dict[str, Any]:
        self.hold_times.append(event.hold_time)

        flight_time = 0.0
        if self.last_release_time is not None:
            flight_time = max(0.0, event.press_time - self.last_release_time)
            self.flight_times.append(flight_time)

        self.last_release_time = event.release_time

        mean_hold = sum(self.hold_times) / len(self.hold_times) if self.hold_times else 0.0
        mean_flight = sum(self.flight_times) / len(self.flight_times) if self.flight_times else 0.0

        std_hold = self._calc_std_dev(self.hold_times, mean_hold)
        std_flight = self._calc_std_dev(self.flight_times, mean_flight)

        return {
            "feature_type": "keystroke_aggregate",
            "hold_time": event.hold_time,
            "flight_time": flight_time,
            "mean_hold_time": round(mean_hold, 5),
            "std_hold_time": round(std_hold, 5),
            "mean_flight_time": round(mean_flight, 5),
            "std_flight_time": round(std_flight, 5),
            "key": event.key,
        }

    def _process_mouse_move(self, event: MouseMoveTelemetry) -> dict[str, Any]:
        self.mouse_velocities.append(event.velocity)
        mean_velocity = sum(self.mouse_velocities) / len(self.mouse_velocities)

        return {
            "feature_type": "mouse_move_aggregate",
            "velocity": event.velocity,
            "acceleration": event.acceleration or 0.0,
            "jerk": event.jerk or 0.0,
            "mean_velocity": round(mean_velocity, 2),
            "duration": event.duration,
        }

    def _process_mouse_click(self, event: MouseClickTelemetry) -> dict[str, Any]:
        return {
            "feature_type": "mouse_click_aggregate",
            "button": event.button,
            "x": event.x,
            "y": event.y,
        }

    @staticmethod
    def _calc_std_dev(data: deque[float], mean: float) -> float:
        if len(data) < 2:
            return 0.0
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return math.sqrt(variance)