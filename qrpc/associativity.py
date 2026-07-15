"""
associativity.py
----------------
Checks the associativity property of QRPC composition for a chain of three
consecutive basic relations.

Definition:
  (R₁₂ ∘ R₂₃) ∘ R₃₄  =  R₁₂ ∘ (R₂₃ ∘ R₃₄)

All operations work exclusively on canonical relation strings.

The full 48³ scan (check_full_associativity) uses a pre-computed BR-level
composition table (~290× speedup over naive approach, ~1.5s total).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet, Optional
from .composition import compose_basic, compose
from .table48 import all_notations

def _p(br: str) -> str:
    """Pretty-print a BR string for display."""
    try:
        from gui.rules_table_panel import pretty_br
        return pretty_br(br)
    except Exception:
        return br


# ── BR-level composition table (built once on first full scan) ────────────────

_BR_COMP: Optional[dict[tuple[str, str], frozenset[str]]] = None


def _get_br_comp() -> dict[tuple[str, str], frozenset[str]]:
    """
    Returns (building on first call) the full 48×48 BR composition table.
    Each entry: (br12, br23) → frozenset of canonical result BR strings.
    Build time: ~0.3s (one-off cost).
    """
    global _BR_COMP
    if _BR_COMP is not None:
        return _BR_COMP
    brs = all_notations()
    table: dict[tuple[str, str], frozenset[str]] = {}
    for br12 in brs:
        for br23 in brs:
            table[(br12, br23)] = compose_basic(br12, br23)
    _BR_COMP = table
    return _BR_COMP


# ── Single-triplet check (canonical strings, full detail) ─────────────────────

@dataclass(frozen=True)
class AssociativityResult:
    """Full outcome of an associativity check on a three-step chain."""
    br12: str
    br23: str
    br34: str
    intermediate_left:  FrozenSet[str]
    intermediate_right: FrozenSet[str]
    left_result:  FrozenSet[str]
    right_result: FrozenSet[str]

    @property
    def is_associative(self) -> bool:
        return self.left_result == self.right_result

    @property
    def only_in_left(self) -> FrozenSet[str]:
        return self.left_result - self.right_result

    @property
    def only_in_right(self) -> FrozenSet[str]:
        return self.right_result - self.left_result

    def __str__(self) -> str:
        def fmt(s): return '∅' if not s else '{ ' + ', '.join(_p(br) for br in sorted(s)) + ' }'
        lines = [
            "=== Associativity Check ===",
            f"  R₁₂ = {_p(self.br12)}",
            f"  R₂₃ = {_p(self.br23)}",
            f"  R₃₄ = {_p(self.br34)}",
            "",
            f"  Intermediate left  (R₁₂ ∘ R₂₃) = {fmt(self.intermediate_left)}",
            f"  Intermediate right (R₂₃ ∘ R₃₄) = {fmt(self.intermediate_right)}",
            "",
            f"  Left  result (R₁₂ ∘ R₂₃) ∘ R₃₄  = {fmt(self.left_result)}",
            f"  Right result  R₁₂ ∘ (R₂₃ ∘ R₃₄) = {fmt(self.right_result)}",
            "",
        ]
        if self.is_associative:
            lines.append("  RESULT: ASSOCIATIVE  (both groupings equal)")
        else:
            lines.append("  RESULT: NOT ASSOCIATIVE")
            lines.append(f"    Only in left:  {[_p(br) for br in sorted(self.only_in_left)] or '∅'}")
            lines.append(f"    Only in right: {[_p(br) for br in sorted(self.only_in_right)] or '∅'}")
        return "\n".join(lines)


def check_associativity(br12: str, br23: str, br34: str) -> AssociativityResult:
    """Checks associativity for R₁₂ ∘ R₂₃ ∘ R₃₄ given canonical strings."""
    g_left  = compose_basic(br12, br23)
    g_right = compose_basic(br23, br34)
    left    = compose(g_left,          frozenset([br34]))
    right   = compose(frozenset([br12]), g_right)
    return AssociativityResult(
        br12=br12, br23=br23, br34=br34,
        intermediate_left=g_left,
        intermediate_right=g_right,
        left_result=left,
        right_result=right,
    )


# ── Fast BR-level result (for the full scan) ──────────────────────────────────

@dataclass(frozen=True)
class AssociativityResultBR:
    """Lightweight result for the 48³ scan — BR strings only."""
    br12: str
    br23: str
    br34: str
    left_brs:  frozenset[str]
    right_brs: frozenset[str]
    intermediate_left_brs:  frozenset[str]
    intermediate_right_brs: frozenset[str]

    @property
    def is_associative(self) -> bool:
        return self.left_brs == self.right_brs

    @property
    def only_in_left(self) -> frozenset[str]:
        return self.left_brs - self.right_brs

    @property
    def only_in_right(self) -> frozenset[str]:
        return self.right_brs - self.left_brs

    def detail_text(self) -> str:
        def fmt(s): return '∅' if not s else '{ ' + ', '.join(_p(br) for br in sorted(s)) + ' }'
        lines = [
            f"R₁₂ = {_p(self.br12)}",
            f"R₂₃ = {_p(self.br23)}",
            f"R₃₄ = {_p(self.br34)}",
            "",
            f"Intermediate left  (R₁₂ ∘ R₂₃): {fmt(self.intermediate_left_brs)}",
            f"Intermediate right (R₂₃ ∘ R₃₄): {fmt(self.intermediate_right_brs)}",
            "",
            f"Left  result  (R₁₂ ∘ R₂₃) ∘ R₃₄  ({len(self.left_brs)} relations):",
        ]
        for br in sorted(self.left_brs):
            lines.append(f"  • {_p(br)}")
        lines += ["",
            f"Right result   R₁₂ ∘ (R₂₃ ∘ R₃₄)  ({len(self.right_brs)} relations):",
        ]
        for br in sorted(self.right_brs):
            lines.append(f"  • {_p(br)}")
        if not self.is_associative:
            lines += ["", "DIFFERENCES:",
                f"  Only in left  ({len(self.only_in_left)}): "
                + (', '.join(_p(br) for br in sorted(self.only_in_left)) or '∅'),
                f"  Only in right ({len(self.only_in_right)}): "
                + (', '.join(_p(br) for br in sorted(self.only_in_right)) or '∅'),
            ]
        return "\n".join(lines)


# ── Full 48³ scan ─────────────────────────────────────────────────────────────

def check_full_associativity(progress_callback=None) -> list[AssociativityResultBR]:
    """
    Full 48³ = 110,592 combinatorial associativity check.

    Uses a pre-computed BR composition table for speed (~1.5s total,
    including the one-off table build of ~0.3s on first call).

    progress_callback: optional callable(done, total, failing)
    Returns list of AssociativityResultBR where is_associative is False.
    """
    comp = _get_br_comp()
    brs  = all_notations()
    total = len(brs) ** 3
    failing: list[AssociativityResultBR] = []
    done = 0

    for br12 in brs:
        for br23 in brs:
            g_left = comp[(br12, br23)]
            for br34 in brs:
                left: set[str] = set()
                for br in g_left:
                    left.update(comp.get((br, br34), ()))

                g_right = comp[(br23, br34)]
                right: set[str] = set()
                for br in g_right:
                    right.update(comp.get((br12, br), ()))

                left_f  = frozenset(left)
                right_f = frozenset(right)

                if left_f != right_f:
                    failing.append(AssociativityResultBR(
                        br12=br12, br23=br23, br34=br34,
                        left_brs=left_f, right_brs=right_f,
                        intermediate_left_brs=g_left,
                        intermediate_right_brs=g_right,
                    ))

                done += 1
                if progress_callback and done % 5000 == 0:
                    progress_callback(done, total, len(failing))

    if progress_callback:
        progress_callback(total, total, len(failing))

    return failing
