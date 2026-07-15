"""
path_consistency.py
-------------------
Path consistency (PC-2) algorithm for QRPC constraint networks.

A constraint network is a set of n objects with a general relation (set of
basic relations) between each ordered pair. PC-2 iteratively enforces the
constraint:

    R_ij ← R_ij ∩ (R_ik ∘ R_kj)   for all triples (i, j, k)

until no further change occurs (fixed point) or the network becomes
inconsistent (some R_ij becomes empty).

All relations are represented as frozensets of canonical strings.
"""

from __future__ import annotations
from typing import Dict, FrozenSet, List, Optional, Tuple
from .composition import compose
from .table48 import all_notations

# Type alias: a constraint network maps (i,j) → frozenset of canonical strings
Network = Dict[Tuple[int, int], FrozenSet[str]]

# Universal relation: all 48 canonical strings
_UNIVERSAL: FrozenSet[str] = frozenset(all_notations())


def make_universal_relation() -> FrozenSet[str]:
    """Returns the universal relation — all 48 canonical relation strings."""
    return _UNIVERSAL


def make_network(n: int,
                 constraints: Optional[Dict[Tuple[int, int],
                              FrozenSet[str]]] = None
                 ) -> Network:
    """
    Creates an n-object constraint network.

    Unspecified pairs are initialised to the universal relation (all 48
    canonical strings).

    Args:
        n:           number of objects (labelled 0..n-1)
        constraints: optional dict of (i,j) → frozenset of canonical strings

    Returns:
        A complete network with an entry for every ordered pair (i,j), i≠j.
    """
    net: Network = {}
    for i in range(n):
        for j in range(n):
            if i != j:
                net[(i, j)] = _UNIVERSAL
    if constraints:
        for (i, j), rel in constraints.items():
            net[(i, j)] = frozenset(rel)
    return net


def pc2(network: Network,
        n: int,
        progress_callback=None
        ) -> Tuple[Network, bool]:
    """
    Applies the PC-2 algorithm to a constraint network.

    Args:
        network:           constraint network (dict (i,j) → frozenset of str)
        n:                 number of objects
        progress_callback: optional callable(iteration: int, changes: int)

    Returns:
        (result_network, is_consistent)
    """
    net: Network = dict(network)

    iteration = 0
    while True:
        changed = False
        iteration += 1

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                for k in range(n):
                    if k == i or k == j:
                        continue

                    r_ij = net[(i, j)]
                    r_ik = net[(i, k)]
                    r_kj = net[(k, j)]

                    composed  = compose(r_ik, r_kj)
                    new_r_ij  = r_ij & composed

                    if new_r_ij != r_ij:
                        net[(i, j)] = new_r_ij
                        changed = True

                    if not net[(i, j)]:
                        if progress_callback:
                            progress_callback(iteration, -1)
                        return net, False

        if progress_callback:
            progress_callback(iteration, int(changed))

        if not changed:
            break

    return net, True


def network_from_notations(
        n: int,
        constraints: Dict[Tuple[int, int], List[str]]
) -> Network:
    """
    Convenience constructor: builds a network from lists of canonical strings.

    Args:
        n:           number of objects
        constraints: dict (i,j) → list of canonical strings

    Returns:
        Network where each relation is a frozenset of canonical strings.
    """
    expanded = {}
    for (i, j), ncs in constraints.items():
        expanded[(i, j)] = frozenset(ncs)
    return make_network(n, expanded)


def notations_from_network(
        network: Network
) -> Dict[Tuple[int, int], List[str]]:
    """
    Converts a network to sorted lists of canonical strings for display.
    """
    return {(i, j): sorted(rel) for (i, j), rel in network.items()}
