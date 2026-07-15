"""
main_window.py
--------------
Main application window for QRPC PyQt6.

Top-level tabs:
  1. Relations   — 2-object canvas: relation identification
  2. Converse    — 2-object canvas: converse operation (synced with Relations)
  3. Composition — geometric viewer + closure/coverage + rules table + associativity
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QFrame,
)
from PyQt6.QtGui import QFont

from . theme import (
    HEADER_BAR, HEADER_ACC, ACCENT, STRIPE_BG,
    font_label_bold, font_small,
)
from . geometry_panel    import _SharedGeomState, RelationsPanel, ConversePanel
from . help_dialog       import make_help_button
from . neighbourhood_panel import NeighbourhoodPanel
from . composition_panel import CompositionPanel


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "QRPC \u2013 Qualitative Rectilinear Projection Calculus"
        )
        self.setMinimumSize(960, 700)
        self.resize(1280, 820)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self._tabs = QTabWidget()
        self._tabs.setFont(font_label_bold())
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {STRIPE_BG};
            }}
            QTabBar::tab {{
                background-color: {STRIPE_BG};
                color: #1A1A2E;
                padding: 8px 20px;
                font-size: 11pt;
                font-weight: bold;
                border: 1px solid #B0BEC5;
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: white;
                color: {ACCENT};
                border-bottom: 2px solid white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #D0D8E8;
            }}
        """)

        # Shared state: both Relations and Converse see the same two objects.
        state = _SharedGeomState()

        self._tabs.addTab(RelationsPanel(state), "Relations")
        self._tabs.addTab(NeighbourhoodPanel(),   "Neighbourhood")
        self._tabs.addTab(ConversePanel(state),  "Converse")
        self._tabs.addTab(CompositionPanel(),     "Composition")

        layout.addWidget(self._tabs, 1)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(64)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {HEADER_BAR};
                border-left: 5px solid {HEADER_ACC};
            }}
        """)
        inner = QHBoxLayout(frame)
        inner.setContentsMargins(18, 0, 18, 0)
        inner.setSpacing(0)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title = QLabel("QRPC \u2013 Qualitative Rectilinear Projection Calculus")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")

        sub = QLabel("Interactive demonstration of the QRPC spatial reasoning algebra")
        sub.setFont(font_small())
        sub.setStyleSheet("color: #90B8DC;")

        text_col.addWidget(title)
        text_col.addWidget(sub)
        inner.addLayout(text_col)
        inner.addStretch()
        help_btn = make_help_button()  # opens help.html at the top
        help_btn.setText("Overview")
        help_btn.setFixedSize(80, 28)
        help_btn.setToolTip("Open the application overview and introduction")
        inner.addWidget(help_btn)
        return frame
