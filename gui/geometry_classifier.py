"""
geometry_classifier.py
-----------------------
Geometric classifier: determines the basic QRPC relation from the
positions and orientations of two objects on a 2-D canvas.

"""

from __future__ import annotations
import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
from qrpc.representation import P12


# ── Tolerances ────────────────────────────────────────────────────────────────

# Angular tolerance used by the editor to make mathematical frontier states
# reachable and stable under direct manipulation. It is used only for equality
# / frontier predicates. Strict open regions remain open, so no artificial
# dead band is created around θ=φ, θ+φ=π, π/2, etc.
ANGLE_EPS    = math.radians(2.0)

# Cross-product tolerances are intentionally split in two:
#
# * A broad tolerance is used only for the strong degeneracy in which BOTH
#   relative cross-products are close to zero.  In that case the configuration
#   is treated as OVL_SAME/OVL_OPP.
# * A tighter tolerance is used for ordinary sign classification.  This avoids
#   turning a relation such as <X,+,+,-,_,-> into a one-zero frontier merely
#   because one angle is close, but not equal, to 0 or π.
CROSS_DOUBLE_ZERO_EPS = math.sin(ANGLE_EPS)
CROSS_SINGLE_ZERO_EPS = math.sin(math.radians(0.75))
CROSS_EPS             = CROSS_SINGLE_ZERO_EPS

# Pixel distance used only to distinguish true overlap/colinearity in the
# projection-family classifier.  This remains a geometric canvas tolerance.
COLINEAR_EPS = 6.0


# ── Enums ─────────────────────────────────────────────────────────────────────

class Sign(Enum):
    NEG  = auto()
    ZERO = auto()
    POS  = auto()

class Pred(Enum):
    ANY   = auto()
    LT90  = auto()
    EQ90  = auto()
    GT90  = auto()
    LT180 = auto()
    EQ180 = auto()
    EQ0   = auto()

class Cmp(Enum):
    ANY = auto()
    LT  = auto()
    EQ  = auto()
    GT  = auto()

class SumPred(Enum):
    ANY   = auto()
    LT180 = auto()
    EQ180 = auto()
    GT180 = auto()
    EQ0   = auto()


# ── Object ────────────────────────────────────────────────────────────────────

class Obj:
    """An oriented point on the canvas with position (x,y) and angle (radians)."""
    __slots__ = ('x', 'y', 'angle')

    def __init__(self, x: float, y: float, angle: float):
        self.x = x
        self.y = y
        self.angle = angle

    def ux(self) -> float: return math.cos(self.angle)
    def uy(self) -> float: return math.sin(self.angle)


# ── Analysis result ───────────────────────────────────────────────────────────

@dataclass
class PairAnalysis:
    br:          str              # basic relation (BR) string
    family:      P12              # projection family
    theta:       float            # angle(u2, v) in radians
    phi:         float            # angle(u1, v) in radians
    sum:         float            # theta + phi
    u1xu2:       float
    u2xv:        float
    u1xv:        float
    u1du2:       float
    u2dv:        float
    u1dv:        float
    sig_u2xv:    Sign
    sig_u1xv:    Sign
    cmp:         int              # -1 / 0 / 1
    status:      str = "FORMAL_MATCH"
    nearest_br:  Optional[str] = None
    matched_brs: tuple[str, ...] = ()  # retained for debugging; not used by the GUI
    norm_u2xv:   float = 0.0
    norm_u1xv:   float = 0.0
    forced_ovl:   bool = False


# ── Rule ─────────────────────────────────────────────────────────────────────

