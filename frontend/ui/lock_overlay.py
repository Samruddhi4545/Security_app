import logging
from PySide6.QtCore import Qt, Signal #type:ignore
from PySide6.QtGui import QKeyEvent, QCloseEvent #type:ignore
from PySide6.QtWidgets import ( #type:ignore
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)

logger = logging.getLogger("SentinelAI.LockOverlay")


class LockOverlayWidget(QWidget):
    """
    Hardened full-screen security lock overlay.
    Triggered when telemetry anomaly score breaches critical thresholds.
    
    Note: Provides strong application-level interface dominance. OS-level
    kiosk lockdown (blocking Ctrl+Alt+Del) requires low-level system hooks.
    """
    unlock_requested = Signal(str)  # Emits (password_attempt)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Sentinel-AI — Security Lockout")

        # Hardened Window Flags: Fullscreen, Always-on-top, Frameless
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.BypassWindowManagerHint
        )

        # Force keyboard focus dominance
        self.setFocusPolicy(Qt.StrongFocus)

        self._init_ui()

    def _init_ui(self):
        # Dark, high-visibility warning background
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Container Box
        card = QFrame()
        card.setFixedSize(420, 320)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 2px solid #ef4444;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)

        # Warning Header
        header = QLabel("🚨 SYSTEM LOCKED")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: bold; border: none;")
        card_layout.addWidget(header)

        subtext = QLabel("Behavioral anomaly detected.\nPlease re-authenticate to restore session access.")
        subtext.setAlignment(Qt.AlignCenter)
        subtext.setWordWrap(True)
        subtext.setStyleSheet("color: #94a3b8; font-size: 13px; border: none; margin-bottom: 10px;")
        card_layout.addWidget(subtext)

        # Password Input
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter administrator password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """)
        self.pass_input.returnPressed.connect(self._on_unlock_click)
        card_layout.addWidget(self.pass_input)

        # Dynamic Error Label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #f87171; font-size: 12px; border: none;")
        card_layout.addWidget(self.error_label)

        # Unlock Button
        self.unlock_btn = QPushButton("Unlock System")
        self.unlock_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.unlock_btn.clicked.connect(self._on_unlock_click)
        card_layout.addWidget(self.unlock_btn)

        main_layout.addWidget(card)

    def lock_system(self):
        """Activates full-screen lockout and captures keyboard/mouse focus."""
        self.pass_input.clear()
        self.error_label.setText("")
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.pass_input.setFocus()
        logger.warning("System locked due to critical behavioral anomaly score.")

    def unlock_system(self):
        """Restores normal interface state."""
        self.hide()
        logger.info("System successfully unlocked.")

    def set_error(self, message: str):
        """Displays authentication failure messages on the overlay."""
        self.error_label.setText(message)
        self.pass_input.clear()
        self.pass_input.setFocus()

    def _on_unlock_click(self):
        password = self.pass_input.text().strip()
        if not password:
            self.set_error("Password cannot be empty.")
            return

        self.error_label.setText("Verifying credentials...")
        self.unlock_requested.emit(password)

    # --- Hardened System Lock Controls ---

    def closeEvent(self, event: QCloseEvent):
        """Block Alt+F4 or window closure attempts while locked."""
        event.ignore()

    def keyPressEvent(self, event: QKeyEvent):
        """Intercept OS and window navigation keys."""
        if event.key() in (Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
            event.ignore()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        """Re-assert top window priority if focus is lost (e.g. Alt+Tab attempt)."""
        if event.type() == event.Type.ActivationChange and not self.isActiveWindow():
            self.raise_()
            self.activateWindow()
        super().changeEvent(event)