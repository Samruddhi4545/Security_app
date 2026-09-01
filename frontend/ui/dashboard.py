import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QFrame
)

logger = logging.getLogger("SentinelAI.Dashboard")


class DashboardWidget(QWidget):
    """Main operational dashboard for continuous telemetry monitoring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sentinel-AI — Behavioral Telemetry Monitor")
        self.resize(650, 480)

        # Track stylesheet state to avoid wasteful QSS re-parsing on every 20Hz event
        self._current_color_tier = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header Bar
        header_layout = QHBoxLayout()
        self.title_label = QLabel("🛡️ Sentinel-AI Continuous Protection")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.status_badge = QLabel("DISCONNECTED")
        self.status_badge.setStyleSheet("""
            background-color: #ef4444; color: white; padding: 4px 8px;
            border-radius: 4px; font-weight: bold; font-size: 11px;
        """)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        layout.addLayout(header_layout)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Anomaly Meter Display
        meter_layout = QVBoxLayout()
        self.score_label = QLabel("Current Anomaly Threat Score: 0.0000")
        self.score_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        meter_layout.addWidget(self.score_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Apply initial green styling
        self._update_progress_style("#22c55e")
        self._current_color_tier = "#22c55e"

        meter_layout.addWidget(self.progress_bar)
        layout.addLayout(meter_layout)

        # Telemetry Stream Log
        log_label = QLabel("Live Behavior Stream Audit:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #4af626; font-family: Consolas, monospace;")
        layout.addWidget(self.log_output)

    def update_connection_status(self, connected: bool):
        """Slot to handle WebSocket state updates."""
        if connected:
            self.status_badge.setText("ACTIVE MONITORING")
            self.status_badge.setStyleSheet("""
                background-color: #22c55e; color: white; padding: 4px 8px;
                border-radius: 4px; font-weight: bold; font-size: 11px;
            """)
        else:
            self.status_badge.setText("DISCONNECTED")
            self.status_badge.setStyleSheet("""
                background-color: #ef4444; color: white; padding: 4px 8px;
                border-radius: 4px; font-weight: bold; font-size: 11px;
            """)

    def update_telemetry(self, event_type: str, score: float):
        """Slot to handle real-time anomaly score updates with optimized state checks."""
        percentage = int(score * 100)
        self.progress_bar.setValue(percentage)
        self.score_label.setText(f"Current Anomaly Threat Score: {score:.4f}")

        # Determine target color tier based on threat severity
        if score >= 0.85:
            target_color = "#ef4444"  # Red
        elif score >= 0.60:
            target_color = "#eab308"  # Yellow
        else:
            target_color = "#22c55e"  # Green

        # Only update stylesheet when crossing threshold boundaries
        if target_color != self._current_color_tier:
            self._update_progress_style(target_color)
            self._current_color_tier = target_color

        # Append to live audit log
        log_entry = f"[{event_type.upper()}] Anomaly Score: {score:.4f}"
        self.log_output.append(log_entry)

    def _update_progress_style(self, chunk_color: str):
        """Helper to re-style progress bar chunk color."""
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc; border-radius: 5px; text-align: center; height: 22px;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
            }}
        """)