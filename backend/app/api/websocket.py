from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status #type:ignore
from pydantic import TypeAdapter, ValidationError

from app.core.connection_manager import manager #type:ignore
from app.core.security import decode_access_token
from app.schemas.stream_data import TelemetryPayload
from app.services.anomaly_detector import BehavioralAnomalyDetector
from app.services.biometrics import BiometricFeatureExtractor

router = APIRouter(prefix="/ws", tags=["Telemetry Stream"])

telemetry_adapter = TypeAdapter(TelemetryPayload)


def _authenticate(token: str) -> str | None:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return payload["sub"]


@router.websocket("/telemetry")
async def telemetry_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Agent connects here — sends telemetry, receives its own score, and
    the computed score is also broadcast to any dashboard connections."""
    user = _authenticate(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    feature_extractor = BiometricFeatureExtractor(window_size=20)
    anomaly_detector = BehavioralAnomalyDetector(user_id=user)

    await websocket.accept()
    manager.connect(user, websocket)
    print(f"Agent WebSocket connected for user: {user}")

    try:
        while True:
            raw_data = await websocket.receive_text()

            try:
                telemetry_event = telemetry_adapter.validate_json(raw_data)
            except ValidationError as val_err:
                await websocket.send_json({"status": "error", "detail": val_err.errors()})
                continue

            features = feature_extractor.process_telemetry(telemetry_event)
            anomaly_score = anomaly_detector.predict_and_update(features) if features else None

            result = {
                "status": "processed",
                "event_type": telemetry_event.type,
                "anomaly_score": round(anomaly_score, 4) if anomaly_score is not None else None,
            }
            # Broadcast to all connections for this user (agent + dashboard)
            await manager.broadcast(user, result)
    except WebSocketDisconnect:
        print(f"Agent WebSocket disconnected for user: {user}. Persisting models...")
        anomaly_detector.save_models()
    except Exception as e:
        print(f"Telemetry stream error: {e}")
        anomaly_detector.save_models()
    finally:
        manager.disconnect(user, websocket)


@router.websocket("/dashboard")
async def dashboard_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Qt dashboard connects here — only listens for broadcasted scores,
    never sends telemetry."""
    user = _authenticate(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    manager.connect(user, websocket)
    print(f"Dashboard WebSocket connected for user: {user}")

    try:
        while True:
            # Keep connection alive; dashboard doesn't send data, just waits
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Dashboard WebSocket disconnected for user: {user}")
    finally:
        manager.disconnect(user, websocket)