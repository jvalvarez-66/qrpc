"""
geometry_panel.py
-----------------
Interactive Geometry Editor panel.
"""

from __future__ import annotations
import math
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QCheckBox, QScrollArea, QDialog, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextBrowser,
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush,
    QCursor, QFontMetrics, QPolygon,
)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qrpc.table48 import get_instantiated, get_compact
from .help_dialog import make_help_button, SEC_GEOMETRY, SEC_CONVERSE
from .geometry_classifier import (
    Obj, PairAnalysis, analyze, normalize_angle,
    distance_to_line, Sign, ANGLE_EPS, COLINEAR_EPS,
)
from .theme import (
    make_button, font_label, font_label_bold,
    BG, CONFIG_BAR, BORDER, BORDER_DARK, ACCENT, ACCENT_DARK,
    TEXT_MAIN, PANEL_BG,
)

# ── Colours ───────────────────────────────────────────────────────────────────
C_O1    = QColor(0x2C4F9E)
C_O2    = QColor(0xC0392B)
C_V     = QColor(0x0D6832)
C_THETA = QColor(0xCC5500)
C_PHI   = QColor(0x7B4C00)
C_C12   = QColor(0x0D6832)
C_GRID  = QColor(0xEEF2F7)
C_POS   = QColor(0xC3EDCE)
C_NEG   = QColor(0xFAD4D4)
C_ZERO  = QColor(0xFFF0C0)


# ── Draw helpers ──────────────────────────────────────────────────────────────

def _draw_arrow(p: QPainter, x1, y1, x2, y2, color: QColor, width=2.0, sz=11):
    p.setPen(QPen(color, width))
    p.drawLine(int(x1), int(y1), int(x2), int(y2))
    angle = math.atan2(y2-y1, x2-x1)
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    pts = [
        QPoint(int(x2), int(y2)),
        QPoint(int(x2 - sz*math.cos(angle-0.4)), int(y2 - sz*math.sin(angle-0.4))),
        QPoint(int(x2 - sz*math.cos(angle+0.4)), int(y2 - sz*math.sin(angle+0.4))),
    ]
    p.drawPolygon(QPolygon(pts))


def _show_relation_table(current_analysis, parent_widget):
    """
    Show a modal dialog with all 48 basic relations.
    Columns: Canonical form, sign(u₂×v), sign(u₁×v), θ, φ, θ?φ, θ+φ.
    The currently identified relation is highlighted in blue.
    """
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QAbstractItemView,
    )
    from PyQt6.QtGui import QFont, QColor, QBrush
    from PyQt6.QtCore import Qt
    from .rules_table_panel import pretty_br
    from .geometry_classifier import RULES

    dlg = QDialog(parent_widget)
    dlg.setWindowTitle("48 Basic Relations — full catalogue")

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(6)

    note = QLabel(
        "All 48 basic relations of the QRPC algebra. "
        "θ = angle(u₂, v),  φ = angle(u₁, v). "
        "The formally identified relation is <b>highlighted in blue</b>. "
        "If there is no formal match, the nearest relation is shown in amber."
    )
    note.setTextFormat(Qt.TextFormat.RichText)
    note.setFont(QFont("Arial", 9))
    lay.addWidget(note)

    headers = ["Canonical form", "sgn(u_j×v)", "sgn(u_i×v)", "θ = ∠(u_j,v)", "φ = ∠(u_i,v)", "θ vs φ", "θ + φ"]
    tbl = QTableWidget(0, len(headers))
    tbl.setHorizontalHeaderLabels(headers)
    tbl.setFont(QFont("Courier New", 9))
    tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tbl.verticalHeader().setVisible(False)
    tbl.setAlternatingRowColors(False)
    tbl.setStyleSheet(
        "QTableWidget { selection-background-color: transparent; }"
        "QTableWidget::item:selected { background-color: transparent; color: black; }"
        "QTableWidget::item:focus { border: none; }"
    )
    tbl.clearSelection()
    tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    # Keep all columns with the same width for easier visual comparison.
    header = tbl.horizontalHeader()
    header.setStretchLastSection(False)
    for c in range(len(headers)):
        header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
    tbl.setWordWrap(False)

    def _sign_str(s):
        """Show full interval description for sign of cross product."""
        if s is None: return "—"
        n = s.name if hasattr(s, 'name') else str(s)
        return {"NEG": "< 0", "ZERO": "= 0", "POS": "> 0"}.get(n, n)

    def _pred_str(p, var="θ"):
        """Show interval/value for angle predicate (radians), matching Table 2."""
        if p is None: return "—"
        n = p.name if hasattr(p, 'name') else str(p)
        return {
            "ANY":   f"(0,π)",
            "LT90":  f"(0,π/2)",
            "EQ90":  f"π/2",
            "GT90":  f"(π/2,π)",
            "LT180": f"(0,π)",
            "EQ180": f"π",
            "EQ0":   f"0",
        }.get(n, n)

    def _cmp_str(rule):
        """Derive θ vs φ from the Cmp field (already corrected in rules)."""
        n = rule.cmp.name if hasattr(rule.cmp, 'name') else str(rule.cmp)
        return {"LT": "θ < φ", "EQ": "θ = φ", "GT": "θ > φ", "ANY": "—"}.get(n, n)

    def _sum_str(s):
        """Show interval/value for angle sum predicate (radians), matching Table 2."""
        if s is None: return "—"
        n = s.name if hasattr(s, 'name') else str(s)
        return {
            "LT180": "(0,π)",
            "EQ180": "π",
            "GT180": "(π,2π)",
            "EQ0":   "0 (mod 2π)",
            "ANY":   "—",
        }.get(n, n)

    current_br = current_analysis.br if current_analysis else None
    nearest_br = getattr(current_analysis, "nearest_br", None) if current_analysis else None
    status = getattr(current_analysis, "status", "FORMAL_MATCH") if current_analysis else "FORMAL_MATCH"
    hi_color  = QColor(30, 100, 200)   # strong blue — active formal relation
    near_color = QColor(255, 235, 190) # amber — nearest only, not formal
    alt_color = QColor(245, 246, 248)   # very light grey — even rows

    for rule in RULES:
        row = tbl.rowCount()
        tbl.insertRow(row)
        cells = [
            pretty_br(rule.br),
            _sign_str(rule.s2),
            _sign_str(rule.s1),
            _pred_str(rule.a, "θ"),
            _pred_str(rule.b, "φ"),
            _cmp_str(rule),
            _sum_str(rule.sum),
        ]
        is_active = (rule.br == current_br and status != "NO_FORMAL_MATCH")
        is_nearest = (status == "NO_FORMAL_MATCH" and rule.br == nearest_br)
        row_color = hi_color if is_active else (near_color if is_nearest else (alt_color if row % 2 == 0 else QColor(255, 255, 255)))
        for col, val in enumerate(cells):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QBrush(row_color))
            if is_active:
                item.setForeground(QBrush(QColor(255, 255, 255)))
            elif is_nearest:
                item.setForeground(QBrush(QColor(80, 50, 0)))
            tbl.setItem(row, col, item)

        if is_active:
            tbl.scrollToItem(tbl.item(row, 0))

    tbl.resizeRowsToContents()

    def _fit_dialog():
        """Open the catalogue taller while preserving the table scrollbars."""
        screen = dlg.screen().availableGeometry() if dlg.screen() else None
        max_w = int(screen.width() * 0.95) if screen else 1280
        max_h = int(screen.height() * 0.90) if screen else 820
        dlg.resize(min(1280, max_w), min(820, max_h))

    from PyQt6.QtCore import QTimer
    QTimer.singleShot(0, _fit_dialog)

    lay.addWidget(tbl, 1)
    dlg.exec()





