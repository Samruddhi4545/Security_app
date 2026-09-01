import json
import logging
from PySide6.QtCore import QObject, Signal, QUrl #type:ignore
from PySide6.QtNetwork import QWebSocket #type:ignore

logger = logging.getLogger("SentinelAI.WSClient")


class TelemetryWebSocketClient(QObject):
    """
    Asynchronous QWebSocket client that receives real-time anomaly scores
    broadcast from the FastAPI backend.
    """
    # Signals expected by main_ui.py
    score_received = Signal(str, float)  # (event_type, score)
    connection_changed = Signal(bool)    # True = connected, False = disconnected

    def __init__(self, base_url: str = "127.0.0.1:8001"):
        super().__init__()
        self.base_url = base_url
        self.ws = QWebSocket()

        self.ws.connected.connect(self._on_connected)
        self.ws.disconnected.connect(self._on_disconnected)
        self.ws.textMessageReceived.connect(self._on_message_received)
        self.ws.errorOccurred.connect(self._on_error)

    def connect_with_token(self, token: str):
        """Initiate WebSocket connection passing the JWT token as a query parameter."""
        # Fixed: Listen-only route for PySide6 Dashboard
        ws_url = f"ws://{self.base_url}/ws/dashboard?token={token}"
        logger.info(f"Connecting QWebSocket to ws://{self.base_url}/ws/dashboard...")
        self.ws.open(QUrl(ws_url))

    def close(self):
        """Gracefully terminate WebSocket connection."""
        if self.ws.isValid():
            self.ws.close()

    def _on_connected(self):
        logger.info("QWebSocket connection established successfully to /ws/dashboard.")
        self.connection_changed.emit(True)

    def _on_disconnected(self):
        logger.warning("QWebSocket connection lost.")
        self.connection_changed.emit(False)

    def _on_message_received(self, message: str):
        """Parse incoming JSON score payload from backend and emit score_received."""
        try:
            data = json.loads(message)
            event_type = data.get("event_type", "unknown")
            score = float(data.get("anomaly_score", 0.0))
            self.score_received.emit(event_type, score)
        except Exception as e:
            logger.error(f"Failed to parse incoming WebSocket message: {e}")

    def _on_error(self, error):
        logger.error(f"QWebSocket error occurred: {self.ws.errorString()}")