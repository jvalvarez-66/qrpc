"""
associativity_panel.py
----------------------
Panel for the Associativity analysis.
Two sub-tabs: individual check and full 48³ combinatorial scan.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QAbstractItemView, QApplication, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qrpc.associativity import (
    check_associativity, check_full_associativity,
    AssociativityResultBR,
)
from . theme import (
    make_button, make_section_card, make_result_area,
    make_desc_label, set_status,
    font_label, font_label_bold, font_mono,
    ACCENT, BG, TEXT_SUB,
    BORDER, SUCCESS, ERROR_COL,
)
from . relation_selector import RelationSelector
from . rules_table_panel import pretty_br as _pbr
from . help_dialog import make_help_button, SEC_ASSOCIATIVITY


def _brs(s) -> list[str]:
    from .rules_table_panel import pretty_br as _pnc_local
    return [_pnc_local(br) for br in sorted(s)]

def _fmt(s) -> str:
    brs = _brs(s)
    return '∅' if not brs else '{ ' + ', '.join(brs) + ' }'


class _FullScanWorker(QThread):
    progress    = pyqtSignal(int, int, int)   # done, total, failing
    row_ready   = pyqtSignal(str, str, str, str, str, str, str, str)  # br12_p,br23_p,br34_p,only_l,only_r,br12_orig,br23_orig,br34_orig
    finished_ok = pyqtSignal(int)             # total failing

    def run(self):
        def cb(done, total, failing):
            self.progress.emit(done, total, failing)

        results = check_full_associativity(progress_callback=cb)
        for ar in results:
            only_l = ', '.join(_pbr(br) for br in sorted(ar.only_in_left))  or '∅'
            only_r = ', '.join(_pbr(br) for br in sorted(ar.only_in_right)) or '∅'
            self.row_ready.emit(_pbr(ar.br12), _pbr(ar.br23), _pbr(ar.br34), only_l, only_r, ar.br12, ar.br23, ar.br34)

        self.finished_ok.emit(len(results))


class AssociativityPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.setFont(font_label())
        tabs.addTab(self._build_single_tab(), "Single triplet")
        tabs.addTab(self._build_full_tab(),   "Full 48³ scan")
        root.addWidget(tabs)

    # ── Single-triplet tab ────────────────────────────────────────────────────

    def _build_single_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {BG};")
        root = QVBoxLayout(w)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        root.addWidget(make_desc_label(
            "Checks associativity for a single chain R<sub>12</sub> ∘ R<sub>23</sub> ∘ R<sub>34</sub>, "
            "evaluated both as (R<sub>12</sub> ∘ R<sub>23</sub>) ∘ R<sub>34</sub> "
            "and as R<sub>12</sub> ∘ (R<sub>23</sub> ∘ R<sub>34</sub>). "
            "Associativity holds if and only if both groupings yield the same set of relations.",
            width=9999
        ))

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)

        # ── Input card inside a scroll area so it never gets crushed ─────────
        from PyQt6.QtWidgets import QScrollArea
        inp_card, inp_layout = make_section_card("Input")
        inp_card.setMinimumHeight(260)
        self._sel12 = RelationSelector("R\u2081\u2082")
        self._sel23 = RelationSelector("R\u2082\u2083")
        self._sel34 = RelationSelector("R\u2083\u2084")
        self._sel23.set_index(2)
        self._sel34.set_index(5)
        for sel in (self._sel12, self._sel23, self._sel34):
            inp_layout.addWidget(sel)
            inp_layout.addSpacing(6)

        btn_row = QHBoxLayout()
        self._btn_single = make_button("Check associativity")
        self._btn_single.setToolTip("Test whether R12 ∘ (R23 ∘ R34) = (R12 ∘ R23) ∘ R34 for the selected triple")
        self._btn_single.clicked.connect(self._compute_single)
        btn_row.addWidget(self._btn_single)
        btn_row.addSpacing(8)
        btn_row.addWidget(make_help_button(SEC_ASSOCIATIVITY))
        btn_row.addStretch()
        inp_layout.addLayout(btn_row)

        inp_scroll = QScrollArea()
        inp_scroll.setWidgetResizable(True)
        inp_scroll.setFrameShape(inp_scroll.Shape.NoFrame)
        inp_scroll.setWidget(inp_card)
        inp_scroll.setMinimumHeight(260)
        splitter.addWidget(inp_scroll)

        # ── Result card ───────────────────────────────────────────────────────
        from PyQt6.QtWidgets import QSizePolicy
        res_card, res_layout = make_section_card("Result")

        # Status + Copy button on same row
        status_row = QHBoxLayout()
        self._status_single = QLabel(" ")
        self._status_single.setFont(font_label_bold())
        self._status_single.setStyleSheet(f"color: {TEXT_SUB};")
        status_row.addWidget(self._status_single, 1)
        self._btn_copy_single = make_button("Copy")
        self._btn_copy_single.setToolTip("Copy the associativity result to the clipboard")
        self._btn_copy_single.setEnabled(False)
        self._btn_copy_single.clicked.connect(self._copy_single_result)
        status_row.addWidget(self._btn_copy_single)
        res_layout.addLayout(status_row)

        self._result_single = make_result_area(8)
        self._result_single.setLineWrapMode(self._result_single.LineWrapMode.NoWrap)
        self._result_single.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._result_single.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._result_single.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        res_layout.addWidget(self._result_single, 1)

        # Set card size policy so it truly expands inside the splitter
        res_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(res_card)

        splitter.setChildrenCollapsible(False)
        splitter.setSizes([260, 500])
        splitter.setStretchFactor(0, 0)   # input: fixed
        splitter.setStretchFactor(1, 1)   # result: absorbs window growth
        root.addWidget(splitter, 1)
        return w

    def _copy_single_result(self):
        from PyQt6.QtWidgets import QApplication
        text = self._result_single.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _compute_single(self):
        br12 = self._sel12.selected_br()
        br23 = self._sel23.selected_br()
        br34 = self._sel34.selected_br()

        ar = check_associativity(br12, br23, br34)
        l_brs  = _brs(ar.left_result)
        r_brs  = _brs(ar.right_result)

        lines = [
            f"  R\u2081\u2082 = {_pbr(ar.br12)}",
            f"  R\u2082\u2083 = {_pbr(ar.br23)}",
            f"  R\u2083\u2084 = {_pbr(ar.br34)}",
            "",
            f"  Intermediate left  (R\u2081\u2082 \u2218 R\u2082\u2083): {_fmt(ar.intermediate_left)}",
            f"  Intermediate right (R\u2082\u2083 \u2218 R\u2083\u2084): {_fmt(ar.intermediate_right)}",
            "",
            f"  Left  result  (R\u2081\u2082 \u2218 R\u2082\u2083) \u2218 R\u2083\u2084  ({len(l_brs)} relations):",
        ]
        for br in l_brs:
            lines.append(f"    \u2022 {br}")
        lines += [
            "",
            f"  Right result   R\u2081\u2082 \u2218 (R\u2082\u2083 \u2218 R\u2083\u2084)  ({len(r_brs)} relations):",
        ]
        for br in r_brs:
            lines.append(f"    \u2022 {br}")

        if not ar.is_associative:
            only_l = _brs(ar.only_in_left)
            only_r = _brs(ar.only_in_right)
            common = sorted(set(l_brs) & set(r_brs))
            lines += ["", f"  ── Non-associative: {len(common)} shared, "
                         f"{len(only_l)} only in left, {len(only_r)} only in right ──"]
            if only_l:
                lines.append(f"  Only in (R\u2081\u2082 \u2218 R\u2082\u2083) \u2218 R\u2083\u2084  ({len(only_l)}):")
                for br in only_l:
                    lines.append(f"    \u2022 {br}")
            if only_r:
                lines.append(f"  Only in R\u2081\u2082 \u2218 (R\u2082\u2083 \u2218 R\u2083\u2084)  ({len(only_r)}):")
                for br in only_r:
                    lines.append(f"    \u2022 {br}")

        self._result_single.setPlainText("\n".join(lines))
        self._btn_copy_single.setEnabled(True)
        if ar.is_associative:
            set_status(self._status_single,
                       f"✓  Associative — both groupings yield {len(l_brs)} relation(s)", "ok")
        else:
            n_left  = len(_brs(ar.only_in_left))
            n_right = len(_brs(ar.only_in_right))
            set_status(self._status_single,
                       f"✗  NOT associative — left has {n_left} extra, "
                       f"right has {n_right} extra", "error")

    # ── Full-scan tab ─────────────────────────────────────────────────────────

    def _build_full_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {BG};")
        root = QVBoxLayout(w)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        root.addWidget(make_desc_label(
            "Runs the full 48\u00b3 = 110,592 combinatorial check. "
            "All non-associative triplets (if any) are listed in the table. "
            "Click a row to see the full breakdown in the detail panel below."
        ))

        # Button bar
        bar = QHBoxLayout()
        self._btn_full = make_button("Run full 48³ scan")
        self._btn_full.setToolTip("Scan all 48³ triples and report non-associative cases")
        self._btn_full.clicked.connect(self._run_full)
        self._btn_export = make_button("Export report")
        self._btn_export.setToolTip("Export the full scan results as a text report")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_report)
        self._progress = QProgressBar()
        self._progress.setRange(0, 110592)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(22)
        self._progress.setFixedWidth(260)
        self._progress.setVisible(False)
        self._lbl_summary = QLabel("  ")
        self._lbl_summary.setFont(font_label_bold())
        self._lbl_summary.setStyleSheet(f"color: {TEXT_SUB};")
        bar.addWidget(self._btn_full)
        bar.addWidget(self._btn_export)
        bar.addSpacing(12)
        bar.addWidget(self._progress)
        bar.addWidget(self._lbl_summary)
        bar.addStretch()
        from .help_dialog import make_help_button, SEC_ASSOCIATIVITY
        bar.addWidget(make_help_button(SEC_ASSOCIATIVITY))
        root.addLayout(bar)

        # Store results for export
        self._full_results: list = []

        # Splitter: table | detail
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)

        # Table
        cols = ["R₁₂", "R₂₃", "R₃₄", "Only in (R∘R)∘R", "Only in R∘(R∘R)"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setFont(font_mono())
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(f"""
            QTableWidget {{ border: 1px solid {BORDER}; }}
            QHeaderView::section {{
                background-color: {ACCENT}; color: white;
                font-weight: bold; padding: 4px;
                border: 1px solid {ACCENT};
            }}
        """)
        self._table.itemSelectionChanged.connect(self._show_detail)
        splitter.addWidget(self._table)

        # Detail area with Copy button
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(3)

        self._detail = make_result_area(8)
        self._detail.setPlainText("Select a row in the table to see the full breakdown.")
        detail_layout.addWidget(self._detail, 1)

        btn_copy_detail = make_button("Copy detail")
        btn_copy_detail.setToolTip("Copy the detail of this non-associative case to the clipboard")
        btn_copy_detail.setFixedHeight(32)
        btn_copy_detail.clicked.connect(
            lambda: QApplication.clipboard().setText(self._detail.toPlainText())
            if self._detail.toPlainText() != "Select a row in the table to see the full breakdown."
            else None
        )
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_copy_detail)
        detail_layout.addLayout(btn_row)

        splitter.addWidget(detail_widget)
        splitter.setSizes([320, 220])
        root.addWidget(splitter, 1)

        self._worker = None
        return w

    def _run_full(self):
        self._btn_full.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._table.setRowCount(0)
        self._full_results = []
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._lbl_summary.setText("  Running…")
        self._lbl_summary.setStyleSheet(f"color: {TEXT_SUB}; font-weight: bold;")

        self._worker = _FullScanWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.row_ready.connect(self._add_row)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.start()

    def _on_progress(self, done: int, total: int, failing: int):
        self._progress.setValue(done)
        self._lbl_summary.setText(f"  {done:,} / {total:,}  ({failing} non-associative so far)")

    def _add_row(self, br12, br23, br34, only_l, only_r, br12_orig="", br23_orig="", br34_orig=""):
        self._full_results.append((br12, br23, br34, only_l, only_r, br12_orig, br23_orig, br34_orig))
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, val in enumerate([br12, br23, br34, only_l, only_r]):
            item = QTableWidgetItem(val)
            item.setFont(font_mono())
            self._table.setItem(row, col, item)

    def _on_done(self, failing: int):
        self._progress.setVisible(False)
        self._btn_full.setEnabled(True)
        self._btn_export.setEnabled(failing > 0)
        total = 110592
        if failing == 0:
            self._lbl_summary.setText(f"  ✓  All {total:,} triplets are associative")
            self._lbl_summary.setStyleSheet(f"color: {SUCCESS}; font-weight: bold;")
        else:
            self._lbl_summary.setText(f"  ✗  {failing} non-associative triplet(s) found")
            self._lbl_summary.setStyleSheet(f"color: {ERROR_COL}; font-weight: bold;")

    def _export_report(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save associativity report", "qrpc_non_associative_triplets.txt",
            "Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        lines = [
            "QRPC Non-Associative Triplets Report",
            "=" * 52,
            f"Total non-associative triplets: {len(self._full_results)}",
            "",
        ]
        for idx, entry in enumerate(self._full_results, 1):
            br12, br23, br34, only_l, only_r = entry[0], entry[1], entry[2], entry[3], entry[4]
            lines += [
                f"Triplet {idx}",
                f"  R₁₂ = {br12}",
                f"  R₂₃ = {br23}",
                f"  R₃₄ = {br34}",
                f"  Only in (R∘R)∘R : {only_l}",
                f"  Only in R∘(R∘R) : {only_r}",
                "",
            ]
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export error", str(e))

    def _show_detail(self):
        row = self._table.currentRow()
        if row < 0 or row >= self._table.rowCount():
            return
        # Indices 5-7 hold the raw BR codes; 0-2 hold pretty-formatted strings for display
        if row < len(self._full_results) and len(self._full_results[row]) >= 8:
            br12 = self._full_results[row][5]
            br23 = self._full_results[row][6]
            br34 = self._full_results[row][7]
        else:
            # Fallback: read raw codes from the table (only works if table stores raw codes)
            br12 = self._table.item(row, 0).text() if self._table.item(row, 0) else ''
            br23 = self._table.item(row, 1).text() if self._table.item(row, 1) else ''
            br34 = self._table.item(row, 2).text() if self._table.item(row, 2) else ''
        if not (br12 and br23 and br34):
            return
        from qrpc.associativity import _get_br_comp, AssociativityResultBR
        try:
            comp = _get_br_comp()
            g_left  = comp.get((br12, br23), frozenset())
            g_right = comp.get((br23, br34), frozenset())
            left  = frozenset(br for g in g_left  for br in comp.get((g, br34), ()))
            right = frozenset(br for g in g_right for br in comp.get((br12, g), ()))
            ar_br = AssociativityResultBR(
                br12=br12, br23=br23, br34=br34,
                left_brs=left, right_brs=right,
                intermediate_left_brs=g_left,
                intermediate_right_brs=g_right,
            )
            self._detail.setPlainText(ar_br.detail_text())
        except Exception as e:
            ar = check_associativity(br12, br23, br34)
            self._detail.setPlainText(str(ar))