class Rule:
    __slots__ = ('br', 'family', 's2', 's1', 'a', 'b', 'cmp', 'sum')

    def __init__(self, br, family, s2, s1, a, b, cmp, sum_p):
        self.br = br; self.family = family
        self.s2 = s2; self.s1 = s1
        self.a = a;   self.b = b
        self.cmp = cmp; self.sum = sum_p

    def matches(self, fam, s2v, s1v, theta, phi, cmp_ab, sum_ab) -> bool:
        # cmp_ab is kept for display/debugging, but rule matching evaluates
        # θ<φ, θ=φ, θ>φ directly. Equalities use ANGLE_EPS; strict
        # inequalities remain open to avoid dead zones next to frontiers.
        return (fam == self.family
                and s2v == self.s2 and s1v == self.s1
                and _mp(self.a, theta) and _mp(self.b, phi)
                and _mc(self.cmp, theta, phi) and _ms(self.sum, sum_ab))

    def soft_score(self, fam, u2xv, u1xv, theta, phi, sum_ab) -> float:
        if fam != self.family:
            return float('inf')
        return (_sd(self.s2, u2xv) + _sd(self.s1, u1xv)
                + _cd(self.cmp, theta, phi)
                + _pd(self.a, theta) + _pd(self.b, phi)
                + _sumd(self.sum, sum_ab))


def _mp(p: Pred, ang: float) -> bool:
    PI2 = math.pi / 2
    if p == Pred.ANY:   return True
    # Open angular regions are evaluated as mathematical open intervals.
    # Equality/frontier states are the only predicates widened by ANGLE_EPS.
    if p == Pred.LT90:  return ang < PI2
    if p == Pred.EQ90:  return abs(ang - PI2) <= ANGLE_EPS
    if p == Pred.GT90:  return ang > PI2
    if p == Pred.LT180: return ang < math.pi
    if p == Pred.EQ180: return abs(ang - math.pi) <= ANGLE_EPS
    if p == Pred.EQ0:   return abs(ang) <= ANGLE_EPS
    return False

def _mc(p: Cmp, theta: float, phi: float) -> bool:
    if p == Cmp.ANY: return True
    if p == Cmp.LT:  return theta < phi
    if p == Cmp.EQ:  return abs(theta - phi) <= ANGLE_EPS
    if p == Cmp.GT:  return theta > phi
    return False

def _ms(p: SumPred, s: float) -> bool:
    if p == SumPred.ANY:   return True
    # Open sum regions are not narrowed by ANGLE_EPS.  The frontier
    # θ+φ=π is widened independently by EQ180.
    if p == SumPred.LT180: return s < math.pi
    if p == SumPred.EQ180: return abs(s - math.pi) <= ANGLE_EPS
    if p == SumPred.GT180: return s > math.pi
    if p == SumPred.EQ0:   return abs(s) <= ANGLE_EPS or abs(s - 2*math.pi) <= ANGLE_EPS
    return False

def _sd(expected: Sign, value: float) -> float:
    if expected == Sign.POS:  return 0.0 if value >= CROSS_EPS  else CROSS_EPS - value
    if expected == Sign.NEG:  return 0.0 if value <= -CROSS_EPS else value + CROSS_EPS
    if expected == Sign.ZERO: return abs(value)
    return float('inf')

def _cd(expected: Cmp, theta: float, phi: float) -> float:
    d = theta - phi
    if expected == Cmp.ANY: return 0.0
    if expected == Cmp.EQ:  return max(0.0, abs(d) - ANGLE_EPS)
    if expected == Cmp.LT:  return max(0.0, d)
    if expected == Cmp.GT:  return max(0.0, -d)
    return float('inf')

def _pd(p: Pred, ang: float) -> float:
    PI2 = math.pi / 2
    if p == Pred.ANY:   return 0.0
    if p == Pred.LT90:  return max(0.0, ang - PI2)
    if p == Pred.EQ90:  return max(0.0, abs(ang - PI2) - ANGLE_EPS)
    if p == Pred.GT90:  return max(0.0, PI2 - ang)
    if p == Pred.LT180: return max(0.0, ang - math.pi)
    if p == Pred.EQ180: return max(0.0, abs(ang - math.pi) - ANGLE_EPS)
    if p == Pred.EQ0:   return max(0.0, abs(ang) - ANGLE_EPS)
    return float('inf')

def _sumd(p: SumPred, s: float) -> float:
    if p == SumPred.ANY:   return 0.0
    if p == SumPred.LT180: return max(0.0, s - math.pi)
    if p == SumPred.EQ180: return max(0.0, abs(s - math.pi) - ANGLE_EPS)
    if p == SumPred.GT180: return max(0.0, math.pi - s)
    if p == SumPred.EQ0:
        return min(max(0.0, abs(s) - ANGLE_EPS),
                   max(0.0, abs(s - 2*math.pi) - ANGLE_EPS))
    return float('inf')


