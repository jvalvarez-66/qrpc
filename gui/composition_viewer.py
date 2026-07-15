"""
composition_viewer.py
---------------------
Interactive geometric viewer for QRPC composition.

Three oriented objects O1 (blue), O2 (red — pivot), O3 (purple).

Canvas style and interaction are identical to DrawCanvas in geometry_panel.py:
  - Long semi-transparent projection lines (L=520, alpha 70)
  - Rotation handles: two thick semi-transparent arm segments (alpha 135)
  - Short direction arrow with arrowhead
  - Filled circle at origin (r=8), label in object colour outside the circle
  - Hit on circle  (r < 18)              → translate
  - Hit on arm segment (24<|along|<120)  → rotate (atan2 to mouse)
  - Mouse wheel near object              → rotate 2°/notch
  - Snap parallel/overlap checkboxes
  - Clamp to canvas bounds

Overlays:
  - Intersection points C12 (green), C23 (amber), C13 (dark red):
    ring-dot (filled outer + white inner) + label — drawn ONCE each
  - Topological partition ticks on P1: thin perpendicular lines at
    -inf, C12, +inf  (tick only, no C12 label — avoids duplication)

Right panel: vertical splitter with two scrollable QTextEdit sub-panels
  1. Input relations     — R₁₂ and R₂₃
  2. Composition result  — full list of BRs in R12 ∘ R23
  3. C12C23 analysis     — current ordering + admissible configurations (§4.3)
"""

from __future__ import annotations
import math
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QScrollArea, QFrame,
    QLabel, QCheckBox, QTextEdit, QComboBox, QListView, QSizePolicy,
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPolygon, QCursor,
)

from .geometry_classifier import Obj, analyze, normalize_angle, distance_to_line
from .rules_table_panel import pretty_br
from .help_dialog import make_help_button, SEC_COMPOSITION_VIEWER
from .theme import (
    make_button,
    font_label, font_label_bold, font_mono,
    BG, ACCENT_DARK, BORDER, BORDER_DARK,
    CONFIG_BAR, TEXT_MAIN, SUCCESS, SUCCESS_BG,
    WARN_BG, ERROR_COL, ERROR_BG,
)

# ── Colours — identical to geometry_panel.py ─────────────────────────────────
_C_O1  = QColor(0x2C4F9E)
_C_O2  = QColor(0xC0392B)
_C_O3  = QColor(0x6A0DAD)
_C_GRID= QColor(0xEEF2F7)
_C_C12 = QColor(0x0D6832)
_C_C23 = QColor(0xCC5500)
_C_C13 = QColor(0x8B0000)
_PROJ_L = 520  # same as DrawCanvas


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _dist(x1, y1, x2, y2): return math.hypot(x1-x2, y1-y2)

def _intersect(ox1,oy1,a1,ox2,oy2,a2):
    ux1,uy1=math.cos(a1),math.sin(a1); ux2,uy2=math.cos(a2),math.sin(a2)
    det=ux1*uy2-uy1*ux2
    if abs(det)<1e-9: return None
    dx,dy=ox2-ox1,oy2-oy1; t=(dx*uy2-dy*ux2)/det
    return ox1+t*ux1, oy1+t*uy1

def _smart_intersect(ox1,oy1,a1,ox2,oy2,a2,canvas_w,canvas_h):
    """
    Return a list of intersection points to draw for the pair (P1, P2):

    - X-type (crossing): one point where the lines cross, only if within canvas.
    - OVL (colinear + nearly parallel): two points — both object origins, since
      both lie on the shared support line. Detected by the same criteria as
      analyze(): angle diff < ANGLE_EPS AND O2 within COLINEAR_EPS of P1.
    - PAR (parallel, not colinear): empty list — lines never intersect.
    - Near-parallel crossing off-canvas: empty list.
    """
    from gui.geometry_classifier import distance_to_line, COLINEAR_EPS, ANGLE_EPS
    ux1,uy1=math.cos(a1),math.sin(a1)
    # OVL / PAR check: nearly parallel
    angle_diff = abs(a1 - a2) % math.pi
    if angle_diff > math.pi / 2:
        angle_diff = math.pi - angle_diff
    if angle_diff < ANGLE_EPS:
        if distance_to_line(ox2,oy2,ox1,oy1,ux1,uy1) < COLINEAR_EPS:
            return [(ox1,oy1),(ox2,oy2)]   # OVL: both origins
        return []                           # PAR: no intersection
    # Normal crossing
    ux2,uy2=math.cos(a2),math.sin(a2)
    det=ux1*uy2-uy1*ux2
    if abs(det)<1e-9: return []
    dx,dy=ox2-ox1,oy2-oy1; t=(dx*uy2-dy*ux2)/det
    cx,cy=ox1+t*ux1,oy1+t*uy1
    margin=200.0
    if cx<-margin or cx>canvas_w+margin or cy<-margin or cy>canvas_h+margin:
        return []
    return [(cx,cy)]

def _proj_t(ox,oy,a,px,py):
    ux,uy=math.cos(a),math.sin(a); return ux*(px-ox)+uy*(py-oy)

def _arrow(p,x1,y1,x2,y2,col,w=3.0,sz=11):
    p.setPen(QPen(col,w)); p.drawLine(int(x1),int(y1),int(x2),int(y2))
    a=math.atan2(y2-y1,x2-x1)
    p.setBrush(QBrush(col)); p.setPen(Qt.PenStyle.NoPen)
    pts=[QPoint(int(x2),int(y2)),
         QPoint(int(x2-sz*math.cos(a-0.4)),int(y2-sz*math.sin(a-0.4))),
         QPoint(int(x2-sz*math.cos(a+0.4)),int(y2-sz*math.sin(a+0.4)))]
    p.drawPolygon(QPolygon(pts))

def _c12c23_rel(o1,o2,o3):
    c12=_intersect(o1.x,o1.y,o1.angle,o2.x,o2.y,o2.angle)
    c23=_intersect(o2.x,o2.y,o2.angle,o3.x,o3.y,o3.angle)
    if c12 is None or c23 is None: return None
    t12=_proj_t(o2.x,o2.y,o2.angle,c12[0],c12[1])
    t23=_proj_t(o2.x,o2.y,o2.angle,c23[0],c23[1])
    if abs(t12-t23)<3: return "0"
    return "+" if t12>t23 else "−"

def _n_configs(r12,r23):
    def _x(br_): return br_.startswith("<X,")
    def _f(br,i):
        try: return br.strip("<>").split(",")[i].strip()
        except: return ""
    if not(_x(r12) and _x(r23)): return 1
    a,b,c,d=_f(r12,1),_f(r12,2),_f(r23,1),_f(r23,2)
    ok=all(v not in("ZERO","_","") for v in [a,b,c,d])
    return 3 if (ok and b==c) else 1


# ── Canvas ────────────────────────────────────────────────────────────────────

CANVAS_W = 1200   # virtual canvas width  — larger than any visible area
CANVAS_H = 900    # virtual canvas height


