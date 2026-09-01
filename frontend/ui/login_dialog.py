import logging
import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)

logger = logging.getLogger("SentinelAI.LoginDialog")


class LoginDialog(QDialog):
    """Initial login dialog for HTTP REST authentication."""

    def __init__(self, base_url: str = "127.0.0.1:8001", parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.access_token = None

        self.setWindowTitle("Sentinel-AI — Authentication")
        self.setFixedSize(360, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel("🔐 Sentinel-AI Security Access")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        # Blank inputs by default — no embedded credentials
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.returnPressed.connect(self._attempt_login)
        layout.addWidget(self.pass_input)

        self.login_btn = QPushButton("Authenticate & Connect")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.login_btn.clicked.connect(self._attempt_login)
        layout.addWidget(self.login_btn)

    def _attempt_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password required.")
            return

        try:
            response = requests.post(
                f"http://{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=4
            )
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                logger.info("REST Authentication successful.")
                self.accept()  # Triggers DialogCode.Accepted
            else:
                QMessageBox.critical(self, "Auth Failed", "Invalid credentials provided.")
        except Exception as e:
            logger.error(f"Login REST request failed: {e}")
            QMessageBox.critical(self, "Connection Error", f"Unable to reach server at {self.base_url}")