"""
qrpc_caches.py
--------------
Shared singleton caches for QRPC composition and converse lookups.

All operations use canonical relation strings throughout.

Public API
----------
_build_caches()  — populate caches on first call (idempotent)
_COMPOSE_CACHE   — dict[(br_a, br_b)] -> frozenset of canonical result strings
_CONVERSE_CACHE  — dict[br] -> converse canonical string
"""
from __future__ import annotations
from qrpc.converse import converse
from qrpc.table48 import all_notations

_COMPOSE_CACHE:  dict[tuple[str, str], frozenset[str]] | None = None
_CONVERSE_CACHE: dict[str, str]                        | None = None

_UNIVERSE_SIZE = 48
_ALL_BRS_SET: frozenset[str] | None = None


def _build_caches() -> None:
    """Build (once) the singleton composition and converse caches."""
    global _COMPOSE_CACHE, _CONVERSE_CACHE, _ALL_BRS_SET
    if _COMPOSE_CACHE is not None:
        return
    from qrpc.composition import compose_basic
    brs = list(all_notations())
    _ALL_BRS_SET = frozenset(brs)

    comp: dict[tuple[str, str], frozenset[str]] = {}
    for br_a in brs:
        for br_b in brs:
            comp[(br_a, br_b)] = compose_basic(br_a, br_b)

    cv: dict[str, str] = {}
    for br in brs:
        c = converse(br)
        if c:
            cv[br] = c

    _COMPOSE_CACHE  = comp
    _CONVERSE_CACHE = cv
