"""Cac tien ich truc quan hoa ban do va bieu do."""
from .illustrations import candidate_panels, compare_regions_panel
from .maps import cluster_map, temporal_shift_map

__all__ = [
    "cluster_map",
    "temporal_shift_map",
    "candidate_panels",
    "compare_regions_panel",
]
