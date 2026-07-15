"""
neighbourhood_panel.py
----------------------
Interactive neighbourhood graph for the 48 QRPC basic relations.
Layout follows the geometric organisation from the paper.
Node labels: Unicode superscripts/subscripts (compact form).
Node tooltips: compact form notation (as used throughout the app).
Panel right: compact form for selected node and its neighbours.
"""
from __future__ import annotations
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics

from .theme import (
    ACCENT, ACCENT_DARK, ACCENT_LIGHT, BG, PANEL_BG,
    BORDER, BORDER_DARK, TEXT_MAIN, TEXT_SUB, STRIPE_BG,
    font_label_bold, font_small, make_button,
)
from .rules_table_panel import pretty_br
from .help_dialog import make_help_button, SEC_NEIGHBOURHOOD
from qrpc.br_neighbours import NEIGHBOURS

# ── Unicode compact notation ───────────────────────────────────────────────────
_SUP = {'PLUS': '⁺', 'MINUS': '⁻', 'ZERO': '⁰', '_': ''}
_SUB = {'PLUS': '₊', 'MINUS': '₋', 'ZERO': '₀', '_': ''}
_DLR = {
    'P_TO_M': '₊|₋', 'M_TO_P': '₋|₊',
    'P_TO_0': '₊|₀', 'M_TO_0': '₋|₀',
    '_0_TO_P': '₀|₊', '_0_TO_M': '₀|₋',
    '_0_TO_0': '₀|₀', '_': ''
}

def _node_label(br: str) -> str:
    inner = br.strip('<>').split(',')
    fam = inner[0].strip()
    if fam == 'X':
        c1=inner[1].strip(); c2=inner[2].strip()
        lr=inner[3].strip(); dlr=inner[4].strip(); ofb=inner[5].strip()
        return 'X'+_SUP.get(c1,'')+_SUP.get(c2,'')+_SUB.get(lr,'')+_DLR.get(dlr,'')+_SUB.get(ofb,'')
    elif fam == 'PAR_SAME': return '↑↑'+_SUB.get(inner[3].strip(),'')+_SUB.get(inner[5].strip(),'')
    elif fam == 'PAR_OPP':  return '↑↓'+_SUB.get(inner[3].strip(),'')+_SUB.get(inner[5].strip(),'')
    elif fam == 'OVL_SAME': return '↑'+_SUB.get(inner[5].strip(),'')
    elif fam == 'OVL_OPP':  return '↕'+_SUB.get(inner[5].strip(),'')
    return br

# ── Family colours ─────────────────────────────────────────────────────────────
FAMILY_COLORS = {
    'X':        ("#1B3A8A", "#D0DEFA"),
    'PAR_SAME': ("#0D6832", "#C3EDCE"),
    'PAR_OPP':  ("#7B4C00", "#FFF0C0"),
    'OVL_SAME': ("#6B1A7A", "#EDD6F5"),
    'OVL_OPP':  ("#8B0000", "#FAD4D4"),
}

def _family(br):
    p = br.lstrip('<').split(',')[0]
    if p == 'PAR_SAME': return 'PAR_SAME'
    if p == 'PAR_OPP':  return 'PAR_OPP'
    if p == 'OVL_SAME': return 'OVL_SAME'
    if p == 'OVL_OPP':  return 'OVL_OPP'
    return 'X'

CANVAS_W, CANVAS_H = 1000, 940
NODE_R, HIT_R = 32, 38

_LAYOUT = None