# ── Helper math ───────────────────────────────────────────────────────────────

def _cross(ax, ay, bx, by): return ax * by - ay * bx
def _dot(ax, ay, bx, by):   return ax * bx + ay * by

def _angle_between(ax, ay, bx, by) -> float:
    na = math.hypot(ax, ay); nb = math.hypot(bx, by)
    if na < 1e-9 or nb < 1e-9: return 0.0
    c = _dot(ax, ay, bx, by) / (na * nb)
    return math.acos(max(-1.0, min(1.0, c)))

def _sign_of(x: float, eps: float = CROSS_SINGLE_ZERO_EPS) -> Sign:
    if x > eps:  return Sign.POS
    if x < -eps: return Sign.NEG
    return Sign.ZERO

def _compare(a: float, b: float) -> int:
    if abs(a - b) <= ANGLE_EPS: return 0
    return -1 if a < b else 1

def _classify_family(u1xu2, u1du2, u2xv) -> P12:
    parallel = abs(u1xu2) <= math.sin(ANGLE_EPS)
    if not parallel: return P12.X
    colinear = abs(u2xv) <= COLINEAR_EPS
    if colinear: return P12.OVL_SAME if u1du2 >= 0 else P12.OVL_OPP
    return P12.PAR_SAME if u1du2 >= 0 else P12.PAR_OPP

def normalize_angle(a: float) -> float:
    while a <= -math.pi: a += 2*math.pi
    while a >  math.pi:  a -= 2*math.pi
    return a

def distance_to_line(px, py, ox, oy, ux, uy) -> float:
    return abs(_cross(px-ox, py-oy, ux, uy))


# ── Rule table (v1.3) ─────────────────────────────────────────────────────────

def _add(rs, br, f, s2, s1, a, b, c, s):
    rs.append(Rule(br, f, s2, s1, a, b, c, s))