class _TriCanvas(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.setStyleSheet("background-color:white;border:1px solid #B0BEC5;")
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.o1=Obj(160,260,math.radians(20))
        self.o2=Obj(310,130,math.radians(115))
        self.o3=Obj(460,260,math.radians(200))
        self.snap_parallel=True; self.snap_colinear=True
        self._drag=None; self._rot=None; self._drag_ix=None
        self._dx=0.0; self._dy=0.0
        self.on_changed=None

    def paintEvent(self,ev):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # grid
        p.setPen(QPen(_C_GRID,1))
        for x in range(40,self.width(),40): p.drawLine(x,0,x,self.height())
        for y in range(40,self.height(),40): p.drawLine(0,y,self.width(),y)
        # Pass 1: projection lines (drawn first, behind everything)
        self._proj_line(p,self.o1,_C_O1)
        self._proj_line(p,self.o2,_C_O2)
        self._proj_line(p,self.o3,_C_O3)
        # partition ticks on P1 (no label)
        self._ticks(p)
        # Pass 2: handles, arrows, circles, labels
        self._obj(p,self.o1,_C_O1,"1")
        self._obj(p,self.o2,_C_O2,"2")
        self._obj(p,self.o3,_C_O3,"3")
        # Pass 3: intersection points (always on top)
        self._ixpts(p)
        p.end()

    def _proj_line(self,p,o,col):
        """Draw only the projection line (called first so it stays behind objects)."""
        ux,uy=math.cos(o.angle),math.sin(o.angle)
        lc=QColor(col.red(),col.green(),col.blue(),70)
        p.setPen(QPen(lc,2.0))
        p.drawLine(int(o.x-ux*_PROJ_L),int(o.y-uy*_PROJ_L),
                   int(o.x+ux*_PROJ_L),int(o.y+uy*_PROJ_L))

    def _obj(self,p,o,col,lbl):
        ux,uy=math.cos(o.angle),math.sin(o.angle)
        # rotation handles (projection line drawn separately in pass 1)
        hc=QColor(col.red(),col.green(),col.blue(),135)
        pen2=QPen(hc,4.5); pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawLine(int(o.x+ux*30),int(o.y+uy*30),int(o.x+ux*95),int(o.y+uy*95))
        p.drawLine(int(o.x-ux*30),int(o.y-uy*30),int(o.x-ux*95),int(o.y-uy*95))
        # direction arrow (length 45)
        _arrow(p,o.x,o.y,o.x+ux*45,o.y+uy*45,col,3.0)
        # origin circle r=8
        p.setBrush(QBrush(col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(o.x-8),int(o.y-8),16,16)
        # label
        p.setPen(QPen(col)); p.setFont(QFont("Arial",11,QFont.Weight.Bold))
        p.drawText(int(o.x+10),int(o.y-10),lbl)

    def _ticks(self,p):
        o1=self.o1; ux,uy=math.cos(o1.angle),math.sin(o1.angle)
        nx,ny=-uy,ux; tk=7
        L=max(self.width(),self.height())*1.4
        tc=QColor(_C_O1.red(),_C_O1.green(),_C_O1.blue(),140)
        p.setPen(QPen(tc,1.5))
        bx,by=o1.x-ux*L,o1.y-uy*L
        p.drawLine(int(bx-nx*tk),int(by-ny*tk),int(bx+nx*tk),int(by+ny*tk))
        fx,fy=o1.x+ux*L,o1.y+uy*L
        p.drawLine(int(fx-nx*tk),int(fy-ny*tk),int(fx+nx*tk),int(fy+ny*tk))
        c12=_intersect(o1.x,o1.y,o1.angle,self.o2.x,self.o2.y,self.o2.angle)
        if c12:
            gc=QColor(_C_C12.red(),_C_C12.green(),_C_C12.blue(),180)
            p.setPen(QPen(gc,2)); t2=int(tk*1.6)
            cx,cy=c12
            p.drawLine(int(cx-nx*t2),int(cy-ny*t2),int(cx+nx*t2),int(cy+ny*t2))

    def _ixpts(self,p):
        w=self.width() if self.width()>0 else CANVAS_W
        h=self.height() if self.height()>0 else CANVAS_H
        for oa,ob,col,lbl in [(self.o1,self.o2,_C_C12,"C₁₂"),
                               (self.o2,self.o3,_C_C23,"C₂₃"),
                               (self.o1,self.o3,_C_C13,"C₁₃")]:
            pts=_smart_intersect(oa.x,oa.y,oa.angle,ob.x,ob.y,ob.angle,w,h)
            for i,pt in enumerate(pts):
                cx,cy=int(pt[0]),int(pt[1])
                p.setBrush(QBrush(col)); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(cx-5,cy-5,10,10)
                p.setBrush(QBrush(QColor("white"))); p.drawEllipse(cx-3,cy-3,6,6)
                p.setPen(QPen(col)); p.setFont(QFont("Arial",9,QFont.Weight.Bold))
                # For OVL (2 points): label first point with the relation name,
                # second point with a prime (′) to indicate the ambiguity
                label = lbl if i == 0 else lbl + "′"
                # OVL: dot is at object origin; object label is always at (+10,-10).
                # Place C label directly below (+0,+18) — always clear.
                # X: dot is a crossing away from objects; use right offset (+7,-4).
                if len(pts) == 2:
                    p.drawText(int(pt[0] - 3), int(pt[1] + 18), label)
                else:
                    p.drawText(int(pt[0]+7), int(pt[1]-4), label)

    def _objs(self): return [self.o1,self.o2,self.o3]

    # ── Intersection-point hit detection ──────────────────────────────────────

    def _ix_pts(self):
        """Return {name: (x,y)} for each defined intersection point.

        OVL intersection points are NOT registered for hit detection because
        they coincide with object origins — registering them would block
        object dragging (intersection check has priority in mousePressEvent).
        """
        w=self.width() if self.width()>0 else CANVAS_W
        h=self.height() if self.height()>0 else CANVAS_H
        pts = {}
        for (oa,ob,key) in [(self.o1,self.o2,'c12'),
                             (self.o2,self.o3,'c23'),
                             (self.o1,self.o3,'c13')]:
            ipts=_smart_intersect(oa.x,oa.y,oa.angle,ob.x,ob.y,ob.angle,w,h)
            if len(ipts) == 1:
                # Normal crossing: register for dragging
                pts[key] = ipts[0]
            # OVL (len==2): dots are at object origins — skip to preserve dragging
        return pts

    def _hit_ix(self, mx, my):
        """Return name of intersection point within 10 px, or None."""
        for name,(px,py) in self._ix_pts().items():
            if _dist(mx,my,px,py) < 10:
                return name
        return None

    # ── Dragging an intersection point ────────────────────────────────────────
    # C12 lies on P1 (O1's line).  Dragging it slides O1 along its own
    # projection direction so that C12 tracks the mouse.
    # Equivalently: project mouse onto P2 (O2's line) to find where C12
    # should land, then back-solve to place O1 on P1 at that intersection.
    # In practice the simplest correct rule is:
    #   "keep O1's angle fixed; move O1's position so that its projection
    #    line passes through the mouse position projected onto P2."
    # Since C12 = P1 ∩ P2, moving the mouse along P2 slides C12 along P2,
    # which in turn translates O1 perpendicularly to P1.
    # Implementation: project mouse onto P2, set that as the new C12 target,
    # then place O1 so that its line passes through that target with its
    # current angle — i.e. translate O1 along the normal to P1 until C12
    # hits the target.

    def _drag_c12(self, mx, my):
        """Slide O1 so that C12 moves to (mx,my) projected onto P2."""
        # Project (mx,my) onto P2
        ux2,uy2=math.cos(self.o2.angle),math.sin(self.o2.angle)
        t=(mx-self.o2.x)*ux2+(my-self.o2.y)*uy2
        tx,ty=self.o2.x+ux2*t, self.o2.y+uy2*t
        # Move O1 along normal to P1 so its line passes through (tx,ty)
        ux1,uy1=math.cos(self.o1.angle),math.sin(self.o1.angle)
        # Normal component from O1 to target
        nx,ny=-uy1,ux1
        dn=(tx-self.o1.x)*nx+(ty-self.o1.y)*ny
        self.o1.x+=nx*dn; self.o1.y+=ny*dn

    def _drag_c23(self, mx, my):
        """Slide O3 so that C23 moves to (mx,my) projected onto P2."""
        ux2,uy2=math.cos(self.o2.angle),math.sin(self.o2.angle)
        t=(mx-self.o2.x)*ux2+(my-self.o2.y)*uy2
        tx,ty=self.o2.x+ux2*t, self.o2.y+uy2*t
        ux3,uy3=math.cos(self.o3.angle),math.sin(self.o3.angle)
        nx,ny=-uy3,ux3
        dn=(tx-self.o3.x)*nx+(ty-self.o3.y)*ny
        self.o3.x+=nx*dn; self.o3.y+=ny*dn

    def _drag_c13(self, mx, my):
        """Slide O1 so that C13 moves to (mx,my) projected onto P3."""
        ux3,uy3=math.cos(self.o3.angle),math.sin(self.o3.angle)
        t=(mx-self.o3.x)*ux3+(my-self.o3.y)*uy3
        tx,ty=self.o3.x+ux3*t, self.o3.y+uy3*t
        ux1,uy1=math.cos(self.o1.angle),math.sin(self.o1.angle)
        nx,ny=-uy1,ux1
        dn=(tx-self.o1.x)*nx+(ty-self.o1.y)*ny
        self.o1.x+=nx*dn; self.o1.y+=ny*dn

    def _hit_rot(self,mx,my):
        for o in self._objs():
            ux,uy=math.cos(o.angle),math.sin(o.angle)
            along=(mx-o.x)*ux+(my-o.y)*uy
            perp=abs((mx-o.x)*uy-(my-o.y)*ux)
            if 24<abs(along)<120 and perp<10: return o
        return None

    def mousePressEvent(self,ev):
        mx,my=ev.position().x(),ev.position().y()
        # Intersection points have priority (smaller hit target, checked first)
        ix = self._hit_ix(mx, my)
        if ix:
            self._drag_ix = ix
            return
        self._drag_ix = None
        for o in self._objs():
            if _dist(mx,my,o.x,o.y)<18:
                self._drag=o; self._dx=mx-o.x; self._dy=my-o.y; return
        self._rot=self._hit_rot(mx,my)

    def mouseMoveEvent(self,ev):
        mx,my=ev.position().x(),ev.position().y()
        if self._drag_ix:
            if   self._drag_ix=='c12': self._drag_c12(mx,my)
            elif self._drag_ix=='c23': self._drag_c23(mx,my)
            elif self._drag_ix=='c13': self._drag_c13(mx,my)
            self._clamp(); self._notify()
        elif self._rot:
            self._rot.angle=normalize_angle(math.atan2(my-self._rot.y,mx-self._rot.x))
            if self.snap_parallel: self._snap_par(self._rot)
            self._clamp(); self._notify()
        elif self._drag:
            self._drag.x=mx-self._dx; self._drag.y=my-self._dy
            if self.snap_colinear: self._snap_col(self._drag)
            self._clamp(); self._notify()

    def mouseReleaseEvent(self,ev): self._drag=None; self._rot=None; self._drag_ix=None

    def wheelEvent(self,ev):
        mx,my=ev.position().x(),ev.position().y()
        d=ev.angleDelta().y()/120
        for o in self._objs():
            if _dist(mx,my,o.x,o.y)<24:
                o.angle=normalize_angle(o.angle-d*math.radians(2))
                if self.snap_parallel: self._snap_par(o)
                self._clamp(); self._notify(); break

    def _snap_par(self,moved):
        for o in self._objs():
            if o is moved: continue
            diff=normalize_angle(o.angle-moved.angle)
            if abs(diff)<math.radians(4): o.angle=moved.angle
            elif abs(abs(diff)-math.pi)<math.radians(4):
                o.angle=normalize_angle(moved.angle+math.pi)

    def _snap_col(self,moving):
        for ref in self._objs():
            if ref is moving: continue
            d=distance_to_line(moving.x,moving.y,ref.x,ref.y,
                               math.cos(ref.angle),math.sin(ref.angle))
            if d<14:
                ux,uy=math.cos(ref.angle),math.sin(ref.angle)
                al=(moving.x-ref.x)*ux+(moving.y-ref.y)*uy
                moving.x=ref.x+ux*al; moving.y=ref.y+uy*al

    def _clamp(self):
        m=22.0
        for o in self._objs():
            o.x=max(m,min(CANVAS_W-m,o.x)); o.y=max(m,min(CANVAS_H-m,o.y))


    def _notify(self):
        self.update()
        if self.on_changed: self.on_changed()


# ── Right panel ───────────────────────────────────────────────────────────────

def _subpanel(title):
    w=QWidget(); w.setStyleSheet("background:white;")
    lay=QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
    hdr=QLabel(f"  {title}"); hdr.setFont(font_label_bold())
    hdr.setStyleSheet(f"color:{ACCENT_DARK};background:{CONFIG_BAR};"
                      f"border-bottom:1px solid {BORDER_DARK};padding:4px 8px;")
    lay.addWidget(hdr)
    te=QTextEdit(); te.setReadOnly(True); te.setFont(font_mono())
    te.setStyleSheet(f"border:none;background:white;padding:6px 8px;color:{TEXT_MAIN};")
    te.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    lay.addWidget(te,1)
    return w,te


class _CompositionReadout(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self._vs=QSplitter(Qt.Orientation.Vertical); self._vs.setHandleWidth(5)
        w1,self._t1=_subpanel("Input relations")
        w2,self._t2=_subpanel("General relation  R₁₂ ∘ R₂₃")
        w4,self._t4=_subpanel("Current configuration and possible ones")
        self._t4.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        w1.setMinimumHeight(100)
        w4.setMinimumHeight(120)
        self._vs.addWidget(w1); self._vs.addWidget(w2); self._vs.addWidget(w4)
        self._vs.setStretchFactor(0, 0)
        self._vs.setStretchFactor(1, 1)
        self._vs.setStretchFactor(2, 0)
        root.addWidget(self._vs,1)

    def update_data(self,o1,o2,o3):
        a12=analyze(o1,o2); a23=analyze(o2,o3)
        r12,r23=a12.br,a23.br

        # panel 1 — input relations
        self._t1.setPlainText(
            f"R₁₂:\n  {pretty_br(r12)}\n\n"
            f"R₂₃:\n  {pretty_br(r23)}")

        # panel 2 — general relation (full set, no R13 here)
        try:
            from . import qrpc_caches as _pc2
            _pc2._build_caches()
            comp=sorted((_pc2._COMPOSE_CACHE or {}).get((r12,r23),frozenset()))
            if comp:
                lines=[f"R₁₂ ∘ R₂₃  →  {len(comp)} basic relation(s):\n"]
                for i,br in enumerate(comp,1):
                    lines.append(f"  {i:2d}.  {pretty_br(br)}")
                self._t2.setPlainText("\n".join(lines))
                self._t2.setStyleSheet(
                    f"border:none;background:{SUCCESS_BG};padding:6px 8px;color:{TEXT_MAIN};")
            else:
                self._t2.setPlainText("∅  — inconsistent composition")
                self._t2.setStyleSheet(
                    f"border:none;background:{ERROR_BG};padding:6px 8px;color:{ERROR_COL};")
        except Exception as e:
            self._t2.setPlainText(f"(error: {e})")
            comp=[]

        # panel 4 — current configuration and possible ones
        rel=_c12c23_rel(o1,o2,o3)
        br=_n_configs(r12,r23)
        lines4=[]
        if rel is None:
            lines4.append("C₁₂C₂₃:  undefined\n(parallel projections)\n")
        else:
            sym={"+":"C₁₂  in front of  C₂₃   (+)",
                 "0":"C₁₂  coincides with  C₂₃  (0)",
                 "−":"C₁₂  behind  C₂₃         (−)"}
            lines4.append(f"Current ordering:\n  {sym.get(rel,rel)}\n")
        if br==3:
            lines4 += [
                "Possible configurations from the composition:  3",
                "  (C₁₂⁺C₂₃),  (C₁₂⁰C₂₃),  (C₁₂⁻C₂₃)",
                "The current layout realises one of these",
                "three admissible configurations.",
            ]
            self._t4.setStyleSheet(
                f"border:none;background:{WARN_BG};padding:6px 8px;color:{TEXT_MAIN};")
        else:
            lines4 += [
                "Possible configurations from the composition:  1",
                "Only the ordering shown above is",
                "compatible with this composition.",
            ]
            self._t4.setStyleSheet(
                f"border:none;background:{SUCCESS_BG};padding:6px 8px;color:{TEXT_MAIN};")
        self._t4.setPlainText("\n".join(lines4))


class _ClickableComboBox(QComboBox):
    """
    QComboBox with split behaviour:
    - Click on the label/text area  → emit `clicked_closed` (regenerate layout),
                                       do NOT open the dropdown.
    - Click on the arrow button     → open the dropdown as normal.

    We track which region was pressed in mousePressEvent and use that in
    showPopup() to decide whether to actually open the popup.
    The arrow button occupies the rightmost ~22 px of the widget.
    """
    clicked_closed = pyqtSignal()
    _ARROW_W = 22   # px width of the drop-down arrow button

    def __init__(self, parent=None):
        super().__init__(parent)
        self._arrow_clicked = False

    def mousePressEvent(self, ev):
        self._arrow_clicked = ev.position().x() >= self.width() - self._ARROW_W
        super().mousePressEvent(ev)

    def showPopup(self):
        if self._arrow_clicked:
            super().showPopup()
        else:
            self.clicked_closed.emit()


# ── Top-level panel ───────────────────────────────────────────────────────────

class CompositionViewerPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._current_comp: list[str] = []
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # config bar
        bar=QWidget(); bar.setFixedHeight(56)
        bar.setStyleSheet(f"background-color:{CONFIG_BAR};border-bottom:1px solid {BORDER_DARK};")
        bl=QHBoxLayout(bar); bl.setContentsMargins(12,6,12,6); bl.setSpacing(12)
        self._chk_par=QCheckBox("Snap parallel/opposite"); self._chk_par.setChecked(True)
        self._chk_par.setFont(font_label())
        self._chk_col=QCheckBox("Snap to overlap"); self._chk_col.setChecked(True)
        self._chk_col.setFont(font_label())
        sep=QLabel("│"); sep.setStyleSheet(f"color:{BORDER_DARK};font-size:16pt;")
        btn=make_button("Reset"); btn.setToolTip("Reset the three objects to their default positions and orientations"); btn.setFixedHeight(30); btn.clicked.connect(self._reset)
        self._lbl_target = QLabel("Current R₁₃:")
        self._lbl_target.setFont(font_label())
        self._cmb_target = _ClickableComboBox()
        self._cmb_target.setView(QListView())
        self._cmb_target.setMinimumWidth(250)
        self._cmb_target.setMaximumWidth(270)
        self._cmb_target.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._cmb_target.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._cmb_target.setMaxVisibleItems(18)
        self._cmb_target.setFont(font_label())
        self._cmb_target.setStyleSheet(
            f"""
            QComboBox {{
                padding:2px 6px;
                background:white;
                border:1px solid {BORDER};
            }}
            QComboBox QAbstractItemView {{
                background:white;
                selection-background-color:{SUCCESS_BG};
                selection-color:{TEXT_MAIN};
                outline:0;
                padding:2px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height:26px;
                padding:4px 10px;
            }}
            """
        )
        self._lbl_status = QLabel("")
        self._lbl_status.setFont(font_label())
        self._lbl_status.setStyleSheet(f"color:{ACCENT_DARK};")
        bl.addWidget(self._chk_par); bl.addWidget(self._chk_col)
        bl.addWidget(sep); bl.addWidget(btn)
        bl.addSpacing(8)
        bl.addWidget(self._lbl_target)
        bl.addWidget(self._cmb_target, 0)
        bl.addSpacing(10)
        bl.addWidget(self._lbl_status, 1)
        bl.addWidget(make_help_button(SEC_COMPOSITION_VIEWER))
        root.addWidget(bar)

        # splitter
        sp=QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(6)
        self._canvas=_TriCanvas()
        self._canvas.on_changed=self._on_changed
        self._chk_par.toggled.connect(lambda v: setattr(self._canvas,'snap_parallel',v))
        self._chk_col.toggled.connect(lambda v: setattr(self._canvas,'snap_colinear',v))
        self._cmb_target.activated.connect(self._on_combo_activated)
        self._cmb_target.clicked_closed.connect(self._on_combo_clicked_closed)
        # Wrap canvas in a scroll area so large layouts remain fully visible
        self._canvas_scroll = QScrollArea()
        self._canvas_scroll.setWidget(self._canvas)
        self._canvas_scroll.setWidgetResizable(False)
        self._canvas_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._canvas_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp.addWidget(self._canvas_scroll)
        self._readout=_CompositionReadout()
        sp.addWidget(self._readout)
        sp.setStretchFactor(0,3); sp.setStretchFactor(1,2); sp.setSizes([600,320])
        root.addWidget(sp,1)
        self._on_changed()

    def showEvent(self, event):
        """Set splitter sizes the first time the panel becomes visible."""
        super().showEvent(event)
        if not getattr(self, '_shown_once', False):
            self._shown_once = True
            from PyQt6.QtCore import QTimer
            def _set_sizes():
                vs = self._readout._vs
                total = vs.height()
                p2 = max(80, total - 128 - 160)
                vs.setSizes([128, p2, 160])
            QTimer.singleShot(0, _set_sizes)

    def _reset(self):
        self._canvas.o1=Obj(160,260,math.radians(20))
        self._canvas.o2=Obj(310,130,math.radians(115))
        self._canvas.o3=Obj(460,260,math.radians(200))
        self._canvas._clamp()
        self._set_status("")
        self._on_changed()
        self._center_scroll_on_objects()

    def _center_scroll_on_objects(self):
        """Scroll the canvas so the three objects are centred in the viewport."""
        from PyQt6.QtCore import QTimer
        def _do():
            xs = [self._canvas.o1.x, self._canvas.o2.x, self._canvas.o3.x]
            ys = [self._canvas.o1.y, self._canvas.o2.y, self._canvas.o3.y]
            cx = (min(xs) + max(xs)) / 2.0
            cy = (min(ys) + max(ys)) / 2.0
            vw = self._canvas_scroll.viewport().width()
            vh = self._canvas_scroll.viewport().height()
            self._canvas_scroll.horizontalScrollBar().setValue(max(0, int(cx - vw / 2)))
            self._canvas_scroll.verticalScrollBar().setValue(max(0, int(cy - vh / 2)))
        QTimer.singleShot(0, _do)

    def _set_status(self, msg: str, ok: bool = True, tooltip: str = ""):
        color = SUCCESS if ok else ERROR_COL
        self._lbl_status.setStyleSheet(f"color:{color};")
        self._lbl_status.setText(msg)
        self._lbl_status.setToolTip(tooltip)

    def _compose_set(self, r12: str, r23: str) -> list[str]:
        from . import qrpc_caches as _pc2
        _pc2._build_caches()
        return sorted((_pc2._COMPOSE_CACHE or {}).get((r12,r23), frozenset()))

    def _update_target_combo(self, comp: list[str]):
        previous = self._cmb_target.currentData()
        self._cmb_target.blockSignals(True)
        self._cmb_target.clear()
        for br in comp:
            self._cmb_target.addItem(pretty_br(br), br)
        if comp:
            idx = comp.index(previous) if previous in comp else 0
            self._cmb_target.setCurrentIndex(idx)
        self._cmb_target.setEnabled(bool(comp))
        self._cmb_target.blockSignals(False)

    def _on_combo_activated(self, _index: int):
        """Trigger layout generation whenever the user selects an item from the
        combo — including re-selecting the same item already shown.
        QComboBox.activated fires on every user interaction with the popup list,
        even when the index has not changed, which is exactly what we need.
        """
        target = self._cmb_target.currentData()
        if not target:
            return
        self._show_selected_layout()


    def _on_combo_clicked_closed(self):
        """Regenerate layout when the user clicks the closed combo.
        This fires via showPopup() override — the popup will still open
        normally afterwards so the user can browse other options.
        But if they just click the currently-shown item, this triggers
        a new layout for the same R₁₃ without needing to re-select it.
        """
        target = self._cmb_target.currentData()
        if target:
            self._show_selected_layout()

    def _candidate_score(self, cand: Obj, ref: Obj) -> float:
        da = abs(normalize_angle(cand.angle - ref.angle))
        return math.hypot(cand.x - ref.x, cand.y - ref.y) + da * 80.0

    @staticmethod
    def _target_required_angles(target: str) -> list | None:
        """
        Return angle offsets (relative to the anchor's angle) that are
        geometrically required for the target relation.

        PAR_SAME / OVL_SAME: objects nearly parallel     (offset ≈ 0°)
        PAR_OPP  / OVL_OPP:  objects nearly antiparallel (offset ≈ 180°)

        Returns a list of radian offsets, or None for unconstrained targets.
        """
        if target.startswith('<PAR_SAME,') or target.startswith('<OVL_SAME,'):
            return [math.radians(d) for d in (0, 1, -1, 2, -2, 3, -3)]
        if target.startswith('<PAR_OPP,') or target.startswith('<OVL_OPP,'):
            return [math.radians(d) for d in (180, 179, 181, 178, 182, 177, 183)]
        return None

    def _generate_pose_candidates(self, anchor: Obj, relation: str, ordered: str, ref_obj: Obj,
                                  cx: float, cy: float, w: float, h: float,
                                  required_angle_offsets=None) -> list:
        results = []
        seen = set()

        def _accept(o: Obj) -> bool:
            if not (24 <= o.x <= w - 24 and 24 <= o.y <= h - 24):
                return False
            rel = analyze(o, anchor).br if ordered == 'oa' else analyze(anchor, o).br
            return rel == relation

        def _add(o: Obj):
            if not _accept(o):
                return
            key = (round(o.x, 1), round(o.y, 1), round(math.degrees(normalize_angle(o.angle)), 1))
            if key in seen:
                return
            seen.add(key)
            results.append(o)

        # Seed with a translated version of the current object.
        dx = ref_obj.x - self._canvas.o2.x
        dy = ref_obj.y - self._canvas.o2.y
        _add(Obj(cx + dx, cy + dy, ref_obj.angle))

        radii = [70, 95, 120, 150, 185, 220]
        bearings = [math.radians(v) for v in range(0, 360, 15)]
        angles = [math.radians(v) for v in range(0, 360, 15)]
        angle_offsets = [0, 10, -10, 25, -25, 45, -45, 70, -70, 90, -90, 135, -135, 180]
        local_bearings = [math.radians(v) for v in (0, 12, -12, 25, -25, 40, -40, 60, -60, 90, -90, 140, -140, 180)]

        ref_radius = math.hypot(ref_obj.x - self._canvas.o2.x, ref_obj.y - self._canvas.o2.y)
        ref_bearing = math.atan2(ref_obj.y - self._canvas.o2.y, ref_obj.x - self._canvas.o2.x)
        for rb in local_bearings:
            for dr in (-35, -15, 0, 20, 45):
                rr = max(55.0, min(230.0, ref_radius + dr))
                x = cx + rr * math.cos(ref_bearing + rb)
                y = cy + rr * math.sin(ref_bearing + rb)
                for da in angle_offsets:
                    _add(Obj(x, y, normalize_angle(ref_obj.angle + math.radians(da))))

        for r in radii:
            for b in bearings:
                x = cx + r * math.cos(b)
                y = cy + r * math.sin(b)
                for a in angles:
                    _add(Obj(x, y, a))

        # Extra dense pass for angle-constrained targets (PAR_*, OVL_*):\n        # sample with orientations fixed to the required angles so these
        # candidates are guaranteed to be present regardless of scoring.
        if required_angle_offsets is not None:
            fine_radii = [55, 75, 100, 130, 165, 200, 235]
            fine_bearings = [math.radians(v) for v in range(0, 360, 10)]
            for r in fine_radii:
                for b in fine_bearings:
                    x = cx + r * math.cos(b)
                    y = cy + r * math.sin(b)
                    for ao in required_angle_offsets:
                        _add(Obj(x, y, normalize_angle(anchor.angle + ao)))

        # Dedicated PAR pool: when the relation itself is PAR_*, candidates must be
        # nearly parallel to anchor AND offset perpendicularly (not colinear).
        # The grid rarely produces these because both angle tolerance (2.5°) and
        # perpendicular placement must coincide. Generate them explicitly.
        if relation.startswith('<PAR_'):
            par_same = relation.startswith('<PAR_SAME,')
            if par_same:
                par_angles = [anchor.angle + math.radians(d) for d in (0, 1, -1, 2, -2, 3, -3)]
            else:
                par_angles = [normalize_angle(anchor.angle + math.pi + math.radians(d))
                              for d in (0, 1, -1, 2, -2, 3, -3)]
            u2x = math.cos(anchor.angle); u2y = math.sin(anchor.angle)
            n2x = -u2y; n2y = u2x  # perpendicular to anchor
            slide = list(range(-220, 221, 14))
            perp_offsets = list(range(8, 80, 8))  # 8..72 px — enough to be non-colinear
            for d in perp_offsets + [-p for p in perp_offsets]:
                for t in slide:
                    ox = cx + t * u2x + d * n2x
                    oy = cy + t * u2y + d * n2y
                    if not (24 <= ox <= w - 24 and 24 <= oy <= h - 24):
                        continue
                    for a in par_angles:
                        _add(Obj(ox, oy, a))

        # Dedicated OVL pool: when the relation itself is OVL_*, candidates must be
        # colinear with the anchor AND nearly parallel/antiparallel.
        # Place candidates directly on the anchor's support line.
        if relation.startswith('<OVL_'):
            ovl_same = relation.startswith('<OVL_SAME,')
            if ovl_same:
                ovl_angles = [anchor.angle + math.radians(d) for d in (0, 1, -1, 2, -2, 3, -3)]
            else:
                ovl_angles = [normalize_angle(anchor.angle + math.pi + math.radians(d))
                              for d in (0, 1, -1, 2, -2, 3, -3)]
            u_ax = math.cos(anchor.angle); u_ay = math.sin(anchor.angle)
            for t in range(-220, 221, 14):
                ox = cx + t * u_ax
                oy = cy + t * u_ay
                if not (24 <= ox <= w - 24 and 24 <= oy <= h - 24):
                    continue
                for a in ovl_angles:
                    _add(Obj(ox, oy, normalize_angle(a)))

        # A small randomized refinement helps with narrow tolerance regions.
        rng = random.Random((hash((relation, ordered)) ^ 0x5F3759DF) & 0xFFFFFFFF)
        for _ in range(600):
            r = rng.uniform(55.0, 225.0)
            b = rng.uniform(-math.pi, math.pi)
            a = rng.uniform(-math.pi, math.pi)
            _add(Obj(cx + r * math.cos(b), cy + r * math.sin(b), a))

        # For angle-constrained targets keep ALL valid candidates (no score pruning)
        # so near-parallel / near-antiparallel ones are not crowded out.
        # For general targets sort by similarity to current layout and keep best 320.
        if required_angle_offsets is not None:
            return results
        results.sort(key=lambda o: self._candidate_score(o, ref_obj))
        return results[:320]

    def _ovl_family(self, relation: str) -> str | None:
        if relation.startswith("<OVL_SAME,"):
            return "same"
        if relation.startswith("<OVL_OPP,"):
            return "opp"
        return None

    def _try_snap_target_ovl(self, layout, r12: str, r23: str, target: str):
        fam = self._ovl_family(target)
        if fam is None or layout is None:
            return layout

        base_o1, base_o2, base_o3 = layout
        best = layout

        def _is_valid(o1: Obj, o2: Obj, o3: Obj) -> bool:
            return (analyze(o1, o2).br == r12 and
                    analyze(o2, o3).br == r23 and
                    analyze(o1, o3).br == target)

        if _is_valid(base_o1, base_o2, base_o3):
            best = (Obj(base_o1.x, base_o1.y, base_o1.angle),
                    Obj(base_o2.x, base_o2.y, base_o2.angle),
                    Obj(base_o3.x, base_o3.y, base_o3.angle))

        # Make O1 and O3 exactly overlapped: same supporting line and exact same/opposite orientation.
        orient3 = normalize_angle(base_o1.angle if fam == "same" else base_o1.angle + math.pi)
        ux, uy = math.cos(base_o1.angle), math.sin(base_o1.angle)
        base_t = (base_o3.x - base_o1.x) * ux + (base_o3.y - base_o1.y) * uy

        offsets = [0.0, -8.0, 8.0, -16.0, 16.0, -28.0, 28.0]
        normal_jitter = [0.0, -2.0, 2.0]

        for delta_t in offsets:
            for dn in normal_jitter:
                # Variant A: keep O1 fixed, snap O3 onto O1 line.
                nx, ny = -uy, ux
                t = base_t + delta_t
                o1 = Obj(base_o1.x, base_o1.y, base_o1.angle)
                o2 = Obj(base_o2.x, base_o2.y, base_o2.angle)
                o3 = Obj(base_o1.x + ux * t + nx * dn, base_o1.y + uy * t + ny * dn, orient3)
                if _is_valid(o1, o2, o3):
                    return (o1, o2, o3)

                # Variant B: keep O3 fixed, snap O1 onto O3 line.
                ux3, uy3 = math.cos(orient3), math.sin(orient3)
                nx3, ny3 = -uy3, ux3
                t13 = (base_o1.x - base_o3.x) * ux3 + (base_o1.y - base_o3.y) * uy3
                o3b = Obj(base_o3.x, base_o3.y, orient3)
                o1b = Obj(base_o3.x + ux3 * (t13 + delta_t) + nx3 * dn,
                          base_o3.y + uy3 * (t13 + delta_t) + ny3 * dn,
                          base_o1.angle)
                if _is_valid(o1b, o2, o3b):
                    return (o1b, o2, o3b)

        # Return the best valid layout found, or the original as fallback.
        return best

    def _target_x_zero_flags(self, relation: str) -> tuple[bool, bool]:
        try:
            parts = [p.strip() for p in relation.strip("<>").split(",")]
        except Exception:
            return (False, False)
        if len(parts) < 3 or parts[0] != "X":
            return (False, False)
        return (parts[1] == "ZERO", parts[2] == "ZERO")

    def _try_snap_target_x_zero(self, layout, r12: str, r23: str, target: str):
        """
        Enforce exact geometric coincidence for X relations where C13 = O1 or C13 = O3.

        ZERO in position 1 of R13 means O1 lies exactly on O3\'s support line.
        ZERO in position 2 of R13 means O3 lies exactly on O1\'s support line.

        Strategy: project the constrained object exactly onto the other\'s support line
        (distance = 0.0), then slide along that line while also nudging O2 to recover
        valid R12 and R23.
        """
        if layout is None:
            return layout
        zero_o1, zero_o3 = self._target_x_zero_flags(target)
        if not (zero_o1 or zero_o3):
            return layout

        base_o1, base_o2, base_o3 = layout

        def _is_valid(o1: Obj, o2: Obj, o3: Obj) -> bool:
            return (analyze(o1, o2).br == r12 and
                    analyze(o2, o3).br == r23 and
                    analyze(o1, o3).br == target)

        u1x, u1y = math.cos(base_o1.angle), math.sin(base_o1.angle)
        u3x, u3y = math.cos(base_o3.angle), math.sin(base_o3.angle)

        # Slide values along the constrained support line.
        slide = [0.0, 16.0, -16.0, 32.0, -32.0, 52.0, -52.0,
                 76.0, -76.0, 104.0, -104.0, 136.0, -136.0]
        # Small nudges for O2 along its own support line to recover R12/R23.
        o2_nudge = [0.0, 12.0, -12.0, 24.0, -24.0, 40.0, -40.0, 60.0, -60.0]

        if zero_o1 and not zero_o3:
            # O1 must lie exactly on O3\'s support line.
            # Project O1 perpendicularly onto O3\'s line, preserving along-axis component.
            dx, dy = base_o1.x - base_o3.x, base_o1.y - base_o3.y
            along = dx * u3x + dy * u3y
            u2x, u2y = math.cos(base_o2.angle), math.sin(base_o2.angle)
            for delta in slide:
                o1 = Obj(base_o3.x + (along + delta) * u3x,
                         base_o3.y + (along + delta) * u3y,
                         base_o1.angle)
                if _is_valid(o1, base_o2, base_o3):
                    return (o1, base_o2, base_o3)
                # Nudge O2 along its support line to recover R12 and R23.
                for nd in o2_nudge[1:]:
                    for sign in (1, -1):
                        o2 = Obj(base_o2.x + sign * nd * u2x,
                                 base_o2.y + sign * nd * u2y,
                                 base_o2.angle)
                        if _is_valid(o1, o2, base_o3):
                            return (o1, o2, base_o3)

        elif zero_o3 and not zero_o1:
            # O3 must lie exactly on O1\'s support line.
            # Project O3 perpendicularly onto O1\'s line.
            dx, dy = base_o3.x - base_o1.x, base_o3.y - base_o1.y
            along = dx * u1x + dy * u1y
            u2x, u2y = math.cos(base_o2.angle), math.sin(base_o2.angle)
            for delta in slide:
                o3 = Obj(base_o1.x + (along + delta) * u1x,
                         base_o1.y + (along + delta) * u1y,
                         base_o3.angle)
                if _is_valid(base_o1, base_o2, o3):
                    return (base_o1, base_o2, o3)
                for nd in o2_nudge[1:]:
                    for sign in (1, -1):
                        o2 = Obj(base_o2.x + sign * nd * u2x,
                                 base_o2.y + sign * nd * u2y,
                                 base_o2.angle)
                        if _is_valid(base_o1, o2, o3):
                            return (base_o1, o2, o3)

        else:
            # Both ZERO (not expected for X — conservative fallback).
            o3 = Obj(base_o1.x, base_o1.y, base_o3.angle)
            if _is_valid(base_o1, base_o2, o3):
                return (base_o1, base_o2, o3)

        # Could not enforce exact projection — return original unchanged.
        return layout

    def _intersection_points_for(self, o1: Obj, o2: Obj, o3: Obj) -> list[tuple[float, float]]:
        pts = []
        for oa, ob in ((o1, o2), (o2, o3), (o1, o3)):
            pts.extend(_smart_intersect(oa.x, oa.y, oa.angle, ob.x, ob.y, ob.angle,
                                        CANVAS_W, CANVAS_H))
        return pts

    def _layout_valid(self, o1: Obj, o2: Obj, o3: Obj, r12: str, r23: str, target: str) -> bool:
        return (analyze(o1, o2).br == r12 and
                analyze(o2, o3).br == r23 and
                analyze(o1, o3).br == target)

    # Minimum pixel distance between any two object origins in a generated layout.
    # Below this threshold objects visually overlap and the diagram becomes unreadable.
    _MIN_OBJ_SEP = 55.0

    def _layout_fits_view(self, o1: Obj, o2: Obj, o3: Obj, w: float, h: float, margin: float = 34.0) -> bool:
        pts = [(o1.x, o1.y), (o2.x, o2.y), (o3.x, o3.y)] + self._intersection_points_for(o1, o2, o3)
        if not pts:
            return False
        if not all(margin <= x <= w - margin and margin <= y <= h - margin for x, y in pts):
            return False
        # Reject layouts where any two objects are too close to be readable
        objs = [(o1.x, o1.y), (o2.x, o2.y), (o3.x, o3.y)]
        if any(_dist(*objs[i], *objs[j]) < self._MIN_OBJ_SEP
               for i in range(3) for j in range(i + 1, 3)):
            return False
        return True

    def _layout_score(self, o1: Obj, o2: Obj, o3: Obj, w: float, h: float) -> float:
        margin = 34.0
        obj_pts = [(o1.x, o1.y), (o2.x, o2.y), (o3.x, o3.y)]
        ix_pts = self._intersection_points_for(o1, o2, o3)
        all_pts = obj_pts + ix_pts
        if not all_pts:
            return 1e12

        xs = [x for x, _ in all_pts]
        ys = [y for _, y in all_pts]
        overflow = 0.0
        outside_count = 0
        for x, y in all_pts:
            dx1 = max(0.0, margin - x)
            dx2 = max(0.0, x - (w - margin))
            dy1 = max(0.0, margin - y)
            dy2 = max(0.0, y - (h - margin))
            over = dx1 + dx2 + dy1 + dy2
            overflow += over
            if over > 0.0:
                outside_count += 1

        min_obj = min(_dist(*obj_pts[i], *obj_pts[j]) for i in range(3) for j in range(i + 1, 3))
        min_ix = min((_dist(*ix_pts[i], *ix_pts[j]) for i in range(len(ix_pts)) for j in range(i + 1, len(ix_pts))), default=40.0)

        # Keep objects somewhat separated, but avoid opening the scene so much
        # that the supporting projections become too short to read well.
        obj_pen = max(0.0, 180.0 - min_obj) * 64.0
        obj_open_pen = max(0.0, min_obj - 214.0) * 5.5
        ix_pen = max(0.0, 22.0 - min_ix) * 8.0

        bbox_w = max(xs) - min(xs)
        bbox_h = max(ys) - min(ys)
        bbox_open_pen = max(0.0, bbox_w - w * 0.56) * 0.75 + max(0.0, bbox_h - h * 0.50) * 0.75

        center_pen = abs((min(xs) + max(xs)) * 0.5 - w * 0.5) + abs((min(ys) + max(ys)) * 0.5 - h * 0.5)

        hard_pen = outside_count * 50000.0 + overflow * 2500.0
        return hard_pen + obj_pen + obj_open_pen + ix_pen + bbox_open_pen + center_pen

    def _beautify_layout(self, layout, r12: str, r23: str, target: str):
        if layout is None:
            return None

        base_o1, base_o2, base_o3 = layout
        w, h = CANVAS_W, CANVAS_H
        target_cx, target_cy = w * 0.50, h * 0.53

        # Detect whether this target requires exact C13 coincidence.
        # If so, we must enforce the geometric constraint after any transform.
        zero_o1, zero_o3 = self._target_x_zero_flags(target)
        _has_zero_constraint = zero_o1 or zero_o3

        def _apply_zero_constraint(o1: Obj, o2: Obj, o3: Obj):
            """Project O1 or O3 exactly onto the other's support line, keeping relations valid."""
            u1x, u1y = math.cos(o1.angle), math.sin(o1.angle)
            u3x, u3y = math.cos(o3.angle), math.sin(o3.angle)
            offsets = [0.0, 16.0, -16.0, 32.0, -32.0, 50.0, -50.0, 70.0, -70.0, 95.0, -95.0, 124.0, -124.0]

            def _valid(a, b, c):
                return (analyze(a, b).br == r12 and
                        analyze(b, c).br == r23 and
                        analyze(a, c).br == target)

            if zero_o1 and not zero_o3:
                # O1 must lie on O3's support line: project O1 onto it.
                dx, dy = o1.x - o3.x, o1.y - o3.y
                along = dx * u3x + dy * u3y
                o1p = Obj(o3.x + along * u3x, o3.y + along * u3y, o1.angle)
                if _valid(o1p, o2, o3):
                    return (o1p, o2, o3)
                # Slide along O3's line to find a valid position
                for d in offsets:
                    o1t = Obj(o3.x + (along + d) * u3x, o3.y + (along + d) * u3y, o1.angle)
                    if _valid(o1t, o2, o3):
                        return (o1t, o2, o3)
            elif zero_o3 and not zero_o1:
                # O3 must lie on O1's support line: project O3 onto it.
                dx, dy = o3.x - o1.x, o3.y - o1.y
                along = dx * u1x + dy * u1y
                o3p = Obj(o1.x + along * u1x, o1.y + along * u1y, o3.angle)
                if _valid(o1, o2, o3p):
                    return (o1, o2, o3p)
                for d in offsets:
                    o3t = Obj(o1.x + (along + d) * u1x, o1.y + (along + d) * u1y, o3.angle)
                    if _valid(o1, o2, o3t):
                        return (o1, o2, o3t)
            return None  # could not enforce — caller falls back to _try_snap_target_x_zero

        def _transform(scale: float, tx: float, ty: float):
            def _map(o: Obj) -> Obj:
                return Obj(
                    base_o2.x + (o.x - base_o2.x) * scale + tx,
                    base_o2.y + (o.y - base_o2.y) * scale + ty,
                    o.angle,
                )
            return _map(base_o1), _map(base_o2), _map(base_o3)

        scales = [1.00, 1.10, 1.18, 1.26, 1.34, 1.42, 1.50, 0.96, 0.92, 0.88]
        offsets = [(0.0, 0.0), (-16.0, 0.0), (16.0, 0.0), (0.0, -16.0), (0.0, 16.0),
                   (-12.0, -12.0), (12.0, -12.0), (-12.0, 12.0), (12.0, 12.0)]

        best = layout
        best_score = self._layout_score(base_o1, base_o2, base_o3, w, h)

        for scale in scales:
            # First center the full scene (objects + intersection points)
            temp = _transform(scale, 0.0, 0.0)
            pts = [(temp[0].x, temp[0].y), (temp[1].x, temp[1].y), (temp[2].x, temp[2].y)] + self._intersection_points_for(*temp)
            xs = [x for x, _ in pts]
            ys = [y for _, y in pts]
            tx0 = target_cx - (min(xs) + max(xs)) * 0.5
            ty0 = target_cy - (min(ys) + max(ys)) * 0.5
            for dx, dy in offsets:
                cand = _transform(scale, tx0 + dx, ty0 + dy)
                if not self._layout_valid(*cand, r12, r23, target):
                    continue
                # If a C13 zero-coincidence constraint exists, enforce it exactly
                # before scoring so the transform doesn't silently degrade it.
                if _has_zero_constraint:
                    enforced = _apply_zero_constraint(*cand)
                    if enforced is not None and self._layout_valid(*enforced, r12, r23, target):
                        cand = enforced
                if not self._layout_fits_view(*cand, w, h):
                    continue
                score = self._layout_score(*cand, w, h)
                if score < best_score:
                    best = cand
                    best_score = score

        # Final gentle spreading: move O1 and O3 radially away from O2 a bit more
        # while preserving R12, R23, the selected witness, and visibility in the viewer.
        o1b, o2b, o3b = best
        for factor in (1.08, 1.14, 1.20, 1.26, 1.32):
            cand = (
                Obj(o2b.x + (o1b.x - o2b.x) * factor, o2b.y + (o1b.y - o2b.y) * factor, o1b.angle),
                Obj(o2b.x, o2b.y, o2b.angle),
                Obj(o2b.x + (o3b.x - o2b.x) * factor, o2b.y + (o3b.y - o2b.y) * factor, o3b.angle),
            )
            if not self._layout_valid(*cand, r12, r23, target):
                continue
            # Re-enforce zero constraint after radial spread too
            if _has_zero_constraint:
                enforced = _apply_zero_constraint(*cand)
                if enforced is not None and self._layout_valid(*enforced, r12, r23, target):
                    cand = enforced
            if not self._layout_fits_view(*cand, w, h):
                continue
            score = self._layout_score(*cand, w, h)
            if score <= best_score + 45.0:
                best = cand
                best_score = score
        return best

    def _search_witness_layout(self, r12: str, r23: str, target: str):
        w, h = CANVAS_W, CANVAS_H
        cx, cy = w / 2.0, h / 2.0
        pivot = Obj(cx, cy, self._canvas.o2.angle)

        req_angles = self._target_required_angles(target)
        is_angle_constrained = req_angles is not None

        # When r12 or r23 is PAR_* or OVL_*, the candidate pools need the dedicated
        # generator (perpendicular-offset or on-line placements). Pass a sentinel
        # req_angles so that _generate_pose_candidates activates those pools AND
        # returns all candidates without score-based pruning.
        par_sentinel = []  # empty list — triggers PAR/OVL pool but no angle filter in search
        r12_req = par_sentinel if (r12.startswith('<PAR_') or r12.startswith('<OVL_')) else req_angles
        r23_req = par_sentinel if (r23.startswith('<PAR_') or r23.startswith('<OVL_')) else req_angles

        # OVL fast path: generate O3 directly on O1's support line
        if target.startswith('<OVL_'):
            result = self._search_ovl_layout(r12, r23, target, pivot, cx, cy, w, h)
            if result is not None:
                return result

        cand12 = self._generate_pose_candidates(
            pivot, r12, 'oa', self._canvas.o1, cx, cy, w, h, r12_req)
        cand23 = self._generate_pose_candidates(
            pivot, r23, 'ao', self._canvas.o3, cx, cy, w, h, r23_req)
        if not cand12 or not cand23:
            return None

        best = None
        best_score = float('inf')

        # Use full candidate lists when r12 or r23 is PAR/OVL (they have targeted pools)
        is_par_input = (r12.startswith('<PAR_') or r23.startswith('<PAR_') or
                        r12.startswith('<OVL_') or r23.startswith('<OVL_'))

        if is_angle_constrained:
            for o1 in cand12:
                o3_angles = [normalize_angle(o1.angle + ao) for ao in req_angles]
                for o3 in cand23:
                    angle_ok = any(
                        abs(normalize_angle(o3.angle - req_a)) < math.radians(3.5)
                        for req_a in o3_angles
                    )
                    if not angle_ok:
                        continue
                    if analyze(o1, o3).br != target:
                        continue
                    score = self._candidate_score(o1, self._canvas.o1) + self._candidate_score(o3, self._canvas.o3)
                    if score < best_score:
                        best_score = score
                        best = (Obj(o1.x, o1.y, o1.angle),
                                Obj(pivot.x, pivot.y, pivot.angle),
                                Obj(o3.x, o3.y, o3.angle))
                        if best_score < 40:
                            return best
        elif is_par_input:
            # PAR inputs: use full candidate lists (targeted PAR pool is large)
            for o1 in cand12:
                for o3 in cand23:
                    if analyze(o1, o3).br != target:
                        continue
                    score = self._candidate_score(o1, self._canvas.o1) + self._candidate_score(o3, self._canvas.o3)
                    if score < best_score:
                        best_score = score
                        best = (Obj(o1.x, o1.y, o1.angle),
                                Obj(pivot.x, pivot.y, pivot.angle),
                                Obj(o3.x, o3.y, o3.angle))
                        if best_score < 40:
                            return best
        else:
            for o1 in cand12[:220]:
                for o3 in cand23[:220]:
                    if analyze(o1, o3).br != target:
                        continue
                    score = self._candidate_score(o1, self._canvas.o1) + self._candidate_score(o3, self._canvas.o3)
                    if score < best_score:
                        best_score = score
                        best = (Obj(o1.x, o1.y, o1.angle),
                                Obj(pivot.x, pivot.y, pivot.angle),
                                Obj(o3.x, o3.y, o3.angle))
                        if best_score < 40:
                            return best

        rng = random.Random((hash((r12, r23, target)) ^ 0x9E3779B9) & 0xFFFFFFFF)
        for _ in range(16000):
            o1 = cand12[rng.randrange(len(cand12))]
            o3 = cand23[rng.randrange(len(cand23))]
            if analyze(o1, o3).br != target:
                continue
            score = self._candidate_score(o1, self._canvas.o1) + self._candidate_score(o3, self._canvas.o3)
            if score < best_score:
                best_score = score
                best = (Obj(o1.x, o1.y, o1.angle),
                        Obj(pivot.x, pivot.y, pivot.angle),
                        Obj(o3.x, o3.y, o3.angle))
                if best_score < 55:
                    return best
        return best

    def _search_ovl_layout(self, r12: str, r23: str, target: str,
                           pivot: Obj, cx: float, cy: float, w: float, h: float):
        """
        Dedicated search for OVL targets.

        OVL requires O1 and O3 to be colinear AND nearly parallel.
        Three O1 pools cover all geometric configurations:

          Pool A: standard grid candidates (works for X-type r12)
          Pool B: O1 placed on pivot's support line (works for OVL/PAR r12)
          Pool C: O1 whose support line passes through the pivot
                  (needed when r23 is itself OVL — requires O3 near pivot's line,
                   which is only possible if O1's line also passes near the pivot)

        For each O1 candidate, O3 is placed directly on O1's support line
        (colinearity exact by construction) and checked against r23 and target.
        """
        ovl_fam = self._ovl_family(target)
        if ovl_fam is None:
            return None

        if ovl_fam == 'same':
            a_offsets = [math.radians(d) for d in (0, 1, -1, 2, -2, 3, -3)]
        else:
            a_offsets = [math.radians(180 + d) for d in (0, 1, -1, 2, -2, 3, -3)]

        slide = list(range(-220, 221, 14))
        u2x = math.cos(pivot.angle)
        u2y = math.sin(pivot.angle)

        # Pool B: O1 placed directly on pivot's support line
        # (satisfies OVL/PAR r12 that the grid misses)
        extra_angles = (
            [pivot.angle + math.radians(d) for d in (0, 1, -1, 2, -2, 3, -3)] +
            [normalize_angle(pivot.angle + math.pi + math.radians(d)) for d in (0, 1, -1, 2, -2, 3, -3)]
        )
        pool_b = []
        for t in slide:
            o1x = cx + t * u2x
            o1y = cy + t * u2y
            if not (24 <= o1x <= CANVAS_W - 24 and 24 <= o1y <= CANVAS_H - 24):
                continue
            for a in extra_angles:
                o1 = Obj(o1x, o1y, normalize_angle(a))
                if (analyze(o1, pivot).br == r12 and
                        _dist(o1x, o1y, pivot.x, pivot.y) >= self._MIN_OBJ_SEP):
                    pool_b.append(o1)

        # Pool C: O1 placed so its support line passes through the pivot
        # (within COLINEAR_EPS). Needed when r23=OVL requires O3 near pivot's line.
        pool_c = []
        fine_angles = [math.radians(a_deg) for a_deg in range(0, 360, 10)]
        d_perp = [0.0, 2.0, -2.0, 4.0, -4.0]  # perpendicular offsets < COLINEAR_EPS
        along_vals = list(range(-200, 201, 18))
        for a1 in fine_angles:
            u1x, u1y = math.cos(a1), math.sin(a1)
            n1x, n1y = -u1y, u1x
            for d in d_perp:
                for along in along_vals:
                    o1x = cx + d * n1x + along * u1x
                    o1y = cy + d * n1y + along * u1y
                    if not (24 <= o1x <= CANVAS_W - 24 and 24 <= o1y <= CANVAS_H - 24):
                        continue
                    o1 = Obj(o1x, o1y, a1)
                    if (analyze(o1, pivot).br == r12 and
                            _dist(o1x, o1y, pivot.x, pivot.y) >= self._MIN_OBJ_SEP):
                        pool_c.append(o1)

        # Pool A: standard grid candidates (good for X-type r12)
        pool_a = self._generate_pose_candidates(
            pivot, r12, 'oa', self._canvas.o1, cx, cy, CANVAS_W, CANVAS_H, None)

        # Merge: targeted pools first, then grid
        all_o1 = pool_b + pool_c + pool_a
        if not all_o1:
            return None

        best = None
        best_score = float('inf')

        for o1 in all_o1:
            u1x = math.cos(o1.angle)
            u1y = math.sin(o1.angle)
            for t in slide:
                o3x = o1.x + t * u1x
                o3y = o1.y + t * u1y
                if not (24 <= o3x <= CANVAS_W - 24 and 24 <= o3y <= CANVAS_H - 24):
                    continue
                # Skip positions where O3 overlaps with O1 or pivot
                if (_dist(o3x, o3y, o1.x, o1.y) < self._MIN_OBJ_SEP or
                        _dist(o3x, o3y, pivot.x, pivot.y) < self._MIN_OBJ_SEP):
                    continue
                for ao in a_offsets:
                    o3 = Obj(o3x, o3y, normalize_angle(o1.angle + ao))
                    if analyze(pivot, o3).br != r23:
                        continue
                    if analyze(o1, o3).br != target:
                        continue
                    score = (self._candidate_score(o1, self._canvas.o1) +
                             self._candidate_score(o3, self._canvas.o3))
                    if score < best_score:
                        best_score = score
                        best = (Obj(o1.x, o1.y, o1.angle),
                                Obj(pivot.x, pivot.y, pivot.angle),
                                Obj(o3.x, o3.y, o3.angle))
                        if best_score < 40:
                            return best
        return best

    def _show_selected_layout(self):
        target = self._cmb_target.currentData()
        if not target:
            self._set_status("No witness relation available.", ok=False)
            return
        r12 = analyze(self._canvas.o1, self._canvas.o2).br
        r23 = analyze(self._canvas.o2, self._canvas.o3).br
        found = self._search_witness_layout(r12, r23, target)
        if found:
            found = self._try_snap_target_ovl(found, r12, r23, target)
            found = self._try_snap_target_x_zero(found, r12, r23, target)
            pre_beautify = found          # keep a copy before beautify may degrade it
            found = self._beautify_layout(found, r12, r23, target)
            found = self._try_snap_target_x_zero(found, r12, r23, target)

            # If the post-beautify snap still didn't achieve exact coincidence,
            # fall back to the pre-beautify layout which already had it enforced.
            zero_o1, zero_o3 = self._target_x_zero_flags(target)
            if (zero_o1 or zero_o3) and found is not None:
                o1, _, o3 = found
                u1x, u1y = math.cos(o1.angle), math.sin(o1.angle)
                u3x, u3y = math.cos(o3.angle), math.sin(o3.angle)
                ok = True
                if zero_o1:
                    ok = ok and abs(distance_to_line(o1.x, o1.y, o3.x, o3.y, u3x, u3y)) < 1.0
                if zero_o3:
                    ok = ok and abs(distance_to_line(o3.x, o3.y, o1.x, o1.y, u1x, u1y)) < 1.0
                if not ok:
                    found = pre_beautify
        if not found:
            self._set_status(
                "Layout not found. Reset and retry.",
                ok=False,
                tooltip=(
                    "The selected basic relation is valid, but the automatic geometric layout "
                    "may fail from the current object positions. Press Reset and try again."
                ),
            )
            return
        self._canvas.o1, self._canvas.o2, self._canvas.o3 = found
        self._canvas._clamp()
        self._center_scroll_on_objects()
        self._set_status(f"Layout generated for {pretty_br(target)}.", ok=True)
        self._on_changed()

    def _on_changed(self):
        self._readout.update_data(self._canvas.o1,self._canvas.o2,self._canvas.o3)
        r12 = analyze(self._canvas.o1, self._canvas.o2).br
        r23 = analyze(self._canvas.o2, self._canvas.o3).br
        comp = self._compose_set(r12, r23)
        if comp != self._current_comp:
            self._current_comp = comp
            self._update_target_combo(comp)
        current_r13 = analyze(self._canvas.o1, self._canvas.o3).br
        if current_r13 in comp:
            idx = self._cmb_target.findData(current_r13)
            if idx >= 0:
                self._cmb_target.blockSignals(True)
                self._cmb_target.setCurrentIndex(idx)
                self._cmb_target.blockSignals(False)
        self._canvas.update()