def _draw_ix_pts(ox1, oy1, a1, ox2, oy2, a2, canvas_w, canvas_h) -> list:
    """
    Return a list of (x, y) intersection points to draw for a pair of objects:
    - X-type: one crossing point, only if within canvas.
    - OVL: two points — both object origins (shared support line, ambiguous).
      OVL is detected by the same criteria as analyze(): angle diff < ANGLE_EPS
      AND O2's origin within COLINEAR_EPS of P1.
    - PAR or off-canvas crossing: empty list.
    """
    ux1, uy1 = math.cos(a1), math.sin(a1)
    # OVL check: nearly parallel AND O2 colinear with P1
    angle_diff = abs(a1 - a2) % math.pi
    if angle_diff > math.pi / 2:
        angle_diff = math.pi - angle_diff
    if angle_diff < ANGLE_EPS:
        if distance_to_line(ox2, oy2, ox1, oy1, ux1, uy1) < COLINEAR_EPS:
            return [(ox1, oy1), (ox2, oy2)]   # OVL: both origins
        return []                               # PAR: no point
    # Normal crossing
    ux2, uy2 = math.cos(a2), math.sin(a2)
    det = ux1*uy2 - uy1*ux2
    if abs(det) < 1e-9:
        return []
    dx, dy = ox2-ox1, oy2-oy1
    t = (dx*uy2 - dy*ux2) / det
    cx, cy = ox1+t*ux1, oy1+t*uy1
    margin = 200.0
    if cx < -margin or cx > canvas_w+margin or cy < -margin or cy > canvas_h+margin:
        return []
    return [(cx, cy)]


# ── Interactive canvas (left panel) ──────────────────────────────────────────

