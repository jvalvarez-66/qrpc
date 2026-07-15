#!/usr/bin/env python3
"""
run_experiment.py
=================
QRPC empirical evaluation using the standard A(n, d, l) random QCN benchmark.

Reference
---------
Renz, J. & Nebel, B. (2001). Efficient methods for qualitative spatial
reasoning. Journal of Artificial Intelligence Research, 15, 289-318.

Model A(n, d, l)
----------------
  n : number of objects (variables)
  d : average degree — average number of constraints per variable
  l : exact number of base relations per label (not expected value)

Network generation (exact Renz & Nebel procedure):
  1. Select floor(n*d/2) pairs uniformly at random WITHOUT replacement from
     all n(n-1)/2 possible pairs. These are the observed (constrained) pairs.
  2. Each observed pair receives exactly l base relations chosen uniformly at
     random WITHOUT replacement from the 48 QRPC base relations.
  3. Converse symmetry: label(j,i) = converse(label(i,j)) immediately.
  4. Unobserved pairs carry the universal relation (all 48 BRs possible).

PC-2 algorithm
--------------
Standard agenda-based path-consistency (Mackworth 1977; Bessiere 1994).
Optimisation: the initial agenda seeds only triples involving at least one
non-universal pair, skipping the O(n^3) universal triples which cannot
contribute any revision. When a label tightens, all affected triples are
added to the agenda and converse symmetry is maintained immediately.
Labels are represented as 48-bit integers for O(1) set operations.

Parameters
----------
  n  in {10, 15, 20, 25, 30}
  d  in {2, 4, 6, 8, 10}  (skipped if d >= n)
  l  in {1, 2, 3, 4, 5, 6, 8, 12, 24, 30}  (skipped if l >= |B|=48)
  200 trials per condition (fixed, no adaptive reduction)

Metrics (all standard in QSR/CSP evaluation)
--------------------------------------------
  failure_rate     : proportion of trials where PC-2 detects inconsistency
                     [Renz & Nebel 2001 — primary metric, reveals phase transition]
  p1               : network density = |E| / [n(n-1)/2]   [Dechter & Meiri 1994]
  t_before         : constraint tightness before PC-2 = 1 - l/|B|
                     [van Beek & Dechter 1997]
  ls_obs_after     : mean label size after PC-2 over OBSERVED pairs
                     [Long et al. 2016; Sioutis et al. 2019]
  ls_unobs_after   : mean label size after PC-2 over UNOBSERVED pairs
                     (initial = 48); measures inferential reach beyond observation
  t_after          : network tightness after PC-2 = 1 - mean_label_all/|B|
                     over ALL pairs [van Beek & Dechter 1997]
  alr              : atomic labelling rate = % of all pairs with singleton label
                     [Liu & Li 2012; proxy for minimal labelling]
  pr_obs           : pruning rate on observed pairs = % with reduced label
                     [Dechter & Meiri 1994]
  pr_unobs         : pruning rate on unobserved pairs = % with label < 48
                     (non-zero means PC-2 propagated beyond direct observations)
  checks           : number of arc revisions attempted
  reductions       : number of successful label reductions

Output
------
  <project_root>/experiment_results.json
  Written incrementally after each condition (safe against interruption).

Usage
-----
  python experiments/run_experiment.py                # default parameters
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import deque
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Path setup — output goes to <project_root>/experiments/results
# The directory must already exist; this script does not create folders.
# ---------------------------------------------------------------------------
def _find_project_root() -> Path:
    """
    Locate the project root by searching upwards from both the script location
    and the current working directory. A valid root must contain:

        qrpc/
        experiments/

    The results sub-directory is created automatically if it does not exist.
    """
    search_starts = [Path(__file__).resolve().parent, Path.cwd().resolve()]
    checked = set()

    for start in search_starts:
        for folder in (start, *start.parents):
            if folder in checked:
                continue
            checked.add(folder)
            if (folder / 'qrpc').is_dir() and (folder / 'experiments').is_dir():
                # Create results/ on first run if absent
                (folder / 'experiments' / 'results').mkdir(exist_ok=True)
                return folder

    raise FileNotFoundError(
        'Project root not found. Expected a folder containing both '
        'qrpc/ and experiments/ sub-directories.\n'
        'Run the script from inside the qrpc_app/ folder, e.g.:\n'
        '    cd qrpc_app\n'
        '    python experiments/run_experiment.py'
    )


PROJECT_ROOT = _find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / 'experiments' / 'results'
OUTPUT_PATH = RESULTS_DIR / 'experiment_results.json'

from qrpc.composition import compose_basic
from qrpc.converse import converse
from qrpc.table48 import all_notations

# ---------------------------------------------------------------------------
# Base relation registry
# ---------------------------------------------------------------------------
BRS: List[str] = sorted(all_notations())
BR_INDEX: Dict[str, int] = {br: i for i, br in enumerate(BRS)}
B: int = len(BRS)           # 48 for QRPC
UNIVERSAL: int = (1 << B) - 1

# ---------------------------------------------------------------------------
# Precompute 48×48 bitmask composition and converse tables (built once)
# ---------------------------------------------------------------------------
def _precompute() -> Tuple[List[List[int]], List[int]]:
    comp: List[List[int]] = [[0] * B for _ in range(B)]
    for br1 in BRS:
        i = BR_INDEX[br1]
        for br2 in BRS:
            j = BR_INDEX[br2]
            for rbr in compose_basic(br1, br2):
                if rbr in BR_INDEX:
                    comp[i][j] |= 1 << BR_INDEX[rbr]
    conv: List[int] = [0] * B
    for br in BRS:
        i = BR_INDEX[br]
        cbr = converse(br)
        if cbr is not None and cbr in BR_INDEX:
            conv[i] = 1 << BR_INDEX[cbr]
    return comp, conv


print('Building QRPC bitmask tables...', end=' ', flush=True)
COMP_TABLE, CONV_TABLE = _precompute()
print('done\n')


# ---------------------------------------------------------------------------
# Bitwise operations
# ---------------------------------------------------------------------------
def compose_masks(a: int, b: int) -> int:
    if not a or not b:
        return 0
    if a == UNIVERSAL or b == UNIVERSAL:
        return UNIVERSAL
    out = 0
    aa = a
    while aa:
        low_a = aa & (-aa)
        i = low_a.bit_length() - 1
        row = COMP_TABLE[i]
        bb = b
        while bb:
            low_b = bb & (-bb)
            j = low_b.bit_length() - 1
            out |= row[j]
            bb ^= low_b
            if out == UNIVERSAL:        # early-exit: result cannot grow further
                return UNIVERSAL
        aa ^= low_a
    return out


def converse_mask(label: int) -> int:
    out = 0
    x = label
    while x:
        low = x & (-x)
        i = low.bit_length() - 1
        out |= CONV_TABLE[i]
        x ^= low
    return out


# ---------------------------------------------------------------------------
# A(n, d, l) network generation — exact Renz & Nebel procedure
# ---------------------------------------------------------------------------
def generate_network(
    n: int, d: float, l: int, rng: random.Random
) -> Tuple[List[List[int]], List[Tuple[int, int]]]:
    """
    Generate one A(n, d, l) random QCN.

    Returns
    -------
    net      : n×n bitmask matrix (converse-symmetric)
    observed : list of (i,j) pairs with i<j that received explicit constraints
    """
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    n_edges = min(int(math.floor(n * d / 2)), len(all_pairs))
    observed = rng.sample(all_pairs, n_edges) if n_edges > 0 else []

    net: List[List[int]] = [[UNIVERSAL] * n for _ in range(n)]
    for i in range(n):
        net[i][i] = 0

    for i, j in observed:
        indices = rng.sample(range(B), l)
        label = sum(1 << k for k in indices)
        net[i][j] = label
        net[j][i] = converse_mask(label)

    return net, observed


# ---------------------------------------------------------------------------
# Optimised agenda-based PC-2
# ---------------------------------------------------------------------------
def run_pc2(
    n: int,
    net: List[List[int]],
    observed: List[Tuple[int, int]],
) -> Tuple[bool, Dict]:
    """
    Agenda-based path-consistency with two optimisations:

    1. Initial agenda seeds only triples (i,k,j) where at least one of
       R(i,k) or R(k,j) is non-universal.  Universal operands contribute
       nothing to R(i,j) ← R(i,j) ∩ (R(i,k) ∘ R(k,j)), so seeding from
       them wastes computation.  This reduces the initial queue from O(n³)
       to O(|E|·n) entries.

    2. Converse symmetry maintained immediately: when net[i][j] tightens,
       net[j][i] ← converse(net[i][j]) is updated before new triples are
       added to the agenda, keeping the network always symmetric.

    Both correctness and completeness are preserved: every triple that could
    produce a revision is eventually added when a relevant arc tightens.
    """
    non_univ: Set[Tuple[int, int]] = set()
    for i, j in observed:
        non_univ.add((i, j))
        non_univ.add((j, i))

    agenda: deque = deque()
    in_agenda: Set[Tuple[int, int, int]] = set()

    def enqueue(t: Tuple[int, int, int]) -> None:
        if t not in in_agenda:
            agenda.append(t)
            in_agenda.add(t)

    # Seed: for each constrained arc (a,b), add triples where it is an operand
    for a, b in list(non_univ):
        for m in range(n):
            if m == a or m == b:
                continue
            # R(m,b) ← R(m,a) ∘ R(a,b)
            if (m, a) in non_univ:
                enqueue((m, a, b))
            # R(a,m) ← R(a,b) ∘ R(b,m)
            if (b, m) in non_univ:
                enqueue((a, b, m))

    checks = reductions = 0

    while agenda:
        i, k, j = agenda.popleft()
        in_agenda.discard((i, k, j))

        rik = net[i][k]
        rkj = net[k][j]
        if rik == UNIVERSAL or rkj == UNIVERSAL:
            continue

        checks += 1
        composed = compose_masks(rik, rkj)
        rij = net[i][j]
        new_ij = rij & composed

        if new_ij == rij:
            continue

        reductions += 1
        net[i][j] = new_ij
        net[j][i] = converse_mask(new_ij)

        if new_ij == 0:
            return False, {'consistent': False,
                           'checks': checks, 'reductions': reductions}

        non_univ.add((i, j))
        non_univ.add((j, i))

        # Propagate: add all triples affected by the tightening of (i,j)
        for m in range(n):
            if m == i or m == j:
                continue
            enqueue((m, i, j))   # R(m,j) ← R(m,i) ∘ R(i,j)
            enqueue((i, j, m))   # R(i,m) ← R(i,j) ∘ R(j,m)
            enqueue((m, j, i))   # R(m,i) ← R(m,j) ∘ R(j,i)
            enqueue((j, i, m))   # R(j,m) ← R(j,i) ∘ R(i,m)

    return True, {'consistent': True,
                  'checks': checks, 'reductions': reductions}


# ---------------------------------------------------------------------------
# Single trial
# ---------------------------------------------------------------------------
def run_trial(n: int, d: float, l: int, trial: int, seed: int) -> Dict:
    rng = random.Random(seed)
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    total_pairs = len(all_pairs)

    net, observed = generate_network(n, d, l, rng)
    obs_set = set(observed)
    unobs_pairs = [(i, j) for i, j in all_pairs if (i, j) not in obs_set]

    ls_obs_before   = float(l)
    ls_unobs_before = float(B)
    ls_all_before   = (len(observed) * ls_obs_before +
                       len(unobs_pairs) * ls_unobs_before) / total_pairs

    net_copy = [row[:] for row in net]
    consistent, stats = run_pc2(n, net_copy, observed)

    base = {
        'n': n, 'd': d, 'l': l, 'trial': trial, 'seed': seed,
        'n_edges':  len(observed),
        'p1':       round(len(observed) / total_pairs, 4),
        'consistent': consistent,
        'checks':      stats['checks'],
        'reductions':  stats['reductions'],
        'ls_obs_before':  round(ls_obs_before, 3),
        'ls_all_before':  round(ls_all_before, 3),
        't_before':       round(1.0 - ls_all_before / B, 4),
    }

    if not consistent:
        return {**base,
                'ls_obs_after': None, 'ls_unobs_after': None,
                'ls_all_after': None, 't_after': None,
                'alr': None, 'pr_obs': None, 'pr_unobs': None}

    # Post-PC-2 metrics (consistent trials only)
    def popcount(x: int) -> int:
        return bin(x).count('1')

    ls_obs_list   = [popcount(net_copy[i][j]) for i, j in observed]
    ls_unobs_list = [popcount(net_copy[i][j]) for i, j in unobs_pairs]
    ls_obs_after   = mean(ls_obs_list)   if ls_obs_list   else 0.0
    ls_unobs_after = mean(ls_unobs_list) if ls_unobs_list else float(B)
    ls_all_after   = ((len(observed)    * ls_obs_after +
                       len(unobs_pairs) * ls_unobs_after) / total_pairs)

    alr     = sum(1 for i, j in all_pairs
                  if popcount(net_copy[i][j]) == 1) / total_pairs
    pr_obs  = (sum(1 for (i, j), ls in zip(observed, ls_obs_list)
                   if ls < l) / len(observed)) if observed else 0.0
    pr_unobs = (sum(1 for ls in ls_unobs_list if ls < B)
                / len(unobs_pairs)) if unobs_pairs else 0.0

    return {**base,
            'ls_obs_after':   round(ls_obs_after,   3),
            'ls_unobs_after': round(ls_unobs_after, 3),
            'ls_all_after':   round(ls_all_after,   3),
            't_after':        round(1.0 - ls_all_after / B, 4),
            'alr':            round(alr,      4),
            'pr_obs':         round(pr_obs,   4),
            'pr_unobs':       round(pr_unobs, 4)}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def aggregate(trials: List[Dict]) -> Dict:
    total = len(trials)
    cons  = [t for t in trials if t['consistent']]

    def stats(vals):
        if not vals:
            return {'mean': None, 'sd': None}
        return {'mean': round(mean(vals), 5),
                'sd':   round(pstdev(vals), 5)}

    def col(key, src=trials):
        return [t[key] for t in src if t.get(key) is not None]

    s: Dict = {
        'n_trials':     total,
        'n_consistent': len(cons),
        'failure_rate': round(1 - len(cons) / total, 4) if total else None,
    }

    # All other metrics
    all_metrics = ['p1', 'n_edges', 'checks', 'reductions',
                   'ls_obs_before', 'ls_all_before', 't_before']
    cons_metrics = ['ls_obs_after', 'ls_unobs_after', 'ls_all_after',
                    't_after', 'alr', 'pr_obs', 'pr_unobs']

    for m in all_metrics:
        st = stats(col(m, trials))
        s[f'{m}_mean'] = st['mean']
        s[f'{m}_sd']   = st['sd']

    for m in cons_metrics:
        st = stats(col(m, cons))
        s[f'{m}_mean'] = st['mean']
        s[f'{m}_sd']   = st['sd']

    return s


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='QRPC A(n,d,l) benchmark — Renz & Nebel (2001)')
    p.add_argument('--n-values', type=int, nargs='+',
                   default=[10, 15, 20, 25, 30])
    p.add_argument('--d-values', type=float, nargs='+',
                   default=[2, 4, 6, 8, 10])
    p.add_argument('--l-values', type=int, nargs='+',
                   default=[1, 2, 3, 4, 5, 6, 8, 12, 24, 30])
    p.add_argument('--trials',   type=int, default=200,
                   help='Number of trials per condition (default: 200)')
    p.add_argument('--seed',     type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print('QRPC A(n,d,l) Benchmark — Renz & Nebel (2001)')
    print(f'  n  ∈ {args.n_values}')
    print(f'  d  ∈ {args.d_values}')
    print(f'  l  ∈ {args.l_values}')
    print(f'  max trials: {args.trials}  |  seed: {args.seed}')
    valid = [
        (n, d, l)
        for n in args.n_values
        for d in args.d_values if d < n
        for l in args.l_values if l < B
    ]
    total_conds = len(valid)

    print(f'  valid conditions: {total_conds}')
    print(f'  total trials:      {total_conds * args.trials:,}')
    print(f'  output: {OUTPUT_PATH}\n')

    results:        Dict = {}
    all_trial_rows: List[Dict] = []
    cond_num = 0

    for n in args.n_values:
        for d in args.d_values:
            if d >= n:
                print(f'  [SKIP] n={n}, d={d}  (d must be < n)')
                continue
            for l in args.l_values:
                if l >= B:
                    print(f'  [SKIP] n={n}, d={d}, l={l}  (l must be < |B|=48)')
                    continue

                cond_num += 1
                key = str((n, float(d), l))

                n_trials = args.trials

                print(f'  [{cond_num:3d}/{total_conds}] '
                      f'A(n={n:2d}, d={d:2.0f}, l={l:2d})  '
                      f'{n_trials:3d} trials ... ', end='', flush=True)

                trials: List[Dict] = []
                for trial in range(n_trials):
                    seed = args.seed + cond_num * 100_003 + trial
                    row  = run_trial(n, d, l, trial, seed)
                    trials.append(row)
                    all_trial_rows.append(row)

                summary = aggregate(trials)
                results[key] = {
                    'params':  {'n': n, 'd': float(d), 'l': l,
                                'n_trials': n_trials},
                    'summary': summary,
                    'trials':  trials,
                }

                fr   = summary.get('failure_rate', '?')
                ls_a = summary.get('ls_all_after_mean')
                t_a  = summary.get('t_after_mean')
                alr  = summary.get('alr_mean')
                print(f'done  '
                      f'fail={fr:.3f}  '
                      f'ls_after={ls_a if ls_a is not None else "-":>6}  '
                      f't_after={t_a if t_a is not None else "-":>7}  '
                      f'alr={alr if alr is not None else "-"}')

                # Incremental save
                with OUTPUT_PATH.open('w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, default=str)

    # Final save
    with OUTPUT_PATH.open('w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)

    print(f'\n✓ experiment_results.json → {OUTPUT_PATH}')
    print(f'  Conditions: {cond_num}  |  '
          f'Total trials: {len(all_trial_rows)}')


if __name__ == '__main__':
    main()