def _get_layout():
    global _LAYOUT
    if _LAYOUT: return _LAYOUT
    cx, cy = CANVAS_W/2, CANVAS_H/2
    by_fam = {}
    for br in sorted(NEIGHBOURS):
        by_fam.setdefault(_family(br), []).append(br)

    pos = {}
    x_brs = by_fam.get('X', [])
    rx, ry = CANVAS_W*0.27, CANVAS_H*0.26
    for i, br in enumerate(x_brs):
        a = 2*math.pi*i/len(x_brs) - math.pi/2
        pos[br] = QPointF(cx + rx*math.cos(a), cy + ry*math.sin(a))

    for fam, base_a, rad, spread in [
        ('PAR_SAME', 3*math.pi/2, CANVAS_W*0.43, 0.36),
        ('PAR_OPP',  math.pi/2,   CANVAS_W*0.43, 0.36),
        ('OVL_SAME', math.pi,     CANVAS_H*0.42, 0.33),
        ('OVL_OPP',  0.0,         CANVAS_H*0.42, 0.33),
    ]:
        brs = by_fam.get(fam, [])
        n = len(brs)
        for i, br in enumerate(brs):
            t = 0.0 if n==1 else (i/(n-1)-0.5)*spread*math.pi
            pos[br] = QPointF(cx + rad*math.cos(base_a+t),
                              cy + rad*math.sin(base_a+t))
    _LAYOUT = pos
    return pos


# ── Graph canvas ───────────────────────────────────────────────────────────────
class _GraphCanvas(QWidget):
    node_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.setMouseTracking(True)
        self._selected = None
        self._hovered  = None
        self._font = QFont('Arial', 10, QFont.Weight.Bold)

    def paintEvent(self, ev):
        pos = _get_layout()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor(PANEL_BG))

        sel = self._selected
        highlight = set(NEIGHBOURS.get(sel, [])) if sel else set()

        # Edges
        drawn = set()
        for br_a, nbrs in NEIGHBOURS.items():
            for br_b in nbrs:
                key = (min(br_a,br_b), max(br_a,br_b))
                if key in drawn: continue
                drawn.add(key)
                pa, pb = pos.get(br_a), pos.get(br_b)
                if pa is None or pb is None: continue
                active = sel and (br_a==sel or br_b==sel)
                hover  = (not sel) and self._hovered and (br_a==self._hovered or br_b==self._hovered)
                if active:   c,w,a = QColor(ACCENT),2.2,220
                elif hover:  c,w,a = QColor(ACCENT),1.6,155
                else:        c,w,a = QColor(BORDER_DARK),1.0,48 if sel else 82
                c.setAlpha(a)
                pen = QPen(c,w); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen); p.drawLine(pa, pb)

        # Nodes
        r = NODE_R
        p.setFont(self._font)
        fm = QFontMetrics(self._font)
        for br, pt in pos.items():
            fam = _family(br)
            sh, fh = FAMILY_COLORS.get(fam, ("#444","#CCC"))
            is_sel = br==sel; is_nbr = br in highlight
            is_hov = br==self._hovered
            is_dim = sel and not is_sel and not is_nbr

            fill   = QColor(sh) if is_sel else \
                     QColor(fh).darker(118) if is_nbr else \
                     QColor(fh).darker(106) if is_hov else \
                     QColor("#E8E8E8") if is_dim else QColor(fh)
            stroke = QColor("#BBBBBB") if is_dim else QColor(sh)
            sw     = 2.8 if is_sel else 2.2 if is_nbr else 2.0 if is_hov else 1.0 if is_dim else 1.6

            p.setBrush(QBrush(fill))
            p.setPen(QPen(stroke, sw))
            p.drawEllipse(QRectF(pt.x()-r, pt.y()-r, 2*r, 2*r))

            lbl = _node_label(br)
            tw  = fm.horizontalAdvance(lbl)
            tc  = QColor("white") if is_sel else \
                  QColor(sh).darker(120) if is_nbr else \
                  QColor(sh) if not is_dim else QColor("#AAAAAA")
            p.setPen(tc)
            p.drawText(QPointF(pt.x()-tw/2, pt.y()+fm.ascent()/2-fm.descent()/2), lbl)

        p.end()

    def _node_at(self, x, y):
        pos = _get_layout()
        best, bd = None, HIT_R**2
        for br, pt in pos.items():
            d2 = (pt.x()-x)**2 + (pt.y()-y)**2
            if d2 < bd: bd, best = d2, br
        return best

    def mouseMoveEvent(self, ev):
        node = self._node_at(ev.position().x(), ev.position().y())
        if node != self._hovered:
            self._hovered = node
            self.setCursor(Qt.CursorShape.PointingHandCursor if node
                           else Qt.CursorShape.ArrowCursor)
            # Show pretty_br as tooltip
            if node:
                from PyQt6.QtWidgets import QToolTip
                QToolTip.showText(ev.globalPosition().toPoint(), pretty_br(node), self)
            self.update()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton: return
        node = self._node_at(ev.position().x(), ev.position().y())
        self._selected = None if node==self._selected else node
        self.update()
        self.node_selected.emit(self._selected or '')

    def leaveEvent(self, ev):
        self._hovered = None; self.update()

    def reset_selection(self):
        self._selected = None
        self.update()
        self.node_selected.emit('')


