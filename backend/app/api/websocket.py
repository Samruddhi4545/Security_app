from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status #type:ignore
from pydantic import TypeAdapter, ValidationError

from app.core.security import decode_access_token #type:ignore
from app.schemas.stream_data import TelemetryPayload #type:ignore
from app.services.anomaly_detector import BehavioralAnomalyDetector #type:ignore
from app.services.biometrics import BiometricFeatureExtractor #type:ignore

router = APIRouter(prefix="/ws", tags=["Telemetry Stream"])

# TypeAdapter for Pydantic V2 discriminated union validation
telemetry_adapter = TypeAdapter(TelemetryPayload)


@router.websocket("/telemetry")
async def telemetry_endpoint(websocket: WebSocket, token: str = Query(...)):
    # 1. Authenticate WebSocket connection token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        print("Rejected unauthorized WebSocket connection attempt.")
        return

    user = payload["sub"]

    # 2. Instantiate per-session biometric feature extractor and user ML detector
    feature_extractor = BiometricFeatureExtractor(window_size=20)
    anomaly_detector = BehavioralAnomalyDetector(user_id=user)

    await websocket.accept()
    print(f"WebSocket connected for user: {user}")

    try:
        while True:
            # 3. Receive raw telemetry packet from background agent
            raw_data = await websocket.receive_text()

            try:
                # Validates against discriminated union using TypeAdapter
                telemetry_event = telemetry_adapter.validate_json(raw_data)
            except ValidationError as val_err:
                await websocket.send_json({"status": "error", "detail": val_err.errors()})
                continue

            # 4. Extract biometric features & run real-time River ML scoring
            features = feature_extractor.process_telemetry(telemetry_event)
            anomaly_score = anomaly_detector.predict_and_update(features) if features else None

            # 5. Send real-time inference result back to client
            await websocket.send_json(
                {
                    "status": "processed",
                    "event_type": telemetry_event.type,
                    "anomaly_score": round(anomaly_score, 4) if anomaly_score is not None else None,
                }
            )

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user: {user}. Persisting models...")
        anomaly_detector.save_models()
    except Exception as e:
        print(f"Telemetry stream error: {e}")
        anomaly_detector.save_models()
        await websocket.close()