def _build_rules() -> list[Rule]:
    X  = P12.X
    PS = P12.PAR_SAME
    PO = P12.PAR_OPP
    OS = P12.OVL_SAME
    OO = P12.OVL_OPP
    N, Z, P = Sign.NEG, Sign.ZERO, Sign.POS
    A = Pred.ANY; L9=Pred.LT90; E9=Pred.EQ90; G9=Pred.GT90
    L1=Pred.LT180; E1=Pred.EQ180; E0=Pred.EQ0
    CL=Cmp.LT; CE=Cmp.EQ; CG=Cmp.GT
    SL=SumPred.LT180; SE=SumPred.EQ180
    SG=SumPred.GT180; S0=SumPred.EQ0
    r = []
    # X regular (24) — table v1.3
    _add(r,"<X,PLUS,PLUS,PLUS,_,PLUS>",  X, N, N, L9, L1, CL, SL)
    _add(r,"<X,PLUS,PLUS,PLUS,_,ZERO>",  X, N, N, L9, G9, CL, SE)
    _add(r,"<X,PLUS,PLUS,PLUS,_,MINUS>", X, N, N, L1, G9, CL, SG)
    _add(r,"<X,PLUS,PLUS,MINUS,_,PLUS>", X, P, P, L9, L1, CL, SL)
    _add(r,"<X,PLUS,PLUS,MINUS,_,ZERO>", X, P, P, L9, G9, CL, SE)
    _add(r,"<X,PLUS,PLUS,MINUS,_,MINUS>",X, P, P, L1, G9, CL, SG)
    _add(r,"<X,PLUS,MINUS,PLUS,_,PLUS>", X, N, P, L1, G9, CL, SG)
    _add(r,"<X,PLUS,MINUS,PLUS,_,ZERO>", X, N, P, G9, G9, CE, SG)
    _add(r,"<X,PLUS,MINUS,PLUS,_,MINUS>",X, N, P, G9, L1, CG, SG)
    _add(r,"<X,PLUS,MINUS,MINUS,_,PLUS>",X, P, N, L1, G9, CL, SG)
    _add(r,"<X,PLUS,MINUS,MINUS,_,ZERO>",X, P, N, G9, G9, CE, SG)
    _add(r,"<X,PLUS,MINUS,MINUS,_,MINUS>",X,P, N, G9, L1, CG, SG)
    _add(r,"<X,MINUS,PLUS,PLUS,_,PLUS>", X, N, P, L9, L1, CL, SL)
    _add(r,"<X,MINUS,PLUS,PLUS,_,ZERO>", X, N, P, L9, L9, CE, SL)
    _add(r,"<X,MINUS,PLUS,PLUS,_,MINUS>",X, N, P, L1, L9, CG, SL)
    _add(r,"<X,MINUS,PLUS,MINUS,_,PLUS>",X, P, N, L9, L1, CL, SL)
    _add(r,"<X,MINUS,PLUS,MINUS,_,ZERO>",X, P, N, L9, L9, CE, SL)
    _add(r,"<X,MINUS,PLUS,MINUS,_,MINUS>",X,P, N, L1, L9, CG, SL)
    _add(r,"<X,MINUS,MINUS,PLUS,_,PLUS>",X, N, N, L1, L9, CG, SL)
    _add(r,"<X,MINUS,MINUS,PLUS,_,ZERO>",X, N, N, G9, L9, CG, SE)
    _add(r,"<X,MINUS,MINUS,PLUS,_,MINUS>",X,N, N, G9, L1, CG, SG)
    _add(r,"<X,MINUS,MINUS,MINUS,_,PLUS>",X,P, P, L1, L9, CG, SL)
    _add(r,"<X,MINUS,MINUS,MINUS,_,ZERO>",X,P, P, G9, L9, CG, SE)
    _add(r,"<X,MINUS,MINUS,MINUS,_,MINUS>",X,P,P, G9, L1, CG, SG)
    # X boundary (8)
    _add(r,"<X,PLUS,ZERO,PLUS,_,_>",  X, N, Z, L1, E1, CL, SG)
    _add(r,"<X,PLUS,ZERO,MINUS,_,_>", X, P, Z, L1, E1, CL, SG)
    _add(r,"<X,MINUS,ZERO,PLUS,_,_>", X, N, Z, L1, E0, CG, SL)
    _add(r,"<X,MINUS,ZERO,MINUS,_,_>",X, P, Z, L1, E0, CG, SL)
    _add(r,"<X,ZERO,PLUS,_,P_TO_M,_>",X, Z, N, E0, L1, CL, SL)
    _add(r,"<X,ZERO,PLUS,_,M_TO_P,_>",X, Z, P, E0, L1, CL, SL)
    _add(r,"<X,ZERO,MINUS,_,P_TO_M,_>",X,Z, P, E1, A,  CG, SG)
    _add(r,"<X,ZERO,MINUS,_,M_TO_P,_>",X,Z, N, E1, A,  CG, SG)
    # PAR/OVL (16)
    _add(r,"<PAR_SAME,_,_,PLUS,_,PLUS>",  PS, N, N, L9, L9, CE, SL)
    _add(r,"<PAR_SAME,_,_,PLUS,_,ZERO>",  PS, N, N, E9, E9, CE, SE)
    _add(r,"<PAR_SAME,_,_,PLUS,_,MINUS>", PS, N, N, G9, G9, CE, SG)
    _add(r,"<PAR_SAME,_,_,MINUS,_,PLUS>", PS, P, P, L9, L9, CE, SL)
    _add(r,"<PAR_SAME,_,_,MINUS,_,ZERO>", PS, P, P, E9, E9, CE, SE)
    _add(r,"<PAR_SAME,_,_,MINUS,_,MINUS>",PS, P, P, G9, G9, CE, SG)
    _add(r,"<PAR_OPP,_,_,PLUS,_,PLUS>",   PO, N, P, L9, G9, CL, SE)
    _add(r,"<PAR_OPP,_,_,PLUS,_,ZERO>",   PO, N, P, E9, E9, CE, SE)
    _add(r,"<PAR_OPP,_,_,PLUS,_,MINUS>",  PO, N, P, G9, L9, CG, SE)
    _add(r,"<PAR_OPP,_,_,MINUS,_,PLUS>",  PO, P, N, L9, G9, CL, SE)
    _add(r,"<PAR_OPP,_,_,MINUS,_,ZERO>",  PO, P, N, E9, E9, CE, SE)
    _add(r,"<PAR_OPP,_,_,MINUS,_,MINUS>", PO, P, N, G9, L9, CG, SE)
    _add(r,"<OVL_SAME,_,_,_,_,PLUS>",     OS, Z, Z, E0, E0, CE, S0)
    _add(r,"<OVL_SAME,_,_,_,_,MINUS>",    OS, Z, Z, E1, E1, CE, S0)
    _add(r,"<OVL_OPP,_,_,_,_,PLUS>",      OO, Z, Z, E0, E1, CL, SE)
    _add(r,"<OVL_OPP,_,_,_,_,MINUS>",     OO, Z, Z, E1, E0, CG, SE)
    return r

