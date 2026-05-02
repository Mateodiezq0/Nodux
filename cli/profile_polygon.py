"""
Polígono de sección en plano local Y–Z (cm) para materiales en modo manual.
"""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import numpy as np


def polygon_area_yz(points: Sequence[Sequence[float]]) -> float:
    """Área (fórmula de shoelace); polígono simple sin autointersecciones."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] != 2:
        return 0.0
    y = pts[:, 0]
    z = pts[:, 1]
    return float(0.5 * abs(np.sum(y * np.roll(z, -1) - z * np.roll(y, -1))))


def normalize_polygon_yz(raw: Any) -> List[List[float]]:
    """Lista de [y,z] con al menos 3 vértices o []."""
    if not isinstance(raw, list) or len(raw) < 3:
        return []
    out: List[List[float]] = []
    for p in raw:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        try:
            out.append([float(p[0]), float(p[1])])
        except (TypeError, ValueError):
            continue
    return out if len(out) >= 3 else []
