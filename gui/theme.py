"""
theme.py
--------
Centralised design tokens for the QRPC PyQt6 GUI.

Mirrors QRPCApp colour/font constants and provides factory functions for
common widgets (buttons, section cards, result areas).
"""

from __future__ import annotations
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton, QLabel, QTextEdit, QFrame,
    QVBoxLayout,
)

# ── Colours (hex strings for QColor / stylesheet use) ────────────────────────

BG           = "#F8F9FA"
PANEL_BG     = "#FFFFFF"
STRIPE_BG    = "#EEF2F7"
ACCENT       = "#2C4F9E"
ACCENT_DARK  = "#1A3270"
ACCENT_LIGHT = "#C8D8F8"
SUCCESS      = "#0D6832"
SUCCESS_BG   = "#C3EDCE"
ERROR_COL    = "#8B0000"
ERROR_BG     = "#FAD4D4"
WARN_COL     = "#7B4C00"
WARN_BG      = "#FFF0C0"
BORDER       = "#B0BEC5"
BORDER_DARK  = "#607D8B"
TEXT_MAIN    = "#1A1A2E"
TEXT_SUB     = "#4A5568"
RESULT_BG    = "#F7F9FC"
HEADER_BAR   = "#0A1628"
HEADER_ACC   = "#2C4F9E"
CONFIG_BAR   = "#DDE4EE"

# ── Fonts ─────────────────────────────────────────────────────────────────────

def font_label() -> QFont:
    return QFont("Arial", 11)

def font_label_bold() -> QFont:
    return QFont("Arial", 11, QFont.Weight.Bold)

def font_mono() -> QFont:
    f = QFont("Courier New", 10)
    return f

def font_small() -> QFont:
    return QFont("Arial", 9)

# ── Button factory ────────────────────────────────────────────────────────────

_BTN_SS = """
QPushButton {{
    background-color: {accent};
    color: white;
    border: 2px solid {dark};
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
    font-size: 11pt;
}}
QPushButton:hover {{
    background-color: {dark};
}}
QPushButton:pressed {{
    background-color: #0F1F50;
}}
QPushButton:disabled {{
    background-color: #5A6A7C;
    color: #DDE4EE;
    border-color: #3D4F60;
}}
""".format(accent=ACCENT, dark=ACCENT_DARK)


def make_button(text: str) -> QPushButton:
    """Creates a styled QRPC action button."""
    btn = QPushButton(text)
    btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
    btn.setStyleSheet(_BTN_SS)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    return btn


_BTN_COPY_SS = """
QPushButton {{
    background-color: {accent};
    color: white;
    border: 1px solid {dark};
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 9pt;
}}
QPushButton:hover {{ background-color: {dark}; }}
QPushButton:pressed {{ background-color: #0F1F50; }}
QPushButton:disabled {{
    background-color: #5A6A7C;
    color: #DDE4EE;
    border-color: #3D4F60;
}}
""".format(accent=ACCENT, dark=ACCENT_DARK)


def make_copy_button(text: str = "Copy") -> QPushButton:
    """Creates a compact Copy button for use inside panel headers."""
    from PyQt6.QtWidgets import QPushButton as _QB
    btn = _QB(text)
    btn.setFont(QFont("Arial", 9, QFont.Weight.Bold))
    btn.setStyleSheet(_BTN_COPY_SS)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn.setFixedHeight(22)
    return btn


# ── Section card ──────────────────────────────────────────────────────────────

def make_section_card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    """
    Returns a white rounded card with an optional blue title label.
    Returns (frame, layout) so caller can add widgets to the layout.
    """
    frame = QFrame()
    frame.setObjectName("sectionCard")
    frame.setStyleSheet(f"""
        QFrame#sectionCard {{
            background-color: {PANEL_BG};
            border: 1px solid {BORDER};
            border-radius: 6px;
        }}
    """)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(8)

    if title:
        lbl = QLabel(title)
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(lbl)

    return frame, layout


# ── Result area ───────────────────────────────────────────────────────────────

def make_result_area(rows: int = 8) -> QTextEdit:
    """Creates a read-only monospaced text area for displaying results."""
    ta = QTextEdit()
    ta.setReadOnly(True)
    ta.setFont(font_mono())
    ta.setStyleSheet(f"""
        QTextEdit {{
            background-color: {RESULT_BG};
            color: {TEXT_MAIN};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 8px;
        }}
    """)
    ta.setMinimumHeight(rows * 18)
    return ta


# ── Status label helpers ──────────────────────────────────────────────────────

def set_status(label: QLabel, text: str, kind: str = "neutral") -> None:
    """Sets label text and colour. kind: 'ok' | 'error' | 'warn' | 'neutral'"""
    colours = {
        "ok":      SUCCESS,
        "error":   ERROR_COL,
        "warn":    WARN_COL,
        "neutral": TEXT_SUB,
    }
    label.setText(text)
    label.setStyleSheet(f"color: {colours.get(kind, TEXT_SUB)}; font-weight: bold;")


# ── Description label ─────────────────────────────────────────────────────────

def make_desc_label(html_text: str, width: int = 620) -> QLabel:
    lbl = QLabel(f'<span style="color:{TEXT_SUB};">{html_text}</span>')
    lbl.setFont(font_label())
    lbl.setWordWrap(True)
    lbl.setMaximumWidth(width)
    return lbl
