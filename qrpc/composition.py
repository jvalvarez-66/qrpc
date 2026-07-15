"""
composition.py
--------------
QRPC composition operation.

Implements the algorithm from Section 4.7 / Appendix C of the paper.

Given s12 and s23 as canonical relation strings, computes the general
relation R13 as a frozenset of canonical strings.

The algorithm operates exclusively on canonical relation strings throughout:
input, output, and all internal π-rotation steps. Instantiated Representation
objects are not used anywhere in this module.

Algorithm:
  1. Determine the rule number via the dynamic rules table.
  2. Rule 0: look up directly in the precomputed Z table.
  3. Rules 1-7: apply π-rotations to (s12, s23) to obtain an equivalent
     Z-pair, look that up, then apply the inverse rotation to recover R13.

Seven transformation rules:
  Rule 1 (1π_23):     Z-query=(α(s12), s23);        output=α on each element
  Rule 2 (12π_3):     Z-query=(β(s12), α(s23));      output=identity
  Rule 3 (123π):      Z-query=(s12, β(s23));          output=β on each element
  Rule 4 (1π_2π_3):   Z-query=(γ(s12), α(s23));      output=α on each element
  Rule 5 (12π_3π):    Z-query=(β(s12), γ(s23));       output=β on each element
  Rule 6 (1π_23π):    Z-query=(α(s12), β(s23));       output=γ on each element
  Rule 7 (1π_2π_3π):  Z-query=(γ(s12), γ(s23));       output=γ on each element
"""

from __future__ import annotations
from typing import Dict, FrozenSet, Set, Optional
from .representation import P12, QVal, DLR, Representation
from .pi_rotations import rot_alpha, rot_beta, rot_gamma, _ALPHA, _BETA, _GAMMA
from .table48 import all_relations, all_notations
from .z_compositions import lookup as z_lookup, get_table as z_get_table

# ── Row/column class (used only during _build_tables) ────────────────────────

def _row_class(r: Representation) -> int:
    """
    Maps a basic relation to its row/column class index (0-23).
    Used only during table initialisation.
    """
    p, c1, c2, lr, dlr, ofb = r.p, r.c1, r.c2, r.lr, r.dlr, r.ofb
    P, Z, M = QVal.PLUS, QVal.ZERO, QVal.MINUS
    PM_ = DLR.P_TO_M

    if p == P12.X:
        if   c1 == P and c2 == P:  return 0 if lr == P else 1
        elif c1 == P and c2 == M:  return 2 if lr == P else 3
        elif c1 == M and c2 == P:  return 4 if lr == P else 5
        elif c1 == M and c2 == M:  return 6 if lr == P else 7
        elif c1 == P and c2 == Z:  return 8 if lr == P else 9
        elif c1 == Z and c2 == P:  return 10 if dlr == PM_ else 11
        elif c1 == M and c2 == Z:  return 12 if lr == P else 13
        elif c1 == Z and c2 == M:  return 14 if dlr == PM_ else 15
        raise ValueError(f"_row_class: unknown X subtype {r}")
    elif p == P12.PAR_SAME: return 16 if lr == P else 17
    elif p == P12.OVL_SAME: return 18 if _ovl_same_plus(r) else 19
    elif p == P12.PAR_OPP:  return 20 if lr == P else 21
    elif p == P12.OVL_OPP:  return 22 if _ovl_opp_plus(r) else 23
    raise ValueError(f"_row_class: unknown P12 {p}")


def _ovl_same_plus(r: Representation) -> bool:
    if r.ofb == QVal.PLUS:  return True
    if r.ofb == QVal.MINUS: return False
    return r.c1 == QVal.MINUS and r.c2 == QVal.ZERO


def _ovl_opp_plus(r: Representation) -> bool:
    if r.ofb == QVal.PLUS:  return True
    if r.ofb == QVal.MINUS: return False
    return r.c1 == QVal.PLUS and r.c2 == QVal.ZERO


# ── Dynamic rules table (24×24) ───────────────────────────────────────────────

_RULES: Dict[tuple, int] = {}        # (row_class, col_class) → rule 0-7
_BR_TO_CLASS: Dict[str, int] = {}    # canonical string → row/column class
_UNASSIGNED: list = []


def _build_tables() -> None:
    """
    Precomputes at import time:
      - _BR_TO_CLASS : canonical string → row/column class index (0-23)
      - _RULES       : (row_class, col_class) → rule number (0-7)

    Instantiated Representation objects are used here only to compute the
    row class index. The rotation maps (_ALPHA, _BETA, _GAMMA) from
    pi_rotations.py are used directly as canonical-string → canonical-string
    lookups; no Representation is instantiated during the rotation steps.
    """
    # Build _BR_TO_CLASS: one representative Representation per canonical string
    seen: set[str] = set()
    for rep, br in all_relations().items():
        if br not in seen:
            seen.add(br)
            _BR_TO_CLASS[br] = _row_class(rep)

    # Initialise rules table
    for r in range(24):
        for c in range(24):
            _RULES[(r, c)] = -1

    rotations = [
        (0, lambda a, b: (a,              b)),
        (1, lambda a, b: (_ALPHA[a],      b)),
        (2, lambda a, b: (_BETA[a],       _ALPHA[b])),
        (3, lambda a, b: (a,              _BETA[b])),
        (4, lambda a, b: (_GAMMA[a],      _ALPHA[b])),
        (5, lambda a, b: (_BETA[a],       _GAMMA[b])),
        (6, lambda a, b: (_ALPHA[a],      _BETA[b])),
        (7, lambda a, b: (_GAMMA[a],      _GAMMA[b])),
    ]

    for z_key in z_get_table():
        sep = z_key.index('|')
        br12, br23 = z_key[:sep], z_key[sep+1:]
        if br12 not in _BR_TO_CLASS or br23 not in _BR_TO_CLASS:
            continue

        for rule, rot_fn in rotations:
            r12, r23 = rot_fn(br12, br23)
            if r12 not in _BR_TO_CLASS or r23 not in _BR_TO_CLASS:
                continue
            row = _BR_TO_CLASS[r12]
            col = _BR_TO_CLASS[r23]
            if _RULES[(row, col)] == -1:
                _RULES[(row, col)] = rule

    for r in range(24):
        for c in range(24):
            if _RULES[(r, c)] == -1:
                _UNASSIGNED.append((r, c))
                _RULES[(r, c)] = 0


