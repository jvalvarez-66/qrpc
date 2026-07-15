"""
table48.py
----------
Catalogue of all 48 basic QRPC relations.

Maps each instantiated representation (concrete six-tuple) to its compact
form string, and provides the reverse lookup (compact form → list of
instantiated representations).
"""

from __future__ import annotations
from typing import Dict, List, Optional
from .representation import P12, QVal, DLR, Representation

# Short aliases for readability inside the catalogue
X   = P12.X
PS  = P12.PAR_SAME
PO  = P12.PAR_OPP
OS  = P12.OVL_SAME
OO  = P12.OVL_OPP

P   = QVal.PLUS
Z   = QVal.ZERO
M   = QVal.MINUS
PM  = QVal.P_OR_M

P0  = DLR.P_TO_0
_0P = DLR._0_TO_P
M0  = DLR.M_TO_0
_0M = DLR._0_TO_M
PM_ = DLR.P_TO_M
MP  = DLR.M_TO_P
_00 = DLR._0_TO_0

_ = None   # wildcard


def _r(p, c1, c2, lr, dlr, ofb) -> Representation:
    return Representation(p, c1, c2, lr, dlr, ofb)


# ── Catalogue: instantiated representation → compact form ────────────────────

_CATALOGUE: Dict[Representation, str] = {}

def _add(br: str, p, c1, c2, lr, dlr, ofb) -> None:
    k = _r(p, c1, c2, lr, dlr, ofb)
    if k in _CATALOGUE:
        raise ValueError(f"Duplicate entry in catalogue: {k}")
    _CATALOGUE[k] = br


# ── X-type regular (24 states) ────────────────────────────────────────────────
_add("<X,PLUS,PLUS,PLUS,_,PLUS>",   X,  P,  P,  P,  P0,  P)
_add("<X,PLUS,PLUS,PLUS,_,ZERO>",   X,  P,  P,  P,  P0,  Z)
_add("<X,PLUS,PLUS,PLUS,_,MINUS>",  X,  P,  P,  P,  P0,  M)
_add("<X,PLUS,PLUS,MINUS,_,PLUS>",  X,  P,  P,  M,  M0,  P)
_add("<X,PLUS,PLUS,MINUS,_,ZERO>",  X,  P,  P,  M,  M0,  Z)
_add("<X,PLUS,PLUS,MINUS,_,MINUS>", X,  P,  P,  M,  M0,  M)

_add("<X,MINUS,MINUS,PLUS,_,PLUS>",   X,  M,  M,  P,  _0P, P)
_add("<X,MINUS,MINUS,PLUS,_,ZERO>",   X,  M,  M,  P,  _0P, Z)
_add("<X,MINUS,MINUS,PLUS,_,MINUS>",  X,  M,  M,  P,  _0P, M)
_add("<X,MINUS,MINUS,MINUS,_,PLUS>",  X,  M,  M,  M,  _0M, P)
_add("<X,MINUS,MINUS,MINUS,_,ZERO>",  X,  M,  M,  M,  _0M, Z)
_add("<X,MINUS,MINUS,MINUS,_,MINUS>", X,  M,  M,  M,  _0M, M)

_add("<X,PLUS,MINUS,PLUS,_,PLUS>",   X,  P,  M,  P,  P0,  P)
_add("<X,PLUS,MINUS,PLUS,_,ZERO>",   X,  P,  M,  P,  P0,  Z)
_add("<X,PLUS,MINUS,PLUS,_,MINUS>",  X,  P,  M,  P,  P0,  M)
_add("<X,PLUS,MINUS,MINUS,_,PLUS>",  X,  P,  M,  M,  M0,  P)
_add("<X,PLUS,MINUS,MINUS,_,ZERO>",  X,  P,  M,  M,  M0,  Z)
_add("<X,PLUS,MINUS,MINUS,_,MINUS>", X,  P,  M,  M,  M0,  M)

_add("<X,MINUS,PLUS,PLUS,_,PLUS>",   X,  M,  P,  P,  _0P, P)
_add("<X,MINUS,PLUS,PLUS,_,ZERO>",   X,  M,  P,  P,  _0P, Z)
_add("<X,MINUS,PLUS,PLUS,_,MINUS>",  X,  M,  P,  P,  _0P, M)
_add("<X,MINUS,PLUS,MINUS,_,PLUS>",  X,  M,  P,  M,  _0M, P)
_add("<X,MINUS,PLUS,MINUS,_,ZERO>",  X,  M,  P,  M,  _0M, Z)
_add("<X,MINUS,PLUS,MINUS,_,MINUS>", X,  M,  P,  M,  _0M, M)

# ── X-type boundary (8 states) ────────────────────────────────────────────────
_add("<X,PLUS,ZERO,PLUS,_,_>",   X,  P,  Z,  P,  P0,  PM)
_add("<X,PLUS,ZERO,MINUS,_,_>",  X,  P,  Z,  M,  M0,  PM)
_add("<X,MINUS,ZERO,PLUS,_,_>",  X,  M,  Z,  P,  _0P, PM)
_add("<X,MINUS,ZERO,MINUS,_,_>", X,  M,  Z,  M,  _0M, PM)

