"""
pi_rotations.py
---------------
π-rotation transformation functions (Table 5 of the paper).

Table 5 defines five component-level mappings (T_P, T_D, T_D^α, T_D^β, T_D^γ)
over the alphabets Σ_P, Σ_D and Σ_D*.  These combine into three composite
π-rotations on a full canonical relation string:

  α(s) : T_P(P), T_D(C₁), C₂,       LR,       T_D*^α(DLR), OFB
  β(s) : T_P(P), C₁,      T_D(C₂),  T_D(LR),  T_D*^β(DLR), T_D(OFB)
  γ(s) : P,      T_D(C₁), T_D(C₂),  T_D(LR),  T_D*^γ(DLR), T_D(OFB)

where T_D*^α and T_D*^β swap P_TO_M ↔ M_TO_P, and T_D*^γ is the identity
on those two values; all _ (wildcard) components are propagated unchanged.

The three public functions below implement α, β and γ directly as
canonical-string → canonical-string maps, with no dependence on
instantiated Representation objects.
"""

from __future__ import annotations

# ── α rotation: canonical string → canonical string ──────────────────────────

_ALPHA: dict[str, str] = {
    '<OVL_OPP,_,_,_,_,MINUS>'       : '<OVL_SAME,_,_,_,_,MINUS>',
    '<OVL_OPP,_,_,_,_,PLUS>'        : '<OVL_SAME,_,_,_,_,PLUS>',
    '<OVL_SAME,_,_,_,_,MINUS>'      : '<OVL_OPP,_,_,_,_,MINUS>',
    '<OVL_SAME,_,_,_,_,PLUS>'       : '<OVL_OPP,_,_,_,_,PLUS>',
    '<PAR_OPP,_,_,MINUS,_,MINUS>'   : '<PAR_SAME,_,_,MINUS,_,MINUS>',
    '<PAR_OPP,_,_,MINUS,_,PLUS>'    : '<PAR_SAME,_,_,MINUS,_,PLUS>',
    '<PAR_OPP,_,_,MINUS,_,ZERO>'    : '<PAR_SAME,_,_,MINUS,_,ZERO>',
    '<PAR_OPP,_,_,PLUS,_,MINUS>'    : '<PAR_SAME,_,_,PLUS,_,MINUS>',
    '<PAR_OPP,_,_,PLUS,_,PLUS>'     : '<PAR_SAME,_,_,PLUS,_,PLUS>',
    '<PAR_OPP,_,_,PLUS,_,ZERO>'     : '<PAR_SAME,_,_,PLUS,_,ZERO>',
    '<PAR_SAME,_,_,MINUS,_,MINUS>'  : '<PAR_OPP,_,_,MINUS,_,MINUS>',
    '<PAR_SAME,_,_,MINUS,_,PLUS>'   : '<PAR_OPP,_,_,MINUS,_,PLUS>',
    '<PAR_SAME,_,_,MINUS,_,ZERO>'   : '<PAR_OPP,_,_,MINUS,_,ZERO>',
    '<PAR_SAME,_,_,PLUS,_,MINUS>'   : '<PAR_OPP,_,_,PLUS,_,MINUS>',
    '<PAR_SAME,_,_,PLUS,_,PLUS>'    : '<PAR_OPP,_,_,PLUS,_,PLUS>',
    '<PAR_SAME,_,_,PLUS,_,ZERO>'    : '<PAR_OPP,_,_,PLUS,_,ZERO>',
    '<X,MINUS,MINUS,MINUS,_,MINUS>' : '<X,PLUS,MINUS,MINUS,_,MINUS>',
    '<X,MINUS,MINUS,MINUS,_,PLUS>'  : '<X,PLUS,MINUS,MINUS,_,PLUS>',
    '<X,MINUS,MINUS,MINUS,_,ZERO>'  : '<X,PLUS,MINUS,MINUS,_,ZERO>',
    '<X,MINUS,MINUS,PLUS,_,MINUS>'  : '<X,PLUS,MINUS,PLUS,_,MINUS>',
    '<X,MINUS,MINUS,PLUS,_,PLUS>'   : '<X,PLUS,MINUS,PLUS,_,PLUS>',
    '<X,MINUS,MINUS,PLUS,_,ZERO>'   : '<X,PLUS,MINUS,PLUS,_,ZERO>',
    '<X,MINUS,PLUS,MINUS,_,MINUS>'  : '<X,PLUS,PLUS,MINUS,_,MINUS>',
    '<X,MINUS,PLUS,MINUS,_,PLUS>'   : '<X,PLUS,PLUS,MINUS,_,PLUS>',
    '<X,MINUS,PLUS,MINUS,_,ZERO>'   : '<X,PLUS,PLUS,MINUS,_,ZERO>',
    '<X,MINUS,PLUS,PLUS,_,MINUS>'   : '<X,PLUS,PLUS,PLUS,_,MINUS>',
    '<X,MINUS,PLUS,PLUS,_,PLUS>'    : '<X,PLUS,PLUS,PLUS,_,PLUS>',
    '<X,MINUS,PLUS,PLUS,_,ZERO>'    : '<X,PLUS,PLUS,PLUS,_,ZERO>',
    '<X,MINUS,ZERO,MINUS,_,_>'      : '<X,PLUS,ZERO,MINUS,_,_>',
    '<X,MINUS,ZERO,PLUS,_,_>'       : '<X,PLUS,ZERO,PLUS,_,_>',
    '<X,PLUS,MINUS,MINUS,_,MINUS>'  : '<X,MINUS,MINUS,MINUS,_,MINUS>',
    '<X,PLUS,MINUS,MINUS,_,PLUS>'   : '<X,MINUS,MINUS,MINUS,_,PLUS>',
    '<X,PLUS,MINUS,MINUS,_,ZERO>'   : '<X,MINUS,MINUS,MINUS,_,ZERO>',
    '<X,PLUS,MINUS,PLUS,_,MINUS>'   : '<X,MINUS,MINUS,PLUS,_,MINUS>',
    '<X,PLUS,MINUS,PLUS,_,PLUS>'    : '<X,MINUS,MINUS,PLUS,_,PLUS>',
    '<X,PLUS,MINUS,PLUS,_,ZERO>'    : '<X,MINUS,MINUS,PLUS,_,ZERO>',
    '<X,PLUS,PLUS,MINUS,_,MINUS>'   : '<X,MINUS,PLUS,MINUS,_,MINUS>',
    '<X,PLUS,PLUS,MINUS,_,PLUS>'    : '<X,MINUS,PLUS,MINUS,_,PLUS>',
    '<X,PLUS,PLUS,MINUS,_,ZERO>'    : '<X,MINUS,PLUS,MINUS,_,ZERO>',
    '<X,PLUS,PLUS,PLUS,_,MINUS>'    : '<X,MINUS,PLUS,PLUS,_,MINUS>',
    '<X,PLUS,PLUS,PLUS,_,PLUS>'     : '<X,MINUS,PLUS,PLUS,_,PLUS>',
    '<X,PLUS,PLUS,PLUS,_,ZERO>'     : '<X,MINUS,PLUS,PLUS,_,ZERO>',
    '<X,PLUS,ZERO,MINUS,_,_>'       : '<X,MINUS,ZERO,MINUS,_,_>',
    '<X,PLUS,ZERO,PLUS,_,_>'        : '<X,MINUS,ZERO,PLUS,_,_>',
    '<X,ZERO,MINUS,_,M_TO_P,_>'     : '<X,ZERO,MINUS,_,P_TO_M,_>',
    '<X,ZERO,MINUS,_,P_TO_M,_>'     : '<X,ZERO,MINUS,_,M_TO_P,_>',
    '<X,ZERO,PLUS,_,M_TO_P,_>'      : '<X,ZERO,PLUS,_,P_TO_M,_>',
    '<X,ZERO,PLUS,_,P_TO_M,_>'      : '<X,ZERO,PLUS,_,M_TO_P,_>',
}