_build_tables()


# ── Public rule query ─────────────────────────────────────────────────────────

def get_rule(s12: str, s23: str) -> int:
    """Returns the rule number (0-7) for the composition s12 ∘ s23."""
    if s12 not in _BR_TO_CLASS or s23 not in _BR_TO_CLASS:
        raise ValueError(f"Unknown canonical relation: {s12!r} or {s23!r}")
    return _RULES[(_BR_TO_CLASS[s12], _BR_TO_CLASS[s23])]


def get_rules_table() -> Dict[tuple, int]:
    """Returns an immutable copy of the 24×24 rules table."""
    return dict(_RULES)


# ── Internal helpers (all operate on canonical strings) ───────────────────────

def _comp_in_z(s12: str, s23: str) -> FrozenSet[str]:
    """Direct Z-table lookup. Returns frozenset of canonical strings."""
    result = z_lookup(s12, s23)
    return frozenset(result) if result else frozenset()


def _rot(br: str, rot: Optional[str]) -> str:
    """Apply a named π-rotation to a canonical string."""
    if rot is None:
        return br
    return {'a': _ALPHA, 'b': _BETA, 'g': _GAMMA}[rot][br]


def _rot_set(brs: FrozenSet[str], rot: Optional[str]) -> FrozenSet[str]:
    """Apply a named π-rotation to every element of a frozenset."""
    if rot is None:
        return brs
    table = {'a': _ALPHA, 'b': _BETA, 'g': _GAMMA}[rot]
    return frozenset(table[br] for br in brs)


# ── Rule implementations ──────────────────────────────────────────────────────

def _rule0(s12, s23): return _comp_in_z(s12, s23)
def _rule1(s12, s23): return _rot_set(_comp_in_z(_ALPHA[s12], s23),          'a')
def _rule2(s12, s23): return           _comp_in_z(_BETA[s12],  _ALPHA[s23])
def _rule3(s12, s23): return _rot_set(_comp_in_z(s12,          _BETA[s23]),  'b')
def _rule4(s12, s23): return _rot_set(_comp_in_z(_GAMMA[s12],  _ALPHA[s23]), 'a')
def _rule5(s12, s23): return _rot_set(_comp_in_z(_BETA[s12],   _GAMMA[s23]), 'b')
def _rule6(s12, s23): return _rot_set(_comp_in_z(_ALPHA[s12],  _BETA[s23]),  'g')
def _rule7(s12, s23): return _rot_set(_comp_in_z(_GAMMA[s12],  _GAMMA[s23]), 'g')

_RULE_FNS = [_rule0, _rule1, _rule2, _rule3, _rule4, _rule5, _rule6, _rule7]


# ── Public API ────────────────────────────────────────────────────────────────

def compose_basic(s12: str, s23: str) -> FrozenSet[str]:
    """
    Computes the weak composition s12 ∘ s23 of two basic relations.
    s12, s23: canonical relation strings.
    Returns a frozenset of canonical strings.
    """
    return _RULE_FNS[get_rule(s12, s23)](s12, s23)


def compose(r12: FrozenSet[str], r23: FrozenSet[str]) -> FrozenSet[str]:
    """
    Computes the composition of two general relations (frozensets of canonical strings).
    Result = ⋃ { compose_basic(s12, s23) | s12 ∈ r12, s23 ∈ r23 }.
    """
    result: Set[str] = set()
    for s12 in r12:
        for s23 in r23:
            result.update(compose_basic(s12, s23))
    return frozenset(result)


def explain_basic_composition(s12: str, s23: str) -> dict:
    """
    Returns a structured trace for the weak composition s12 ∘ s23.
    s12, s23: canonical relation strings.
    """
    rule = get_rule(s12, s23)

    in_rot  = {0: (None,None), 1: ('a',None), 2: ('b','a'), 3: (None,'b'),
               4: ('g','a'),   5: ('b','g'),  6: ('a','b'), 7: ('g','g')}
    out_rot = {0: None, 1: 'a', 2: None, 3: 'b', 4: 'a', 5: 'b', 6: 'g', 7: 'g'}

    s12_z      = _rot(s12, in_rot[rule][0])
    s23_z      = _rot(s23, in_rot[rule][1])
    z_result   = _comp_in_z(s12_z, s23_z)
    final      = _rot_set(z_result, out_rot[rule])

    return {
        'rule':               rule,
        'row_class':          _BR_TO_CLASS[s12],
        'col_class':          _BR_TO_CLASS[s23],
        'input_r12_br':       s12,
        'input_r23_br':       s23,
        'z_r12_br':           s12_z,
        'z_r23_br':           s23_z,
        'input_rotation_r12': in_rot[rule][0],
        'input_rotation_r23': in_rot[rule][1],
        'output_rotation':    out_rot[rule],
        'z_result_ncs':       sorted(z_result),
        'final_result_ncs':   sorted(final),
        'direct_z_lookup':    rule == 0,
    }