RULES = _build_rules()



def _priority_key(rule: Rule) -> tuple[int, int, str]:
    """Deterministic priority when tolerance bands make several rules valid.

    Frontier predicates are preferred over interior predicates.  This keeps
    states such as θ≈0, θ≈π, φ≈0, φ≈π, θ≈φ, or θ+φ≈π from being swallowed by
    adjacent open regions.
    """
    score = 0
    if rule.a in (Pred.EQ0, Pred.EQ180):
        score += 40
    elif rule.a == Pred.EQ90:
        score += 25
    if rule.b in (Pred.EQ0, Pred.EQ180):
        score += 40
    elif rule.b == Pred.EQ90:
        score += 25
    if rule.s2 == Sign.ZERO:
        score += 20
    if rule.s1 == Sign.ZERO:
        score += 20
    if rule.cmp == Cmp.EQ:
        score += 10
    if rule.sum in (SumPred.EQ180, SumPred.EQ0):
        score += 10
    # Higher score first, then more specific rules, then lexical stability.
    specificity = sum([
        rule.s2 != Sign.ZERO, rule.s1 != Sign.ZERO,
        rule.a != Pred.ANY, rule.b != Pred.ANY,
        rule.cmp != Cmp.ANY, rule.sum != SumPred.ANY,
    ])
    return (-score, -specificity, rule.br)


def _choose_ambiguous_rule(rules: list[Rule], theta: float, phi: float, sum_ab: float) -> Rule:
    """Choose a display relation when tolerance makes several rules valid.

    Equality predicates are widened to make frontier states reachable, but when
    the measured value is clearly on one side of a frontier we prefer the open
    region on that side.  This prevents cases such as θ+φ=182° from being
    displayed as the θ+φ=180° boundary merely because they still lie inside the
    broad equality tolerance band.
    """
    candidates = list(rules)
    frontier_core = ANGLE_EPS * 0.5

    # θ vs φ: if the configuration is clearly on one side of θ=φ, prefer that
    # side over the widened equality band.
    d = theta - phi
    if abs(d) > frontier_core:
        wanted_cmp = Cmp.GT if d > 0 else Cmp.LT
        side_candidates = [r for r in candidates if r.cmp in (Cmp.ANY, wanted_cmp)]
        if side_candidates:
            candidates = side_candidates

    # θ+φ vs π: same policy for the sum boundary.
    ds = sum_ab - math.pi
    if abs(ds) > frontier_core:
        wanted_sum = SumPred.GT180 if ds > 0 else SumPred.LT180
        side_candidates = [r for r in candidates if r.sum in (SumPred.ANY, wanted_sum)]
        if side_candidates:
            candidates = side_candidates

    return sorted(candidates, key=_priority_key)[0]

def _normalized_cross_with_v(raw_cross: float, vx: float, vy: float) -> float:
    nv = math.hypot(vx, vy)
    if nv < 1e-9:
        return 0.0
    return raw_cross / nv

# ── Main classifier ───────────────────────────────────────────────────────────