# ── Side detail panel ──────────────────────────────────────────────────────────
class _NodeDetailPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"QFrame{{background:{PANEL_BG};border:1px solid {BORDER_DARK};"
            f"border-radius:6px;}}"
        )
        self.setFixedWidth(310)
        lay = QVBoxLayout(self); lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)

        self._badge = QLabel("—")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setMinimumHeight(54)
        self._badge.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self._badge.setWordWrap(True)
        self._badge.setStyleSheet(
            f"background:{STRIPE_BG};border:2px solid {BORDER};"
            f"border-radius:8px;padding:6px;color:{ACCENT};"
        )
        lay.addWidget(self._badge)

        self._fam = QLabel()
        self._fam.setFont(font_small())
        self._fam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fam.setStyleSheet(f"color:{TEXT_SUB};border:none;")
        self._fam.setWordWrap(True)
        lay.addWidget(self._fam)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};"); lay.addWidget(sep)

        hdr = QLabel("Geometric neighbours")
        hdr.setFont(font_label_bold())
        hdr.setStyleSheet(f"color:{TEXT_MAIN};border:none;")
        lay.addWidget(hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._inner = QWidget()
        self._ilay  = QVBoxLayout(self._inner)
        self._ilay.setContentsMargins(0,0,0,0); self._ilay.setSpacing(4)
        scroll.setWidget(self._inner)
        lay.addWidget(scroll, 1)

        self._stats = QLabel()
        self._stats.setFont(font_small())
        self._stats.setStyleSheet(f"color:{TEXT_SUB};border:none;")
        self._stats.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(self._stats)

    def show_node(self, br: str):
        for i in reversed(range(self._ilay.count())):
            w = self._ilay.itemAt(i).widget()
            if w: w.deleteLater()

        if not br:
            self._badge.setText("—")
            self._badge.setStyleSheet(
                f"background:{STRIPE_BG};border:2px solid {BORDER};"
                f"border-radius:8px;padding:6px;color:{ACCENT};"
            )
            self._fam.setText(""); self._stats.setText(""); return

        fam = _family(br)
        sh, fh = FAMILY_COLORS.get(fam, ("#444","#CCC"))
        fam_names = {
            'X':        'Crossing  (X)',
            'PAR_SAME': 'Parallel — same direction  (↑↑)',
            'PAR_OPP':  'Parallel — opposite direction  (↑↓)',
            'OVL_SAME': 'Overlapping — same direction  (↑)',
            'OVL_OPP':  'Overlapping — opposite direction  (↕)',
        }

        self._badge.setText(pretty_br(br))
        self._badge.setStyleSheet(
            f"background:{fh};border:2px solid {sh};"
            f"border-radius:8px;padding:6px;color:{sh};"
            f"font-size:13pt;font-weight:bold;"
        )
        self._fam.setText(fam_names.get(fam, fam))

        nbrs = sorted(NEIGHBOURS.get(br, []))
        for nbr in nbrs:
            nfam = _family(nbr)
            ns, nf = FAMILY_COLORS.get(nfam, ("#444","#CCC"))
            row = QFrame()
            row.setStyleSheet(f"QFrame{{background:{nf};border:1px solid {ns};border-radius:4px;}}")
            rl = QHBoxLayout(row); rl.setContentsMargins(8,5,8,5)
            lbl = QLabel(pretty_br(nbr))
            lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{ns};border:none;background:transparent;")
            rl.addWidget(lbl)
            self._ilay.addWidget(row)

        self._ilay.addStretch()
        self._stats.setText(f"{len(nbrs)} neighbour(s)")


# ── Legend ─────────────────────────────────────────────────────────────────────
class _Legend(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{STRIPE_BG};border-top:1px solid {BORDER};")
        lay = QHBoxLayout(self); lay.setContentsMargins(12,6,12,6); lay.setSpacing(18)
        for fam, label in [
            ('X',       'Crossing  X'),
            ('PAR_SAME','↑↑  PAR Same'),
            ('PAR_OPP', '↑↓  PAR Opposite'),
            ('OVL_SAME','↑  OVL Same'),
            ('OVL_OPP', '↕  OVL Opposite'),
        ]:
            sh, _ = FAMILY_COLORS[fam]
            dot = QLabel("●"); dot.setStyleSheet(f"color:{sh};font-size:14px;border:none;background:transparent;")
            lbl = QLabel(label); lbl.setFont(font_small())
            lbl.setStyleSheet(f"color:{TEXT_MAIN};border:none;background:transparent;")
            lay.addWidget(dot); lay.addWidget(lbl)
        lay.addStretch()
        hint = QLabel("Click node to select  ·  click again to deselect  ·  hover for full notation")
        hint.setFont(font_small()); hint.setStyleSheet(f"color:{TEXT_SUB};border:none;background:transparent;")
        lay.addWidget(hint)


# ── Main panel ─────────────────────────────────────────────────────────────────
class NeighbourhoodPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        hdr = QFrame(); hdr.setStyleSheet(f"background:{ACCENT_DARK};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16,8,16,8)
        t = QLabel("QRPC Geometric Neighbourhood Graph")
        t.setFont(font_label_bold()); t.setStyleSheet("color:white;border:none;")
        s = QLabel("48 basic relations · 128 neighbour pairs")
        s.setFont(font_small()); s.setStyleSheet(f"color:{ACCENT_LIGHT};border:none;")
        hl.addWidget(t); hl.addStretch(); hl.addWidget(s)

        btn_reset = make_button("Reset")
        btn_reset.setFixedWidth(80)
        btn_reset.setEnabled(False)
        btn_reset.setToolTip("Clear the current selection and restore the full graph")
        btn_reset.setStyleSheet(btn_reset.styleSheet() + """
            QToolTip { background-color: #FFFFF0; color: #1A1A2E;
                       border: 1px solid #607D8B; padding: 4px; }
        """)
        hl.addWidget(btn_reset)
        help_btn = make_help_button(SEC_NEIGHBOURHOOD)
        help_btn.setStyleSheet(help_btn.styleSheet() + """
            QToolTip { background-color: #FFFFF0; color: #1A1A2E;
                       border: 1px solid #607D8B; padding: 4px; }
        """)
        hl.addWidget(help_btn)
        root.addWidget(hdr)

        body = QWidget()
        bl = QHBoxLayout(body); bl.setContentsMargins(8,8,8,8); bl.setSpacing(8)

        scroll = QScrollArea(); scroll.setWidgetResizable(False)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {PANEL_BG}; border: 1px solid {BORDER_DARK}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._canvas = _GraphCanvas()
        scroll.setWidget(self._canvas)

        self._detail = _NodeDetailPanel()
        bl.addWidget(scroll, 1); bl.addWidget(self._detail)
        root.addWidget(body, 1)
        root.addWidget(_Legend())

        self._canvas.node_selected.connect(self._detail.show_node)
        self._canvas.node_selected.connect(lambda br: btn_reset.setEnabled(bool(br)))
        btn_reset.clicked.connect(self._canvas.reset_selection)
        btn_reset.clicked.connect(lambda: self._detail.show_node(''))
        btn_reset.clicked.connect(lambda: btn_reset.setEnabled(False))
