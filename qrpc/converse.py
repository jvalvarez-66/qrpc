"""
converse.py
-----------
Converse operation for QRPC basic relations.

Given a canonical relation string r describing the configuration of O_i
w.r.t. O_j, the converse r^∪ describes the same configuration as seen
from O_j w.r.t. O_i — the two objects swap roles.

The operation is defined directly over canonical (compact) form strings,
which are the minimal unique identifiers of each of the 48 basic QRPC
relations. No instantiated representation is needed: the converse mapping
is structurally determined by the canonical components alone.
"""

from __future__ import annotations
from typing import Optional

# ── Canonical converse table (str → str) ──────────────────────────────────────
# Derived from the geometric analysis in Table 4 of the paper.
# For X,c1==c2 relations (++/--), both LR and OFB are inverted.
# For X,c1!=c2 relations (+-/-+), only LR changes (OFB preserved).
# PAR_SAME: both LR and OFB are inverted.
# PAR_OPP: self-converse (all).
# OVL_SAME: OFB inverted.
# OVL_OPP: self-converse (all).

_CONVERSE: dict[str, str] = {
    # ── X regular c1==c2 (LR inverted, OFB inverted) ──────────────────────────
    "<X,PLUS,PLUS,PLUS,_,PLUS>":    "<X,PLUS,PLUS,MINUS,_,MINUS>",
    "<X,PLUS,PLUS,PLUS,_,ZERO>":    "<X,PLUS,PLUS,MINUS,_,ZERO>",
    "<X,PLUS,PLUS,PLUS,_,MINUS>":   "<X,PLUS,PLUS,MINUS,_,PLUS>",
    "<X,PLUS,PLUS,MINUS,_,PLUS>":   "<X,PLUS,PLUS,PLUS,_,MINUS>",
    "<X,PLUS,PLUS,MINUS,_,ZERO>":   "<X,PLUS,PLUS,PLUS,_,ZERO>",
    "<X,PLUS,PLUS,MINUS,_,MINUS>":  "<X,PLUS,PLUS,PLUS,_,PLUS>",

    "<X,MINUS,MINUS,PLUS,_,PLUS>":  "<X,MINUS,MINUS,MINUS,_,MINUS>",
    "<X,MINUS,MINUS,PLUS,_,ZERO>":  "<X,MINUS,MINUS,MINUS,_,ZERO>",
    "<X,MINUS,MINUS,PLUS,_,MINUS>": "<X,MINUS,MINUS,MINUS,_,PLUS>",
    "<X,MINUS,MINUS,MINUS,_,PLUS>": "<X,MINUS,MINUS,PLUS,_,MINUS>",
    "<X,MINUS,MINUS,MINUS,_,ZERO>": "<X,MINUS,MINUS,PLUS,_,ZERO>",
    "<X,MINUS,MINUS,MINUS,_,MINUS>":"<X,MINUS,MINUS,PLUS,_,PLUS>",

    # ── X regular c1!=c2 (LR swaps c1/c2, OFB preserved) ─────────────────────
    "<X,PLUS,MINUS,PLUS,_,PLUS>":   "<X,MINUS,PLUS,PLUS,_,PLUS>",
    "<X,PLUS,MINUS,PLUS,_,ZERO>":   "<X,MINUS,PLUS,PLUS,_,ZERO>",
    "<X,PLUS,MINUS,PLUS,_,MINUS>":  "<X,MINUS,PLUS,PLUS,_,MINUS>",
    "<X,PLUS,MINUS,MINUS,_,PLUS>":  "<X,MINUS,PLUS,MINUS,_,PLUS>",
    "<X,PLUS,MINUS,MINUS,_,ZERO>":  "<X,MINUS,PLUS,MINUS,_,ZERO>",
    "<X,PLUS,MINUS,MINUS,_,MINUS>": "<X,MINUS,PLUS,MINUS,_,MINUS>",

    "<X,MINUS,PLUS,PLUS,_,PLUS>":   "<X,PLUS,MINUS,PLUS,_,PLUS>",
    "<X,MINUS,PLUS,PLUS,_,ZERO>":   "<X,PLUS,MINUS,PLUS,_,ZERO>",
    "<X,MINUS,PLUS,PLUS,_,MINUS>":  "<X,PLUS,MINUS,PLUS,_,MINUS>",
    "<X,MINUS,PLUS,MINUS,_,PLUS>":  "<X,PLUS,MINUS,MINUS,_,PLUS>",
    "<X,MINUS,PLUS,MINUS,_,ZERO>":  "<X,PLUS,MINUS,MINUS,_,ZERO>",
    "<X,MINUS,PLUS,MINUS,_,MINUS>": "<X,PLUS,MINUS,MINUS,_,MINUS>",

    # ── X boundary ────────────────────────────────────────────────────────────
    "<X,PLUS,ZERO,PLUS,_,_>":       "<X,ZERO,PLUS,_,M_TO_P,_>",
    "<X,PLUS,ZERO,MINUS,_,_>":      "<X,ZERO,PLUS,_,P_TO_M,_>",
    "<X,MINUS,ZERO,PLUS,_,_>":      "<X,ZERO,MINUS,_,P_TO_M,_>",
    "<X,MINUS,ZERO,MINUS,_,_>":     "<X,ZERO,MINUS,_,M_TO_P,_>",

    "<X,ZERO,PLUS,_,P_TO_M,_>":     "<X,PLUS,ZERO,MINUS,_,_>",
    "<X,ZERO,PLUS,_,M_TO_P,_>":     "<X,PLUS,ZERO,PLUS,_,_>",
    "<X,ZERO,MINUS,_,P_TO_M,_>":    "<X,MINUS,ZERO,PLUS,_,_>",
    "<X,ZERO,MINUS,_,M_TO_P,_>":    "<X,MINUS,ZERO,MINUS,_,_>",

    # ── PAR_SAME — LR and OFB both inverted ───────────────────────────────────
    "<PAR_SAME,_,_,PLUS,_,PLUS>":   "<PAR_SAME,_,_,MINUS,_,MINUS>",
    "<PAR_SAME,_,_,PLUS,_,ZERO>":   "<PAR_SAME,_,_,MINUS,_,ZERO>",
    "<PAR_SAME,_,_,PLUS,_,MINUS>":  "<PAR_SAME,_,_,MINUS,_,PLUS>",
    "<PAR_SAME,_,_,MINUS,_,PLUS>":  "<PAR_SAME,_,_,PLUS,_,MINUS>",
    "<PAR_SAME,_,_,MINUS,_,ZERO>":  "<PAR_SAME,_,_,PLUS,_,ZERO>",
    "<PAR_SAME,_,_,MINUS,_,MINUS>": "<PAR_SAME,_,_,PLUS,_,PLUS>",

    # ── PAR_OPP — self-converse ────────────────────────────────────────────────
    "<PAR_OPP,_,_,PLUS,_,PLUS>":    "<PAR_OPP,_,_,PLUS,_,PLUS>",
    "<PAR_OPP,_,_,PLUS,_,ZERO>":    "<PAR_OPP,_,_,PLUS,_,ZERO>",
    "<PAR_OPP,_,_,PLUS,_,MINUS>":   "<PAR_OPP,_,_,PLUS,_,MINUS>",
    "<PAR_OPP,_,_,MINUS,_,PLUS>":   "<PAR_OPP,_,_,MINUS,_,PLUS>",
    "<PAR_OPP,_,_,MINUS,_,ZERO>":   "<PAR_OPP,_,_,MINUS,_,ZERO>",
    "<PAR_OPP,_,_,MINUS,_,MINUS>":  "<PAR_OPP,_,_,MINUS,_,MINUS>",

    # ── OVL_SAME — OFB inverted ───────────────────────────────────────────────
    "<OVL_SAME,_,_,_,_,PLUS>":      "<OVL_SAME,_,_,_,_,MINUS>",
    "<OVL_SAME,_,_,_,_,MINUS>":     "<OVL_SAME,_,_,_,_,PLUS>",

    # ── OVL_OPP — self-converse ───────────────────────────────────────────────
    "<OVL_OPP,_,_,_,_,PLUS>":       "<OVL_OPP,_,_,_,_,PLUS>",
    "<OVL_OPP,_,_,_,_,MINUS>":      "<OVL_OPP,_,_,_,_,MINUS>",
}


def converse(br: str) -> Optional[str]:
    """
    Returns the converse r^∪ of the given canonical basic relation string.
    Returns None if br is not a valid canonical relation.
    """
    return _CONVERSE.get(br)


def converse_set(brs: frozenset[str]) -> frozenset[str]:
    """
    Returns the converse of a general relation (frozenset of canonical strings).
    """
    result = set()
    for br in brs:
        c = _CONVERSE.get(br)
        if c:
            result.add(c)
    return frozenset(result)
