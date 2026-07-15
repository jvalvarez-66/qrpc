"""
zset_panel.py
-------------
PC-2 verification panel: two sub-tabs
  1. Missing-triplet analysis  (omission analysis over the Z generating set)
  2. Triplet inspector         (direct path-consistency check for any triplet)
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QAbstractItemView,
    QComboBox, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qrpc.zset_verification import (
    TripletReport,
    verify_z_triplets,
    analyze_triplet_omission, explain_triplet_pc, omission_cache_status,
)
from .help_dialog import make_help_button, SEC_PC_CLOSURE, SEC_TRIPLET_INSPECTOR
from .rules_table_panel import pretty_br as _pbr
from .theme import (
    make_button, make_copy_button, make_result_area, make_section_card,
    font_label, font_label_bold, font_mono, font_small,
    ACCENT, ACCENT_DARK, BG, BORDER, BORDER_DARK, CONFIG_BAR, TEXT_SUB,
    SUCCESS, ERROR_COL, STRIPE_BG,
)


# ── Worker threads ────────────────────────────────────────────────────────────

class _SeedTripletsWorker(QThread):
    done = pyqtSignal(list)

    def run(self):
        self.done.emit(verify_z_triplets())


class _OmissionWorker(QThread):
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object)

    def __init__(self, seed_report: TripletReport):
        super().__init__()
        self._seed = seed_report

    def run(self):
        result = analyze_triplet_omission(
            self._seed,
            progress_cb=lambda d, t: self.progress.emit(d, t)
        )
        self.done.emit(result)


# ── Shared table builder ──────────────────────────────────────────────────────

def _make_table(cols: list[str], widths: list[int]) -> QTableWidget:
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setFont(font_mono())
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.setStyleSheet(f"""
        QTableWidget {{ border: 1px solid {BORDER}; }}
        QHeaderView::section {{
            background-color: {ACCENT}; color: white;
            font-weight: bold; padding: 4px;
            border: 1px solid {ACCENT};
        }}
    """)
    for i, w in enumerate(widths):
        t.setColumnWidth(i, w)
    return t


def _item(text: str, ok: bool = True) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setFont(font_mono())
    if not ok:
        item.setForeground(__import__('PyQt6.QtGui', fromlist=['QColor']).QColor(ERROR_COL))
    return item


# ── ZSet panel ────────────────────────────────────────────────────────────────

class ZSetPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cached_z_triplet_reports = None

    def _format_triplet_label(self, r: TripletReport) -> str:
        return f"[{r.entry_num}] {_pbr(r.br12)}  ∘  {_pbr(r.br23)}  →  {_pbr(r.br13)}"

    def _build_pc_closure_unified(self) -> QWidget:
        """
        PC-2 verification panel with two sub-tabs:
          1. Missing-triplet analysis
          2. Triplet inspector
        """
        outer = QTabWidget()
        outer.setFont(font_label())
        outer.addTab(self._build_omission_tab(),          "Missing-triplet analysis")
        outer.addTab(self._build_triplet_inspector_tab(), "Triplet inspector")
        return outer

    # ── Missing-triplet analysis tab ──────────────────────────────────────────

    def _build_omission_tab(self) -> QWidget:
        """
        Omission analysis: select a canonical Z triplet, run the analysis,
        inspect which triplets fail when that seed is removed from the basis.
        """
        from PyQt6.QtGui import QBrush, QColor

        w = QWidget()
        w.setStyleSheet(f"background-color: {BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # ── Description ───────────────────────────────────────────────────────
        desc = QLabel(
            f'<span style="color:{TEXT_SUB};">Select one of the canonical Z triplets '
            f'(the ~3,382 triplets obtained from the 288 Z entries) and simulate what '
            f'happens if that triplet is omitted from the verification basis. The analysis '
            f'reports which triplets stop satisfying the path-consistency conditions under '
            f'that omission. The <b>Set</b> column marks whether each failing triplet belongs '
            f'to Z (part of the canonical generating set) or to X\\Z (in the full composition '
            f'space but not in Z). Click any row to see its explanation.</span>'
        )
        desc.setWordWrap(True)
        desc.setFont(font_label())
        lay.addWidget(desc)

        # ── Top bar: combo + run button ───────────────────────────────────────
        top = QHBoxLayout()
        top.addWidget(QLabel("Omitted Z triplet:"))
        combo = QComboBox()
        combo.setEditable(True)
        combo.setMinimumWidth(520)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        top.addWidget(combo, 1)
        run_btn = make_button("Run omission analysis")
        run_btn.setToolTip("Scan the full composition table for missing result cases")
        top.addWidget(run_btn)
        top.addWidget(make_help_button(SEC_PC_CLOSURE))
        lay.addLayout(top)

        summary = QLabel("Choose a Z triplet and run the omission analysis.")
        summary.setFont(font_label_bold())
        summary.setStyleSheet(f"color: {TEXT_SUB};")
        lay.addWidget(summary)

        pairs_summary = QLabel("")
        pairs_summary.setWordWrap(True)
        pairs_summary.setStyleSheet(f"color: {TEXT_SUB};")
        lay.addWidget(pairs_summary)

        cache_note = QLabel("")
        cache_note.setWordWrap(True)
        cache_note.setStyleSheet(f"color: {TEXT_SUB};")
        cache_note.setFont(font_small())
        lay.addWidget(cache_note)

        # ── Unified table ─────────────────────────────────────────────────────
        unified_tab = _make_table(
            ["#", "R₁₂", "R₂₃", "r₁₃", "PC", "Set"],
            [46, 162, 162, 162, 40, 58]
        )
        lay.addWidget(unified_tab, 2)

        # ── Detail panel with Copy button ─────────────────────────────────────
        detail_frame = QWidget()
        detail_frame.setStyleSheet(f"background: {BG};")
        df_lay = QVBoxLayout(detail_frame)
        df_lay.setContentsMargins(0, 0, 0, 0)
        df_lay.setSpacing(0)
        hdr_w = QWidget()
        hdr_w.setStyleSheet(
            f"background: {CONFIG_BAR}; border-bottom: 1px solid {BORDER_DARK};"
        )
        hdr_lay = QHBoxLayout(hdr_w)
        hdr_lay.setContentsMargins(8, 2, 6, 2)
        hdr_lbl = QLabel("  Detail")
        hdr_lbl.setFont(font_label_bold())
        hdr_lbl.setStyleSheet(f"color: {ACCENT_DARK};")
        hdr_lay.addWidget(hdr_lbl, 1)
        btn_copy = make_copy_button()
        btn_copy.setToolTip("Copy the analysis results to the clipboard")
        btn_copy.setEnabled(False)
        btn_copy.setFixedWidth(62)
        hdr_lay.addWidget(btn_copy)
        df_lay.addWidget(hdr_w)
        detail = make_result_area(10)
        detail.setPlainText("Select a failing triplet to see its explanation.")
        detail.textChanged.connect(
            lambda: btn_copy.setEnabled(bool(detail.toPlainText()))
        )
        btn_copy.clicked.connect(
            lambda: QApplication.clipboard().setText(detail.toPlainText())
        )
        df_lay.addWidget(detail, 1)
        lay.addWidget(detail_frame, 1)

        # ── State ─────────────────────────────────────────────────────────────
        state = {'result': None}
        combo_reports = []
        combo.setEnabled(False)
        run_btn.setEnabled(False)
        summary.setText("Loading canonical Z triplets…")

        def _refresh_cache_note():
            st = omission_cache_status()
            if st["baseline_ready"]:
                cache_note.setText(
                    "Cache: baseline Z/X verifications already cached — "
                    "repeated analyses reuse them."
                )
            else:
                cache_note.setText(
                    "Cache: the first omission analysis builds the baseline "
                    "caches; later runs reuse them."
                )

        _refresh_cache_note()

        def _on_seed_reports_ready(seed_reports):
            self._cached_z_triplet_reports = seed_reports
            state.pop('seed_loader', None)   # release reference once done
            combo.clear()
            combo_reports.clear()
            for r in seed_reports:
                combo.addItem(self._format_triplet_label(r))
                combo_reports.append(r)
            combo.setEnabled(bool(combo_reports))
            run_btn.setEnabled(bool(combo_reports))
            combo.setCurrentIndex(0 if combo.count() else -1)
            summary.setText("Choose a Z triplet and run the omission analysis.")
            summary.setStyleSheet(f"color: {TEXT_SUB};")
            _refresh_cache_note()

        if self._cached_z_triplet_reports is not None:
            _on_seed_reports_ready(self._cached_z_triplet_reports)
        else:
            seed_loader = _SeedTripletsWorker()
            state['seed_loader'] = seed_loader   # keep reference alive until thread finishes
            seed_loader.done.connect(_on_seed_reports_ready)
            seed_loader.start()

        def _populate_unified(result):
            unified_tab.setRowCount(0)
            z_keys = {(r.br12, r.br23, r.br13) for r in result.z_failing}
            x_keys = {(r.br12, r.br23, r.br13) for r in result.x_failing}
            seen = {}
            for r in result.z_failing:
                seen[(r.br12, r.br23, r.br13)] = r
            for r in result.x_failing:
                key = (r.br12, r.br23, r.br13)
                if key not in seen:
                    seen[key] = r
            for key, r in seen.items():
                in_z = key in z_keys
                in_x = key in x_keys
                set_label = "Z" if in_z else "X∖Z"
                row = unified_tab.rowCount()
                unified_tab.insertRow(row)
                unified_tab.setItem(row, 0, _item(str(r.entry_num)))
                unified_tab.setItem(row, 1, _item(_pbr(r.br12)))
                unified_tab.setItem(row, 2, _item(_pbr(r.br23)))
                unified_tab.setItem(row, 3, _item(_pbr(r.br13)))
                unified_tab.setItem(row, 4,
                    _item('✓' if r.satisfies_pc else '✗', ok=r.satisfies_pc))
                set_item = _item(set_label)
                if in_z:
                    set_item.setForeground(QBrush(QColor(ACCENT)))
                    f = set_item.font()
                    f.setBold(True)
                    set_item.setFont(f)
                unified_tab.setItem(row, 5, set_item)
                for c in range(6):
                    unified_tab.item(row, c).setData(Qt.ItemDataRole.UserRole, r)

        def _render_explanation():
            row = unified_tab.currentRow()
            result = state['result']
            if row < 0 or result is None:
                detail.setPlainText("Select a failing triplet to see its explanation.")
                return
            it = unified_tab.item(row, 0)
            if it is None:
                return
            rep = it.data(Qt.ItemDataRole.UserRole)
            if rep is None:
                return

            from qrpc.zset_verification import _compose_singles_omitting, _converse_br

            origin_label = "not directly derived from the omitted seed orbit"
            for rule, a, b, c in result.omitted_triplets:
                if a == rep.br12 and b == rep.br23 and c == rep.br13:
                    origin_label = (
                        "the omitted canonical seed itself" if rule == 0
                        else f"an omitted π-image via rule {rule}"
                    )
                    break

            omitted_lines = "; ".join(
                f"rule {rule}: {_pbr(a)} ∘ {_pbr(b)} → {_pbr(c)}"
                for rule, a, b, c in result.omitted_triplets
            )

            # Build omitted_map from result (same structure as in zset_verification)
            omitted_map: dict = {}
            for _rule, a, b, c in result.omitted_triplets:
                omitted_map.setdefault((a, b), set()).add(c)

            # Evaluate conditions under the REDUCED basis
            br21 = _converse_br(rep.br12) or "?"
            br32 = _converse_br(rep.br23) or "?"
            c2_set_red = _compose_singles_omitting(rep.br13, br32, omitted_map) if br32 != "?" else set()
            c3_set_red = _compose_singles_omitting(br21, rep.br13, omitted_map) if br21 != "?" else set()
            c2_ok = rep.br12 in c2_set_red
            c3_ok = rep.br23 in c3_set_red

            def fmt_set(vals):
                if not vals:
                    return "∅"
                items = sorted(vals)
                chunks = []
                for i in range(0, len(items), 4):
                    chunks.append("    " + ",  ".join(_pbr(n) for n in items[i:i+4]))
                return "{\n" + "\n".join(chunks) + "\n  }"

            lines = [
                f"Selected failing triplet: {_pbr(rep.br12)}  ∘  {_pbr(rep.br23)}  →  {_pbr(rep.br13)}",
                f"Relation to omitted seed: {origin_label}",
                "",
                f"Omitted orbit: {omitted_lines}",
                "",
                "── Path-consistency analysis under the REDUCED basis ──────────────────",
                "",
                "── cond. 2: R₁₂ ∈ r₁₃ ∘ R₃₂  (with omitted triplets removed) ─────────",
                f"  R₃₂ = conv(R₂₃) = {_pbr(br32)}",
                f"  r₁₃ ∘ R₃₂ (reduced) = {fmt_set(c2_set_red)}",
                f"  R₁₂ = {_pbr(rep.br12)}  {'∈' if c2_ok else '∉'}  r₁₃ ∘ R₃₂",
                f"  → cond. 2: {'✓ satisfied' if c2_ok else '✗ NOT satisfied — R₁₂ was removed from the composition result'}",
                "",
                "── cond. 3: R₂₃ ∈ R₂₁ ∘ r₁₃  (with omitted triplets removed) ─────────",
                f"  R₂₁ = conv(R₁₂) = {_pbr(br21)}",
                f"  R₂₁ ∘ r₁₃ (reduced) = {fmt_set(c3_set_red)}",
                f"  R₂₃ = {_pbr(rep.br23)}  {'∈' if c3_ok else '∉'}  R₂₁ ∘ r₁₃",
                f"  → cond. 3: {'✓ satisfied' if c3_ok else '✗ NOT satisfied — R₂₃ was removed from the composition result'}",
                "",
                "── Conclusion ───────────────────────────────────────────────────────────",
                f"  Removing seed #{result.seed.entry_num} deletes its π-orbit from the verification basis.",
                f"  As a result, the composition result for one or more supporting pairs loses",
                f"  the basic relation needed to satisfy the path-consistency condition,",
                f"  causing this triplet to appear as failing in the reduced basis.",
            ]
            detail.setPlainText("\n".join(lines))

        def _on_done(result):
            state['result'] = result
            _populate_unified(result)
            n_z = len(result.z_failing)
            n_x = len(result.x_failing)
            seen = {(r.br12, r.br23, r.br13) for r in result.z_failing} | \
                   {(r.br12, r.br23, r.br13) for r in result.x_failing}
            summary.setText(
                f"Omitted seed #{result.seed.entry_num}: "
                f"{len(seen)} unique failing triplets "
                f"({n_z} in Z · {n_x} in X)"
            )
            summary.setStyleSheet(f"color: {SUCCESS}; font-weight: bold;")
            pairs_summary.setText(
                "Omitted orbit: " + "; ".join(
                    f"rule {rule}: {_pbr(a)} ∘ {_pbr(b)} → {_pbr(c)}"
                    for rule, a, b, c in result.omitted_triplets
                )
            )
            detail.setPlainText("Select a failing triplet to see its explanation.")
            run_btn.setEnabled(True)
            _refresh_cache_note()

        def _run():
            idx = combo.currentIndex()
            if idx < 0 or idx >= len(combo_reports):
                summary.setText("No canonical Z triplet is currently available.")
                return
            run_btn.setEnabled(False)
            summary.setText("Running omission analysis…")
            summary.setStyleSheet(f"color: {TEXT_SUB};")
            _refresh_cache_note()
            pairs_summary.setText("")
            unified_tab.setRowCount(0)
            detail.setPlainText("Working…")
            worker = _OmissionWorker(combo_reports[idx])
            state['worker'] = worker
            worker.done.connect(_on_done)
            worker.start()

        run_btn.clicked.connect(_run)
        unified_tab.itemSelectionChanged.connect(_render_explanation)
        return w

    # ── Triplet inspector tab ─────────────────────────────────────────────────

    def _build_triplet_inspector_tab(self) -> QWidget:
        """
        Direct-access path-consistency inspector.
        Row 1: R12 selector  |  R23 selector
        Row 2: r13 label + combo (populated from composition result)
        Row 3: Analyse button + help
        Bottom: path-consistency result area
        """
        from .relation_selector import RelationSelector
        from PyQt6.QtWidgets import QSizePolicy

        w = QWidget()
        w.setStyleSheet(f"background-color: {BG};")
        root = QVBoxLayout(w)
        root.setContentsMargins(22, 14, 22, 14)
        root.setSpacing(10)

        desc = QLabel(
            f'<span style="color:{TEXT_SUB};">'
            "Direct access to the path-consistency analysis for any specific triplet. "
            "Select R<sub>12</sub> and R<sub>23</sub>: the possible r<sub>13</sub> values "
            "are populated automatically in the third selector. "
            "Choose one r<sub>13</sub> and click <b>Analyse triplet</b> to see the full "
            "path-consistency verification."
            "</span>"
        )
        desc.setFont(font_label())
        desc.setWordWrap(True)
        root.addWidget(desc)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)

        # ── Input card ────────────────────────────────────────────────────────
        inp_card, inp_lay = make_section_card("Triplet selection")
        inp_lay.setSpacing(10)

        sel_row = QHBoxLayout()
        sel_row.setSpacing(16)
        self._ti_sel12 = RelationSelector("R\u2081\u2082")
        self._ti_sel23 = RelationSelector("R\u2082\u2083")
        self._ti_sel12.hide_index_label()
        self._ti_sel23.hide_index_label()
        self._ti_sel23.set_index(2)
        sel_row.addWidget(self._ti_sel12, 1)
        sel_row.addWidget(self._ti_sel23, 1)
        inp_lay.addLayout(sel_row)

        r13_lbl = QLabel("r\u2081\u2083 — select one result relation:")
        r13_lbl.setFont(font_label())
        r13_lbl.setStyleSheet(f"color: {TEXT_SUB};")
        inp_lay.addWidget(r13_lbl)

        self._ti_r13_combo = QComboBox()
        self._ti_r13_combo.setFont(font_mono())
        self._ti_r13_combo.setMinimumHeight(32)
        self._ti_r13_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._ti_r13_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #B0BEC5;
                border-radius: 4px;
                padding: 4px 8px;
                color: {TEXT_SUB};
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                selection-background-color: {ACCENT};
                selection-color: white;
            }}
        """)
        inp_lay.addWidget(self._ti_r13_combo)

        btn_row = QHBoxLayout()
        self._ti_btn = make_button("Analyse triplet")
        self._ti_btn.setToolTip("Run path-consistency analysis for the selected triplet")
        self._ti_btn.setEnabled(False)
        self._ti_btn.clicked.connect(self._ti_run_analysis)
        btn_row.addWidget(self._ti_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(make_help_button(SEC_TRIPLET_INSPECTOR))
        btn_row.addStretch()
        inp_lay.addLayout(btn_row)

        inp_card.setMinimumHeight(220)
        inp_card.setMaximumHeight(280)
        splitter.addWidget(inp_card)

        # ── Result card ───────────────────────────────────────────────────────
        res_card, res_lay = make_section_card("Path-consistency analysis")
        res_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        res_hdr = QHBoxLayout()
        self._ti_status = QLabel(" ")
        self._ti_status.setFont(font_label_bold())
        self._ti_status.setStyleSheet(f"color: {TEXT_SUB};")
        res_hdr.addWidget(self._ti_status, 1)
        self._ti_btn_copy = make_copy_button()
        self._ti_btn_copy.setToolTip("Copy analysis to clipboard")
        self._ti_btn_copy.setFixedWidth(62)
        self._ti_btn_copy.setEnabled(False)
        self._ti_btn_copy.clicked.connect(
            lambda: QApplication.clipboard().setText(self._ti_detail.toPlainText())
        )
        res_hdr.addWidget(self._ti_btn_copy)
        res_lay.addLayout(res_hdr)

        self._ti_detail = make_result_area(10)
        self._ti_detail.setPlainText(
            "Select R\u2081\u2082 and R\u2082\u2083, choose an r\u2081\u2083 "
            "from the selector above, then click \u2018Analyse triplet\u2019."
        )
        res_lay.addWidget(self._ti_detail, 1)

        splitter.addWidget(res_card)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([240, 9999])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._ti_sel12._combo.currentIndexChanged.connect(self._ti_update_composition)
        self._ti_sel23._combo.currentIndexChanged.connect(self._ti_update_composition)
        self._ti_r13_combo.currentIndexChanged.connect(
            lambda: self._ti_btn.setEnabled(self._ti_r13_combo.count() > 0)
        )
        self._ti_update_composition()
        return w

    def _ti_update_composition(self):
        """Recompute R12 ∘ R23 live and repopulate the r13 combo."""
        from qrpc.zset_verification import _compose_singles
        from qrpc.table48 import get_compact

        sel12 = self._ti_sel12.selected_rep()
        sel23 = self._ti_sel23.selected_rep()
        br12 = get_compact(sel12) if sel12 else None
        br23 = get_compact(sel23) if sel23 else None

        if not br12 or not br23:
            self._ti_r13_combo.clear()
            self._ti_btn.setEnabled(False)
            return

        r13_set = sorted(_compose_singles(br12, br23))
        if not r13_set:
            self._ti_r13_combo.clear()
            self._ti_btn.setEnabled(False)
            return

        self._ti_r13_combo.blockSignals(True)
        self._ti_r13_combo.clear()
        for br in r13_set:
            self._ti_r13_combo.addItem(_pbr(br), userData=br)
        self._ti_r13_combo.blockSignals(False)
        self._ti_btn.setEnabled(True)

    def _ti_run_analysis(self):
        """Run and display the full path-consistency analysis for the selected triplet."""
        from qrpc.zset_verification import _compose_singles, _converse_br
        from qrpc.table48 import get_compact

        sel12 = self._ti_sel12.selected_rep()
        sel23 = self._ti_sel23.selected_rep()
        if not sel12 or not sel23:
            return
        br12 = get_compact(sel12)
        br23 = get_compact(sel23)
        br13 = self._ti_r13_combo.currentData()
        if not br12 or not br23 or not br13:
            return

        br21 = _converse_br(br12) or "?"
        br32 = _converse_br(br23) or "?"
        c2_set = _compose_singles(br13, br32) if br32 != "?" else set()
        c3_set = _compose_singles(br21, br13) if br21 != "?" else set()
        c2_ok  = br12 in c2_set
        c3_ok  = br23 in c3_set

        def fmt_set(s):
            if not s:
                return "\u2205"
            items = sorted(s)
            chunks = []
            for i in range(0, len(items), 4):
                chunks.append("    " + ",  ".join(_pbr(n) for n in items[i:i+4]))
            return "{\n" + "\n".join(chunks) + "\n  }"

        lines = [
            f"  R\u2081\u2082 = {_pbr(br12)}",
            f"  R\u2082\u2083 = {_pbr(br23)}",
            f"  r\u2081\u2083 = {_pbr(br13)}",
            "",
            "\u2500\u2500 cond. 2: R\u2081\u2082 \u2208 r\u2081\u2083 \u2218 R\u2083\u2082 " + "\u2500"*30,
            f"  R\u2083\u2082 = conv(R\u2082\u2083) = {_pbr(br32)}",
            f"  r\u2081\u2083 \u2218 R\u2083\u2082 = {fmt_set(c2_set)}",
            f"  R\u2081\u2082 = {_pbr(br12)}  {'∈' if c2_ok else '∉'}  r\u2081\u2083 \u2218 R\u2083\u2082",
            f"  \u2192 cond. 2: {chr(10003)+' satisfied' if c2_ok else chr(10007)+' NOT satisfied'}",
            "",
            "\u2500\u2500 cond. 3: R\u2082\u2083 \u2208 R\u2082\u2081 \u2218 r\u2081\u2083 " + "\u2500"*30,
            f"  R\u2082\u2081 = conv(R\u2081\u2082) = {_pbr(br21)}",
            f"  R\u2082\u2081 \u2218 r\u2081\u2083 = {fmt_set(c3_set)}",
            f"  R\u2082\u2083 = {_pbr(br23)}  {'∈' if c3_ok else '∉'}  R\u2082\u2081 \u2218 r\u2081\u2083",
            f"  \u2192 cond. 3: {chr(10003)+' satisfied' if c3_ok else chr(10007)+' NOT satisfied'}",
        ]
        self._ti_detail.setPlainText("\n".join(lines))
        self._ti_btn_copy.setEnabled(True)

        if c2_ok and c3_ok:
            self._ti_status.setText(
                f"  \u2713  {_pbr(br12)} \u2218 {_pbr(br23)} \u2192 {_pbr(br13)}"
                f"  \u2014  cond. 2 \u2713  cond. 3 \u2713  (PC-consistent)"
            )
            self._ti_status.setStyleSheet(f"color: {SUCCESS}; font-weight: bold;")
        else:
            parts = (["cond. 2 \u2717"] if not c2_ok else []) + (["cond. 3 \u2717"] if not c3_ok else [])
            self._ti_status.setText(
                f"  \u2717  {_pbr(br12)} \u2218 {_pbr(br23)} \u2192 {_pbr(br13)}"
                f"  \u2014  {',  '.join(parts)}  (NOT PC-consistent)"
            )
            self._ti_status.setStyleSheet(f"color: {ERROR_COL}; font-weight: bold;")
