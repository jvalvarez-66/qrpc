"""
help_dialog.py
--------------
Contextual help button that opens help.html in the system default browser,
scrolled to the relevant section anchor. No internet connection needed.
"""

from __future__ import annotations
import pathlib
from PyQt6.QtWidgets import QPushButton, QMessageBox
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtCore import QUrl

from .theme import ACCENT

# ── Section anchors (match IDs in help.html) ──────────────────────────────────
SEC_GEOMETRY      = "geometry"
SEC_CONVERSE      = "converse"
SEC_ASSOCIATIVITY = "associativity"
SEC_PC_CLOSURE    = "pc2verification"
SEC_TRIPLET_INSPECTOR = "tripletinspector"
SEC_RULES_TABLE   = "rulestable"
SEC_NEIGHBOURHOOD = "neighbourhood"
SEC_COMPOSITION_VIEWER = "compviewer"

_HELP_FILE = pathlib.Path(__file__).parent / "help.html"


def make_help_button(section: str = "") -> QPushButton:
    """Returns a small '?' button that opens help.html in the system browser."""
    btn = QPushButton("?")
    btn.setFixedSize(28, 28)
    btn.setToolTip("Open help (opens in your browser)")
    btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {ACCENT};
            color: white;
            border-radius: 14px;
            border: none;
        }}
        QPushButton:hover {{ background-color: #1A3270; }}
    """)
    btn.clicked.connect(lambda: _open_help(section))
    return btn


def _open_help(section: str = "") -> None:
    """Opens help.html (with optional #anchor) in the system default browser."""
    if not _HELP_FILE.exists():
        QMessageBox.warning(
            None, "Help not found",
            f"Help file not found:\n{_HELP_FILE}"
        )
        return

    url_str = _HELP_FILE.as_uri()
    if section:
        url_str += f"#{section}"

    url = QUrl(url_str)
    if not QDesktopServices.openUrl(url):
        QMessageBox.warning(
            None, "Cannot open browser",
            f"Could not open the help file in your browser.\n\nPath:\n{_HELP_FILE}"
        )