# ── β rotation: canonical string → canonical string ──────────────────────────

_BETA: dict[str, str] = {
    '<OVL_OPP,_,_,_,_,MINUS>'       : '<OVL_SAME,_,_,_,_,PLUS>',
    '<OVL_OPP,_,_,_,_,PLUS>'        : '<OVL_SAME,_,_,_,_,MINUS>',
    '<OVL_SAME,_,_,_,_,MINUS>'      : '<OVL_OPP,_,_,_,_,PLUS>',
    '<OVL_SAME,_,_,_,_,PLUS>'       : '<OVL_OPP,_,_,_,_,MINUS>',
    '<PAR_OPP,_,_,MINUS,_,MINUS>'   : '<PAR_SAME,_,_,PLUS,_,PLUS>',
    '<PAR_OPP,_,_,MINUS,_,PLUS>'    : '<PAR_SAME,_,_,PLUS,_,MINUS>',
    '<PAR_OPP,_,_,MINUS,_,ZERO>'    : '<PAR_SAME,_,_,PLUS,_,ZERO>',
    '<PAR_OPP,_,_,PLUS,_,MINUS>'    : '<PAR_SAME,_,_,MINUS,_,PLUS>',
    '<PAR_OPP,_,_,PLUS,_,PLUS>'     : '<PAR_SAME,_,_,MINUS,_,MINUS>',
    '<PAR_OPP,_,_,PLUS,_,ZERO>'     : '<PAR_SAME,_,_,MINUS,_,ZERO>',
    '<PAR_SAME,_,_,MINUS,_,MINUS>'  : '<PAR_OPP,_,_,PLUS,_,PLUS>',
    '<PAR_SAME,_,_,MINUS,_,PLUS>'   : '<PAR_OPP,_,_,PLUS,_,MINUS>',
    '<PAR_SAME,_,_,MINUS,_,ZERO>'   : '<PAR_OPP,_,_,PLUS,_,ZERO>',
    '<PAR_SAME,_,_,PLUS,_,MINUS>'   : '<PAR_OPP,_,_,MINUS,_,PLUS>',
    '<PAR_SAME,_,_,PLUS,_,PLUS>'    : '<PAR_OPP,_,_,MINUS,_,MINUS>',
    '<PAR_SAME,_,_,PLUS,_,ZERO>'    : '<PAR_OPP,_,_,MINUS,_,ZERO>',
    '<X,MINUS,MINUS,MINUS,_,MINUS>' : '<X,MINUS,PLUS,PLUS,_,PLUS>',
    '<X,MINUS,MINUS,MINUS,_,PLUS>'  : '<X,MINUS,PLUS,PLUS,_,MINUS>',
    '<X,MINUS,MINUS,MINUS,_,ZERO>'  : '<X,MINUS,PLUS,PLUS,_,ZERO>',
    '<X,MINUS,MINUS,PLUS,_,MINUS>'  : '<X,MINUS,PLUS,MINUS,_,PLUS>',
    '<X,MINUS,MINUS,PLUS,_,PLUS>'   : '<X,MINUS,PLUS,MINUS,_,MINUS>',
    '<X,MINUS,MINUS,PLUS,_,ZERO>'   : '<X,MINUS,PLUS,MINUS,_,ZERO>',
    '<X,MINUS,PLUS,MINUS,_,MINUS>'  : '<X,MINUS,MINUS,PLUS,_,PLUS>',
    '<X,MINUS,PLUS,MINUS,_,PLUS>'   : '<X,MINUS,MINUS,PLUS,_,MINUS>',
    '<X,MINUS,PLUS,MINUS,_,ZERO>'   : '<X,MINUS,MINUS,PLUS,_,ZERO>',
    '<X,MINUS,PLUS,PLUS,_,MINUS>'   : '<X,MINUS,MINUS,MINUS,_,PLUS>',
    '<X,MINUS,PLUS,PLUS,_,PLUS>'    : '<X,MINUS,MINUS,MINUS,_,MINUS>',
    '<X,MINUS,PLUS,PLUS,_,ZERO>'    : '<X,MINUS,MINUS,MINUS,_,ZERO>',
    '<X,MINUS,ZERO,MINUS,_,_>'      : '<X,MINUS,ZERO,PLUS,_,_>',
    '<X,MINUS,ZERO,PLUS,_,_>'       : '<X,MINUS,ZERO,MINUS,_,_>',
    '<X,PLUS,MINUS,MINUS,_,MINUS>'  : '<X,PLUS,PLUS,PLUS,_,PLUS>',
    '<X,PLUS,MINUS,MINUS,_,PLUS>'   : '<X,PLUS,PLUS,PLUS,_,MINUS>',
    '<X,PLUS,MINUS,MINUS,_,ZERO>'   : '<X,PLUS,PLUS,PLUS,_,ZERO>',
    '<X,PLUS,MINUS,PLUS,_,MINUS>'   : '<X,PLUS,PLUS,MINUS,_,PLUS>',
    '<X,PLUS,MINUS,PLUS,_,PLUS>'    : '<X,PLUS,PLUS,MINUS,_,MINUS>',
    '<X,PLUS,MINUS,PLUS,_,ZERO>'    : '<X,PLUS,PLUS,MINUS,_,ZERO>',
    '<X,PLUS,PLUS,MINUS,_,MINUS>'   : '<X,PLUS,MINUS,PLUS,_,PLUS>',
    '<X,PLUS,PLUS,MINUS,_,PLUS>'    : '<X,PLUS,MINUS,PLUS,_,MINUS>',
    '<X,PLUS,PLUS,MINUS,_,ZERO>'    : '<X,PLUS,MINUS,PLUS,_,ZERO>',
    '<X,PLUS,PLUS,PLUS,_,MINUS>'    : '<X,PLUS,MINUS,MINUS,_,PLUS>',
    '<X,PLUS,PLUS,PLUS,_,PLUS>'     : '<X,PLUS,MINUS,MINUS,_,MINUS>',
    '<X,PLUS,PLUS,PLUS,_,ZERO>'     : '<X,PLUS,MINUS,MINUS,_,ZERO>',
    '<X,PLUS,ZERO,MINUS,_,_>'       : '<X,PLUS,ZERO,PLUS,_,_>',
    '<X,PLUS,ZERO,PLUS,_,_>'        : '<X,PLUS,ZERO,MINUS,_,_>',
    '<X,ZERO,MINUS,_,M_TO_P,_>'     : '<X,ZERO,PLUS,_,P_TO_M,_>',
    '<X,ZERO,MINUS,_,P_TO_M,_>'     : '<X,ZERO,PLUS,_,M_TO_P,_>',
    '<X,ZERO,PLUS,_,M_TO_P,_>'      : '<X,ZERO,MINUS,_,P_TO_M,_>',
    '<X,ZERO,PLUS,_,P_TO_M,_>'      : '<X,ZERO,MINUS,_,M_TO_P,_>',
}

