"""
rules_table_panel.py
--------------------
Displays the 24x24 composition rules table generated dynamically from
the Z composition set.  Each cell shows which rule (0-7) must be applied
to compute the composition (row_class o col_class).  A reference table
above maps each of the 24 class indices to the catalogue NCs it represents.
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea, QApplication,
)
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QColor, QFont

from qrpc.composition import get_rules_table, explain_basic_composition
from .theme import (
    font_label, font_label_bold, font_mono, font_small, make_button,
    ACCENT, ACCENT_DARK, BG, BORDER, BORDER_DARK, TEXT_MAIN, TEXT_SUB, STRIPE_BG,
)
from .relation_selector import CATALOG
from .help_dialog import make_help_button, SEC_RULES_TABLE

# ── Rule colours ──────────────────────────────────────────────────────────────
RULE_FG = ["#0D5C2A","#1A4D8C","#8B2600","#5C0080",
           "#7B4C00","#006B6B","#8B0045","#004D40"]
RULE_BG = ["#C8F0D8","#C8DCFF","#FFD8C8","#EBC8FF",
           "#FFEECC","#C8F0EE","#FFCCE0","#C8EDE8"]
RULE_LABELS = [
    "Rule 0 — direct Z lookup",
    "Rule 1 — α(R₁₂), R₂₃",
    "Rule 2 — β(R₁₂), α(R₂₃)",
    "Rule 3 — R₁₂, β(R₂₃)",
    "Rule 4 — γ(R₁₂), α(R₂₃)",
    "Rule 5 — β(R₁₂), γ(R₂₃)",
    "Rule 6 — α(R₁₂), β(R₂₃)",
    "Rule 7 — γ(R₁₂), γ(R₂₃)",
]

# ── HTML delegate for cells and header ───────────────────────────────────────







# ── Viewport event filter for custom tooltip styling ─────────────────────────

class _TableTooltipFilter(QObject):
    """Intercepts ToolTip events on a QTableWidget viewport and shows
    the tooltip with explicit light styling, bypassing widget stylesheet
    inheritance issues in PyQt6."""

    def __init__(self, table):
        super().__init__(table)
        self._table = table

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QToolTip
        if ev.type() == QEvent.Type.ToolTip:
            pos = ev.pos()
            row = self._table.rowAt(pos.y())
            col = self._table.columnAt(pos.x())
            tip = ""
            # Check cellWidget first (rows 0 and col 0 use QLabel widgets)
            w = self._table.cellWidget(row, col)
            if w is not None:
                tip = w.toolTip()
            # Fall back to item tooltip
            if not tip:
                item = self._table.item(row, col)
                if item:
                    tip = item.toolTip()
            if tip:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtGui import QPalette, QColor
                # Force light tooltip palette immediately before showing
                app = QApplication.instance()
                app.setStyleSheet(
                    "QToolTip { background-color: #FFFDE7; color: #1A1A2E; "
                    "border: 1px solid #B0BEC5; padding: 4px; "
                    "font-family: Courier New; font-size: 9pt; }")
                QToolTip.showText(ev.globalPos(), tip)
            else:
                QToolTip.hideText()
            return True
        return False


# Row-class -> catalogue indices (1-based)
ROW_TO_CATALOG = [
    [ 1, 2, 3],[ 4, 5, 6],[13,14,15],[16,17,18],
    [19,20,21],[22,23,24],[ 7, 8, 9],[10,11,12],
    [25],[26],[29],[30],[27],[28],[31],[32],
    [33,34,35],[36,37,38],[45],[46],
    [39,40,41],[42,43,44],[47],[48],
]
SIZE = 24

# ── Instantiated representation display (token replacement) ──────────────────
# Replaces code tokens with the symbols used in the paper, keeping <...> structure.
# e.g. <X,PLUS,PLUS,PLUS,_,PLUS>  ->  <X,+,+,+,_,+>  (instantiated repr.)
#      <X,ZERO,PLUS,_,P_TO_M,_>   ->  <X,0,+,_,+|-,_>
#      <PAR_SAME,_,_,PLUS,_,PLUS> ->  <↑↑,_,_,+,_,+>

def pretty_br(br: str) -> str:
    """
    Converts a BR code string (instantiated representation) to readable
    notation by replacing tokens with paper symbols.
    Keeps the <...> structure so the result stays unambiguous.
    e.g. <X,PLUS,PLUS,PLUS,_,PLUS>  ->  <X,+,+,+,_,+>
    """
    s = br
    s = s.replace('PAR_SAME', '↑↑')
    s = s.replace('PAR_OPP',  '↑↓')
    s = s.replace('OVL_SAME', '↑')
    s = s.replace('OVL_OPP',  '↕')
    s = s.replace('P_TO_M',   '+|-')
    s = s.replace('M_TO_P',   '-|+')
    s = s.replace('P_TO_0',   '+|0')
    s = s.replace('M_TO_0',   '-|0')
    s = s.replace('_0_TO_P',  '0|+')
    s = s.replace('_0_TO_M',  '0|-')
    s = s.replace('_0_TO_0',  '0|0')
    s = s.replace('P_OR_M',   '(+,-)')
    s = s.replace('PLUS',     '+')
    s = s.replace('MINUS',    '-')
    s = s.replace('ZERO',     '0')
    return s
def _compact_br(br: str) -> str:
    """
    Renders the compact form of a BR as HTML using <sup>/<sub> tags
    for superscripts/subscripts (paper notation).
    Wildcard OFB position shown as <sub>*</sub>.
    e.g. <X,+,+,+,_,+>  ->  X<sup>+</sup><sup>+</sup><sub>+</sub><sub>+</sub>
    """
    def sup(v):
        if v == '_': return ''
        return {'PLUS':'<sup>+</sup>','MINUS':'<sup>-</sup>','ZERO':'<sup>0</sup>','*':'<sup>*</sup>'}.get(v,v)
    def sub(v):
        if v == '_': return ''
        return {'PLUS':'<sub>+</sub>','MINUS':'<sub>-</sub>','ZERO':'<sub>0</sub>','*':'<sub>*</sub>'}.get(v,v)
    def dlr(v):
        if v == '_': return ''
        return {
            'P_TO_M':'<sub>+|-</sub>','M_TO_P':'<sub>-|+</sub>',
            'P_TO_0':'<sub>+|0</sub>','M_TO_0':'<sub>-|0</sub>',
            '_0_TO_P':'<sub>0|+</sub>','_0_TO_M':'<sub>0|-</sub>',
            '_0_TO_0':'<sub>0|0</sub>','P_OR_M':'<sub>(+,-)</sub>','*':'<sub>*</sub>',
        }.get(v,v)
    inner = br.strip('<>').split(',')
    fam = inner[0].strip()
    if fam == 'X':
        c1=inner[1].strip(); c2=inner[2].strip()
        lr=inner[3].strip(); dv=inner[4].strip(); ofb=inner[5].strip()
        return 'X'+sup(c1)+sup(c2)+sub(lr)+dlr(dv)+sub(ofb)
    elif fam == 'PAR_SAME':
        return '↑↑'+sub(inner[3].strip())+sub(inner[5].strip())
    elif fam == 'PAR_OPP':
        return '↑↓'+sub(inner[3].strip())+sub(inner[5].strip())
    elif fam == 'OVL_SAME':
        return '↑'+sub(inner[5].strip())
    elif fam == 'OVL_OPP':
        return '↕'+sub(inner[5].strip())
    return br


def _compact_br_plain(br: str) -> str:
    """Plain-text compact form (Unicode superscripts/subscripts) — used for tooltips."""
    _SUP = {'PLUS':'⁺','MINUS':'⁻','ZERO':'⁰','_':'','*':'*'}
    _SUB = {'PLUS':'₊','MINUS':'₋','ZERO':'₀','_':'','*':'*'}
    _DLR = {
        'P_TO_M':'₊|₋','M_TO_P':'₋|₊','P_TO_0':'₊|₀','M_TO_0':'₋|₀',
        '_0_TO_P':'₀|₊','_0_TO_M':'₀|₋','_0_TO_0':'₀|₀','_':'','*':'*','P_OR_M':'(₊,₋)',
    }
    inner = br.strip('<>').split(',')
    fam = inner[0].strip()
    if fam == 'X':
        c1=inner[1].strip(); c2=inner[2].strip()
        lr=inner[3].strip(); dv=inner[4].strip(); ofb=inner[5].strip()
        return 'X'+_SUP.get(c1,c1)+_SUP.get(c2,c2)+_SUB.get(lr,lr)+_DLR.get(dv,dv)+_SUB.get(ofb,ofb)
    elif fam == 'PAR_SAME': return '↑↑'+_SUB.get(inner[3].strip(),'')+_SUB.get(inner[5].strip(),'')
    elif fam == 'PAR_OPP':  return '↑↓'+_SUB.get(inner[3].strip(),'')+_SUB.get(inner[5].strip(),'')
    elif fam == 'OVL_SAME': return '↑'+_SUB.get(inner[5].strip(),'')
    elif fam == 'OVL_OPP':  return '↕'+_SUB.get(inner[5].strip(),'')
    return br


def _canon(cats: list[int]) -> str:
    """HTML compact form for a row class.
    Singleton: exact BR compact form. Group of 3 (differ only in OFB): substitutes <sub>*</sub>."""
    if len(cats) == 1:
        return _compact_br(CATALOG[cats[0]-1])
    base = CATALOG[cats[0]-1]
    raw = base[:base.rfind(',')+1] + '*>'
    return _compact_br(raw)


def _canon_plain(cats: list[int]) -> str:
    """Plain-text compact form for tooltips."""
    if len(cats) == 1:
        return _compact_br_plain(CATALOG[cats[0]-1])
    base = CATALOG[cats[0]-1]
    raw = base[:base.rfind(',')+1] + '*>'
    return _compact_br_plain(raw)


# ── Rule application metadata ─────────────────────────────────────────────────

# (rule, r12_label, r23_label, output_rot_label, description)
# Note: out_rot_label is the rotation applied to R₁₃ to recover the original frame.
# Since α, β, γ are π-rotations (involutions), applying them once IS their own inverse.
_RULE_FORMULAS = [
    (0, "R₁₂",       "R₂₃",       "none",  "Direct Z lookup — no rotation needed"),
    (1, "α(R₁₂)",    "R₂₃",       "α",    "Rotate R₁₂ by α and look up in Z; then apply α to R₁₃"),
    (2, "β(R₁₂)",    "α(R₂₃)",    "none",  "Rotate R₁₂ by β and R₂₃ by α; result is final (self-inverse)"),
    (3, "R₁₂",       "β(R₂₃)",    "β",    "Rotate R₂₃ by β and look up in Z; then apply β to R₁₃"),
    (4, "γ(R₁₂)",    "α(R₂₃)",    "α",    "Rotate R₁₂ by γ and R₂₃ by α; then apply α to R₁₃"),
    (5, "β(R₁₂)",    "γ(R₂₃)",    "β",    "Rotate R₁₂ by β and R₂₃ by γ; then apply β to R₁₃"),
    (6, "α(R₁₂)",    "β(R₂₃)",    "γ",    "Rotate R₁₂ by α and R₂₃ by β; then apply γ to R₁₃"),
    (7, "γ(R₁₂)",    "γ(R₂₃)",    "γ",    "Rotate both by γ and look up in Z; then apply γ to R₁₃"),
]


def _show_rule_popup(row_class: int, col_class: int, rule: int) -> None:
    """Shows a detailed popup for a cell in the 24x24 rules table."""
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    )
    from PyQt6.QtCore import Qt, QObject
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QComboBox, QPushButton

    rc_cats = ROW_TO_CATALOG[row_class]
    cc_cats = ROW_TO_CATALOG[col_class]

    # If the class has multiple NCs, the user can choose which representative to show
    def pick_nc(cats, label):
        if len(cats) == 1:
            return CATALOG[cats[0]-1], None
        # Build a mini combo selector
        combo = QComboBox()
        for c in cats:
            combo.addItem(f"{c}:  {pretty_br(CATALOG[c-1])}")
        combo.setFont(QFont("Courier New", 9))
        return CATALOG[cats[0]-1], combo

    nc_r12, combo_r12 = pick_nc(rc_cats, "R₁₂")
    nc_r23, combo_r23 = pick_nc(cc_cats, "R₂₃")

    trace = explain_basic_composition(nc_r12, nc_r23)
    nc_r12_z = trace["z_r12_br"]
    nc_r23_z = trace["z_r23_br"]
    r13_z_ncs = trace["z_result_ncs"]
    r13_final = trace["final_result_ncs"]

    _, r12_lbl, r23_lbl, out_lbl, desc = _RULE_FORMULAS[rule]

    # ── Dialog ────────────────────────────────────────────────────────────────
    dlg = QDialog()
    dlg.setWindowTitle(
        f"Rule {rule}  —  Class {row_class+1} ∘ Class {col_class+1}"
    )
    dlg.resize(760, 560)
    dlg.setMinimumSize(680, 460)
    outer = QVBoxLayout(dlg)
    outer.setSpacing(8)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setSpacing(10)

    def sec(txt):
        l = QLabel(txt); l.setFont(QFont("Arial",11,QFont.Weight.Bold))
        l.setStyleSheet(f"color:{ACCENT}; padding:2px 0;"); return l

    def card(title, lines):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:white;border:1px solid {BORDER};"
                        "border-radius:4px;}")
        fl = QVBoxLayout(f); fl.setSpacing(3); fl.setContentsMargins(6, 6, 6, 6)
        t = QLabel(f"<b>{title}</b>"); t.setFont(QFont("Arial",9)); fl.addWidget(t)
        for txt, mono in lines:
            l = QLabel(txt)
            l.setFont(QFont("Courier New",10) if mono else QFont("Arial",9))
            l.setStyleSheet(f"color:{TEXT_MAIN if mono else TEXT_SUB};")
            l.setWordWrap(True); fl.addWidget(l)
        return f

    # ── 1. Selected composition ───────────────────────────────────────────────
    lay.addWidget(sec("1 · Selected composition"))
    row1 = QHBoxLayout(); row1.setSpacing(8)

    def class_card(title, cats, combo, nc_repr):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:white;border:1px solid {BORDER};"
                        "border-radius:4px;}")
        fl = QVBoxLayout(f); fl.setSpacing(3); fl.setContentsMargins(6, 6, 6, 6)
        fl.addWidget(QLabel(f"<b>{title}</b>"))
        if combo is not None:
            note = QLabel("This class contains multiple basic relations — select one to inspect:")
            note.setFont(QFont("Arial", 8))
            note.setStyleSheet(f"color:{TEXT_SUB};")
            fl.addWidget(note)
            fl.addWidget(combo)
        else:
            lbl = QLabel(pretty_br(nc_repr))
            lbl.setFont(QFont("Courier New", 10))
            lbl.setStyleSheet(f"color:{TEXT_MAIN};")
            fl.addWidget(lbl)
        idxs = f"Catalogue: {', '.join(str(c) for c in cats)}"
        l2 = QLabel(idxs); l2.setFont(QFont("Arial", 8))
        l2.setStyleSheet(f"color:{TEXT_SUB};"); fl.addWidget(l2)
        return f

    row1.addWidget(class_card(f"R₁₂ — row class {row_class+1}", rc_cats, combo_r12, nc_r12))
    row1.addWidget(class_card(f"R₂₃ — col class {col_class+1}", cc_cats, combo_r23, nc_r23))
    lay.addLayout(row1)

    # ── 2. Rule applied ───────────────────────────────────────────────────────
    lay.addWidget(sec(f"2 · Rule {rule} applied"))
    rule_f = QFrame()
    rule_f.setStyleSheet(
        f"QFrame{{background:{RULE_BG[rule]};border:1px solid {RULE_FG[rule]};"
        "border-radius:4px;}"
    )
    rf_lay = QVBoxLayout(rule_f); rf_lay.setSpacing(4); rf_lay.setContentsMargins(8, 8, 8, 8)
    formula = (f"Z-query  =  ({r12_lbl},  {r23_lbl})"
               + (f"     →  apply {out_lbl}  to  R₁₃"
                  if out_lbl != "none" else "     →  result is final"))
    fl2 = QLabel(formula); fl2.setFont(QFont("Courier New",10,QFont.Weight.Bold))
    fl2.setStyleSheet(f"color:{RULE_FG[rule]};"); rf_lay.addWidget(fl2)
    d2 = QLabel(desc); d2.setFont(QFont("Arial",9))
    d2.setStyleSheet(f"color:{TEXT_SUB};"); rf_lay.addWidget(d2)
    lay.addWidget(rule_f)

    # ── 3. Z-lookup pair ──────────────────────────────────────────────────────
    lay.addWidget(sec("3 · Z-table lookup pair  (after applying the rotation)"))
    row3 = QHBoxLayout(); row3.setSpacing(8)
    for lbl, orig, rot in [
        (f"{r12_lbl}", nc_r12, nc_r12_z),
        (f"{r23_lbl}", nc_r23, nc_r23_z),
    ]:
        lines = [(pretty_br(rot), True)]
        if orig != rot:
            lines.insert(0, (f"original: {pretty_br(orig)}", False))
        else:
            lines.append(("(unchanged)", False))
        row3.addWidget(card(lbl, lines))
    lay.addLayout(row3)

    # ── 4. Composition result ─────────────────────────────────────────────────
    n_rel = len(r13_final)
    label4 = (f"4 · R₁₃ result  "
              f"({'after applying ' + out_lbl if out_lbl != 'none' else 'direct from Z'})"
              f"  —  {n_rel} relation{'s' if n_rel != 1 else ''}")
    lay.addWidget(sec(label4))
    if r13_final:
        chunk = 3
        for i in range(0, len(r13_final), chunk):
            row_ncs = r13_final[i:i+chunk]
            l = QLabel("   " + "   ".join(pretty_br(br) for br in row_ncs))
            l.setFont(QFont("Courier New", 9)); lay.addWidget(l)
    else:
        l = QLabel("(no result found)"); l.setFont(QFont("Arial",9))
        l.setStyleSheet(f"color:{TEXT_SUB};"); lay.addWidget(l)

    # ── 5. Trace summary ───────────────────────────────────────────────────────
    lay.addWidget(sec("5 · Trace summary"))
    trace_lines = [
        (f"Original pair: {pretty_br(nc_r12)}  ∘  {pretty_br(nc_r23)}", True),
        (f"Canonical Z pair: {pretty_br(nc_r12_z)}  ∘  {pretty_br(nc_r23_z)}", True),
        (f"Lookup mode: {'direct Z lookup' if trace and trace['direct_z_lookup'] else 'canonical reduction via π-rule'}", False),
        (f"Result in Z: {', '.join(pretty_br(br) for br in r13_z_ncs) if r13_z_ncs else '(no result found)'}", True),
        (f"Recovered final result: {', '.join(pretty_br(br) for br in r13_final) if r13_final else '(no result found)'}", True),
    ]
    lay.addWidget(card("Derivation path", trace_lines))

    def _plain_trace_text() -> str:
        lines = [
            f"Rule {rule} — Class {row_class+1} ∘ Class {col_class+1}",
            f"R12 = {pretty_br(nc_r12)}",
            f"R23 = {pretty_br(nc_r23)}",
            f"Canonical Z pair = {pretty_br(nc_r12_z)} ∘ {pretty_br(nc_r23_z)}",
            f"Z result = {', '.join(pretty_br(br) for br in r13_z_ncs) if r13_z_ncs else '(no result found)'}",
            f"Final result = {', '.join(pretty_br(br) for br in r13_final) if r13_final else '(no result found)'}",
        ]
        return '\n'.join(lines)

    lay.addStretch()
    scroll.setWidget(body)
    outer.addWidget(scroll, 1)
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    copy_btn = make_button("Copy trace")
    copy_btn.setToolTip("Copy the composition trace for this rule to the clipboard")
    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(_plain_trace_text()))
    btn_row.addWidget(copy_btn)
    outer.addLayout(btn_row)
    dlg.exec()



def _show_rule_popup_for(row_class: int, col_class: int, rule: int,
                          nc_r12: str, nc_r23: str) -> None:
    """Like _show_rule_popup but with explicit BR strings for the pair."""
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    )
    from PyQt6.QtCore import Qt, QObject
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QPushButton

    rc_cats = ROW_TO_CATALOG[row_class]
    cc_cats = ROW_TO_CATALOG[col_class]

    trace = explain_basic_composition(nc_r12, nc_r23)
    nc_r12_z = trace["z_r12_br"]
    nc_r23_z = trace["z_r23_br"]
    r13_z_ncs = trace["z_result_ncs"]
    r13_final = trace["final_result_ncs"]

    _, r12_lbl, r23_lbl, out_lbl, desc = _RULE_FORMULAS[rule]

    dlg = QDialog()
    dlg.setWindowTitle(f"Rule {rule}  —  {pretty_br(nc_r12)} ∘ {pretty_br(nc_r23)}")
    dlg.resize(760, 540)
    dlg.setMinimumSize(680, 460)
    outer = QVBoxLayout(dlg)
    outer.setSpacing(8)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setSpacing(10)

    def sec(txt):
        l = QLabel(txt); l.setFont(QFont("Arial",11,QFont.Weight.Bold))
        l.setStyleSheet(f"color:{ACCENT}; padding:2px 0;"); return l

    def card(title, lines):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:white;border:1px solid {BORDER};"
                        "border-radius:4px;}")
        fl = QVBoxLayout(f); fl.setSpacing(3); fl.setContentsMargins(6, 6, 6, 6)
        tt = QLabel(f"<b>{title}</b>"); tt.setFont(QFont("Arial",9)); fl.addWidget(tt)
        for txt, mono in lines:
            l = QLabel(txt)
            l.setFont(QFont("Courier New",10) if mono else QFont("Arial",9))
            l.setStyleSheet(f"color:{TEXT_MAIN if mono else TEXT_SUB};")
            l.setWordWrap(True); fl.addWidget(l)
        return f

    lay.addWidget(sec("1 · Selected composition"))
    row1 = QHBoxLayout(); row1.setSpacing(8)
    row1.addWidget(card(f"R₁₂ — row class {row_class+1}",
        [(pretty_br(nc_r12), True),
         (f"Catalogue: {', '.join(str(c) for c in rc_cats)}", False)]))
    row1.addWidget(card(f"R₂₃ — col class {col_class+1}",
        [(pretty_br(nc_r23), True),
         (f"Catalogue: {', '.join(str(c) for c in cc_cats)}", False)]))
    lay.addLayout(row1)

    lay.addWidget(sec(f"2 · Rule {rule} applied"))
    rule_f = QFrame()
    rule_f.setStyleSheet(f"QFrame{{background:{RULE_BG[rule]};border:1px solid {RULE_FG[rule]};"
                         "border-radius:4px;}")
    rf_lay = QVBoxLayout(rule_f); rf_lay.setSpacing(4); rf_lay.setContentsMargins(8, 8, 8, 8)
    formula = (f"Z-query  =  ({r12_lbl},  {r23_lbl})"
               + (f"     →  apply {out_lbl}  to  R₁₃"
                  if out_lbl != "none" else "     →  result is final"))
    fl2 = QLabel(formula); fl2.setFont(QFont("Courier New",10,QFont.Weight.Bold))
    fl2.setStyleSheet(f"color:{RULE_FG[rule]};"); rf_lay.addWidget(fl2)
    d2 = QLabel(desc); d2.setFont(QFont("Arial",9))
    d2.setStyleSheet(f"color:{TEXT_SUB};"); rf_lay.addWidget(d2)
    lay.addWidget(rule_f)

    lay.addWidget(sec("3 · Z-table lookup pair  (after applying the rotation)"))
    row3 = QHBoxLayout(); row3.setSpacing(8)
    for lbl, orig, rot in [
        (f"{r12_lbl}", nc_r12, nc_r12_z),
        (f"{r23_lbl}", nc_r23, nc_r23_z),
    ]:
        lines = [(pretty_br(rot), True)]
        if orig != rot:
            lines.insert(0, (f"original: {pretty_br(orig)}", False))
        else:
            lines.append(("(unchanged)", False))
        row3.addWidget(card(lbl, lines))
    lay.addLayout(row3)

    n_rel = len(r13_final)
    label4 = (f"4 · R₁₃ result  "
              f"({'after applying ' + out_lbl if out_lbl != 'none' else 'direct from Z'})"
              f"  —  {n_rel} relation{'s' if n_rel != 1 else ''}")
    lay.addWidget(sec(label4))
    if r13_final:
        chunk = 3
        for i in range(0, len(r13_final), chunk):
            row_ncs = r13_final[i:i+chunk]
            l = QLabel("   " + "   ".join(pretty_br(br) for br in row_ncs))
            l.setFont(QFont("Courier New", 9)); lay.addWidget(l)
    else:
        l = QLabel("(no result found)"); l.setFont(QFont("Arial",9))
        l.setStyleSheet(f"color:{TEXT_SUB};"); lay.addWidget(l)

    # ── 5. Trace summary ───────────────────────────────────────────────────────
    lay.addWidget(sec("5 · Trace summary"))
    trace_lines = [
        (f"Original pair: {pretty_br(nc_r12)}  ∘  {pretty_br(nc_r23)}", True),
        (f"Canonical Z pair: {pretty_br(nc_r12_z)}  ∘  {pretty_br(nc_r23_z)}", True),
        (f"Lookup mode: {'direct Z lookup' if trace and trace['direct_z_lookup'] else 'canonical reduction via π-rule'}", False),
        (f"Result in Z: {', '.join(pretty_br(br) for br in r13_z_ncs) if r13_z_ncs else '(no result found)'}", True),
        (f"Recovered final result: {', '.join(pretty_br(br) for br in r13_final) if r13_final else '(no result found)'}", True),
    ]
    lay.addWidget(card("Derivation path", trace_lines))

    def _plain_trace_text() -> str:
        lines = [
            f"Rule {rule} — Class {row_class+1} ∘ Class {col_class+1}",
            f"R12 = {pretty_br(nc_r12)}",
            f"R23 = {pretty_br(nc_r23)}",
            f"Canonical Z pair = {pretty_br(nc_r12_z)} ∘ {pretty_br(nc_r23_z)}",
            f"Z result = {', '.join(pretty_br(br) for br in r13_z_ncs) if r13_z_ncs else '(no result found)'}",
            f"Final result = {', '.join(pretty_br(br) for br in r13_final) if r13_final else '(no result found)'}",
        ]
        return '\n'.join(lines)

    lay.addStretch()
    scroll.setWidget(body)
    outer.addWidget(scroll, 1)
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    copy_btn = make_button("Copy trace")
    copy_btn.setToolTip("Copy the composition trace for this rule to the clipboard")
    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(_plain_trace_text()))
    btn_row.addWidget(copy_btn)
    outer.addLayout(btn_row)
    dlg.exec()


class RulesTablePanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Description
        desc = QLabel(
            f'<span style="color:{TEXT_SUB};">'
            "The 24×24 table shows which π-rule (0–7) applies to each pair of the 24 "
            "row/column classes when computing R₁₂ ∘ R₂₃. Rule 0 means a direct lookup in "
            "the Z table; rules 1–7 apply the corresponding π-rotation to reduce the pair to "
            "a canonical Z lookup and then apply the inverse rotation to recover the final "
            "R₁₃ result. The class reference table maps each class to the catalogue basic "
            "relations it represents."
            "</span>"
        )
        desc.setFont(font_label())
        desc.setWordWrap(True)
        desc.setContentsMargins(16, 10, 16, 6)
        desc_row = QWidget()
        desc_row_lay = QHBoxLayout(desc_row)
        desc_row_lay.setContentsMargins(0, 0, 0, 0)
        desc_row_lay.setSpacing(8)
        desc_row_lay.addWidget(desc, 1)
        desc_row_lay.addWidget(make_help_button(SEC_RULES_TABLE), 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(desc_row)

        # Colour legend
        legend_w = QWidget()
        legend_w.setStyleSheet(f"background: {STRIPE_BG};")
        leg_lay = QHBoxLayout(legend_w)
        leg_lay.setContentsMargins(12, 4, 12, 4)
        leg_lay.setSpacing(6)
        lbl_leg = QLabel("Rules:")
        lbl_leg.setFont(font_label_bold())
        leg_lay.addWidget(lbl_leg)
        for r in range(8):
            chip = QLabel(f"  {r}  ")
            chip.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            chip.setStyleSheet(
                f"background-color: {RULE_BG[r]}; color: {RULE_FG[r]}; "
                f"border: 1px solid {RULE_FG[r]}; border-radius: 3px;"
            )
            chip.setToolTip(RULE_LABELS[r])
            leg_lay.addWidget(chip)
            txt = QLabel(RULE_LABELS[r].split("—")[1].strip())
            txt.setFont(font_small())
            txt.setStyleSheet(f"color: {TEXT_SUB};")
            leg_lay.addWidget(txt)
            if r < 7:
                leg_lay.addSpacing(8)
        leg_lay.addStretch()
        root.addWidget(legend_w)

        # Splitter: reference table (top) | rules table (bottom)
        # ── 24x24 rules table ─────────────────────────────────────────────────
        rules_lbl = QLabel("  24\u00d724 Composition rules table  (row = R\u2081\u2082 class, col = R\u2082\u2083 class)  \u2014  hover row/col labels for full BR notation")
        rules_lbl.setFont(font_label_bold())
        rules_lbl.setStyleSheet(f"color: {ACCENT}; padding: 4px 8px; background: {STRIPE_BG};")

        # Header row: blank corner + col class compact BR labels
        # SIZE+1 rows: row 0 = manual header (QLabels), rows 1..SIZE = data
        rules_tbl = QTableWidget(SIZE + 1, SIZE + 1)
        rules_tbl.setHorizontalHeaderLabels([""] * (SIZE + 1))
        rules_tbl.horizontalHeader().setVisible(False)
        rules_tbl.verticalHeader().setVisible(False)
        rules_tbl.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        rules_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rules_tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        rules_tbl.setAlternatingRowColors(False)
        rules_tbl.setStyleSheet(f"""
            QTableWidget {{ border: 1px solid {BORDER_DARK}; gridline-color: #CFD8DC; }}
            QTableWidget::item:selected {{ background-color: {ACCENT}; color: white; }}
        """)

        rules_tbl.setColumnWidth(0, 90)
        for c in range(1, SIZE+1):
            rules_tbl.setColumnWidth(c, 52)
        rules_tbl.setRowHeight(0, 28)
        for r in range(1, SIZE+1):
            rules_tbl.setRowHeight(r, 22)

        # ── Row 0: manual header with QLabels (HTML renders natively) ────────
        # Corner cell
        _lbl_corner = QLabel("R₁₂ \\ R₂₃")
        _lbl_corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _lbl_corner.setStyleSheet(f"QLabel {{ color: white; font-weight: bold; background: {ACCENT}; }}")
        _c0_item = QTableWidgetItem("")
        _c0_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        _c0_item.setBackground(QColor(ACCENT))
        rules_tbl.setItem(0, 0, _c0_item)
        rules_tbl.setCellWidget(0, 0, _lbl_corner)
        # Column header cells
        for _c in range(SIZE):
            _html = _canon(ROW_TO_CATALOG[_c])
            _tip  = "\n".join(pretty_br(CATALOG[_cat-1]) for _cat in ROW_TO_CATALOG[_c])
            _lbl = QLabel(_html)
            _lbl.setTextFormat(Qt.TextFormat.RichText)
            _lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _lbl.setStyleSheet(
                f"QLabel {{ color: white; font-weight: bold; font-size: 8pt; "
                f"font-family: Courier New; background: {ACCENT}; }}")
            _hdr_item = QTableWidgetItem("")
            _hdr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            _hdr_item.setBackground(QColor(ACCENT))
            rules_tbl.setItem(0, _c + 1, _hdr_item)
            rules_tbl.setCellWidget(0, _c + 1, _lbl)
            _lbl.setToolTip(_tip)

        # Install viewport event filter for consistent tooltip styling
        _ttf = _TableTooltipFilter(rules_tbl)
        rules_tbl.viewport().installEventFilter(_ttf)
        rules_tbl.viewport().setMouseTracking(True)

        # Get the rules table from the logic layer: dict (row,col) -> rule
        rt = get_rules_table()

        for row in range(SIZE):
            tbl_row = row + 1  # offset by 1 due to manual header row
            # Col 0: row label QLabel with HTML
            _lbl = QLabel(
                f'<div style="color:white;font-weight:bold;'
                f'font-family:Courier New;font-size:8pt;"'
                f' align="center">{_canon(ROW_TO_CATALOG[row])}</div>')
            _lbl.setTextFormat(Qt.TextFormat.RichText)
            _lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Use QLabel { } selector — does NOT affect QToolTip inheritance
            _lbl.setStyleSheet(f"QLabel {{ background-color: {ACCENT_DARK}; }}")
            _r0 = QTableWidgetItem("")
            _r0.setFlags(Qt.ItemFlag.ItemIsEnabled)
            _r0.setBackground(QColor(ACCENT_DARK))
            rules_tbl.setItem(tbl_row, 0, _r0)
            rules_tbl.setCellWidget(tbl_row, 0, _lbl)
            _lbl.setToolTip("\n".join(pretty_br(CATALOG[_cat-1]) for _cat in ROW_TO_CATALOG[row]))

            for col in range(SIZE):
                rule = rt.get((row, col), 0)
                item = QTableWidgetItem(str(rule))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setBackground(QColor(RULE_BG[rule]))
                item.setForeground(QColor(RULE_FG[rule]))
                item.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                item.setToolTip(
                    f"Row class {row+1} x Col class {col+1}\n"
                    f"{RULE_LABELS[rule]}\n"
                    f"Row BRs: {', '.join(str(c) for c in ROW_TO_CATALOG[row])}\n"
                    f"Col BRs: {', '.join(str(c) for c in ROW_TO_CATALOG[col])}"
                )
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                rules_tbl.setItem(tbl_row, col+1, item)

        # ── Cell click → popup ────────────────────────────────────────────────
        def _on_cell_clicked(tbl_row: int, tbl_col: int):
            if tbl_col == 0 or tbl_row == 0:  # ignore header row/col
                return
            row_class = tbl_row - 1  # offset: row 0 is manual header
            col_class = tbl_col - 1
            rule = rt.get((row_class, col_class), 0)
            rc_cats = ROW_TO_CATALOG[row_class]
            cc_cats = ROW_TO_CATALOG[col_class]
            # If both classes are singletons, go directly to detail popup
            if len(rc_cats) == 1 and len(cc_cats) == 1:
                _show_rule_popup(row_class, col_class, rule)
                return
            # Otherwise show an intermediate dialog listing all combinations
            from PyQt6.QtWidgets import (
                QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                QHeaderView, QAbstractItemView,
            )
            from PyQt6.QtGui import QFont
            dlg = QDialog()
            n_r12 = len(rc_cats)
            n_r23 = len(cc_cats)
            dlg.setWindowTitle(
                f"Class {row_class+1} × Class {col_class+1}  —  "
                f"{n_r12 * n_r23} composition(s)  —  Rule {rule}"
            )
            dlg.resize(760, 460)
            lay = QVBoxLayout(dlg)
            lay.setSpacing(8)
            info = QLabel(
                f"<b>Row class {row_class+1}</b> contains {n_r12} basic relation(s) &nbsp;·&nbsp; "
                f"<b>Col class {col_class+1}</b> contains {n_r23} basic relation(s).<br>"
                f"Click a row to see the full detail for that composition."
            )
            info.setTextFormat(Qt.TextFormat.RichText)
            info.setFont(QFont("Arial", 9))
            lay.addWidget(info)
            tbl = QTableWidget(0, 3)
            tbl.setHorizontalHeaderLabels(["R₁₂", "R₂₃", "Rule"])
            tbl.setFont(QFont("Courier New", 10))
            tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setAlternatingRowColors(True)
            pairs = []
            for ri, cat_r in enumerate(rc_cats):
                for ci, cat_c in enumerate(cc_cats):
                    br_r = CATALOG[cat_r - 1]
                    nc_c = CATALOG[cat_c - 1]
                    row_idx = tbl.rowCount()
                    tbl.insertRow(row_idx)
                    tbl.setItem(row_idx, 0, QTableWidgetItem(pretty_br(br_r)))
                    tbl.setItem(row_idx, 1, QTableWidgetItem(pretty_br(nc_c)))
                    tbl.setItem(row_idx, 2, QTableWidgetItem(str(rule)))
                    pairs.append((ri, ci))
            lay.addWidget(tbl, 1)
            def _open_detail(item):
                r = item.row()
                ri, ci = pairs[r]
                nc_r12_sel = CATALOG[rc_cats[ri] - 1]
                nc_r23_sel = CATALOG[cc_cats[ci] - 1]
                _show_rule_popup_for(row_class, col_class, rule, nc_r12_sel, nc_r23_sel)
            tbl.itemClicked.connect(_open_detail)
            dlg.exec()

        rules_tbl.cellClicked.connect(_on_cell_clicked)

        rules_frame = QWidget()
        rl_lay = QVBoxLayout(rules_frame)
        rl_lay.setContentsMargins(0, 0, 0, 0)
        rl_lay.setSpacing(0)
        rl_lay.addWidget(rules_lbl)
        rl_lay.addWidget(rules_tbl, 1)
        root.addWidget(rules_frame, 1)

        # Source note
        note = QLabel(
            "  Source: dynamically computed from Z at startup via DynamicRulesTable "
            "(Section 4.3 of the paper)."
        )
        note.setFont(font_small())
        note.setStyleSheet(f"color: {TEXT_SUB}; padding: 4px 12px;")
        root.addWidget(note)
