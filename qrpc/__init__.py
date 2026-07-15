"""
QRPC — Qualitative Reasoning with Projected Configurations
Logic layer (pure Python, no GUI dependencies).

Modules:
    representation    — P12, QVal, DLR, Representation (instantiated repr.)
    pi_rotations      — rot_alpha, rot_beta, rot_gamma
    table48           — 48-relation catalogue (get_compact, get_instantiated)
                        get_compact:     instantiated repr. → compact form string
                        get_instantiated: compact form string → list of instantiated reprs.
    converse          — converse operation
    z_compositions    — Z-table (288 canonical compositions)
    composition       — full composition engine + dynamic rules table
    path_consistency  — PC-2 algorithm
"""

from .representation import P12, QVal, DLR, Representation
from .pi_rotations import rot_alpha, rot_beta, rot_gamma
from .table48 import get_compact, get_instantiated, get_br, get_tuples, all_notations, all_relations
from .converse import converse
from .composition import compose_basic, compose
from .path_consistency import (
    make_network, pc2, network_from_notations, notations_from_network
)

__all__ = [
    'P12', 'QVal', 'DLR', 'Representation',
    'rot_alpha', 'rot_beta', 'rot_gamma',
    'get_compact', 'get_instantiated',
    'get_br', 'get_tuples',          # backward-compatibility aliases
    'all_notations', 'all_relations',
    'converse',
    'compose_basic', 'compose',
    'make_network', 'pc2', 'network_from_notations', 'notations_from_network',
]
