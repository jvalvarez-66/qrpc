"""
zset_verification.py
--------------------
Verification logic for the Z-set algebraic closure:
  path-consistency check and Z coverage / orbit analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from functools import lru_cache
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qrpc.table48 import get_compact, get_instantiated, all_notations
from qrpc.composition import compose_basic
from qrpc.converse import converse
from qrpc.pi_rotations import rot_alpha, rot_beta, rot_gamma, _ALPHA, _BETA, _GAMMA
from qrpc.z_compositions import get_table as z_get_table
from qrpc.representation import Representation


# ── Helpers ───────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _converse_br(br: str) -> Optional[str]:
    return converse(br)


@lru_cache(maxsize=None)
def _compose_singles_cached(br12: str, br23: str) -> tuple[str, ...]:
    return tuple(sorted(compose_basic(br12, br23)))


def _compose_singles(br12: str, br23: str) -> set[str]:
    return set(_compose_singles_cached(br12, br23))


# ── Triplet verification (C2 / C3) ───────────────────────────────────────────

@dataclass
class TripletReport:
    entry_num: int
    br12: str
    br23: str
    br13: str       # one specific r13 from the result set
    c2: bool
    c3: bool

    @property
    def satisfies_pc(self) -> bool:
        return self.c2 and self.c3

    @property
    def pc_label(self) -> str:
        if self.c2 and self.c3:  return "✓"
        if not self.c2 and not self.c3: return "✗ cond.2+3"
        return "✗ cond. 2" if not self.c2 else "✗ cond. 3"


@lru_cache(maxsize=1)
def _verify_z_triplets_cached() -> tuple[TripletReport, ...]:
    reports: list[TripletReport] = []
    entries = list(z_get_table().items())
    for idx, (key, result_ncs) in enumerate(entries):
        sep = key.index('|')
        br12, br23 = key[:sep], key[sep+1:]
        br21 = _converse_br(br12)
        br32 = _converse_br(br23)
        for br13 in sorted(result_ncs):
            c2 = br12 in _compose_singles(br13, br32) if br32 else False
            c3 = br23 in _compose_singles(br21, br13) if br21 else False
            reports.append(TripletReport(
                entry_num=idx+1, br12=br12, br23=br23, br13=br13, c2=c2, c3=c3
            ))
    return tuple(reports)


def verify_z_triplets(progress_cb=None) -> list[TripletReport]:
    """
    Verifies path-consistency conditions for every triplet (R12, R23, r13) in the Z table.
    ~3,382 triplets (288 entries × avg result size).
    Results are cached after the first computation.
    """
    reports = list(_verify_z_triplets_cached())
    if progress_cb:
        progress_cb(1, 1)
    return reports


@lru_cache(maxsize=1)
def _verify_all_triplets_cached() -> tuple[TripletReport, ...]:
    notations = all_notations()
    reports: list[TripletReport] = []
    total = len(notations) ** 2
    done = 0
    for br12 in notations:
        for br23 in notations:
            done += 1
            r13_set = _compose_singles(br12, br23)
            if not r13_set:
                continue
            br21 = _converse_br(br12)
            br32 = _converse_br(br23)
            for br13 in sorted(r13_set):
                c2 = br12 in _compose_singles(br13, br32) if br32 else False
                c3 = br23 in _compose_singles(br21, br13) if br21 else False
                reports.append(TripletReport(
                    entry_num=done, br12=br12, br23=br23, br13=br13, c2=c2, c3=c3
                ))
    return tuple(reports)


def verify_all_triplets(progress_cb=None) -> list[TripletReport]:
    """
    Verifies path-consistency conditions for ALL 48×48 = 2304 pairs (full X space).
    ~27,000 individual triplets.
    Results are cached after the first computation.
    """
    reports = list(_verify_all_triplets_cached())
    if progress_cb:
        progress_cb(1, 1)
    return reports


@dataclass
class OmissionAnalysisResult:
    seed: TripletReport
    omitted_triplets: list[tuple[int, str, str, str]]
    z_failing: list[TripletReport]
    x_failing: list[TripletReport]


def explain_triplet_pc(br12: str, br23: str, br13: str) -> dict:
    """Returns a detailed path-consistency explanation for a concrete triplet."""
    br21 = _converse_br(br12)
    br32 = _converse_br(br23)
    c2_set = _compose_singles(br13, br32) if br32 else set()
    c3_set = _compose_singles(br21, br13) if br21 else set()
    c2 = br12 in c2_set
    c3 = br23 in c3_set
    return {
        'br12': br12, 'br23': br23, 'br13': br13,
        'br21': br21, 'br32': br32,
        'c2_set': sorted(c2_set), 'c3_set': sorted(c3_set),
        'c2': c2, 'c3': c3, 'pc': c2 and c3,
    }


def _apply_rot_to_br(br: str, rot: str | None) -> str | None:
    if rot is None:
        return br
    return {'a': _ALPHA, 'b': _BETA, 'g': _GAMMA}[rot].get(br)


def build_omitted_triplet_orbit(seed: TripletReport) -> list[tuple[int, str, str, str]]:
    """Builds the 8 triplet positions removed when one canonical Z triplet is omitted."""
    # Input rotations for pair reduction; output rotation applied to r13.
    in_rot = {
        0: (None, None),
        1: ('a', None),
        2: ('b', 'a'),
        3: (None, 'b'),
        4: ('g', 'a'),
        5: ('b', 'g'),
        6: ('a', 'b'),
        7: ('g', 'g'),
    }
    out_rot = {0: None, 1: 'a', 2: None, 3: 'b', 4: 'a', 5: 'b', 6: 'g', 7: 'g'}
    orbit = []
    seen = set()
    for rule in range(8):
        br12r = _apply_rot_to_br(seed.br12, in_rot[rule][0])
        br23r = _apply_rot_to_br(seed.br23, in_rot[rule][1])
        br13r = _apply_rot_to_br(seed.br13, out_rot[rule])
        if not (br12r and br23r and br13r):
            continue
        key = (br12r, br23r, br13r)
        if key in seen:
            continue
        seen.add(key)
        orbit.append((rule, br12r, br23r, br13r))
    return orbit


def _compose_singles_omitting(br12: str, br23: str, omitted_map: dict[tuple[str, str], set[str]]) -> set[str]:
    result = _compose_singles(br12, br23)
    omitted = omitted_map.get((br12, br23))
    if omitted:
        result = set(result) - set(omitted)
    return result


def _reevaluate_reports_with_omission(reports: list[TripletReport], omitted_map: dict[tuple[str, str], set[str]], progress_cb=None, progress_range=(0,1)) -> list[TripletReport]:
    failing = []
    total = len(reports)
    start, span = progress_range
    impacted_pairs = set(omitted_map.keys())
    for idx, r in enumerate(reports, start=1):
        br21 = _converse_br(r.br12)
        br32 = _converse_br(r.br23)
        c2_pair = (r.br13, br32) if br32 else None
        c3_pair = (br21, r.br13) if br21 else None

        # Fast path: if the omitted orbit never touches either supporting composition pair,
        # this report stays valid exactly as in the baseline verification.
        if (c2_pair not in impacted_pairs) and (c3_pair not in impacted_pairs):
            if progress_cb and idx % 500 == 0:
                prog = start + int(span * idx / total)
                progress_cb(prog, 100)
            continue

        c2_set = _compose_singles_omitting(r.br13, br32, omitted_map) if br32 else set()
        c3_set = _compose_singles_omitting(br21, r.br13, omitted_map) if br21 else set()
        c2 = r.br12 in c2_set
        c3 = r.br23 in c3_set
        if not (c2 and c3):
            failing.append(TripletReport(entry_num=r.entry_num, br12=r.br12, br23=r.br23, br13=r.br13, c2=c2, c3=c3))
        if progress_cb and idx % 500 == 0:
            prog = start + int(span * idx / total)
            progress_cb(prog, 100)
    if progress_cb:
        progress_cb(start + span, 100)
    return failing




def omission_cache_status() -> dict:
    """Reports whether omission-analysis baseline caches are already available."""
    z_info = _verify_z_triplets_cached.cache_info()
    x_info = _verify_all_triplets_cached.cache_info()
    comp_info = _compose_singles_cached.cache_info()
    conv_info = _converse_br.cache_info()
    return {
        "z_ready": z_info.currsize > 0,
        "x_ready": x_info.currsize > 0,
        "baseline_ready": (z_info.currsize > 0 and x_info.currsize > 0),
        "compose_ready": comp_info.currsize > 0,
        "converse_ready": conv_info.currsize > 0,
    }
def analyze_triplet_omission(seed: TripletReport, progress_cb=None) -> OmissionAnalysisResult:
    """
    Simulates removing one canonical Z triplet from the verification basis and reports
    which triplets in Z and in the full X space stop satisfying path-consistency conditions under that omission.
    """
    omitted_triplets = build_omitted_triplet_orbit(seed)
    omitted_map: dict[tuple[str, str], set[str]] = {}
    for _rule, a, b, c in omitted_triplets:
        omitted_map.setdefault((a, b), set()).add(c)

    z_all = verify_z_triplets()
    if progress_cb:
        progress_cb(10, 100)
    x_all = verify_all_triplets()
    if progress_cb:
        progress_cb(35, 100)

    z_failing = _reevaluate_reports_with_omission(z_all, omitted_map, progress_cb, (35, 20))
    x_failing = _reevaluate_reports_with_omission(x_all, omitted_map, progress_cb, (55, 45))
    return OmissionAnalysisResult(
        seed=seed,
        omitted_triplets=omitted_triplets,
        z_failing=z_failing,
        x_failing=x_failing,
    )


# ── Coverage / orbit analysis ─────────────────────────────────────────────────

@dataclass
class OrbitPair:
    rule: int
    br12: str
    br23: str


@dataclass
class ZEntry:
    idx: int
    br12: str
    br23: str
    r13_set: set[str]
    orbit_pairs: list[OrbitPair] = field(default_factory=list)


def analyze_coverage(progress_cb=None) -> tuple[list[ZEntry], bool, int, int]:
    """
    Verifies that the 288 Z entries cover all 2,304 pairs via π-rotation orbits.

    Returns (entries, is_complete, covered, total).
    """
    all_ncs = all_notations()
    nc_to_rep: dict[str, Representation] = {}
    from qrpc.table48 import all_relations
    for rep, br in all_relations().items():
        nc_to_rep.setdefault(br, rep)

    covered: set[str] = set()   # "br12|br23" pairs covered
    entries: list[ZEntry] = []

    rot_fns = [
        (0, lambda r12, r23: (r12, r23)),
        (1, lambda r12, r23: (_ALPHA[r12], r23)),
        (2, lambda r12, r23: (_BETA[r12],  _ALPHA[r23])),
        (3, lambda r12, r23: (r12,          _BETA[r23])),
        (4, lambda r12, r23: (_GAMMA[r12],  _ALPHA[r23])),
        (5, lambda r12, r23: (_BETA[r12],   _GAMMA[r23])),
        (6, lambda r12, r23: (_ALPHA[r12],  _BETA[r23])),
        (7, lambda r12, r23: (_GAMMA[r12],  _GAMMA[r23])),
    ]

    z_items = list(z_get_table().items())
    for idx, (key, r13_ncs) in enumerate(z_items):
        sep = key.index('|')
        br12, br23 = key[:sep], key[sep+1:]
        t12 = nc_to_rep.get(br12)
        t23 = nc_to_rep.get(br23)
        orbit: list[OrbitPair] = []
        if t12 and t23:
            for rule, fn in rot_fns[1:]:   # rules 1-7 (satellites)
                r12r, r23r = fn(t12, t23)
                sbr12 = get_compact(r12r)
                sbr23 = get_compact(r23r)
                if sbr12 and sbr23:
                    covered.add(f"{sbr12}|{sbr23}")
                    orbit.append(OrbitPair(rule, sbr12, sbr23))
            covered.add(f"{br12}|{br23}")

        entries.append(ZEntry(
            idx=idx+1, br12=br12, br23=br23,
            r13_set=set(r13_ncs), orbit_pairs=orbit
        ))
        if progress_cb and idx % 30 == 0:
            progress_cb(idx+1, len(z_items))

    if progress_cb:
        progress_cb(len(z_items), len(z_items))

    total = len(all_ncs) ** 2
    is_complete = len(covered) >= total
    return entries, is_complete, len(covered), total