def analyze(o1: Obj, o2: Obj) -> PairAnalysis:
    """Classifies the geometric configuration of two objects."""
    # Screen y is downward → invert y for math coordinates
    ux1 =  math.cos(o1.angle);  uy1 = -math.sin(o1.angle)
    ux2 =  math.cos(o2.angle);  uy2 = -math.sin(o2.angle)
    vx  =  o1.x - o2.x;        vy  = -(o1.y - o2.y)

    u1xu2 = _cross(ux1, uy1, ux2, uy2)
    u2xv  = _cross(ux2, uy2, vx,  vy)
    u1xv  = _cross(ux1, uy1, vx,  vy)
    u1du2 = _dot(ux1, uy1, ux2, uy2)
    u2dv  = _dot(ux2, uy2, vx,  vy)
    u1dv  = _dot(ux1, uy1, vx,  vy)
    theta = _angle_between(ux2, uy2, vx, vy)
    phi  = _angle_between(ux1, uy1, vx, vy)
    s     = theta + phi
    cmp   = _compare(theta, phi)

    # Sign predicates are computed from normalized cross-products.  Raw values
    # are still retained in PairAnalysis for display/debugging.
    norm_u2xv = _normalized_cross_with_v(u2xv, vx, vy)
    norm_u1xv = _normalized_cross_with_v(u1xv, vx, vy)

    # Degenerate overlap priority:
    # If BOTH relative cross-products are practically zero under the broad
    # tolerance, v lies on both support lines.  This is not a stable X-boundary
    # case: it is an overlap configuration.  The only remaining decision is
    # whether the two oriented trajectories have the same or opposite direction.
    #
    # For ordinary one-zero cases we deliberately use a tighter tolerance. This
    # prevents near-π or near-0 angles from being prematurely classified as ZERO
    # when the remaining angular predicates clearly place the configuration in
    # an open X region.
    double_zero_ovl = (
        math.hypot(vx, vy) > 1e-9
        and abs(norm_u2xv) <= CROSS_DOUBLE_ZERO_EPS
        and abs(norm_u1xv) <= CROSS_DOUBLE_ZERO_EPS
    )
    if double_zero_ovl:
        fam = P12.OVL_SAME if u1du2 >= 0 else P12.OVL_OPP
        s2 = Sign.ZERO
        s1 = Sign.ZERO

        # In a forced-overlap configuration the two normalized cross-products
        # are intentionally interpreted as zero.  The corresponding angular
        # predicates must therefore be evaluated on the same canonical OVL
        # geometry, not on the small residual angular error produced while the
        # user is dragging or rotating the objects.  Without this normalization,
        # values such as 178°+178° could miss the formal OVL_SAME rule even
        # though the editor has already classified the state as forced overlap.
        theta = 0.0 if u2dv >= 0 else math.pi
        phi = 0.0 if u1dv >= 0 else math.pi
        s = theta + phi
        cmp = _compare(theta, phi)
    else:
        fam = _classify_family(u1xu2, u1du2, u2xv)
        s2 = _sign_of(norm_u2xv, CROSS_SINGLE_ZERO_EPS)
        s1 = _sign_of(norm_u1xv, CROSS_SINGLE_ZERO_EPS)

    matched_rules = [
        rule for rule in RULES
        if rule.matches(fam, s2, s1, theta, phi, cmp, s)
    ]

    nearest = min(
        (rule for rule in RULES if rule.family == fam),
        key=lambda r: r.soft_score(fam, norm_u2xv, norm_u1xv, theta, phi, s),
        default=None,
    )
    nearest_br = nearest.br if nearest is not None else None

    if len(matched_rules) == 1:
        br = matched_rules[0].br
        status = "FORMAL_MATCH"
    elif len(matched_rules) > 1:
        chosen = _choose_ambiguous_rule(matched_rules, theta, phi, s)
        br = chosen.br
        status = "AMBIGUOUS_WITH_TOLERANCE"
    else:
        br = "<NO_MATCH>"
        status = "NO_FORMAL_MATCH"

    return PairAnalysis(
        br=br, family=fam,
        theta=theta, phi=phi, sum=s,
        u1xu2=u1xu2, u2xv=u2xv, u1xv=u1xv,
        u1du2=u1du2, u2dv=u2dv, u1dv=u1dv,
        sig_u2xv=s2, sig_u1xv=s1,
        cmp=cmp,
        status=status,
        nearest_br=nearest_br,
        matched_brs=tuple(rule.br for rule in sorted(matched_rules, key=_priority_key)),
        norm_u2xv=norm_u2xv,
        norm_u1xv=norm_u1xv,
        forced_ovl=double_zero_ovl,
    )