_add("<X,ZERO,PLUS,_,P_TO_M,_>",  X,  Z,  P,  Z,  PM_, P)
_add("<X,ZERO,PLUS,_,M_TO_P,_>",  X,  Z,  P,  Z,  MP,  P)
_add("<X,ZERO,MINUS,_,P_TO_M,_>", X,  Z,  M,  Z,  PM_, M)
_add("<X,ZERO,MINUS,_,M_TO_P,_>", X,  Z,  M,  Z,  MP,  M)

# ── PAR_SAME (12 instantiated representations → 6 compact forms) ─────────────
_add("<PAR_SAME,_,_,PLUS,_,PLUS>",   PS, P, P, P, P0,  P)
_add("<PAR_SAME,_,_,PLUS,_,PLUS>",   PS, M, M, P, _0P, P)
_add("<PAR_SAME,_,_,PLUS,_,ZERO>",   PS, P, P, P, P0,  Z)
_add("<PAR_SAME,_,_,PLUS,_,ZERO>",   PS, M, M, P, _0P, Z)
_add("<PAR_SAME,_,_,PLUS,_,MINUS>",  PS, P, P, P, P0,  M)
_add("<PAR_SAME,_,_,PLUS,_,MINUS>",  PS, M, M, P, _0P, M)
_add("<PAR_SAME,_,_,MINUS,_,PLUS>",  PS, P, P, M, M0,  P)
_add("<PAR_SAME,_,_,MINUS,_,PLUS>",  PS, M, M, M, _0M, P)
_add("<PAR_SAME,_,_,MINUS,_,ZERO>",  PS, P, P, M, M0,  Z)
_add("<PAR_SAME,_,_,MINUS,_,ZERO>",  PS, M, M, M, _0M, Z)
_add("<PAR_SAME,_,_,MINUS,_,MINUS>", PS, P, P, M, M0,  M)
_add("<PAR_SAME,_,_,MINUS,_,MINUS>", PS, M, M, M, _0M, M)

# ── PAR_OPP (12 instantiated representations → 6 compact forms) ──────────────
_add("<PAR_OPP,_,_,PLUS,_,PLUS>",   PO, P, M, P, P0,  P)
_add("<PAR_OPP,_,_,PLUS,_,PLUS>",   PO, M, P, P, _0P, P)
_add("<PAR_OPP,_,_,PLUS,_,ZERO>",   PO, P, M, P, P0,  Z)
_add("<PAR_OPP,_,_,PLUS,_,ZERO>",   PO, M, P, P, _0P, Z)
_add("<PAR_OPP,_,_,PLUS,_,MINUS>",  PO, P, M, P, P0,  M)
_add("<PAR_OPP,_,_,PLUS,_,MINUS>",  PO, M, P, P, _0P, M)
_add("<PAR_OPP,_,_,MINUS,_,PLUS>",  PO, P, M, M, M0,  P)
_add("<PAR_OPP,_,_,MINUS,_,PLUS>",  PO, M, P, M, _0M, P)
_add("<PAR_OPP,_,_,MINUS,_,ZERO>",  PO, P, M, M, M0,  Z)
_add("<PAR_OPP,_,_,MINUS,_,ZERO>",  PO, M, P, M, _0M, Z)
_add("<PAR_OPP,_,_,MINUS,_,MINUS>", PO, P, M, M, M0,  M)
_add("<PAR_OPP,_,_,MINUS,_,MINUS>", PO, M, P, M, _0M, M)

# ── OVL_SAME (4 instantiated representations → 2 compact forms) ──────────────
_add("<OVL_SAME,_,_,_,_,PLUS>",  OS, Z,  P,  Z,  _00, P)
_add("<OVL_SAME,_,_,_,_,PLUS>",  OS, M,  Z,  Z,  _00, PM)
_add("<OVL_SAME,_,_,_,_,MINUS>", OS, Z,  M,  Z,  _00, M)
_add("<OVL_SAME,_,_,_,_,MINUS>", OS, P,  Z,  Z,  _00, PM)

# ── OVL_OPP (4 instantiated representations → 2 compact forms) ───────────────
_add("<OVL_OPP,_,_,_,_,PLUS>",  OO, Z,  P,  Z,  _00, P)
_add("<OVL_OPP,_,_,_,_,PLUS>",  OO, P,  Z,  Z,  _00, PM)
_add("<OVL_OPP,_,_,_,_,MINUS>", OO, Z,  M,  Z,  _00, M)
_add("<OVL_OPP,_,_,_,_,MINUS>", OO, M,  Z,  Z,  _00, PM)


# ── Public API ────────────────────────────────────────────────────────────────

def get_compact(r: Representation) -> Optional[str]:
    """
    Returns the compact form of the given instantiated representation,
    or None if the representation is not in the catalogue.
    """
    return _CATALOGUE.get(r)

# Backward-compatibility alias
get_br = get_compact


def get_instantiated(br: str) -> List[Representation]:
    """
    Returns all instantiated representations that realise the given
    compact form. Most compact forms have one instantiated representation;
    PAR and OVL types may have two due to geometric ambivalence in
    wildcard components.
    """
    return [r for r, n in _CATALOGUE.items() if n == br]

# Backward-compatibility alias
get_tuples = get_instantiated


def all_relations() -> Dict[Representation, str]:
    """Returns an immutable view of the full catalogue."""
    return dict(_CATALOGUE)


def all_notations() -> List[str]:
    """Returns the list of the 48 distinct compact forms."""
    seen = []
    for br in _CATALOGUE.values():
        if br not in seen:
            seen.append(br)
    return seen
