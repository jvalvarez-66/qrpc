"""
composition_panel.py
--------------------
Top-level Composition tab: four nested sub-tabs
  1. Geometric viewer  (interactive 3-object composition canvas)
  2. Rules Table       (24×24 π-rule table)
  3. PC-2 verification (missing-triplet analysis + triplet inspector)
  4. Associativity
"""
from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from .theme import font_label_bold, ACCENT, STRIPE_BG

class CompositionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        tabs = QTabWidget()
        tabs.setFont(font_label_bold())
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background-color: {STRIPE_BG}; }}
            QTabBar::tab {{
                background-color: {STRIPE_BG}; color: #1A1A2E;
                padding: 7px 18px; font-size: 10pt; font-weight: bold;
                border: 1px solid #B0BEC5; border-bottom: none;
                border-radius: 4px 4px 0 0; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background-color: white; color: {ACCENT}; }}
            QTabBar::tab:hover:!selected {{ background-color: #D0D8E8; }}
        """)

        from .composition_viewer import CompositionViewerPanel
        from .zset_panel import ZSetPanel
        from .rules_table_panel import RulesTablePanel
        from .associativity_panel import AssociativityPanel

        self._zset_panel = ZSetPanel()
        tabs.addTab(CompositionViewerPanel(),                     "Geometric viewer")
        tabs.addTab(RulesTablePanel(),                            "Rules Table  (24×24)")
        tabs.addTab(self._zset_panel._build_pc_closure_unified(), "PC-2 verification")
        tabs.addTab(AssociativityPanel(),                         "Associativity")

        lay.addWidget(tabs, 1)
