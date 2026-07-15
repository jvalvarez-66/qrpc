"""
representation.py
-----------------
Core domain types for the QRPC six-component instantiated representation.
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Optional


# ── Projection type ───────────────────────────────────────────────────────────

class P12(Enum):
    """
    Projection type P₁₂ — first component of the six-tuple.

    Describes the geometric relationship between the projections of two
    oriented objects O_i and O_j onto a common reference line.
    """
    X        = auto()   # crossing projections
    PAR_SAME = auto()   # parallel, same direction
    PAR_OPP  = auto()   # parallel, opposite directions
    OVL_SAME = auto()   # overlapping, same direction
    OVL_OPP  = auto()   # overlapping, opposite directions


# ── Qualitative sign domain ───────────────────────────────────────────────────

class QVal(Enum):
    """
    Qualitative value domain Σ_D shared by C₁, C₂, LR and OFB components.

    None is used to represent wildcards (_).
    P_OR_M represents the ambiguity +|− in the OFB component for certain
    projection types.
    """
    PLUS   = auto()   # positive:  +
    ZERO   = auto()   # neutral:   0
    MINUS  = auto()   # negative:  −
    P_OR_M = auto()   # ambiguous: +|−

    def __str__(self) -> str:
        return {
            QVal.PLUS:   'PLUS',
            QVal.ZERO:   'ZERO',
            QVal.MINUS:  'MINUS',
            QVal.P_OR_M: 'P_OR_M',
        }[self]


# ── Lateral relative movement direction ──────────────────────────────────────

class DLR(Enum):
    """
    Direction domain Σ_D* for the D_{ij}^{LR} component.

    Only meaningful for X-type relations; None (wildcard) for PAR/OVL.
    """
    P_TO_0  = auto()   # +→0
    _0_TO_P = auto()   # 0→+
    M_TO_0  = auto()   # −→0
    _0_TO_M = auto()   # 0→−
    P_TO_M  = auto()   # +→−
    M_TO_P  = auto()   # −→+
    _0_TO_0 = auto()   # 0→0

    def __str__(self) -> str:
        return {
            DLR.P_TO_0:  'P_TO_0',
            DLR._0_TO_P: '_0_TO_P',
            DLR.M_TO_0:  'M_TO_0',
            DLR._0_TO_M: '_0_TO_M',
            DLR.P_TO_M:  'P_TO_M',
            DLR.M_TO_P:  'M_TO_P',
            DLR._0_TO_0: '_0_TO_0',
        }[self]


# ── Six-tuple ─────────────────────────────────────────────────────────────────

class Representation:
    """
    Immutable instantiated representation of one of the 48 basic QRPC relations.

    Six-component encoding: (P₁₂, C₁, C₂, LR, DLR, OFB).

    A component value of None denotes a wildcard (_) — the component is not
    semantically relevant for that relation type (canonical representation
    abstracts over such components).
    """

    __slots__ = ('p', 'c1', 'c2', 'lr', 'dlr', 'ofb')

    def __init__(
        self,
        p:   P12,
        c1:  Optional[QVal],
        c2:  Optional[QVal],
        lr:  Optional[QVal],
        dlr: Optional[DLR],
        ofb: Optional[QVal],
    ) -> None:
        self.p   = p
        self.c1  = c1
        self.c2  = c2
        self.lr  = lr
        self.dlr = dlr
        self.ofb = ofb

    # ── Equality and hashing ──────────────────────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Representation):
            return NotImplemented
        return (self.p, self.c1, self.c2, self.lr, self.dlr, self.ofb) == \
               (other.p, other.c1, other.c2, other.lr, other.dlr, other.ofb)

    def __hash__(self) -> int:
        return hash((self.p, self.c1, self.c2, self.lr, self.dlr, self.ofb))

    # ── String representation ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (f"Representation({self.p.name}, {self.c1}, "
                f"{self.c2}, {self.lr}, {self.dlr}, {self.ofb})")

    def __str__(self) -> str:
        """Returns the tuple in the format <P,C1,C2,LR,DLR,OFB>."""
        def s(v): return str(v.name) if v is not None else '_'
        return f"<{self.p.name},{s(self.c1)},{s(self.c2)},{s(self.lr)},{s(self.dlr)},{s(self.ofb)}>"
