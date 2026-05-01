"""
Visualización auxiliar para la GUI Ftool: nodos coloreados por restricciones (coherente con matplotlib).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from plot.plot import _color_nodo_por_restricciones, _dims_perfil_ipn

# Texto para barra de estado (leyenda de colores de nodos; ya no se dibuja en el viewport VTK).
NODOS_LEGEND_STATUS = (
    "Nodos (indeformados):  ·  verde: 1 restr.  ·  amarillo: 3  ·  "
    "rojo: empotrado (6)  ·  gris: libre / indef."
)


def _etiqueta_restricciones(nodo: Any) -> str:
    raw = getattr(nodo, "restricciones", None)
    if raw is None:
        return "?"
    rlist = list(raw)[:6]
    names = ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz")
    parts = [names[i] for i, v in enumerate(rlist) if v is True]
    if not parts:
        return "libre"
    return ",".join(parts)


def _radio_esfera_nodo(
    nodos: Sequence[Any], ipn_dims: Optional[Dict[str, float]], escala_seccion: float
) -> float:
    h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
    base = float(max(h, b)) * 0.14
    if len(nodos) == 0:
        return max(base, 1.0)
    pts = np.array([[float(n.x), float(n.y), float(n.z)] for n in nodos], dtype=float)
    ext = float(np.ptp(pts, axis=0).max()) if pts.size else 0.0
    r = max(ext * 0.018, base, 0.5)
    return r


def add_nodos_overlay_pyvista(
    plotter: Any,
    nodos: List[Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float = 1.0,
) -> None:
    """Esferas por nodo (color = restricciones), etiquetas N# + DOF fijos, leyenda texto."""
    if not nodos:
        return
    import pyvista as pv

    r = _radio_esfera_nodo(nodos, ipn_dims, escala_seccion)
    points: List[List[float]] = []
    labels: List[str] = []
    for n in nodos:
        c = _color_nodo_por_restricciones(n)
        cx, cy, cz = float(n.x), float(n.y), float(n.z)
        sp = pv.Sphere(
            radius=r,
            center=(cx, cy, cz),
            theta_resolution=14,
            phi_resolution=14,
        )
        plotter.add_mesh(sp, color=c, smooth_shading=True, pickable=False)
        points.append([cx, cy, cz])
        labels.append(f"N{int(getattr(n, 'id', 0))} [{_etiqueta_restricciones(n)}]")
    if points:
        pts = np.asarray(points, dtype=float)
        plotter.add_point_labels(
            pts,
            labels,
            font_size=int(max(8, min(13, r * 0.85))),
            text_color="#1a1d22",
            show_points=False,
            shape_opacity=0.28,
            always_visible=True,
            pickable=False,
        )


def parse_tupla3_floats(text: str) -> Optional[Tuple[float, float, float]]:
    """
    Interpreta '(a,b,c)', 'a,b,c' o separadores por espacio.
    Acepta coma decimal en cada componente.
    """
    s = (text or "").strip().strip("()[]")
    if not s:
        return None
    parts = re.split(r"[,;\s]+", s)
    parts = [p for p in parts if p != ""]
    if len(parts) != 3:
        return None
    try:
        return (
            float(parts[0].replace(",", ".")),
            float(parts[1].replace(",", ".")),
            float(parts[2].replace(",", ".")),
        )
    except ValueError:
        return None


def parse_restricciones_texto(text: str) -> Optional[List[bool]]:
    """
    Texto editable para la columna restricciones: libre, emp., o lista Ux,Uy,Uz,Rx,Ry,Rz.
    Devuelve None si hay token inválido.
    """
    t = (text or "").strip()
    if not t:
        return [False] * 6
    low = t.lower()
    if low in ("libre", "-", "0"):
        return [False] * 6
    if low in ("emp", "emp.", "empotrado", "fijo"):
        return [True] * 6
    names_map = {"ux": 0, "uy": 1, "uz": 2, "rx": 3, "ry": 4, "rz": 5}
    out = [False] * 6
    for part in re.split(r"[,;\s]+", low):
        if not part:
            continue
        if part not in names_map:
            return None
        out[names_map[part]] = True
    return out


def restricciones_texto_desde_spec(n: Dict[str, Any]) -> str:
    """Columna restricciones para tablas (sin coordenadas)."""
    d = detalle_nodo_spec(n)
    sep = " — "
    if sep in d:
        return d.split(sep, 1)[1].strip()
    return d


def detalle_nodo_spec(n: Dict[str, Any]) -> str:
    """Texto para columna Detalle del árbol (coordenadas + resumen de fix)."""
    fix = n.get("fix") or n.get("restricciones")
    if not isinstance(fix, list):
        fix = []
    while len(fix) < 6:
        fix.append(False)
    names = ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz")
    parts = [names[i] for i, v in enumerate(fix[:6]) if v is True]
    nfix = sum(1 for v in fix[:6] if v is True)
    if nfix == 0:
        suf = "libre"
    elif nfix == 6:
        suf = "emp."
    else:
        suf = ",".join(parts)
    return f"({n['x']},{n['y']},{n['z']}) — {suf}"
