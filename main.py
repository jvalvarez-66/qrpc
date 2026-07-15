"""
main.py
-------
Entry point for the QRPC PyQt6 application.

Usage:
    python main.py
    # or from the qrpc_python directory:
    python -m qrpc_python.main
"""

import sys
import os

# Ensure the package root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("QRPC")
    app.setOrganizationName("QRPC Research")

    # Use the fusion style for a clean cross-platform look
    app.setStyle("Fusion")

    # Force tooltip colours globally via QPalette — works in PyQt6/Fusion
    # regardless of individual widget stylesheets
    from PyQt6.QtGui import QPalette, QColor
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFDE7"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1A1A2E"))
    app.setPalette(palette)
    # Also set via stylesheet as belt-and-braces
    app.setStyleSheet(
        "QToolTip { background-color: #FFFDE7; color: #1A1A2E; "
        "border: 1px solid #B0BEC5; padding: 4px; "
        "font-family: Courier New; font-size: 9pt; }")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