# ── γ rotation: canonical string → canonical string ──────────────────────────

_GAMMA: dict[str, str] = {
    '<OVL_OPP,_,_,_,_,MINUS>'       : '<OVL_OPP,_,_,_,_,PLUS>',
    '<OVL_OPP,_,_,_,_,PLUS>'        : '<OVL_OPP,_,_,_,_,MINUS>',
    '<OVL_SAME,_,_,_,_,MINUS>'      : '<OVL_SAME,_,_,_,_,PLUS>',
    '<OVL_SAME,_,_,_,_,PLUS>'       : '<OVL_SAME,_,_,_,_,MINUS>',
    '<PAR_OPP,_,_,MINUS,_,MINUS>'   : '<PAR_OPP,_,_,PLUS,_,PLUS>',
    '<PAR_OPP,_,_,MINUS,_,PLUS>'    : '<PAR_OPP,_,_,PLUS,_,MINUS>',
    '<PAR_OPP,_,_,MINUS,_,ZERO>'    : '<PAR_OPP,_,_,PLUS,_,ZERO>',
    '<PAR_OPP,_,_,PLUS,_,MINUS>'    : '<PAR_OPP,_,_,MINUS,_,PLUS>',
    '<PAR_OPP,_,_,PLUS,_,PLUS>'     : '<PAR_OPP,_,_,MINUS,_,MINUS>',
    '<PAR_OPP,_,_,PLUS,_,ZERO>'     : '<PAR_OPP,_,_,MINUS,_,ZERO>',
    '<PAR_SAME,_,_,MINUS,_,MINUS>'  : '<PAR_SAME,_,_,PLUS,_,PLUS>',
    '<PAR_SAME,_,_,MINUS,_,PLUS>'   : '<PAR_SAME,_,_,PLUS,_,MINUS>',
    '<PAR_SAME,_,_,MINUS,_,ZERO>'   : '<PAR_SAME,_,_,PLUS,_,ZERO>',
    '<PAR_SAME,_,_,PLUS,_,MINUS>'   : '<PAR_SAME,_,_,MINUS,_,PLUS>',
    '<PAR_SAME,_,_,PLUS,_,PLUS>'    : '<PAR_SAME,_,_,MINUS,_,MINUS>',
    '<PAR_SAME,_,_,PLUS,_,ZERO>'    : '<PAR_SAME,_,_,MINUS,_,ZERO>',
    '<X,MINUS,MINUS,MINUS,_,MINUS>' : '<X,PLUS,PLUS,PLUS,_,PLUS>',
    '<X,MINUS,MINUS,MINUS,_,PLUS>'  : '<X,PLUS,PLUS,PLUS,_,MINUS>',
    '<X,MINUS,MINUS,MINUS,_,ZERO>'  : '<X,PLUS,PLUS,PLUS,_,ZERO>',
    '<X,MINUS,MINUS,PLUS,_,MINUS>'  : '<X,PLUS,PLUS,MINUS,_,PLUS>',
    '<X,MINUS,MINUS,PLUS,_,PLUS>'   : '<X,PLUS,PLUS,MINUS,_,MINUS>',
    '<X,MINUS,MINUS,PLUS,_,ZERO>'   : '<X,PLUS,PLUS,MINUS,_,ZERO>',
    '<X,MINUS,PLUS,MINUS,_,MINUS>'  : '<X,PLUS,MINUS,PLUS,_,PLUS>',
    '<X,MINUS,PLUS,MINUS,_,PLUS>'   : '<X,PLUS,MINUS,PLUS,_,MINUS>',
    '<X,MINUS,PLUS,MINUS,_,ZERO>'   : '<X,PLUS,MINUS,PLUS,_,ZERO>',
    '<X,MINUS,PLUS,PLUS,_,MINUS>'   : '<X,PLUS,MINUS,MINUS,_,PLUS>',
    '<X,MINUS,PLUS,PLUS,_,PLUS>'    : '<X,PLUS,MINUS,MINUS,_,MINUS>',
    '<X,MINUS,PLUS,PLUS,_,ZERO>'    : '<X,PLUS,MINUS,MINUS,_,ZERO>',
    '<X,MINUS,ZERO,MINUS,_,_>'      : '<X,PLUS,ZERO,PLUS,_,_>',
    '<X,MINUS,ZERO,PLUS,_,_>'       : '<X,PLUS,ZERO,MINUS,_,_>',
    '<X,PLUS,MINUS,MINUS,_,MINUS>'  : '<X,MINUS,PLUS,PLUS,_,PLUS>',
    '<X,PLUS,MINUS,MINUS,_,PLUS>'   : '<X,MINUS,PLUS,PLUS,_,MINUS>',
    '<X,PLUS,MINUS,MINUS,_,ZERO>'   : '<X,MINUS,PLUS,PLUS,_,ZERO>',
    '<X,PLUS,MINUS,PLUS,_,MINUS>'   : '<X,MINUS,PLUS,MINUS,_,PLUS>',
    '<X,PLUS,MINUS,PLUS,_,PLUS>'    : '<X,MINUS,PLUS,MINUS,_,MINUS>',
    '<X,PLUS,MINUS,PLUS,_,ZERO>'    : '<X,MINUS,PLUS,MINUS,_,ZERO>',
    '<X,PLUS,PLUS,MINUS,_,MINUS>'   : '<X,MINUS,MINUS,PLUS,_,PLUS>',
    '<X,PLUS,PLUS,MINUS,_,PLUS>'    : '<X,MINUS,MINUS,PLUS,_,MINUS>',
    '<X,PLUS,PLUS,MINUS,_,ZERO>'    : '<X,MINUS,MINUS,PLUS,_,ZERO>',
    '<X,PLUS,PLUS,PLUS,_,MINUS>'    : '<X,MINUS,MINUS,MINUS,_,PLUS>',
    '<X,PLUS,PLUS,PLUS,_,PLUS>'     : '<X,MINUS,MINUS,MINUS,_,MINUS>',
    '<X,PLUS,PLUS,PLUS,_,ZERO>'     : '<X,MINUS,MINUS,MINUS,_,ZERO>',
    '<X,PLUS,ZERO,MINUS,_,_>'       : '<X,MINUS,ZERO,PLUS,_,_>',
    '<X,PLUS,ZERO,PLUS,_,_>'        : '<X,MINUS,ZERO,MINUS,_,_>',
    '<X,ZERO,MINUS,_,M_TO_P,_>'     : '<X,ZERO,PLUS,_,M_TO_P,_>',
    '<X,ZERO,MINUS,_,P_TO_M,_>'     : '<X,ZERO,PLUS,_,P_TO_M,_>',
    '<X,ZERO,PLUS,_,M_TO_P,_>'      : '<X,ZERO,MINUS,_,M_TO_P,_>',
    '<X,ZERO,PLUS,_,P_TO_M,_>'      : '<X,ZERO,MINUS,_,P_TO_M,_>',
}


# ── Public API ────────────────────────────────────────────────────────────────

def rot_alpha(br: str) -> str:
    """Apply the α π-rotation to a canonical relation string."""
    return _ALPHA[br]

def rot_beta(br: str) -> str:
    """Apply the β π-rotation to a canonical relation string."""
    return _BETA[br]

def rot_gamma(br: str) -> str:
    """Apply the γ π-rotation to a canonical relation string."""
    return _GAMMA[br]
