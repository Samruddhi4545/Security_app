import asyncio
import json
import math
import time
import requests
import websockets #type:ignore
from pynput import keyboard, mouse #type:ignore

# API Configuration
BASE_URL = "http://127.0.0.1:8001"
WS_URL = "ws://127.0.0.1:8001/ws/telemetry"

USERNAME = "admin"
PASSWORD = "password123"

# Thread-safe async event queue & loop handle
event_queue = asyncio.Queue()
main_loop: asyncio.AbstractEventLoop | None = None

# Keystroke tracking state
active_keys: dict[str, float] = {}

# Mouse movement sampling & physics state
mouse_state = {
    "last_x": None,
    "last_y": None,
    "last_time": None,
    "last_velocity": 0.0,
    "last_acceleration": 0.0,
}
MOUSE_SAMPLE_INTERVAL = 0.05  # Sample mouse movement every 50ms (20 Hz)


def get_jwt_token() -> str | None:
    """Authenticate with backend and retrieve a JWT access token."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5,
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("Successfully authenticated and received JWT token.")
            return token
        print(f"Login failed: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"Could not connect to auth server: {e}")
        return None


# --- Pynput Event Listeners ---

def on_key_press(key):
    try:
        key_name = key.char if hasattr(key, "char") and key.char else str(key)
        if key_name not in active_keys:
            active_keys[key_name] = time.time()
    except Exception:
        pass


def on_key_release(key):
    try:
        key_name = key.char if hasattr(key, "char") and key.char else str(key)
        press_time = active_keys.pop(key_name, None)
        release_time = time.time()

        if press_time and main_loop:
            hold_time = release_time - press_time
            payload = {
                "type": "keystroke",
                "key": key_name,
                "press_time": press_time,
                "release_time": release_time,
                "hold_time": hold_time,
            }
            asyncio.run_coroutine_threadsafe(event_queue.put(payload), main_loop)
    except Exception as e:
        print(f"Error handling key release: {e}")


def on_mouse_click(x, y, button, pressed):
    if not pressed and main_loop:  # Log on release
        payload = {
            "type": "mouse_click",
            "button": str(button),
            "x": float(x),
            "y": float(y),
            "timestamp": time.time(),
        }
        asyncio.run_coroutine_threadsafe(event_queue.put(payload), main_loop)


def on_mouse_move(x, y):
    current_time = time.time()
    last_time = mouse_state["last_time"]

    # Sample rate throttling
    if last_time is not None and (current_time - last_time) < MOUSE_SAMPLE_INTERVAL:
        return

    if mouse_state["last_x"] is not None and main_loop:
        dt = current_time - last_time
        if dt > 0:
            dx = x - mouse_state["last_x"]
            dy = y - mouse_state["last_y"]
            distance = math.hypot(dx, dy)

            # Kinematic calculations: Velocity, Acceleration, Jerk
            velocity = distance / dt
            dv = velocity - mouse_state["last_velocity"]
            acceleration = dv / dt

            da = acceleration - mouse_state["last_acceleration"]
            jerk = da / dt

            payload = {
                "type": "mouse_move",
                "start_x": float(mouse_state["last_x"]),
                "start_y": float(mouse_state["last_y"]),
                "end_x": float(x),
                "end_y": float(y),
                "duration": round(dt, 4),
                "velocity": round(velocity, 2),
                "acceleration": round(acceleration, 2),
                "jerk": round(jerk, 2),
                "timestamp": current_time,
            }

            # Update kinematics state
            mouse_state["last_velocity"] = velocity
            mouse_state["last_acceleration"] = acceleration
            asyncio.run_coroutine_threadsafe(event_queue.put(payload), main_loop)

    # Update position and timestamp
    mouse_state["last_x"] = x
    mouse_state["last_y"] = y
    mouse_state["last_time"] = current_time


# --- Async Stream Manager ---

async def stream_telemetry(token: str):
    """Maintain WebSocket connection and stream queued events."""
    uri = f"{WS_URL}?token={token}"

    async with websockets.connect(uri) as ws:
        print("Telemetry stream established with backend!")

        while True:
            event_data = await event_queue.get()
            await ws.send(json.dumps(event_data))

            # Receive real-time anomaly score response from backend
            response_raw = await ws.recv()
            # response = json.loads(response_raw)
            # if response.get("anomaly_score") is not None:
            #     print(f"Anomaly Score: {response['anomaly_score']}")

            event_queue.task_done()


async def main():
    global main_loop
    main_loop = asyncio.get_running_loop()

    token = get_jwt_token()
    if not token:
        print("Exiting: Failed to acquire valid JWT token.")
        return

    # Start pynput background listeners
    keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    mouse_listener = mouse.Listener(on_click=on_mouse_click, on_move=on_mouse_move)

    keyboard_listener.start()
    mouse_listener.start()
    print("Input listeners active (Keystrokes + Throttled Mouse Kinematics)...")

    try:
        await stream_telemetry(token)
    except websockets.exceptions.ConnectionClosed:
        print("Telemetry WebSocket connection dropped.")
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        keyboard_listener.stop()
        mouse_listener.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBackground agent stopped manually.")