class DrawCanvas(QWidget):
    """The interactive canvas where objects can be dragged and rotated."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: white; border: 1px solid #B0BEC5;")
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        self.o1 = Obj(180, 220, math.radians(15))
        self.o2 = Obj(430, 180, math.radians(110))

        self._dragging: Optional[Obj] = None
        self._rotating: Optional[Obj] = None
        self._off_x = 0.0
        self._off_y = 0.0

        self.snap_parallel   = True
        self.snap_colinear   = True
        self.on_changed = None    # callback

        self.setMouseTracking(False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Grid
        p.setPen(QPen(C_GRID, 1))
        for x in range(40, self.width(), 40):
            p.drawLine(x, 0, x, self.height())
        for y in range(40, self.height(), 40):
            p.drawLine(0, y, self.width(), y)

        # Pass 1: projection lines (behind everything)
        for o, col in [(self.o1, C_O1), (self.o2, C_O2)]:
            ux, uy = math.cos(o.angle), math.sin(o.angle)
            _pen = QPen(col, 2.0)
            _pen.setColor(QColor(col.red(), col.green(), col.blue(), 70))
            p.setPen(_pen)
            p.drawLine(int(o.x-ux*520), int(o.y-uy*520),
                       int(o.x+ux*520), int(o.y+uy*520))
        # Pass 2: handles, arrows, circles, labels
        self._draw_obj(p, self.o1, C_O1, "1")
        self._draw_obj(p, self.o2, C_O2, "2")
        p.end()

    def _draw_obj(self, p: QPainter, o: Obj, color: QColor, label: str):
        ux, uy = math.cos(o.angle), math.sin(o.angle)
        # Rotation handles (projection line drawn in pass 1)

        # Rotation handles
        pen2 = QPen(color, 4.5)
        pen2.setColor(QColor(color.red(), color.green(), color.blue(), 135))
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawLine(int(o.x+ux*30), int(o.y+uy*30), int(o.x+ux*95), int(o.y+uy*95))
        p.drawLine(int(o.x-ux*30), int(o.y-uy*30), int(o.x-ux*95), int(o.y-uy*95))

        # Direction arrow
        _draw_arrow(p, o.x, o.y, o.x+ux*45, o.y+uy*45, color, 3.0)

        # Origin circle
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(o.x-8), int(o.y-8), 16, 16)

        # Label
        p.setPen(QPen(color))
        p.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        p.drawText(int(o.x+10), int(o.y-10), label)

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, ev):
        mx, my = ev.position().x(), ev.position().y()
        if _dist(mx, my, self.o1.x, self.o1.y) < 18:
            self._dragging = self.o1
            self._off_x = mx - self.o1.x
            self._off_y = my - self.o1.y
        elif _dist(mx, my, self.o2.x, self.o2.y) < 18:
            self._dragging = self.o2
            self._off_x = mx - self.o2.x
            self._off_y = my - self.o2.y
        else:
            self._rotating = self._hit_rot_line(mx, my)

    def mouseMoveEvent(self, ev):
        mx, my = ev.position().x(), ev.position().y()
        if self._rotating:
            self._rotating.angle = math.atan2(my - self._rotating.y,
                                               mx - self._rotating.x)
            other = self.o2 if self._rotating is self.o1 else self.o1
            # Internal priority: if the broad double-zero case is active,
            # the forced OVL snap absorbs the parallel/opposite snap for this
            # interaction cycle.  This avoids both checkboxes applying two
            # independent geometry corrections over the same movement.
            if not self._snap_overlap_if_double_zero(self._rotating):
                self._snap(self._rotating, other)
            self._clamp()
            self._notify()
        elif self._dragging:
            self._dragging.x = mx - self._off_x
            self._dragging.y = my - self._off_y
            # Forced OVL has priority over the generic colinear projection.
            # If it is not active, the ordinary overlap snap can still help
            # the user reach the double-zero state; _update_analysis will then
            # apply the forced OVL once, respecting the checkbox state.
            if not self._snap_overlap_if_double_zero(self._dragging):
                if self.snap_colinear:
                    self._snap_colinear(self._dragging)
            self._clamp()
            self._notify()

    def mouseReleaseEvent(self, ev):
        self._dragging = None
        self._rotating = None

    def wheelEvent(self, ev):
        mx, my = ev.position().x(), ev.position().y()
        target = None
        if _dist(mx, my, self.o1.x, self.o1.y) < 24:
            target = self.o1
        elif _dist(mx, my, self.o2.x, self.o2.y) < 24:
            target = self.o2
        if target:
            delta = ev.angleDelta().y() / 120
            target.angle = normalize_angle(
                target.angle - delta * math.radians(2)
            )
            other = self.o2 if target is self.o1 else self.o1
            # Internal priority: forced OVL absorbs the parallel/opposite snap
            # when the broad double-zero condition is already active.
            if not self._snap_overlap_if_double_zero(target):
                self._snap(target, other)
            self._clamp()
            self._notify()

    def _hit_rot_line(self, mx, my) -> Optional[Obj]:
        for o in (self.o1, self.o2):
            ux, uy = math.cos(o.angle), math.sin(o.angle)
            along = (mx-o.x)*ux + (my-o.y)*uy
            perp  = abs((mx-o.x)*uy - (my-o.y)*ux)
            if 24 < abs(along) < 120 and perp < 10:
                return o
        return None

    def _snap(self, moved: Obj, other: Obj):
        if not self.snap_parallel:
            return
        moved.angle = normalize_angle(moved.angle)
        other.angle = normalize_angle(other.angle)
        diff = normalize_angle(other.angle - moved.angle)
        if abs(diff) < math.radians(4):
            other.angle = moved.angle
        elif abs(abs(diff) - math.pi) < math.radians(4):
            other.angle = normalize_angle(moved.angle + math.pi)

    def _snap_colinear(self, moving: Obj):
        ref = self.o2 if moving is self.o1 else self.o1
        d = distance_to_line(moving.x, moving.y, ref.x, ref.y,
                              math.cos(ref.angle), math.sin(ref.angle))
        if d < 14:
            ux, uy = math.cos(ref.angle), math.sin(ref.angle)
            along = (moving.x-ref.x)*ux + (moving.y-ref.y)*uy
            moving.x = ref.x + ux * along
            moving.y = ref.y + uy * along

    def _snap_overlap_if_double_zero(self, moving: Optional[Obj] = None) -> bool:
        """Force the visual scene to true OVL when both cross-products are zero.

        This is a real canvas trigger, not only a readout status.  If the
        classifier detects the broad double-zero case, the object currently
        being manipulated is snapped so that its support line becomes exactly
        the same support line as the other object.  The orientation is also
        forced to the OVL family selected by the classifier.

        The trigger is controlled by the ``Snap to overlap`` checkbox.  It does
        not depend on the ``Snap parallel/opposite`` checkbox, because in a
        forced OVL case the parallel/opposite orientation is part of the overlap
        itself.

        Returns True if the canvas geometry was changed.
        """
        if not self.snap_colinear:
            return False

        a = analyze(self.o1, self.o2)
        if not getattr(a, "forced_ovl", False):
            return False

        return self._force_overlap_from_analysis(a, moving)

    def _force_overlap_from_analysis(self, analysis: PairAnalysis,
                                     moving: Optional[Obj] = None) -> bool:
        """Make the canvas geometry exactly match a forced OVL analysis."""
        target = moving if moving in (self.o1, self.o2) else self.o2
        ref = self.o2 if target is self.o1 else self.o1

        old = (target.x, target.y, target.angle)

        # The family decided by the classifier chooses SAME vs OPP.  Use the
        # relation semantics, not the current almost-parallel visual state.
        fam_name = getattr(getattr(analysis, "family", None), "name", "")
        if fam_name == "OVL_OPP":
            target.angle = normalize_angle(ref.angle + math.pi)
        else:
            target.angle = normalize_angle(ref.angle)

        # Project the moved origin onto the reference support line.  From this
        # point on, both infinite projections are exactly the same line.
        ux, uy = math.cos(ref.angle), math.sin(ref.angle)
        along = (target.x - ref.x) * ux + (target.y - ref.y) * uy

        # Guard against a degenerate forced-overlap state.  In OVL_OPP, if both
        # origins collapse onto the same point, the vector between objects has
        # zero length and the classifier cannot decide between the two opposite
        # overlap orientations, so it reports NO_MATCH.  Keep a tiny, visually
        # harmless separation along the common support line so that the forced
        # geometry remains a valid basic relation after reanalysis.
        if fam_name == "OVL_OPP" and abs(along) < 1e-6:
            along = 1e-6

        target.x = ref.x + ux * along
        target.y = ref.y + uy * along

        return (abs(target.x - old[0]) > 1e-6 or
                abs(target.y - old[1]) > 1e-6 or
                abs(normalize_angle(target.angle - old[2])) > 1e-6)

    def _clamp(self):
        w = self.width()  if self.width()  > 0 else 600
        h = self.height() if self.height() > 0 else 400
        m = 22.0
        for o in (self.o1, self.o2):
            o.x = max(m, min(w-m, o.x))
            o.y = max(m, min(h-m, o.y))
        dx, dy = self.o2.x-self.o1.x, self.o2.y-self.o1.y
        if math.hypot(dx, dy) < 22:
            ang = math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-6 else self.o1.angle
            self.o2.x = max(m, min(w-m, self.o1.x + math.cos(ang)*22))
            self.o2.y = max(m, min(h-m, self.o1.y + math.sin(ang)*22))

    def resizeEvent(self, ev):
        self._clamp()
        self.update()

    def _notify(self):
        self.update()
        if self.on_changed:
            self.on_changed()


def _dist(x1, y1, x2, y2): return math.hypot(x1-x2, y1-y2)


# ── Read-only diagram (right panel top) ──────────────────────────────────────

class ReadoutDiagram(QWidget):
    """Non-interactive replica showing θ, φ, v overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis: Optional[PairAnalysis] = None
        self._o1: Optional[Obj] = None
        self._o2: Optional[Obj] = None
        self.setMinimumSize(200, 160)
        self.setStyleSheet("background-color: white;")

    def update_data(self, analysis: PairAnalysis, o1: Obj, o2: Obj):
        self._analysis = analysis
        # Scale objects to fit panel
        w = max(self.width(), 200)
        h = max(self.height(), 160)
        mcx = (o1.x + o2.x) / 2
        mcy = (o1.y + o2.y) / 2
        dist = math.hypot(o2.x-o1.x, o2.y-o1.y)
        if dist < 1: dist = 1
        scale = min(w, h) * 0.45 / dist
        scale = max(0.1, min(scale, 1.0))
        self._o1 = Obj(w/2 + (o1.x-mcx)*scale, h/2 + (o1.y-mcy)*scale, o1.angle)
        self._o2 = Obj(w/2 + (o2.x-mcx)*scale, h/2 + (o2.y-mcy)*scale, o2.angle)
        self.update()

    def paintEvent(self, event):
        if not self._analysis or not self._o1:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Grid
        p.setPen(QPen(C_GRID, 1))
        for x in range(20, self.width(), 20): p.drawLine(x, 0, x, self.height())
        for y in range(20, self.height(), 20): p.drawLine(0, y, self.width(), y)

        o1, o2 = self._o1, self._o2
        # Pass 1: projection lines (behind everything)
        for o, col in [(o1, C_O1), (o2, C_O2)]:
            ux, uy = math.cos(o.angle), math.sin(o.angle)
            _pen = QPen(col, 1.5)
            _pen.setColor(QColor(col.red(), col.green(), col.blue(), 70))
            p.setPen(_pen)
            p.drawLine(int(o.x-ux*160), int(o.y-uy*160),
                       int(o.x+ux*160), int(o.y+uy*160))
        # Pass 2: handles, arrows, circles, labels, overlay
        self._draw_obj(p, o1, C_O1, "1", 160)
        self._draw_obj(p, o2, C_O2, "2", 160)
        self._draw_overlay(p, o1, o2)
        p.end()

    def _draw_obj(self, p, o, color, label, _L):
        ux, uy = math.cos(o.angle), math.sin(o.angle)
        _draw_arrow(p, o.x, o.y, o.x+ux*32, o.y+uy*32, color, 2.0, 8)
        p.setBrush(QBrush(color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(o.x-6), int(o.y-6), 12, 12)
        p.setPen(QPen(color))
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        p.drawText(int(o.x+8), int(o.y-8), label)

    def _draw_overlay(self, p, o1, o2):
        # v: O2→O1
        vang = math.atan2(o1.y-o2.y, o1.x-o2.x)
        pen_v = QPen(C_V, 1.6, Qt.PenStyle.DashLine)
        p.setPen(pen_v)
        p.drawLine(int(o2.x), int(o2.y), int(o1.x), int(o1.y))
        _draw_arrow(p, o2.x, o2.y, o1.x, o1.y, C_V, 1.6, 7)
        p.setPen(QPen(C_V))
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        p.drawText(int((o1.x+o2.x)/2+5), int((o1.y+o2.y)/2-4), "v")

        # θ arc at O2
        rA = 26
        u2ang = o2.angle
        self._draw_arc_label(p, o2.x, o2.y, rA, u2ang, vang,
                              C_THETA, f"\u03b8={math.degrees(self._analysis.theta):.0f}\u00b0")

        # φ arc at O1 + extension of v
        rB = 32
        vFromO1 = math.atan2(o1.y-o2.y, o1.x-o2.x)
        vExtX = o1.x + (rB+12)*math.cos(vFromO1)
        vExtY = o1.y + (rB+12)*math.sin(vFromO1)
        pen_ext = QPen(C_V, 1.2, Qt.PenStyle.DashLine)
        p.setPen(pen_ext)
        p.drawLine(int(o1.x), int(o1.y), int(vExtX), int(vExtY))
        u1ang = o1.angle
        self._draw_arc_label(p, o1.x, o1.y, rB, u1ang, vFromO1,
                              C_PHI, f"\u03c6={math.degrees(self._analysis.phi):.0f}\u00b0")

        # C12 — draw for X (one crossing point) and OVL (both object origins)
        family = self._analysis.family.name
        if family in ('X', 'OVL_SAME', 'OVL_OPP'):
            w = self.width() if self.width() > 0 else 600
            h = self.height() if self.height() > 0 else 400
            pts = _draw_ix_pts(o1.x, o1.y, o1.angle, o2.x, o2.y, o2.angle, w, h)
            is_ovl = len(pts) == 2
            for i, (cx, cy) in enumerate(pts):
                p.setBrush(QBrush(C_C12)); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(int(cx-5), int(cy-5), 10, 10)
                p.setBrush(QBrush(QColor("white"))); p.drawEllipse(int(cx-3), int(cy-3), 6, 6)
                p.setPen(QPen(C_C12))
                p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                label = "C₁₂" if i == 0 else "C₁₂′"
                # OVL: dot is at object origin; object label is at (+10,-10).
                # Place C label directly below the dot (+0,+18) — always clear.
                # X:   dot is a crossing point away from objects; use right offset.
                if is_ovl:
                    p.drawText(int(cx - 3), int(cy + 18), label)
                else:
                    p.drawText(int(cx+6), int(cy-3), label)

    def _draw_arc_label(self, p, cx, cy, r, a1, a2, color, text):
        # Draw arc
        p.setPen(QPen(color, 2.0))
        rect = QRect(int(cx-r), int(cy-r), 2*r, 2*r)
        startDeg = int(-math.degrees(a1)) * 16
        diff = a1 - a2
        while diff > math.pi:  diff -= 2*math.pi
        while diff < -math.pi: diff += 2*math.pi
        spanDeg = int(math.degrees(diff)) * 16
        p.drawArc(rect, startDeg, spanDeg)

        # Label with white background pill
        midA = a1 - diff/2
        lx = int(cx + (r+11)*math.cos(midA))
        ly = int(cy + (r+11)*math.sin(midA))
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(text)
        th = fm.ascent()
        pad = 3
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(lx-pad, ly-th, tw+2*pad, th+pad+1, 3, 3)
        p.setPen(QPen(color.darker()))
        p.drawText(lx, ly, text)


# ── Signature table (right panel bottom) ─────────────────────────────────────

class SignatureTable(QWidget):
    """Displays the 5 signature quantities and the identified relation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis: Optional[PairAnalysis] = None
        self.setMinimumHeight(200)
        self.setStyleSheet(f"background-color: {PANEL_BG};")

    def update_data(self, analysis: PairAnalysis):
        self._analysis = analysis
        self.update()

    def paintEvent(self, event):
        if not self._analysis:
            return
        from .rules_table_panel import pretty_br, pretty_br as _pbr
        a = self._analysis
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = self.width()
        y = 10

        def row_bg(i): return QColor(0xF5F7FA) if i % 2 == 0 else QColor(0xFFFFFF)
        def chip(bg): return QColor(bg)

        # Relation — pretty notation
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        p.setPen(QPen(QColor(ACCENT_DARK)))
        p.drawText(10, y+14, "R\u2081\u2082 =")
        br_display = _pbr(a.br) if a.br else "—"
        p.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        p.setPen(QPen(QColor(ACCENT)))
        br = a.br or "—"
        if p.fontMetrics().horizontalAdvance(br_display) > w - 55:
            mid = len(br_display) // 2
            p.drawText(50, y+14, br_display[:mid])
            p.drawText(58, y+28, br_display[mid:])
            y += 14
        else:
            p.drawText(50, y+14, br_display)
        y += 22

        # Classification status: keep only the forced-overlap notice in the
        # side panel. Ambiguity/no-match and nearest-relation messages are
        # intentionally hidden to avoid redundant noise in normal use.
        if getattr(a, "forced_ovl", False):
            p.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            p.setPen(QPen(QColor(0x0D6832)))
            p.drawText(10, y+11, "Status: broad double-zero cross → forced OVL")
            y += 14

        # Compact form
        br = a.br or ""
        canon = pretty_br(br)
        if canon:
            p.end()
            p = None
            # Use a temporary QTextDocument to render the HTML canonical label
            from PyQt6.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Arial", 11))
            doc.setHtml(
                f"<span style='font-size:12pt;color:{ACCENT};font-weight:bold;'>{canon}</span>"
            )
            doc.setTextWidth(w - 16)
            p2 = QPainter(self)
            p2.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            p2.translate(10, y)
            doc.drawContents(p2)
            p2.end()
            y += int(doc.size().height()) + 4
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Tuples
        tuples = get_instantiated(a.br) if a.br else []
        p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor(ACCENT_DARK)))
        p.drawText(10, y+12, "Instantiated representation(s):")
        y += 15
        for i, tup in enumerate(tuples):
            p.setFont(QFont("Courier New", 9))
            p.fillRect(6, y, w-12, 14, QColor(0xEEF4FF) if i%2==0 else QColor(0xF5F7FA))
            p.setPen(QPen(QColor(ACCENT_DARK)))
            p.drawText(10, y+11, _pbr(str(tup)))
            y += 14
        y += 4

        # Separator
        p.setPen(QPen(QColor(BORDER)))
        p.drawLine(8, y, w-8, y)
        y += 6

        # 5 signature rows
        def sign_color(s: Sign) -> QColor:
            if s == Sign.POS:  return C_POS
            if s == Sign.NEG:  return C_NEG
            return C_ZERO

        def ang_color(rad: float) -> QColor:
            d = math.degrees(rad)
            if abs(d-90) < 3: return C_ZERO
            return C_POS if d < 90 else C_NEG

        def sum_color(s: float) -> QColor:
            d = math.degrees(s)
            if abs(d-180) < 3: return C_ZERO
            return C_POS if d < 180 else C_NEG

        rows = [
            ("sign(u\u2082\u00d7v)", _sign_label(a.sig_u2xv), sign_color(a.sig_u2xv)),
            ("sign(u\u2081\u00d7v)", _sign_label(a.sig_u1xv), sign_color(a.sig_u1xv)),
            (f"\u03b8 = \u2220(u\u2082,v)", f"{math.degrees(a.theta):.1f}\u00b0", ang_color(a.theta)),
            (f"\u03c6 = \u2220(u\u2081,v)", f"{math.degrees(a.phi):.1f}\u00b0", ang_color(a.phi)),
            (f"\u03b8+\u03c6", f"{math.degrees(a.sum):.1f}\u00b0", sum_color(a.sum)),
        ]
        rh = 20
        col2 = w - 100
        for i, (sym, val, bg) in enumerate(rows):
            p.fillRect(6, y, w-12, rh-1, row_bg(i))
            p.fillRect(col2, y+3, 90, rh-7, bg)
            p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            p.setPen(QPen(QColor(TEXT_MAIN)))
            p.drawText(10, y+14, sym)
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            fm = p.fontMetrics()
            vw = fm.horizontalAdvance(val)
            p.drawText(col2 + (90-vw)//2, y+14, val)
            y += rh

        cmp_sym = "<" if a.cmp < 0 else ">" if a.cmp > 0 else "="
        p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor(TEXT_MAIN)))
        p.drawText(10, y+14, f"\u03b8 {cmp_sym} \u03c6")
        y += 20

        # Scalars
        p.setPen(QPen(QColor(BORDER)))
        p.drawLine(8, y, w-8, y)
        y += 6
        p.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor(ACCENT_DARK)))
        p.drawText(10, y+12, "Vector & dot products")
        y += 16
        scalars = [
            ("u\u2081\u00d7u\u2082", f"{a.u1xu2:.4f}"),
            ("u\u2082\u00d7v",        f"{a.u2xv:.4f}"),
            ("u\u2081\u00d7v",        f"{a.u1xv:.4f}"),
            ("u\u2081\u00b7u\u2082",  f"{a.u1du2:.4f}"),
            ("u\u2082\u00b7v",        f"{a.u2dv:.4f}"),
            ("u\u2081\u00b7v",        f"{a.u1dv:.4f}"),
        ]
        srh = 16
        for i, (sym, val) in enumerate(scalars):
            p.fillRect(6, y, w-12, srh-1, row_bg(i))
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QPen(QColor(ACCENT_DARK)))
            p.drawText(10, y+12, sym)
            p.setFont(QFont("Courier New", 9))
            p.setPen(QPen(QColor(TEXT_MAIN)))
            p.drawText(70, y+12, val)
            y += srh

        self.setMinimumHeight(y+12)


def _sign_label(s: Sign) -> str:
    if s == Sign.POS:  return "+ (>0)"
    if s == Sign.NEG:  return "− (<0)"
    return "0 (≈0)"


# ── Main panel ────────────────────────────────────────────────────────────────



# ── Converse Readout Panel ────────────────────────────────────────────────────

class ConverseReadoutPanel(QWidget):
    """
    Right-panel for the Converse sub-tab.

    It intentionally avoids a second angular/vectorial analysis. The goal is
    to illustrate the idea of converse with the minimum necessary information:
      - the scene shown on the left,
      - the same scene after swapping the roles of O₁ and O₂,
      - the relation identified on the left,
      - and the converse of that relation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        v_split = QSplitter(Qt.Orientation.Vertical)
        v_split.setHandleWidth(5)

        # ── TOP: converse diagram ─────────────────────────────────────────────
        diag_w = QWidget()
        diag_w.setStyleSheet(f"background: white; border: 1px solid {BORDER};")
        dl = QVBoxLayout(diag_w)
        dl.setContentsMargins(0, 0, 0, 0)
        hdr = QLabel("  Converse view  —  same scene after swapping O₁ and O₂")
        hdr.setFont(font_label_bold())
        hdr.setStyleSheet(f"color: {ACCENT_DARK}; background: {CONFIG_BAR}; padding: 4px;")
        dl.addWidget(hdr)
        self._conv_diagram = ConverseReadoutDiagram()
        dl.addWidget(self._conv_diagram, 1)
        v_split.addWidget(diag_w)

        # ── BOTTOM: horizontal split — current relation (left) | table converse (right) ──
        bottom_w = QWidget()
        bottom_w.setStyleSheet(f"background: {BG};")
        bl = QVBoxLayout(bottom_w)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        bottom_hdr = QLabel("  Converse readout  —  R(O₁, O₂) on the left  |  R(O₂, O₁) on the right")
        bottom_hdr.setFont(font_label_bold())
        bottom_hdr.setStyleSheet(f"color: {ACCENT_DARK}; background: {CONFIG_BAR}; padding: 4px;")
        bl.addWidget(bottom_hdr)

        h_info = QSplitter(Qt.Orientation.Horizontal)
        h_info.setHandleWidth(4)

        # Left: current relation info
        self._browser_cur = QTextBrowser()
        self._browser_cur.setReadOnly(True)
        self._browser_cur.setOpenLinks(False)
        self._browser_cur.setStyleSheet(f"border: 1px solid {BORDER}; background: white;")
        h_info.addWidget(self._browser_cur)

        # Right: converse info + verification badge
        self._browser_conv = QTextBrowser()
        self._browser_conv.setReadOnly(True)
        self._browser_conv.setOpenLinks(False)
        self._browser_conv.setStyleSheet(f"border: 1px solid {BORDER}; background: white;")
        h_info.addWidget(self._browser_conv)

        h_info.setSizes([1, 1])
        bl.addWidget(h_info, 1)
        v_split.addWidget(bottom_w)

        v_split.setSizes([280, 220])
        lay.addWidget(v_split, 1)

    def update_data(self, analysis: PairAnalysis, o1: Obj, o2: Obj) -> None:
        if analysis is None:
            return
        self._o1 = o1
        self._o2 = o2
        self._conv_diagram.update_data(analysis, o1, o2)
        self._rebuild_table(analysis, o1, o2)

    def _rebuild_table(self, a: PairAnalysis, o1: Obj, o2: Obj) -> None:
        from qrpc.converse import converse as _conv_fn
        from .rules_table_panel import pretty_br
        import html as _html

        current_br = (a.br if hasattr(a, 'br') else '?') or '?'

        table_conv_nc = _conv_fn(current_br) or '?'

        def card_html(title: str, body: str) -> str:
            return (
                f"<html><body style='font-family:Arial,sans-serif;font-size:10pt;"
                f"margin:0;background:white;'>"
                f"<div style='font-weight:bold;color:{ACCENT_DARK};font-size:10pt;"
                f"padding:4px 6px 3px 6px;border-bottom:1px solid #DDE4EE;"
                f"background:#EEF2F7;'>{title}</div>"
                f"<div style='padding:8px 10px;line-height:1.45;'>{body}</div>"
                f"</body></html>"
            )

        self._browser_cur.setHtml(card_html(
            "R(O\u2081, O\u2082)",
            (
                f"<div style='font-family:monospace;'>"
                f"{_html.escape(pretty_br(current_br))}"
                f"</div>"
            )
        ))

        self._browser_conv.setHtml(card_html(
            "R(O\u2082, O\u2081)  \u2014  converse",
            (
                f"<div style='font-family:monospace;'>"
                f"{_html.escape(pretty_br(table_conv_nc))}"
                f"</div>"
            )
        ))



class ConverseReadoutDiagram(ReadoutDiagram):
    """Displays the same scene after swapping the roles of O₁ and O₂."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def update_data(self, analysis: PairAnalysis, o1: Obj, o2: Obj):
        """Swaps O1 and O2 for the converse display."""
        super().update_data(analysis, o2, o1)

    def _draw_overlay(self, p, o1_swapped, o2_swapped):
        """Draw only the swapped-role cue, without angular labels or vector v."""
        family = self._analysis.family.name if self._analysis else None
        if family in ('X', 'OVL_SAME', 'OVL_OPP'):
            w = self.width() if self.width() > 0 else 600
            h = self.height() if self.height() > 0 else 400
            pts = _draw_ix_pts(o1_swapped.x, o1_swapped.y, o1_swapped.angle,
                               o2_swapped.x, o2_swapped.y, o2_swapped.angle, w, h)
            is_ovl = len(pts) == 2
            for i, (cx, cy) in enumerate(pts):
                p.setBrush(QBrush(C_C12)); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(int(cx-5), int(cy-5), 10, 10)
                p.setBrush(QBrush(QColor("white"))); p.drawEllipse(int(cx-3), int(cy-3), 6, 6)
                p.setPen(QPen(C_C12))
                label = "C₁₂" if i == 0 else "C₁₂′"
                # OVL: dot is at object origin; object label is at (+10,-10).
                # Place C label directly below the dot (+0,+18) — always clear.
                # X:   dot is a crossing point away from objects; use right offset.
                if is_ovl:
                    p.drawText(int(cx - 3), int(cy + 18), label)
                else:
                    p.drawText(int(cx+6), int(cy-3), label)


# ── Module-level helper: separator label ──────────────────────────────────────

def _sep_label() -> QLabel:
    s = QLabel("│")
    s.setStyleSheet(f"color: {BORDER_DARK}; font-size: 16pt;")
    return s


class _SharedGeomState:
    """
    Holds the two Obj instances shared between RelationsPanel and ConversePanel.
    Moving an object in either panel notifies the other immediately.
    """
    def __init__(self):
        self.o1 = Obj(180, 220, math.radians(15))
        self.o2 = Obj(430, 180, math.radians(110))
        self._listeners: list = []

    def add_listener(self, fn):
        self._listeners.append(fn)

    def notify(self):
        for fn in self._listeners:
            fn()


# ── RelationsPanel ────────────────────────────────────────────────────────────

class RelationsPanel(QWidget):
    """
    Stand-alone top-level 'Relations' tab.
    Same layout and behaviour as the original Relation sub-tab.
    Shares Obj state with ConversePanel via _SharedGeomState.
    """

    def __init__(self, state: _SharedGeomState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setStyleSheet(f"background-color: {BG};")
        self._current: Optional[PairAnalysis] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_config_bar())

        self._canvas = DrawCanvas()
        self._canvas.o1 = state.o1
        self._canvas.o2 = state.o2
        self._canvas.snap_parallel = True
        self._canvas.snap_colinear = True
        self._canvas.on_changed = self._on_canvas_changed

        h_split = QSplitter(Qt.Orientation.Horizontal)
        h_split.setHandleWidth(6)
        h_split.addWidget(self._canvas)

        v_split = QSplitter(Qt.Orientation.Vertical)
        v_split.setHandleWidth(5)

        diag_w = QWidget()
        diag_w.setStyleSheet(f"background: white; border: 1px solid {BORDER};")
        dl = QVBoxLayout(diag_w)
        dl.setContentsMargins(0, 0, 0, 0)
        dt = QLabel("  Geometric signature diagram")
        dt.setFont(font_label_bold())
        dt.setStyleSheet(f"color: {ACCENT_DARK}; background: {CONFIG_BAR}; padding: 4px;")
        dl.addWidget(dt)
        self._diagram = ReadoutDiagram()
        dl.addWidget(self._diagram, 1)
        v_split.addWidget(diag_w)

        sig_w = QWidget()
        sig_w.setStyleSheet(f"background: white; border: 1px solid {BORDER};")
        sl = QVBoxLayout(sig_w)
        sl.setContentsMargins(0, 0, 0, 0)
        st = QLabel("  Basic relation (canonical form)")
        st.setFont(font_label_bold())
        st.setStyleSheet(f"color: {ACCENT_DARK}; background: {CONFIG_BAR}; padding: 4px;")
        sl.addWidget(st)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._sig_table = SignatureTable()
        scroll.setWidget(self._sig_table)
        sl.addWidget(scroll, 1)
        v_split.addWidget(sig_w)

        v_split.setSizes([280, 300])
        h_split.addWidget(v_split)
        h_split.setStretchFactor(0, 2)
        h_split.setStretchFactor(1, 1)
        h_split.setSizes([700, 320])
        root.addWidget(h_split, 1)

        state.add_listener(self._on_external_change)
        self._update_analysis()

    def _build_config_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background-color: {CONFIG_BAR}; "
            f"border-bottom: 1px solid {BORDER_DARK};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        chk_par = QCheckBox("Snap parallel/opposite")
        chk_par.setChecked(True)
        chk_par.setFont(font_label())
        chk_par.toggled.connect(lambda v: setattr(self._canvas, 'snap_parallel', v))

        chk_col = QCheckBox("Snap to overlap")
        chk_col.setChecked(True)
        chk_col.setFont(font_label())
        chk_col.toggled.connect(lambda v: setattr(self._canvas, 'snap_colinear', v))

        lay.addWidget(chk_par)
        lay.addWidget(chk_col)
        lay.addWidget(_sep_label())

        btn_reset = make_button("Reset")
        btn_reset.setToolTip("Reset both objects to their default positions and orientations")
        btn_reset.setFixedHeight(30)
        btn_reset.clicked.connect(self._reset)
        lay.addWidget(btn_reset)
        lay.addWidget(make_help_button(SEC_GEOMETRY))

        btn_table = make_button("Relation table")
        btn_table.setToolTip("Open the full 48-relation reference table")
        btn_table.setFixedHeight(30)
        btn_table.clicked.connect(lambda: _show_relation_table(self._current, self))
        lay.addWidget(btn_table)

        lay.addStretch()
        return bar

    def _reset(self):
        self._state.o1.x = 180; self._state.o1.y = 220
        self._state.o1.angle = math.radians(15)
        self._state.o2.x = 430; self._state.o2.y = 180
        self._state.o2.angle = math.radians(110)
        self._canvas.o1 = self._state.o1
        self._canvas.o2 = self._state.o2
        self._canvas._clamp()
        self._on_canvas_changed()

    def _on_canvas_changed(self):
        self._state.o1 = self._canvas.o1
        self._state.o2 = self._canvas.o2
        self._update_analysis()
        # _update_analysis may trigger a real forced-OVL snap on the canvas.
        # Keep the shared state synchronized with the final, snapped geometry.
        self._state.o1 = self._canvas.o1
        self._state.o2 = self._canvas.o2
        self._state.notify()

    def _on_external_change(self):
        self._canvas.o1 = self._state.o1
        self._canvas.o2 = self._state.o2
        self._update_analysis()
        self._canvas.update()

    def _update_analysis(self):
        o1, o2 = self._canvas.o1, self._canvas.o2
        self._current = analyze(o1, o2)

        # Real forced-OVL trigger: if the mathematical state says that both
        # products are practically zero, snap the canvas itself and reanalyse so
        # the right panel and the editor show the same geometry.
        if (self._canvas.snap_colinear and
                getattr(self._current, "forced_ovl", False)):
            # Force the canvas first, then always recompute the analysis from
            # the final snapped geometry.  The forced-OVL trigger may be reached
            # from a near-frontier state whose angular values still belong to
            # the pre-snap geometry; matching must use the post-overlap values.
            self._canvas._force_overlap_from_analysis(self._current)
            o1, o2 = self._canvas.o1, self._canvas.o2
            self._current = analyze(o1, o2)

        self._diagram.update_data(self._current, o1, o2)
        self._sig_table.update_data(self._current)
        self._canvas.update()


# ── ConversePanel ─────────────────────────────────────────────────────────────

class ConversePanel(QWidget):
    """
    Stand-alone top-level 'Converse' tab.
    Same layout and behaviour as the original Converse sub-tab.
    Shares Obj state with RelationsPanel via _SharedGeomState.
    """

    def __init__(self, state: _SharedGeomState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setStyleSheet(f"background-color: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_config_bar())

        self._canvas = DrawCanvas()
        self._canvas.o1 = state.o1
        self._canvas.o2 = state.o2
        self._canvas.snap_parallel = True
        self._canvas.snap_colinear = True
        self._canvas.on_changed = self._on_canvas_changed

        conv_h_split = QSplitter(Qt.Orientation.Horizontal)
        conv_h_split.setHandleWidth(6)
        conv_h_split.addWidget(self._canvas)

        self._converse_readout = ConverseReadoutPanel()
        conv_h_split.addWidget(self._converse_readout)
        conv_h_split.setStretchFactor(0, 2)
        conv_h_split.setStretchFactor(1, 1)
        conv_h_split.setSizes([700, 320])
        root.addWidget(conv_h_split, 1)

        state.add_listener(self._on_external_change)
        self._update_analysis()

    def _build_config_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background-color: {CONFIG_BAR}; "
            f"border-bottom: 1px solid {BORDER_DARK};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        chk_par = QCheckBox("Snap parallel/opposite")
        chk_par.setChecked(True)
        chk_par.setFont(font_label())
        chk_par.toggled.connect(lambda v: setattr(self._canvas, 'snap_parallel', v))

        chk_col = QCheckBox("Snap to overlap")
        chk_col.setChecked(True)
        chk_col.setFont(font_label())
        chk_col.toggled.connect(lambda v: setattr(self._canvas, 'snap_colinear', v))

        lay.addWidget(chk_par)
        lay.addWidget(chk_col)
        lay.addWidget(_sep_label())

        btn_reset = make_button("Reset")
        btn_reset.setToolTip("Reset both objects to their default positions and orientations")
        btn_reset.setFixedHeight(30)
        btn_reset.clicked.connect(self._reset)
        lay.addWidget(btn_reset)
        lay.addWidget(make_help_button(SEC_CONVERSE))

        lay.addStretch()
        return bar

    def _reset(self):
        self._state.o1.x = 180; self._state.o1.y = 220
        self._state.o1.angle = math.radians(15)
        self._state.o2.x = 430; self._state.o2.y = 180
        self._state.o2.angle = math.radians(110)
        self._canvas.o1 = self._state.o1
        self._canvas.o2 = self._state.o2
        self._canvas._clamp()
        self._on_canvas_changed()

    def _on_canvas_changed(self):
        self._state.o1 = self._canvas.o1
        self._state.o2 = self._canvas.o2
        self._update_analysis()
        # _update_analysis may trigger a real forced-OVL snap on the canvas.
        # Keep the shared state synchronized with the final, snapped geometry.
        self._state.o1 = self._canvas.o1
        self._state.o2 = self._canvas.o2
        self._state.notify()

    def _on_external_change(self):
        self._canvas.o1 = self._state.o1
        self._canvas.o2 = self._state.o2
        self._update_analysis()
        self._canvas.update()

    def _update_analysis(self):
        o1, o2 = self._canvas.o1, self._canvas.o2
        current = analyze(o1, o2)
        if (self._canvas.snap_colinear and
                getattr(current, "forced_ovl", False)):
            # Same rule as in RelationsPanel: after a forced overlap, display
            # and match only against the final snapped geometry.
            self._canvas._force_overlap_from_analysis(current)
            o1, o2 = self._canvas.o1, self._canvas.o2
            current = analyze(o1, o2)
        self._converse_readout.update_data(current, o1, o2)
        self._canvas.update()
