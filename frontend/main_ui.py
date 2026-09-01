import sys
import logging
import requests
from PySide6.QtWidgets import QApplication #type:ignore

from frontend.network.ws_client import TelemetryWebSocketClient
from frontend.ui.dashboard import DashboardWidget
from frontend.ui.lock_overlay import LockOverlayWidget
from frontend.ui.login_dialog import LoginDialog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SentinelAI.Main")

# Corrected to Port 8001 (resolves Windows Socket Permission Issue)
BASE_URL = "127.0.0.1:8001"
ANOMALY_THRESHOLD = 0.85
CONSECUTIVE_BREACH_LIMIT = 3


class SentinelAppController:
    """State Machine Controller managing UI components, security states, and network events."""

    def __init__(self, app: QApplication):
        self.app = app
        self.jwt_token = None
        self.consecutive_high_scores = 0

        # Instantiate UI components with port 8001
        self.dashboard = DashboardWidget()
        self.lock_overlay = LockOverlayWidget()
        self.ws_client = TelemetryWebSocketClient(base_url=BASE_URL)

        self._wire_signals()

    def _wire_signals(self):
        # WS Score -> Dashboard Update & Lock Evaluation
        self.ws_client.score_received.connect(self._handle_score)
        self.ws_client.connection_changed.connect(self.dashboard.update_connection_status)

        # Lock Overlay Re-Auth Request
        self.lock_overlay.unlock_requested.connect(self._handle_unlock_attempt)

    def start(self):
        """Execute authentication dialog and launch the monitoring state."""
        login_dialog = LoginDialog(base_url=BASE_URL)
        if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
            logger.info("Authentication cancelled by user. Exiting.")
            sys.exit(0)

        self.jwt_token = login_dialog.access_token
        logger.info("Authentication successful. Displaying dashboard.")

        self.dashboard.show()
        self.ws_client.connect_with_token(self.jwt_token)

    def _handle_score(self, event_type: str, score: float):
        self.dashboard.update_telemetry(event_type, score)

        # Multi-frame threshold evaluation (prevents false positives from brief speed spikes)
        if score >= ANOMALY_THRESHOLD:
            self.consecutive_high_scores += 1
            logger.warning(
                f"High anomaly score ({score:.4f}). "
                f"Breach count: {self.consecutive_high_scores}/{CONSECUTIVE_BREACH_LIMIT}"
            )
        else:
            self.consecutive_high_scores = 0

        if self.consecutive_high_scores >= CONSECUTIVE_BREACH_LIMIT and not self.lock_overlay.isVisible():
            logger.error("Sustained anomaly detected! Triggering system lock screen.")
            self.lock_overlay.lock_system()

    def _handle_unlock_attempt(self, password: str):
        logger.info("Verifying secondary re-authentication request...")
        try:
            response = requests.post(
                f"http://{BASE_URL}/auth/login",
                json={"username": "admin", "password": password},
                timeout=4,
            )
            if response.status_code == 200:
                logger.info("Re-authentication verified. Resetting threat counters and unlocking.")
                self.consecutive_high_scores = 0
                self.lock_overlay.unlock_system()
            else:
                self.lock_overlay.set_error("Invalid password. Unlock denied.")
        except Exception as e:
            logger.error(f"Re-auth request error: {e}")
            self.lock_overlay.set_error("Backend verification unreachable.")

    def shutdown(self):
        logger.info("Shutting down Sentinel-AI Frontend...")
        self.ws_client.close()


def main():
    app = QApplication(sys.argv)
    controller = SentinelAppController(app)

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()