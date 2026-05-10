"""
Extrusión de polígono Y–Z a lo largo del eje local de barra (PyVista).
"""

from __future__ import annotations

from typing import List

import numpy as np

try:
    import pyvista as pv
except ImportError:  # pragma: no cover
    pv = None  # type: ignore


def extrude_polygon_yz_prism(
    pts_yz: np.ndarray,
    L: float,
    origin: np.ndarray,
    x_local: np.ndarray,
    y_local: np.ndarray,
    z_local: np.ndarray,
) -> "pv.PolyData":
    """
    Prisma recto: polígono en el plano (y_local, z_local) en x=0 extruido hasta x=L.
    ``pts_yz`` forma (n, 2) vértices en orden; el primer punto no debe repetirse al final.
    """
    if pv is None:
        raise ImportError("pyvista")
    pts_yz = np.asarray(pts_yz, dtype=float)
    n = int(pts_yz.shape[0])
    if n < 3:
        return pv.PolyData()
    L = float(L)
    if L < 1e-12:
        return pv.PolyData()

    yl = pts_yz[:, 0]
    zl = pts_yz[:, 1]
    pts0 = np.zeros((n, 3), dtype=float)
    pts1 = np.zeros((n, 3), dtype=float)
    o = np.asarray(origin, dtype=float).ravel()[:3]
    xl = np.asarray(x_local, dtype=float).ravel()[:3]
    yvec = np.asarray(y_local, dtype=float).ravel()[:3]
    zvec = np.asarray(z_local, dtype=float).ravel()[:3]
    for i in range(n):
        base = o + yl[i] * yvec + zl[i] * zvec
        pts0[i] = base
        pts1[i] = base + L * xl

    all_pts = np.vstack([pts0, pts1])
    faces: List[int] = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([4, i, j, j + n, i + n])
    faces.extend([n] + list(range(n)))
    faces.extend([n] + list(range(2 * n - 1, n - 1, -1)))
    mesh = pv.PolyData(all_pts, np.asarray(faces, dtype=np.int64))
    return mesh
