"""
relation_selector.py
--------------------
A labelled QComboBox showing all 48 compact forms.
"""

from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox
from . theme import font_label, font_mono, ACCENT, TEXT_MAIN, TEXT_SUB
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from qrpc.table48 import get_instantiated
from qrpc.representation import Representation
# Import lazily to avoid circular import at module load
def _pretty(br):
    try:
        from .rules_table_panel import pretty_br
        return pretty_br(br)
    except Exception:
        return br

# Ordered list of all 48 compact forms
CATALOG = [
    "<X,PLUS,PLUS,PLUS,_,PLUS>",    "<X,PLUS,PLUS,PLUS,_,ZERO>",    "<X,PLUS,PLUS,PLUS,_,MINUS>",
    "<X,PLUS,PLUS,MINUS,_,PLUS>",   "<X,PLUS,PLUS,MINUS,_,ZERO>",   "<X,PLUS,PLUS,MINUS,_,MINUS>",
    "<X,MINUS,MINUS,PLUS,_,PLUS>",  "<X,MINUS,MINUS,PLUS,_,ZERO>",  "<X,MINUS,MINUS,PLUS,_,MINUS>",
    "<X,MINUS,MINUS,MINUS,_,PLUS>", "<X,MINUS,MINUS,MINUS,_,ZERO>", "<X,MINUS,MINUS,MINUS,_,MINUS>",
    "<X,PLUS,MINUS,PLUS,_,PLUS>",   "<X,PLUS,MINUS,PLUS,_,ZERO>",   "<X,PLUS,MINUS,PLUS,_,MINUS>",
    "<X,PLUS,MINUS,MINUS,_,PLUS>",  "<X,PLUS,MINUS,MINUS,_,ZERO>",  "<X,PLUS,MINUS,MINUS,_,MINUS>",
    "<X,MINUS,PLUS,PLUS,_,PLUS>",   "<X,MINUS,PLUS,PLUS,_,ZERO>",   "<X,MINUS,PLUS,PLUS,_,MINUS>",
    "<X,MINUS,PLUS,MINUS,_,PLUS>",  "<X,MINUS,PLUS,MINUS,_,ZERO>",  "<X,MINUS,PLUS,MINUS,_,MINUS>",
    "<X,PLUS,ZERO,PLUS,_,_>",       "<X,PLUS,ZERO,MINUS,_,_>",
    "<X,MINUS,ZERO,PLUS,_,_>",      "<X,MINUS,ZERO,MINUS,_,_>",
    "<X,ZERO,PLUS,_,P_TO_M,_>",    "<X,ZERO,PLUS,_,M_TO_P,_>",
    "<X,ZERO,MINUS,_,P_TO_M,_>",   "<X,ZERO,MINUS,_,M_TO_P,_>",
    "<PAR_SAME,_,_,PLUS,_,PLUS>",  "<PAR_SAME,_,_,PLUS,_,ZERO>",  "<PAR_SAME,_,_,PLUS,_,MINUS>",
    "<PAR_SAME,_,_,MINUS,_,PLUS>", "<PAR_SAME,_,_,MINUS,_,ZERO>", "<PAR_SAME,_,_,MINUS,_,MINUS>",
    "<PAR_OPP,_,_,PLUS,_,PLUS>",   "<PAR_OPP,_,_,PLUS,_,ZERO>",   "<PAR_OPP,_,_,PLUS,_,MINUS>",
    "<PAR_OPP,_,_,MINUS,_,PLUS>",  "<PAR_OPP,_,_,MINUS,_,ZERO>",  "<PAR_OPP,_,_,MINUS,_,MINUS>",
    "<OVL_SAME,_,_,_,_,PLUS>",     "<OVL_SAME,_,_,_,_,MINUS>",
    "<OVL_OPP,_,_,_,_,PLUS>",      "<OVL_OPP,_,_,_,_,MINUS>",
]


class RelationSelector(QWidget):
    """
    A labelled drop-down selector for all 48 basic QRPC relations.
    Items are shown with a 1-based index prefix for easy reference.
    """

    def __init__(self, label_text: str = "R", parent: QWidget = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label
        self._lbl = QLabel(label_text)
        self._lbl.setFont(font_label())
        self._lbl.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(self._lbl)

        # ComboBox row
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._combo = QComboBox()
        self._combo.setFont(font_mono())
        self._combo.setMinimumHeight(30)
        self._combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._combo.setMinimumContentsLength(28)
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #B0BEC5;
                border-radius: 4px;
                padding: 4px 8px;
                color: {TEXT_MAIN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                selection-background-color: {ACCENT};
                selection-color: white;
            }}
        """)
        for i, br in enumerate(CATALOG):
            self._combo.addItem(f"{i+1:2d}.  {_pretty(br)}")

        self._idx_label = QLabel(" (1)")
        self._idx_label.setFont(font_label())
        self._idx_label.setStyleSheet(f"color: {TEXT_SUB};")
        self._idx_label.setMinimumWidth(48)

        self._combo.currentIndexChanged.connect(
            lambda i: self._idx_label.setText(f" ({i+1})")
        )

        row.addWidget(self._combo, 1)
        row.addWidget(self._idx_label)
        layout.addLayout(row)

    # ── Public API ─────────────────────────────────────────────────────────────

    def selected_br(self) -> str:
        """Returns the canonical string of the selected relation."""
        return CATALOG[self._combo.currentIndex()]

    def selected_rep(self) -> 'Representation | None':
        """Returns the first instantiated representation of the selected relation.
        Used only by geometry_panel to display the Signature diagram."""
        tuples = get_instantiated(CATALOG[self._combo.currentIndex()])
        return tuples[0] if tuples else None

    def set_index(self, idx: int) -> None:
        """Sets the selection by 0-based index."""
        self._combo.setCurrentIndex(idx)

    def set_label(self, text: str) -> None:
        self._lbl.setText(text)

    def hide_index_label(self) -> None:
        """Hide the (n) index label — useful when the index adds no value."""
        self._idx_label.setVisible(False)
