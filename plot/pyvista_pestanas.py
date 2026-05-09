"""
Pestañas PyVista equivalentes a ``mostrar_dibujos_matplotlib_pestanas`` (plot.plot).

Requiere: ``pip install pyvista pyvistaqt PySide6`` (o ``PyQt5`` en lugar de PySide6).

- Sin esferas en nodos ni eje negro sobre el alma de las barras (solo perfil IPN).
- Pestaña **Deformada** si se pasa el vector de desplazamientos D (amplificación con slider).
- Exportación VTK multiblock completa para ParaView.
"""

from __future__ import annotations

import sys
import time
import types
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

import numpy as np

_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from plot.plot import (  # noqa: E402
    _COLOR_CARGA_DISTRIB_BAR,
    _COLOR_CARGA_PUNTUAL_BAR,
    _DIAG_COLOR_NEG,
    _DIAG_COLOR_POS,
    _DIAG_COLOR_ZERO,
    _box_faces_local,
    _diagrama_corte_local_barra,
    _diagrama_momento_my_local_barra,
    _diagrama_momento_mz_local_barra,
    _diagrama_mx_torsion_local_barra,
    _dims_perfil_ipn,
    _local_to_global,
    _momento_polyline_con_cruces_cero,
    _punto_carga_banda_superior_ipn,
    _vector_global_carga_puntual,
    obtener_coordenadas_barra,
)
from plot.pyvista_vista import (  # noqa: E402
    _collect_franja_quads_momento_linear,
    _iter_polilinea_segmentos,
    _merge_line_tubes,
    _merge_quad_meshes_same_color,
    _quad_to_polydata,
    _require_pyvista,
    _segment_length,
    _terna_seccion_desde_cuerda,
    build_ipn_mesh,
    collect_mz_diagram_geometry,
)

try:
    import pyvista as pv
except ImportError:
    pv = None  # type: ignore


def _nodo_dof6_visual(nodo: Any, D: np.ndarray, factor: float) -> np.ndarray:
    uid = int(getattr(nodo, "id", 0))
    base = (uid - 1) * 6
    Dv = np.asarray(D, dtype=float).ravel()
    if base + 5 < len(Dv):
        return Dv[base : base + 6] * float(factor)
    return np.zeros(6, dtype=float)


def _centroid_disp_local_bern(x: float, L: float, ul: np.ndarray) -> np.ndarray:
    """Eje barra en locales: axial lineal + flexión Hermite (orden GDL de ``Barra._calcular_K_local``)."""
    if L < 1e-18:
        return np.zeros(3, dtype=float)
    xi = x / L
    p1 = 1.0 - 3.0 * xi * xi + 2.0 * xi * xi * xi
    p2 = L * (xi - 2.0 * xi * xi + xi * xi * xi)
    p3 = 3.0 * xi * xi - 2.0 * xi * xi * xi
    p4 = L * (xi * xi * xi - xi * xi)
    ux = (1.0 - xi) * ul[0] + xi * ul[6]
    uy = p1 * ul[1] + p2 * ul[5] + p3 * ul[7] + p4 * ul[11]
    uz = p1 * ul[2] + p2 * ul[4] + p3 * ul[8] + p4 * ul[10]
    return np.array([ux, uy, uz], dtype=float)


def build_ipn_mesh_deformada_curva(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    D: np.ndarray,
    factor_visual: float,
    *,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
) -> "pv.PolyData":
    """
    Malla IPN siguiendo el eje deformado (Bernoulli: axial + Hermite en y/z local según K_local).
    ``factor_visual`` escala U y rotaciones (mismo factor que el deslizador de la pestaña).
    """
    _require_pyvista()
    meshes: List[pv.PolyData] = []
    for barra in barras:
        bid = getattr(barra, "id", None)
        bid_int = int(bid) if bid is not None else None
        ci0, cf0 = obtener_coordenadas_barra(barra, nodos_dict)
        if ci0 is None or cf0 is None:
            continue
        Gi = np.asarray(ci0, dtype=float).ravel()[:3]
        Gf = np.asarray(cf0, dtype=float).ravel()[:3]
        vec = Gf - Gi
        L0 = float(np.linalg.norm(vec))
        if L0 < 1e-9:
            continue
        ni = nodos_dict.get(barra.nodo_i)
        nf = nodos_dict.get(barra.nodo_f)
        if ni is None or nf is None:
            continue
        if hasattr(barra, "calcular_longitud_y_bases"):
            try:
                barra.calcular_longitud_y_bases()
            except Exception:
                pass
        Lbar = float(getattr(barra, "L", 0.0) or 0.0)
        if Lbar < 1e-9:
            Lbar = L0
        if not barra.asegurar_terna_ejes_locales():
            continue
        T = barra.construir_matriz_rotacion_T_12x12()
        d_g = np.concatenate(
            [
                _nodo_dof6_visual(ni, D, factor_visual),
                _nodo_dof6_visual(nf, D, factor_visual),
            ]
        )
        ul = (T @ np.asarray(d_g, dtype=float).reshape(12, 1)).ravel()
        R = barra.construir_matriz_rotacion_R_3x3()
        y_ref = np.asarray(barra.y_local, dtype=float).ravel()[:3]
        z_ref = np.asarray(barra.z_local, dtype=float).ravel()[:3]
        ns = int(max(10, min(40, round(Lbar / 30.0 * 12))))
        xs = np.linspace(0.0, Lbar, ns + 1, dtype=float)
        poly: List[np.ndarray] = []
        for xk in xs:
            r0 = Gi + (float(xk) / Lbar) * vec
            dloc = _centroid_disp_local_bern(float(xk), Lbar, ul)
            poly.append(r0 + R.T @ dloc)
        poly_a = np.array(poly, dtype=float)
        pts_prof = None
        if profile_polygon_yz_per_bar_id is not None and bid_int is not None:
            raw_poly = profile_polygon_yz_per_bar_id.get(bid_int)
            if raw_poly is not None:
                pts_prof = np.asarray(raw_poly, dtype=float)

        if (
            pts_prof is not None
            and pts_prof.ndim == 2
            and pts_prof.shape[0] >= 3
            and pts_prof.shape[1] >= 2
        ):
            from plot.profile_extrude import extrude_polygon_yz_prism

            P = pts_prof[:, :2] * float(escala_seccion)
            for seg in range(ns):
                origin = poly_a[seg]
                vend = poly_a[seg + 1] - origin
                Lseg = float(np.linalg.norm(vend))
                if Lseg < 1e-10:
                    continue
                x_loc, y_loc, z_loc = _terna_seccion_desde_cuerda(vend, y_ref, z_ref)
                mseg = extrude_polygon_yz_prism(
                    P, Lseg, origin, x_loc, y_loc, z_loc
                )
                if mseg.n_points > 0:
                    meshes.append(mseg)
            continue

        custom_ipn = (
            ipn_dims_per_bar_id is not None
            and bid_int is not None
            and bid_int in ipn_dims_per_bar_id
        )
        if custom_ipn:
            h, b, tw, tf = _dims_perfil_ipn(
                ipn_dims_per_bar_id[bid_int], escala_seccion
            )
        elif (
            bid_int is not None
            and tube_outer_radius_per_bar_id is not None
            and bid_int in tube_outer_radius_per_bar_id
        ):
            Ro = float(tube_outer_radius_per_bar_id[bid_int]) * float(escala_seccion)
            if poly_a.shape[0] >= 2:
                meshes.append(
                    pv.lines_from_points(poly_a).tube(
                        radius=max(Ro, 1e-12), n_sides=48
                    )
                )
            continue
        else:
            h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)

        for seg in range(ns):
            origin = poly_a[seg]
            vend = poly_a[seg + 1] - origin
            Lseg = float(np.linalg.norm(vend))
            if Lseg < 1e-10:
                continue
            x_loc, y_loc, z_loc = _terna_seccion_desde_cuerda(vend, y_ref, z_ref)
            boxes_seg = [
                (0.0, Lseg, -b / 2.0, b / 2.0, h / 2.0 - tf, h / 2.0),
                (0.0, Lseg, -tw / 2.0, tw / 2.0, -h / 2.0 + tf, h / 2.0 - tf),
                (0.0, Lseg, -b / 2.0, b / 2.0, -h / 2.0, -h / 2.0 + tf),
            ]
            for xa, xb, y0, y1, z0, z1 in boxes_seg:
                for face in _box_faces_local(xa, xb, y0, y1, z0, z1):
                    g = _local_to_global(face, origin, x_loc, y_loc, z_loc)
                    meshes.append(_quad_to_polydata(np.array(g, dtype=float)))
    if not meshes:
        return pv.PolyData()
    return meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]


def _collect_escalonado_franja_quads(
    origin: np.ndarray,
    x_local: np.ndarray,
    offset_local: np.ndarray,
    x_b: np.ndarray,
    v_b: np.ndarray,
    escala_v: float,
    color_pos: str,
    color_neg: str,
    color_zero: str,
) -> List[Tuple[np.ndarray, str]]:
    """
    Quads/triángulos para el relleno del diagrama escalonado (o lineal a trozos).
    Soporta tanto segmentos constantes (cargas puntuales) como con rampa
    (cargas distribuidas).  Cuando hay cruce de cero se generan dos triángulos.
    """
    out: List[Tuple[np.ndarray, str]] = []
    if x_b.size < 2:
        return out
    atol = 1e-9 * max(1.0, float(np.max(np.abs(v_b))) if v_b.size else 1.0)
    for k in range(len(x_b) - 1):
        xa, xb = float(x_b[k]), float(x_b[k + 1])
        va, vb = float(v_b[k]), float(v_b[k + 1])
        if abs(xb - xa) < 1e-12:
            continue
        base_a = origin + xa * x_local
        base_b = origin + xb * x_local
        top_a = base_a + va * escala_v * offset_local
        top_b = base_b + vb * escala_v * offset_local

        # Cruce de cero: dividir en dos triángulos
        if va * vb < 0 and abs(vb - va) > 1e-18:
            x_m = xa + abs(va) / abs(vb - va) * (xb - xa)
            x_m = float(np.clip(x_m, min(xa, xb), max(xa, xb)))
            base_m = origin + x_m * x_local
            tri1 = np.vstack([base_a, base_m, top_a])
            col1 = color_zero if abs(va) <= atol else (color_pos if va > 0 else color_neg)
            out.append((tri1, col1))
            tri2 = np.vstack([base_m, base_b, top_b])
            col2 = color_zero if abs(vb) <= atol else (color_pos if vb > 0 else color_neg)
            out.append((tri2, col2))
        else:
            quad = np.vstack([base_a, base_b, top_b, top_a])
            v_avg = (va + vb) / 2.0
            col = color_zero if abs(v_avg) <= atol else (color_pos if v_avg > 0 else color_neg)
            out.append((quad, col))
    return out


def _escala_corte_global(
    barras: List[Any], idx_corte: int, escala_diagrama: float, nx_invert: bool
) -> float:
    max_abs_v = 0.0
    Ls: List[float] = []
    for barra in barras:
        x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, idx_corte)
        if x_b.size > 0:
            v_esc = -v_b if nx_invert else v_b
            max_abs_v = max(max_abs_v, float(np.max(np.abs(v_esc))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_v) if max_abs_v > 1e-12 else 1.0
    return escala_base * float(escala_diagrama)


def _escala_momento_my_global(barras: List[Any], escala_diagrama: float) -> float:
    max_abs_m = 0.0
    Ls: List[float] = []
    for barra in barras:
        xs, ms, L = _diagrama_momento_my_local_barra(barra)
        if xs.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(ms))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    return escala_base * float(escala_diagrama)


def _escala_momento_mx_global(barras: List[Any], escala_diagrama: float) -> float:
    max_abs_m = 0.0
    Ls: List[float] = []
    for barra in barras:
        x_b, m_b, L, _, _ = _diagrama_mx_torsion_local_barra(barra)
        if x_b.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(m_b))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    return escala_base * float(escala_diagrama)


def collect_corte_diagram_geometry(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    corte: str,
    escala_diagrama_corte: float = 1.0,
) -> Tuple[
    List[Tuple[np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray]],
    float,
    List[Dict[str, Any]],
]:
    assert corte in ("vy", "vz", "nx")
    idx = {"vy": 1, "vz": 2, "nx": 0}[corte]
    nx_inv = corte == "nx"
    escala_v = _escala_corte_global(barras, idx, escala_diagrama_corte, nx_inv)
    cp, cn, cz = _DIAG_COLOR_POS, _DIAG_COLOR_NEG, _DIAG_COLOR_ZERO
    quads: List[Tuple[np.ndarray, str]] = []
    segs: List[Tuple[np.ndarray, np.ndarray, str]] = []
    refs: List[Tuple[np.ndarray, np.ndarray]] = []
    hover: List[Dict[str, Any]] = []

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()
        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        y_local = np.asarray(getattr(barra, "y_local", [0.0, 1.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        x_local /= max(np.linalg.norm(x_local), 1e-12)
        y_local /= max(np.linalg.norm(y_local), 1e-12)
        z_local /= max(np.linalg.norm(z_local), 1e-12)
        offset_local = y_local if corte in ("vy", "nx") else z_local

        x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, idx)
        if x_b.size == 0:
            continue
        v_dib = (-v_b) if nx_inv else v_b

        quads.extend(
            _collect_escalonado_franja_quads(
                origin, x_local, offset_local, x_b, v_dib, escala_v, cp, cn, cz
            )
        )
        pts = np.array(
            [origin + float(xb) * x_local + float(vb) * escala_v * offset_local for xb, vb in zip(x_b, v_dib)],
            dtype=float,
        )
        for p0, p1, col in _iter_polilinea_segmentos(pts, v_dib, cp, cn, cz):
            segs.append((p0, p1, col))
        refs.append((origin, origin + L * x_local))

        bid = getattr(barra, "id", None)
        for k in range(len(x_b)):
            ptk = pts[k]
            hover.append(
                {
                    "bar_id": bid,
                    "x_local": float(x_b[k]),
                    "v": float(v_dib[k]),
                    "corte": corte,
                    "pos": (float(ptk[0]), float(ptk[1]), float(ptk[2])),
                }
            )
        for k in range(len(x_b) - 1):
            xa, xb = float(x_b[k]), float(x_b[k + 1])
            va, vb = float(v_dib[k]), float(v_dib[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            if not np.isclose(va, vb, rtol=1e-9, atol=1e-12 * max(1.0, abs(va), abs(vb))):
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                pt = origin + xm * x_local + va * escala_v * offset_local
                hover.append(
                    {
                        "bar_id": bid,
                        "x_local": float(xm),
                        "v": float(va),
                        "corte": corte,
                        "pos": (float(pt[0]), float(pt[1]), float(pt[2])),
                    }
                )

    return quads, segs, refs, escala_v, hover


def collect_my_diagram_geometry(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    escala_diagrama_momento: float,
) -> Tuple[
    List[Tuple[np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray]],
    float,
    List[Dict[str, Any]],
]:
    _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
    escala_m = _escala_momento_my_global(barras, escala_diagrama_momento)
    cp, cn, cz = _DIAG_COLOR_POS, _DIAG_COLOR_NEG, _DIAG_COLOR_ZERO
    quads: List[Tuple[np.ndarray, str]] = []
    segs: List[Tuple[np.ndarray, np.ndarray, str]] = []
    refs: List[Tuple[np.ndarray, np.ndarray]] = []
    hover: List[Dict[str, Any]] = []

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()
        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        x_local /= max(np.linalg.norm(x_local), 1e-12)
        z_local /= max(np.linalg.norm(z_local), 1e-12)

        xs, ms, L = _diagrama_momento_my_local_barra(barra)
        if xs.size == 0:
            continue
        bid = getattr(barra, "id", None)
        for k in range(xs.size - 1):
            quads.extend(
                _collect_franja_quads_momento_linear(
                    origin,
                    x_local,
                    z_local,
                    float(xs[k]),
                    float(xs[k + 1]),
                    float(ms[k]),
                    float(ms[k + 1]),
                    escala_m,
                    cp,
                    cn,
                    cz,
                    sign_draw=-1.0,
                )
            )
        px, pm = _momento_polyline_con_cruces_cero(xs, ms)
        pts = np.array(
            [origin + xv * x_local - mv * escala_m * z_local for xv, mv in zip(px, pm)],
            dtype=float,
        )
        for p0, p1, col in _iter_polilinea_segmentos(pts, pm, cp, cn, cz):
            segs.append((p0, p1, col))
        refs.append((origin, origin + L * x_local))

        for k in range(px.size):
            ptk = pts[k]
            hover.append(
                {
                    "bar_id": bid,
                    "x_local": float(px[k]),
                    "v": float(pm[k]),
                    "corte": "my",
                    "pos": (float(ptk[0]), float(ptk[1]), float(ptk[2])),
                }
            )
        for k in range(xs.size - 1):
            xa, xb = float(xs[k]), float(xs[k + 1])
            Ma, Mb = float(ms[k]), float(ms[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                Mm = Ma + t * (Mb - Ma)
                pt = origin + xm * x_local - Mm * escala_m * z_local
                hover.append(
                    {
                        "bar_id": bid,
                        "x_local": float(xm),
                        "v": float(Mm),
                        "corte": "my",
                        "pos": (float(pt[0]), float(pt[1]), float(pt[2])),
                    }
                )

    return quads, segs, refs, escala_m, hover


def collect_mx_diagram_geometry(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    escala_diagrama_mx: float = 1.0,
) -> Tuple[
    List[Tuple[np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray]],
    float,
    List[Dict[str, Any]],
]:
    escala_m = _escala_momento_mx_global(barras, escala_diagrama_mx)
    cp, cn, cz = _DIAG_COLOR_POS, _DIAG_COLOR_NEG, _DIAG_COLOR_ZERO
    quads: List[Tuple[np.ndarray, str]] = []
    segs: List[Tuple[np.ndarray, np.ndarray, str]] = []
    refs: List[Tuple[np.ndarray, np.ndarray]] = []
    hover: List[Dict[str, Any]] = []

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()
        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        x_local /= max(np.linalg.norm(x_local), 1e-12)
        z_local /= max(np.linalg.norm(z_local), 1e-12)

        x_b, m_b, L, _, _ = _diagrama_mx_torsion_local_barra(barra)
        if x_b.size == 0:
            continue
        m_dib = m_b
        bid = getattr(barra, "id", None)
        quads.extend(
            _collect_escalonado_franja_quads(
                origin, x_local, z_local, x_b, m_dib, escala_m, cp, cn, cz
            )
        )
        pts = np.array(
            [origin + float(xb) * x_local + float(vb) * escala_m * z_local for xb, vb in zip(x_b, m_dib)],
            dtype=float,
        )
        for p0, p1, col in _iter_polilinea_segmentos(pts, m_dib, cp, cn, cz):
            segs.append((p0, p1, col))
        refs.append((origin, origin + L * x_local))

        for k in range(len(x_b)):
            ptk = pts[k]
            hover.append(
                {
                    "bar_id": bid,
                    "x_local": float(x_b[k]),
                    "v": float(m_dib[k]),
                    "corte": "mx",
                    "pos": (float(ptk[0]), float(ptk[1]), float(ptk[2])),
                }
            )
        for k in range(len(x_b) - 1):
            xa, xb = float(x_b[k]), float(x_b[k + 1])
            va, vb = float(m_dib[k]), float(m_dib[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            if not np.isclose(va, vb, rtol=1e-9, atol=1e-12 * max(1.0, abs(va), abs(vb))):
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                pt = origin + xm * x_local + va * escala_m * z_local
                hover.append(
                    {
                        "bar_id": bid,
                        "x_local": float(xm),
                        "v": float(va),
                        "corte": "mx",
                        "pos": (float(pt[0]), float(pt[1]), float(pt[2])),
                    }
                )

    return quads, segs, refs, escala_m, hover


def _add_terna_global(plotter: Any, longitud: float) -> None:
    O = np.zeros(3, dtype=float)
    specs = [
        (np.array([1.0, 0.0, 0.0], dtype=float), "#c0392b"),
        (np.array([0.0, 1.0, 0.0], dtype=float), "#27ae60"),
        (np.array([0.0, 0.0, 1.0], dtype=float), "#2980b9"),
    ]
    for u, col in specs:
        plotter.add_mesh(pv.Line(O, O + float(longitud) * u), color=col, line_width=4)


def _add_ejes_locales_barras(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    escala: float,
    solo_nodos_dict: bool = False,
) -> None:
    for barra in barras:
        coord_i, _ = obtener_coordenadas_barra(barra, nodos_dict, solo_nodos_dict=solo_nodos_dict)
        if coord_i is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()
        c = np.asarray(coord_i, dtype=float)
        xl = np.asarray(getattr(barra, "x_local", [1, 0, 0]), float).ravel()[:3]
        yl = np.asarray(getattr(barra, "y_local", [0, 1, 0]), float).ravel()[:3]
        zl = np.asarray(getattr(barra, "z_local", [0, 0, 1]), float).ravel()[:3]
        xl /= max(np.linalg.norm(xl), 1e-12)
        yl /= max(np.linalg.norm(yl), 1e-12)
        zl /= max(np.linalg.norm(zl), 1e-12)
        plotter.add_mesh(pv.Line(c, c + xl * escala), color="red", line_width=2)
        plotter.add_mesh(pv.Line(c, c + yl * escala), color="green", line_width=2)
        plotter.add_mesh(pv.Line(c, c + zl * escala), color="blue", line_width=2)


def _nodal_moment_rh_basis(axis_idx: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eje del par e_i y base (v,w) en el plano del arco con v×w = e_i (mano derecha)."""
    ex = np.array([1.0, 0.0, 0.0], dtype=float)
    ey = np.array([0.0, 1.0, 0.0], dtype=float)
    ez = np.array([0.0, 0.0, 1.0], dtype=float)
    if axis_idx == 0:
        return ex, ey, ez
    if axis_idx == 1:
        return ey, ez, ex
    return ez, ex, ey


def _nodal_moment_arc_points(
    P: np.ndarray,
    axis_idx: int,
    M_component: float,
    R_M: float,
    delta_deg: float = 220.0,
    n_pts: int = 42,
) -> np.ndarray:
    """Polilínea 3D del arco de momento (sentido según signo de M, RHR sobre eje axis_idx)."""
    _, v, w = _nodal_moment_rh_basis(axis_idx)
    sign = 1.0 if float(M_component) >= 0.0 else -1.0
    dtheta = np.radians(float(delta_deg) * sign)
    thetas = np.linspace(0.0, dtheta, int(max(8, n_pts)), dtype=float)
    ring = np.outer(np.cos(thetas), v) + np.outer(np.sin(thetas), w)
    return np.asarray(P, dtype=float).reshape(1, 3) + float(R_M) * ring


def _add_fuerzas_globales(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    cargas_nodales: Optional[List[Any]],
    longitud_vector: float,
    tol: float,
    h_perfil: float,
    tube_r: float,
) -> None:
    for barra in barras:
        for carga in getattr(barra, "cargas", []) or []:
            if getattr(carga, "is_distributed", False):
                F_int = np.asarray(
                    getattr(carga, "force_global_intensity", np.zeros(3)), dtype=float
                ).ravel()[:3]
                F_mag = float(np.linalg.norm(F_int))
                if F_mag <= tol:
                    continue
                F_dir = F_int / F_mag
                p_start = np.array(
                    [float(getattr(carga, "x", 0.0)),
                     float(getattr(carga, "y", 0.0)),
                     float(getattr(carga, "z", 0.0))], dtype=float
                )
                p_end = np.array(
                    [float(getattr(carga, "x_f", p_start[0])),
                     float(getattr(carga, "y_f", p_start[1])),
                     float(getattr(carga, "z_f", p_start[2]))], dtype=float
                )
                span = float(np.linalg.norm(p_end - p_start))
                chord = p_end - p_start
                n_strip = int(
                    max(12, min(40, int(span / max(longitud_vector * 0.28, 1e-9)) + 10))
                )
                ts = np.linspace(0.0, 1.0, n_strip + 1, dtype=float)
                B = np.array(
                    [_punto_carga_banda_superior_ipn(barra, p_start + t * chord, h_perfil) for t in ts],
                    dtype=float,
                )
                H_udl = float(
                    min(
                        max(longitud_vector * 0.88, span * 0.12),
                        span * 1.08,
                        longitud_vector * 2.6,
                    )
                )
                T = B - H_udl * F_dir.reshape(1, 3)
                n_pts = B.shape[0]
                verts = np.vstack([B, T])
                faces_l: List[int] = []
                for i in range(n_strip):
                    b0, b1 = i, i + 1
                    t0, t1 = n_pts + i, n_pts + i + 1
                    faces_l.extend([4, b0, b1, t1, t0])
                faces_arr = np.array(faces_l, dtype=np.int64)
                surf = pv.PolyData(verts, faces_arr)
                if surf.n_points > 0:
                    plotter.add_mesh(
                        surf,
                        color=_COLOR_CARGA_DISTRIB_BAR,
                        opacity=0.38,
                        smooth_shading=True,
                        pickable=False,
                    )
                _lw = 2.6
                for poly, lw in (
                    (pv.lines_from_points(B), _lw),
                    (pv.lines_from_points(T), _lw),
                    (pv.Line(B[0], T[0]), _lw),
                    (pv.Line(B[-1], T[-1]), _lw),
                ):
                    if poly.n_points > 0:
                        plotter.add_mesh(
                            poly,
                            color=_COLOR_CARGA_DISTRIB_BAR,
                            line_width=lw,
                            pickable=False,
                        )
                step = max(1, n_strip // 7)
                cone_h = float(max(tube_r * 5.0, H_udl * 0.14, 0.38))
                cone_r = float(max(tube_r * 2.2, cone_h * 0.22))
                for i in range(0, n_pts, step):
                    ln = pv.Line(T[i], B[i])
                    if ln.n_points > 0:
                        plotter.add_mesh(
                            ln.tube(radius=tube_r * 0.55),
                            color=_COLOR_CARGA_DISTRIB_BAR,
                            smooth_shading=True,
                            pickable=False,
                        )
                    tip = np.asarray(B[i], dtype=float).ravel()[:3]
                    c_ctr = tip - F_dir * (0.5 * cone_h)
                    cone = pv.Cone(
                        center=c_ctr.tolist(),
                        direction=F_dir.tolist(),
                        height=cone_h,
                        radius=cone_r,
                    )
                    if cone.n_points > 0:
                        plotter.add_mesh(
                            cone,
                            color=_COLOR_CARGA_DISTRIB_BAR,
                            smooth_shading=True,
                            pickable=False,
                        )
            else:
                F = _vector_global_carga_puntual(carga)
                P_raw = np.array(
                    [float(getattr(carga, "x", 0.0)), float(getattr(carga, "y", 0.0)), float(getattr(carga, "z", 0.0))],
                    dtype=float,
                )
                P = _punto_carga_banda_superior_ipn(barra, P_raw, h_perfil)
                for i in range(3):
                    if abs(F[i]) <= tol:
                        continue
                    u = np.zeros(3, dtype=float)
                    u[i] = float(np.sign(F[i]))
                    tail = P - longitud_vector * u
                    ln = pv.Line(tail, P)
                    if ln.n_points > 0:
                        plotter.add_mesh(
                            ln.tube(radius=tube_r), color=_COLOR_CARGA_PUNTUAL_BAR, smooth_shading=True
                        )

    color_fuerza_nodal = "#c83232"
    color_momento_nodal = "#7a3fbf"

    if cargas_nodales:
        for cn in cargas_nodales:
            nid = getattr(cn, "nodo_id", None)
            if nid is None:
                continue
            nodo = nodos_dict.get(nid)
            if nodo is None:
                continue
            P = np.array([float(nodo.x), float(nodo.y), float(nodo.z)], dtype=float)
            F = np.array(
                [
                    float(getattr(cn, "fx", 0.0) or 0.0),
                    float(getattr(cn, "fy", 0.0) or 0.0),
                    float(getattr(cn, "fz", 0.0) or 0.0),
                ],
                dtype=float,
            )
            fn = float(np.linalg.norm(F))
            if fn > tol:
                u_F = F / fn
                L_F = float(longitud_vector * 1.08)
                tail = P - L_F * u_F
                r_anchor = float(max(tube_r * 2.9, longitud_vector * 0.065, 0.42))
                sph = pv.Sphere(
                    radius=r_anchor,
                    center=(float(P[0]), float(P[1]), float(P[2])),
                    theta_resolution=14,
                    phi_resolution=14,
                )
                plotter.add_mesh(
                    sph,
                    color=color_fuerza_nodal,
                    opacity=0.42,
                    smooth_shading=True,
                    pickable=False,
                )
                ln_f = pv.Line(tail, P)
                if ln_f.n_points > 0:
                    plotter.add_mesh(
                        ln_f.tube(radius=tube_r * 1.22),
                        color=color_fuerza_nodal,
                        smooth_shading=True,
                        pickable=False,
                    )
                cone_hf = float(max(tube_r * 5.2, L_F * 0.12, 0.38))
                cone_rf = float(max(tube_r * 2.35, cone_hf * 0.22))
                c_cf = P - u_F * (0.5 * cone_hf)
                mesh_f_cone = pv.Cone(
                    center=c_cf.tolist(),
                    direction=u_F.tolist(),
                    height=cone_hf,
                    radius=cone_rf,
                )
                if mesh_f_cone.n_points > 0:
                    plotter.add_mesh(mesh_f_cone, color=color_fuerza_nodal, smooth_shading=True, pickable=False)

            Mv = np.array(
                [
                    float(getattr(cn, "mx", 0.0) or 0.0),
                    float(getattr(cn, "my", 0.0) or 0.0),
                    float(getattr(cn, "mz", 0.0) or 0.0),
                ],
                dtype=float,
            )
            Mabs = np.abs(Mv)
            Mmax = float(np.max(Mabs)) if np.any(Mabs > tol) else 1.0
            R_base = float(longitud_vector * 0.52)
            cone_h_m = float(max(tube_r * 4.6, 0.34))
            cone_r_m = float(max(tube_r * 2.15, cone_h_m * 0.21))
            for i in range(3):
                if abs(Mv[i]) <= tol:
                    continue
                R_M = R_base * (0.62 + 0.38 * abs(Mv[i]) / max(Mmax, 1e-18))
                pts = _nodal_moment_arc_points(P, i, float(Mv[i]), R_M)
                if pts.shape[0] < 3:
                    continue
                arc_ln = pv.lines_from_points(pts)
                if arc_ln.n_points > 0:
                    plotter.add_mesh(
                        arc_ln.tube(radius=tube_r * 0.78),
                        color=color_momento_nodal,
                        smooth_shading=True,
                        pickable=False,
                    )
                ts = (pts[1] - pts[0]) / max(float(np.linalg.norm(pts[1] - pts[0])), 1e-12)
                te = (pts[-1] - pts[-2]) / max(float(np.linalg.norm(pts[-1] - pts[-2])), 1e-12)
                u_out_s = -ts
                c_s = pts[0] - u_out_s * (0.5 * cone_h_m)
                co_s = pv.Cone(
                    center=c_s.tolist(),
                    direction=u_out_s.tolist(),
                    height=cone_h_m,
                    radius=cone_r_m,
                )
                if co_s.n_points > 0:
                    plotter.add_mesh(co_s, color=color_momento_nodal, smooth_shading=True, pickable=False)
                c_e = pts[-1] - te * (0.5 * cone_h_m)
                co_e = pv.Cone(
                    center=c_e.tolist(),
                    direction=te.tolist(),
                    height=cone_h_m,
                    radius=cone_r_m,
                )
                if co_e.n_points > 0:
                    plotter.add_mesh(co_e, color=color_momento_nodal, smooth_shading=True, pickable=False)


def _tube_radius_from_ipn(ipn: pv.PolyData) -> Tuple[float, float]:
    if ipn.n_points == 0:
        return 0.35, 1.0
    bd = ipn.bounds
    diag = float(np.linalg.norm([bd[1] - bd[0], bd[3] - bd[2], bd[5] - bd[4]]))
    r = max(diag * 0.0025, 0.25)
    seg_tol = max(1e-9, 1e-12 * diag)
    return r, seg_tol


def _diagram_segment_tolerance(
    ipn: pv.PolyData,
    segs: List[Tuple[np.ndarray, np.ndarray, str]],
    refs: List[Tuple[np.ndarray, np.ndarray]],
) -> float:
    """Evita filtrar tramos cortos legítimos del diagrama (p. ej. curvas densas)."""
    lens: List[float] = []
    for p0, p1, _ in segs:
        lens.append(_segment_length(p0, p1))
    for a, b in refs:
        lens.append(_segment_length(a, b))
    lens = [x for x in lens if x > 0]
    med = float(np.median(lens)) if lens else 1.0
    _, bbox_tol = _tube_radius_from_ipn(ipn)
    return max(1e-15 * max(med, 1.0), min(bbox_tol, 1e-12 * max(med, 1.0)))


def _plotter_set_background_from_style(
    plotter: Any, viewport_style: Optional[Mapping[str, Any]]
) -> None:
    if viewport_style is None:
        return
    bg = str(viewport_style.get("background_color") or "#ffffff")
    top = viewport_style.get("background_top")
    if top:
        try:
            plotter.set_background(bg, top=str(top))
        except TypeError:
            plotter.set_background(bg)
    else:
        plotter.set_background(bg)


def _ipn_mesh_face_edge_colors(
    viewport_style: Optional[Mapping[str, Any]],
) -> Tuple[str, str]:
    if viewport_style is None:
        return "#7fb3d5", "#1b4f72"
    return (
        str(viewport_style.get("mesh_color") or "#7fb3d5"),
        str(viewport_style.get("mesh_edge_color") or "#1b4f72"),
    )


def _ipn_mesh_edge_line_width(viewport_style: Optional[Mapping[str, Any]]) -> float:
    """Grosor de aristas del perfil IPN (tema oscuro suele pedir > 1)."""
    if viewport_style is None:
        return 1.0
    w = viewport_style.get("mesh_edge_line_width")
    if w is None:
        return 1.0
    try:
        return float(max(0.5, min(4.0, float(w))))
    except (TypeError, ValueError):
        return 1.0


def _add_diagram_layers(
    plotter: Any,
    ipn: pv.PolyData,
    quads: List[Tuple[np.ndarray, str]],
    segs: List[Tuple[np.ndarray, np.ndarray, str]],
    refs: List[Tuple[np.ndarray, np.ndarray]],
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> None:
    _require_pyvista()
    if viewport_style is not None:
        _plotter_set_background_from_style(plotter, viewport_style)
    else:
        plotter.set_background("white")
    mc, mec = _ipn_mesh_face_edge_colors(viewport_style)
    lw_ipn = _ipn_mesh_edge_line_width(viewport_style)
    if ipn.n_points > 0:
        plotter.add_mesh(
            ipn,
            color=mc,
            opacity=0.9,
            show_edges=True,
            edge_color=mec,
            line_width=lw_ipn,
        )
    for quad, col in quads:
        qm = _quad_to_polydata(quad)
        if qm.n_points > 0:
            plotter.add_mesh(qm, color=col, opacity=0.42, show_edges=True, edge_color=col, line_width=0.5)
    r_tube, _ = _tube_radius_from_ipn(ipn)
    seg_tol = _diagram_segment_tolerance(ipn, segs, refs)
    for p0, p1, col in segs:
        if _segment_length(p0, p1) < seg_tol:
            continue
        p0a = np.asarray(p0, dtype=float).ravel()[:3]
        p1a = np.asarray(p1, dtype=float).ravel()[:3]
        line = pv.Line(p0a, p1a)
        tubed = line.tube(radius=r_tube)
        if tubed.n_points > 0:
            plotter.add_mesh(tubed, color=col, smooth_shading=True)
        else:
            plotter.add_mesh(line, color=col, line_width=3)
    for a, b in refs:
        if _segment_length(a, b) < seg_tol:
            continue
        aa = np.asarray(a, dtype=float).ravel()[:3]
        bb = np.asarray(b, dtype=float).ravel()[:3]
        rl = pv.Line(aa, bb)
        if rl.n_points > 0:
            plotter.add_mesh(rl, color="#7f8c8d", line_width=2)


def _populate_estructura(
    plotter: Any,
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    longitud_terna: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> None:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    _require_pyvista()
    if viewport_style is not None:
        _plotter_set_background_from_style(plotter, viewport_style)
    else:
        plotter.set_background("white")
    mc, mec = _ipn_mesh_face_edge_colors(viewport_style)
    lw_ipn = _ipn_mesh_edge_line_width(viewport_style)
    if ipn.n_points > 0:
        plotter.add_mesh(
            ipn,
            color=mc,
            opacity=0.9,
            show_edges=True,
            edge_color=mec,
            line_width=lw_ipn,
            label="Estructura",
        )
    _add_terna_global(plotter, longitud_terna)
    if mostrar_ejes_locales:
        h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)


def _populate_fuerzas(
    plotter: Any,
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    cargas_nodales: Optional[List[Any]],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    longitud_vector: float,
    tol_componente: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> None:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
    _require_pyvista()
    if viewport_style is not None:
        _plotter_set_background_from_style(plotter, viewport_style)
    else:
        plotter.set_background("white")
    mc, mec = _ipn_mesh_face_edge_colors(viewport_style)
    lw_ipn = _ipn_mesh_edge_line_width(viewport_style)
    if ipn.n_points > 0:
        plotter.add_mesh(
            ipn,
            color=mc,
            opacity=0.9,
            show_edges=True,
            edge_color=mec,
            line_width=lw_ipn,
        )
    _add_terna_global(plotter, longitud_vector)
    r_force, _ = _tube_radius_from_ipn(ipn)
    r_force *= 0.45
    _add_fuerzas_globales(
        plotter, barras, nodos_dict, cargas_nodales, longitud_vector, tol_componente, h, r_force
    )
    if mostrar_ejes_locales:
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)


def _escala_intrinseca_deformacion(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    D: np.ndarray,
) -> float:
    """Factor para que el desplazamiento sea del orden del 18 % de la luz media de barra (como diagramas)."""
    Dv = np.asarray(D, dtype=float).ravel()
    max_u = 0.0
    for n in nodos_dict.values():
        uid = int(getattr(n, "id", 0))
        base = (uid - 1) * 6
        if base + 2 < len(Dv):
            u = Dv[base : base + 3]
            max_u = max(max_u, float(np.linalg.norm(u)))
    Ls: List[float] = []
    for b in barras:
        ci, cf = obtener_coordenadas_barra(b, nodos_dict)
        if ci is not None and cf is not None:
            Ls.append(float(np.linalg.norm(np.asarray(cf, dtype=float) - np.asarray(ci, dtype=float))))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    if max_u <= 1e-18:
        return 1.0
    return 0.18 * L_ref / max_u


def _nodos_dict_proxy_deformado(
    nodos_dict: Dict[Any, Any],
    D: np.ndarray,
    disp_scale: float,
) -> Dict[Any, Any]:
    Dv = np.asarray(D, dtype=float).ravel()
    out: Dict[Any, Any] = {}
    for nid, n in nodos_dict.items():
        uid = int(getattr(n, "id", nid))
        base = (uid - 1) * 6
        ux = uy = uz = 0.0
        if base + 2 < len(Dv):
            ux, uy, uz = float(Dv[base]), float(Dv[base + 1]), float(Dv[base + 2])
        out[nid] = types.SimpleNamespace(
            id=uid,
            x=float(n.x) + disp_scale * ux,
            y=float(n.y) + disp_scale * uy,
            z=float(n.z) + disp_scale * uz,
        )
    return out


def _populate_deformada(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    longitud_terna: float,
    D: np.ndarray,
    escala_diagrama_slider: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> None:
    g = _escala_intrinseca_deformacion(barras, nodos_dict, D)
    disp = float(escala_diagrama_slider) * g
    nd_def = _nodos_dict_proxy_deformado(nodos_dict, D, disp)
    _require_pyvista()
    if viewport_style is not None:
        _plotter_set_background_from_style(plotter, viewport_style)
    else:
        plotter.set_background("white")
    for b in barras:
        c0, c1 = obtener_coordenadas_barra(b, nodos_dict)
        if c0 is None or c1 is None:
            continue
        a0 = np.asarray(c0, dtype=float).ravel()[:3]
        a1 = np.asarray(c1, dtype=float).ravel()[:3]
        ln = pv.Line(a0, a1)
        if ln.n_points > 0:
            plotter.add_mesh(ln, color="#bdc3c7", line_width=2)
    ipn = build_ipn_mesh_deformada_curva(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        D,
        disp,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    if ipn.n_points > 0:
        if viewport_style is not None:
            d_mc, d_ec = _ipn_mesh_face_edge_colors(viewport_style)
            lw_ipn = _ipn_mesh_edge_line_width(viewport_style)
        else:
            d_mc, d_ec = "#2980b9", "#1a5276"
            lw_ipn = 1.0
        plotter.add_mesh(
            ipn,
            color=d_mc,
            opacity=0.92,
            show_edges=True,
            edge_color=d_ec,
            line_width=lw_ipn,
        )
    _add_terna_global(plotter, longitud_terna)
    if mostrar_ejes_locales:
        h, b_dim, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(
            plotter, barras, nd_def, max(h, b_dim) * 0.8, solo_nodos_dict=True
        )


def _populate_corte(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    corte: str,
    escala_diagrama: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    quads, segs, refs, _, hover = collect_corte_diagram_geometry(barras, nodos_dict, corte, escala_diagrama)
    _add_diagram_layers(plotter, ipn, quads, segs, refs, viewport_style=viewport_style)
    if mostrar_ejes_locales:
        h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)
    return hover


def _populate_my(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    escala_diagrama: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    quads, segs, refs, _, hover = collect_my_diagram_geometry(
        barras, nodos_dict, ipn_dims, escala_seccion, escala_diagrama
    )
    _add_diagram_layers(plotter, ipn, quads, segs, refs, viewport_style=viewport_style)
    if mostrar_ejes_locales:
        h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)
    return hover


def _populate_mz(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    escala_diagrama: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    quads, segs, refs, _, hover = collect_mz_diagram_geometry(
        barras,
        nodos_dict,
        ipn_dims=ipn_dims,
        escala_seccion=escala_seccion,
        escala_diagrama_momento=escala_diagrama,
    )
    _add_diagram_layers(plotter, ipn, quads, segs, refs, viewport_style=viewport_style)
    if mostrar_ejes_locales:
        h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)
    return hover


def _populate_mx(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    mostrar_ejes_locales: bool,
    escala_diagrama: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
    viewport_style: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    quads, segs, refs, _, hover = collect_mx_diagram_geometry(barras, nodos_dict, escala_diagrama)
    _add_diagram_layers(plotter, ipn, quads, segs, refs, viewport_style=viewport_style)
    if mostrar_ejes_locales:
        h, b, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)
        _add_ejes_locales_barras(plotter, barras, nodos_dict, max(h, b) * 0.8)
    return hover


def _hover_etiqueta(corte_key: str) -> str:
    return {
        "vy": "V_y",
        "vz": "V_z",
        "nx": "N_x",
        "my": "M_y",
        "mz": "M_z",
        "mx": "M_x",
    }.get(corte_key, corte_key)


def _hover_suffix(corte_key: str) -> str:
    if corte_key == "nx":
        return " (conv. visual: compresión → −, tracción → +)"
    if corte_key == "my":
        return " (local; +M_y → −z_local)"
    if corte_key == "mz":
        return " (local; +M_z → +y_local)"
    if corte_key == "mx":
        return " (local; +M_x → +z_local)"
    return " (local)"


def _diagram_key_str(diagram_key: Union[str, Callable[[], str]]) -> str:
    if callable(diagram_key):
        try:
            return str(diagram_key())
        except Exception:
            return "vy"
    return str(diagram_key)


def _closest_hover_row(
    ren: Any,
    hp: List[Dict[str, Any]],
    x: float,
    y: float,
    tol_px: float,
) -> int:
    """Índice del punto de diagrama más cercano en pantalla, o -1."""
    tol_px2 = tol_px * tol_px
    best_i = -1
    best_d2 = tol_px2 * 4.0
    for i, p in enumerate(hp):
        pos = p.get("pos")
        if pos is None or len(pos) < 3:
            continue
        try:
            ren.SetWorldPoint(float(pos[0]), float(pos[1]), float(pos[2]), 1.0)
            ren.WorldToDisplay()
            dp = ren.GetDisplayPoint()
            dx = float(dp[0]) - x
            dy = float(dp[1]) - y
            d2 = dx * dx + dy * dy
        except Exception:
            continue
        if d2 < best_d2:
            best_d2 = d2
            best_i = i
    return best_i if best_i >= 0 and best_d2 <= tol_px2 else -1


def ftool_selection_highlight_radius(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]],
    escala_seccion: float,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
) -> float:
    """Radio del tubo de resaltado coherente con la escena."""
    _require_pyvista()
    ipn = build_ipn_mesh(
        barras,
        nodos_dict,
        ipn_dims,
        escala_seccion,
        ipn_dims_per_bar_id=ipn_dims_per_bar_id,
        tube_outer_radius_per_bar_id=tube_outer_radius_per_bar_id,
        profile_polygon_yz_per_bar_id=profile_polygon_yz_per_bar_id,
    )
    r, _ = _tube_radius_from_ipn(ipn)
    return max(float(r) * 6.0, 0.45)


def add_ftool_bar_selection_highlight(
    plotter: Any,
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    selected_bar_id: Optional[int],
    tube_radius: float,
) -> None:
    if selected_bar_id is None:
        return
    _require_pyvista()
    for barra in barras:
        bid = getattr(barra, "id", None)
        if bid is None or int(bid) != int(selected_bar_id):
            continue
        ci, cf = obtener_coordenadas_barra(barra, nodos_dict)
        if ci is None or cf is None:
            return
        Gi = np.asarray(ci, dtype=float).ravel()[:3]
        Gf = np.asarray(cf, dtype=float).ravel()[:3]
        line = pv.Line(Gi, Gf)
        tubed = line.tube(radius=float(tube_radius))
        if tubed.n_points > 0:
            plotter.add_mesh(
                tubed,
                color="#e67e22",
                opacity=0.95,
                smooth_shading=True,
                name="ftool_bar_highlight",
                pickable=False,
            )
        return


def build_ftool_legend_lines(view_key: str, escala: float) -> List[str]:
    """Textos leyenda esquina (unidades, convención, atajos)."""
    ctrl = "Selección barra en tabla · Esc quita el resaltado"
    if view_key == "geom":
        return ["Geometría · coordenadas en cm", ctrl]
    if view_key == "loads":
        return [
            "Cargas · vectores en sistema global",
            "Barra: negro = puntual (X,Y,Z)",
            "Barra: naranja = UDL (área sombreada + flechas iguales sobre el tramo)",
            "Nodo: rojo = fuerza resultante + esfera en el nodo",
            "Nodo: violeta = momento (arco en el plano del par)",
            ctrl,
        ]
    if view_key == "def":
        return [
            "Deformada · desplazamientos en cm",
            f"Amplificación visual (slider) = {escala:.2f}",
            ctrl,
        ]
    if view_key in ("vy", "vz", "nx", "my", "mz", "mx"):
        lab = _hover_etiqueta(view_key)
        suf = _hover_suffix(view_key).strip()
        return [
            f"Diagrama {lab} · escala relativa = {escala:.2f}",
            "Unidades: Tn (corte y axial); Tn·cm (momentos y torsión); longitudes en cm.",
            suf,
            "Colores: rojo / azul según signo (referencia local de cada barra).",
            ctrl,
        ]
    return []


def add_ftool_viewport_legend(plotter: Any, view_key: str, escala: float) -> None:
    lines = build_ftool_legend_lines(view_key, escala)
    if not lines:
        return
    text = "\n".join(lines)
    try:
        plotter.add_text(
            text,
            position="lower_left",
            viewport=True,
            font_size=9,
            color="#1a1a1a",
            shadow=True,
        )
    except Exception:
        pass


def _install_diagram_hover(
    plotter: Any,
    get_hover_fn: Callable[[], List[Dict[str, Any]]],
    diagram_key: Union[str, Callable[[], str]],
) -> None:
    """Tooltip al mover el mouse (proyección pantalla; evita vtkCellPicker / wglMakeCurrent en Win32)."""
    if getattr(plotter, "_hyperstatic_hover_installed", False):
        return
    plotter._hyperstatic_hover_installed = True
    try:
        from vtkmodules.vtkCommonCore import vtkCommand
    except ImportError:  # pragma: no cover
        import vtk as _vtk

        vtkCommand = _vtk.vtkCommand

    try:
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QToolTip
    except ImportError:
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QToolTip

    last_t = [0.0]
    tol_px = 30.0

    def on_move(_obj: Any, _event: str) -> None:
        t = time.monotonic()
        if t - last_t[0] < 0.045:
            return
        last_t[0] = t
        try:
            ir = plotter.iren
            if hasattr(ir, "get_event_position"):
                xy = ir.get_event_position()
            else:
                xy = ir.GetEventPosition()
        except Exception:
            return
        x, y = float(xy[0]), float(xy[1])
        hp = get_hover_fn() or []
        if not hp:
            QToolTip.hideText()
            return
        try:
            ren = plotter.renderer
            i = _closest_hover_row(ren, hp, x, y, tol_px)
        except Exception:
            QToolTip.hideText()
            return
        if i < 0:
            QToolTip.hideText()
            return
        best = hp[i]
        ck = str(best.get("corte", _diagram_key_str(diagram_key)))
        lab = _hover_etiqueta(ck)
        suf = _hover_suffix(ck)
        v = float(best["v"])
        xl = float(best["x_local"])
        bid = best["bar_id"]
        txt = f"Barra {bid} | x_local = {xl:.2f} cm | {lab} = {v:.6g}{suf}"
        QToolTip.showText(QCursor.pos(), txt)

    # PyVista envuelve el interactor VTK: ``add_observer(event, call, ...)``, no ``AddObserver``.
    iren = plotter.iren
    if hasattr(iren, "add_observer"):
        iren.add_observer(vtkCommand.MouseMoveEvent, on_move)
    else:
        iren.AddObserver(vtkCommand.MouseMoveEvent, on_move, 1.0)


def _try_import_qt():
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout

        from pyvistaqt import QtInteractor

        return "PySide6", QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QtInteractor
    except ImportError:
        pass
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout

        from pyvistaqt import QtInteractor

        return "PyQt5", QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QtInteractor
    except ImportError:
        return None


def _qt_widget_xy_to_vtk_display(plotter: Any, x_qt: int, y_qt: int) -> Optional[Tuple[int, int]]:
    """
    Convierte (x, y) del widget Qt al sistema de píxeles de display de VTK.

    Debe coincidir con ``QVTKRenderWindowInteractor._setEventInformation`` en
    ``pyvistaqt`` (origen Y abajo en Qt, arriba en VTK, y ``devicePixelRatio``).
    Si no, ``FindPokedRenderer`` / ``DisplayToWorld`` fallan y el zoom “hacia el
    cursor” desplaza mal la cámara (y se siente rota la navegación).
    """
    try:
        iw = plotter.interactor
    except Exception:
        return None
    try:
        scale = float(iw._getPixelRatio())  # type: ignore[attr-defined]
    except Exception:
        try:
            scale = float(iw.devicePixelRatioF())
        except Exception:
            try:
                scale = float(iw.devicePixelRatio())
            except Exception:
                scale = 1.0
    try:
        h = int(iw.height())
    except Exception:
        return None
    if h <= 0:
        return None
    x_vtk = int(round(float(x_qt) * scale))
    y_vtk = int(round(float(h - int(y_qt) - 1) * scale))
    return x_vtk, y_vtk


def install_zoom_toward_cursor(
    plotter: Any,
    zoom_in_factor: float = 0.88,
    zoom_out_factor: float = 1.14,
) -> None:
    """
    Guarda factores de zoom hacia cursor. El manejo real de la rueda se hace en Qt
    (``FtoolMainWindow.eventFilter``) llamando a ``ftool_zoom_wheel_toward_pixel``,
    para no duplicar el dolly VTK y no depender de vtkCallbackCommand en Python.
    """
    plotter._ftool_wheel_zoom_in = float(zoom_in_factor)
    plotter._ftool_wheel_zoom_out = float(zoom_out_factor)


def ftool_zoom_wheel_toward_pixel(plotter: Any, x: int, y: int, zoom_in: bool) -> bool:
    """
    Zoom en perspectiva anclado al píxel (x,y): intersección del rayo de vista con el plano
    por el focal perpendicular al eje de vista. Devuelve True si aplicó zoom (y la GUI
    puede consumir el evento Wheel).
    """
    _require_pyvista()
    try:
        iren = plotter.iren.interactor
    except Exception:
        return False
    xy_vtk = _qt_widget_xy_to_vtk_display(plotter, int(x), int(y))
    if xy_vtk is None:
        return False
    xd_i, yd_i = xy_vtk
    iren.SetEventPosition(xd_i, yd_i)
    rw = iren.GetRenderWindow()
    if rw is None:
        return False
    renderer = iren.FindPokedRenderer(xd_i, yd_i)
    if renderer is None:
        return False
    camera = renderer.GetActiveCamera()
    if camera.GetParallelProjection():
        return False

    C = np.array(camera.GetPosition(), dtype=float).ravel()[:3]
    F = np.array(camera.GetFocalPoint(), dtype=float).ravel()[:3]
    v = F - C
    vn = float(np.linalg.norm(v))
    if vn < 1e-12:
        return False
    v = v / vn

    def _hom(renderer: Any, xd: float, yd: float, zd: float) -> np.ndarray:
        renderer.SetDisplayPoint(float(xd), float(yd), float(zd))
        renderer.DisplayToWorld()
        wp = np.array(renderer.GetWorldPoint(), dtype=float).ravel()
        if wp.size < 4:
            return np.zeros(3, dtype=float)
        w = float(wp[3])
        if abs(w) < 1e-12:
            return wp[:3].astype(float)
        return (wp[:3] / w).astype(float)

    xf, yf = float(xd_i), float(yd_i)
    w0 = _hom(renderer, xf, yf, 0.0)
    w1 = _hom(renderer, xf, yf, 1.0)
    D = w1 - w0
    dn = float(np.linalg.norm(D))
    if dn < 1e-12:
        return False
    D = D / dn

    denom = float(np.dot(D, v))
    if abs(denom) < 1e-9:
        A = F.copy()
    else:
        t = float(np.dot(F - w0, v) / denom)
        A = w0 + t * D

    zi = float(getattr(plotter, "_ftool_wheel_zoom_in", 0.88))
    zo = float(getattr(plotter, "_ftool_wheel_zoom_out", 1.14))
    fac = zi if zoom_in else zo
    Cn = A + fac * (C - A)
    Fn = A + fac * (F - A)
    camera.SetPosition(float(Cn[0]), float(Cn[1]), float(Cn[2]))
    camera.SetFocalPoint(float(Fn[0]), float(Fn[1]), float(Fn[2]))
    try:
        renderer.ResetCameraClippingRange()
    except Exception:
        pass
    try:
        rw.Render()
    except Exception:
        pass
    return True


def _finish_plotter(plotter: Any) -> None:
    plotter.add_axes()
    try:
        plotter.show_grid(font_size=8, color="#888888")
    except Exception:
        try:
            plotter.show_bounds(grid=True, location="outer", all_edges=True)
        except Exception:
            pass
    plotter.reset_camera()


def mostrar_dibujos_pyvista_pestanas(
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    cargas_nodales: Optional[List[Any]] = None,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = True,
    longitud_vector: float = 45.0,
    escala_diagrama_corte: float = 1.0,
    titulo_app: str = "Dibujos — PyVista (todas las vistas)",
    desplazamientos: Optional[np.ndarray] = None,
    escala_deform_inicial: float = 1.0,
) -> None:
    _require_pyvista()
    qt = _try_import_qt()
    if qt is None:
        raise ImportError(
            "Para pestañas PyVista instalá: pip install pyvistaqt PySide6   (o pyvistaqt PyQt5)"
        )
    _backend, QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QtInteractor = qt

    if _backend == "PySide6":
        from PySide6.QtCore import Qt as _Qt, QTimer
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider

        _slider_ori = _Qt.Orientation.Horizontal
    else:
        from PyQt5.QtCore import Qt as _Qt, QTimer
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider

        _slider_ori = _Qt.Horizontal

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    win = QMainWindow()
    win.setWindowTitle(titulo_app)
    win.resize(1040, 820)
    tabs = QTabWidget()
    win.setCentralWidget(tabs)

    def _mk_tab_plain(tab_title: str, subtitle: str, setup: Callable[[Any], None]) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        hdr = QLabel(subtitle)
        hdr.setWordWrap(True)
        lay.addWidget(hdr)
        plotter = QtInteractor(w)
        lay.addWidget(plotter.interactor, stretch=1)
        setup(plotter)
        _finish_plotter(plotter)
        tabs.addTab(w, tab_title)

    def _mk_tab_diagram(
        tab_title: str,
        subtitle: str,
        escala_inicial: float,
        diagram_key: str,
        populate: Callable[[Any, float], List[Dict[str, Any]]],
    ) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        hdr = QLabel(subtitle)
        hdr.setWordWrap(True)
        lay.addWidget(hdr)
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Escala diagrama (0.2 - 10.0):"))
        slider = QSlider(_slider_ori)
        slider.setMinimum(20)
        slider.setMaximum(1000)
        ev = int(round(min(10.0, max(0.2, float(escala_inicial))) * 100.0))
        slider.setValue(ev)
        val_lbl = QLabel(f"{ev / 100.0:.2f}")
        val_lbl.setMinimumWidth(48)
        ctrl.addWidget(slider, stretch=1)
        ctrl.addWidget(val_lbl)
        lay.addLayout(ctrl)
        plotter = QtInteractor(w)
        lay.addWidget(plotter.interactor, stretch=1)

        state: Dict[str, Any] = {"hover": []}
        debounce = QTimer(w)
        debounce.setSingleShot(True)
        debounce.setInterval(45)

        def escala_actual() -> float:
            return slider.value() / 100.0

        def on_value(_: int = 0) -> None:
            val_lbl.setText(f"{escala_actual():.2f}")

        def redraw() -> None:
            plotter.clear()
            state["hover"] = populate(plotter, escala_actual()) or []
            _finish_plotter(plotter)

        def schedule_redraw() -> None:
            debounce.stop()
            debounce.start()

        def on_slider_value(_: int) -> None:
            on_value()
            schedule_redraw()

        debounce.timeout.connect(redraw)
        slider.valueChanged.connect(on_slider_value)
        on_value()
        redraw()
        _install_diagram_hover(plotter, lambda: state["hover"], diagram_key)
        tabs.addTab(w, tab_title)

    def _mk_tab_deformada(
        tab_title: str,
        subtitle: str,
        escala_inicial: float,
        D_vec: np.ndarray,
    ) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        hdr = QLabel(subtitle)
        hdr.setWordWrap(True)
        lay.addWidget(hdr)
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Amplificación deformación (0.2 - 10.0):"))
        slider = QSlider(_slider_ori)
        slider.setMinimum(20)
        slider.setMaximum(1000)
        ev = int(round(min(10.0, max(0.2, float(escala_inicial))) * 100.0))
        slider.setValue(ev)
        val_lbl = QLabel(f"{ev / 100.0:.2f}")
        val_lbl.setMinimumWidth(48)
        ctrl.addWidget(slider, stretch=1)
        ctrl.addWidget(val_lbl)
        lay.addLayout(ctrl)
        plotter = QtInteractor(w)
        lay.addWidget(plotter.interactor, stretch=1)

        debounce = QTimer(w)
        debounce.setSingleShot(True)
        debounce.setInterval(45)

        def escala_actual() -> float:
            return slider.value() / 100.0

        def on_value(_: int = 0) -> None:
            val_lbl.setText(f"{escala_actual():.2f}")

        def redraw() -> None:
            plotter.clear()
            _populate_deformada(
                plotter,
                barras,
                nodos_dict,
                ipn_dims,
                escala_seccion,
                mostrar_ejes_locales,
                longitud_vector,
                D_vec,
                escala_actual(),
            )
            _finish_plotter(plotter)

        def schedule_redraw() -> None:
            debounce.stop()
            debounce.start()

        def on_slider_value(_: int) -> None:
            on_value()
            schedule_redraw()

        debounce.timeout.connect(redraw)
        slider.valueChanged.connect(on_slider_value)
        on_value()
        redraw()
        tabs.addTab(w, tab_title)

    cargas_nodales = cargas_nodales or []

    _mk_tab_plain(
        "Dibujo_Estructura",
        "Geometría IPN, terna global en el origen y ejes locales opcionales (PyVista).",
        lambda p: _populate_estructura(
            p, nodos, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, longitud_vector
        ),
    )
    _mk_tab_plain(
        "Dibujo_Fuerzas",
        "Misma geometría más vectores de carga en global (longitud fija en pantalla).",
        lambda p: _populate_fuerzas(
            p,
            nodos,
            barras,
            nodos_dict,
            cargas_nodales,
            ipn_dims,
            escala_seccion,
            mostrar_ejes_locales,
            longitud_vector,
            1e-9,
        ),
    )
    if desplazamientos is not None:
        _mk_tab_deformada(
            "Deformada",
            "Eje deformado (Bernoulli: traslaciones y rotaciones nodales según K de barra) y perfil IPN "
            "subdividido a lo largo de la fibra. Líneas grises: eje indeformado. Amplificá con el deslizador.",
            escala_deform_inicial,
            np.asarray(desplazamientos, dtype=float),
        )
    _mk_tab_diagram(
        "Esfuerzos de corte V_y",
        "Diagrama escalonado V_y local (verde + / rojo -). Pasá el mouse sobre el diagrama para ver valores; la escala se actualiza al mover el deslizador.",
        escala_diagrama_corte,
        "vy",
        lambda p, esc: _populate_corte(
            p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, "vy", esc
        ),
    )
    _mk_tab_diagram(
        "Esfuerzos de corte V_z",
        "Diagrama escalonado V_z local.",
        escala_diagrama_corte,
        "vz",
        lambda p, esc: _populate_corte(
            p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, "vz", esc
        ),
    )
    _mk_tab_diagram(
        "Esfuerzo normal N_x",
        "N_x local (convención visual como en matplotlib).",
        escala_diagrama_corte,
        "nx",
        lambda p, esc: _populate_corte(
            p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, "nx", esc
        ),
    )
    _mk_tab_diagram(
        "Momento M_y",
        "Momento flector M_y en plano X-Z (+M_y hacia -z_local).",
        escala_diagrama_corte,
        "my",
        lambda p, esc: _populate_my(p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, esc),
    )
    _mk_tab_diagram(
        "Momento M_z",
        "Momento flector M_z en plano X-Y (+M_z hacia +y_local).",
        escala_diagrama_corte,
        "mz",
        lambda p, esc: _populate_mz(p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, esc),
    )
    _mk_tab_diagram(
        "Momento M_x",
        "Momento torsor M_x (diagrama escalonado).",
        escala_diagrama_corte,
        "mx",
        lambda p, esc: _populate_mx(p, barras, nodos_dict, ipn_dims, escala_seccion, mostrar_ejes_locales, esc),
    )

    win.show()
    app.exec() if hasattr(app, "exec") else app.exec_()


def export_paraview_todo(
    path_vtm: Path,
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    cargas_nodales: Optional[List[Any]] = None,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    escala_diagrama: float = 1.0,
    longitud_vector: float = 45.0,
) -> None:
    """Un único .vtm con sub-bloques por vista (sin malla de nodos)."""
    _require_pyvista()
    path_vtm = Path(path_vtm)
    path_vtm.parent.mkdir(parents=True, exist_ok=True)
    cargas_nodales = cargas_nodales or []

    ipn = build_ipn_mesh(barras, nodos_dict, ipn_dims, escala_seccion)
    h, _, _, _ = _dims_perfil_ipn(ipn_dims, escala_seccion)

    root = pv.MultiBlock()
    root["00_ipn"] = ipn

    def _sub(name: str, quads: List, segs: List, refs: List) -> pv.MultiBlock:
        sub = pv.MultiBlock()
        r_auto = 0.35
        if ipn.n_points > 0:
            b = ipn.bounds
            diag = float(np.linalg.norm([b[1] - b[0], b[3] - b[2], b[5] - b[4]]))
            r_auto = max(diag * 0.002, 0.35)
        for suffix, col in (("_pos", _DIAG_COLOR_POS), ("_neg", _DIAG_COLOR_NEG), ("_zero", _DIAG_COLOR_ZERO)):
            fr = _merge_quad_meshes_same_color(quads, col)
            sub[f"franja{suffix}"] = fr if fr is not None else pv.PolyData()
            tb = _merge_line_tubes(segs, col, r_auto)
            sub[f"borde{suffix}"] = tb if tb is not None else pv.PolyData()
        ref_m = [pv.Line(np.asarray(a).ravel()[:3], np.asarray(b).ravel()[:3]) for a, b in refs if _segment_length(a, b) >= 1e-9]
        if ref_m:
            sub["referencia"] = ref_m[0].merge(ref_m[1:]) if len(ref_m) > 1 else ref_m[0]
        else:
            sub["referencia"] = pv.PolyData()
        root[name] = sub
        return sub

    q_f, s_f, r_f, _, _ = collect_corte_diagram_geometry(barras, nodos_dict, "vy", escala_diagrama)
    _sub("01_Vy", q_f, s_f, r_f)
    q_f, s_f, r_f, _, _ = collect_corte_diagram_geometry(barras, nodos_dict, "vz", escala_diagrama)
    _sub("02_Vz", q_f, s_f, r_f)
    q_f, s_f, r_f, _, _ = collect_corte_diagram_geometry(barras, nodos_dict, "nx", escala_diagrama)
    _sub("03_Nx", q_f, s_f, r_f)
    q_f, s_f, r_f, _, _ = collect_my_diagram_geometry(barras, nodos_dict, ipn_dims, escala_seccion, escala_diagrama)
    _sub("04_My", q_f, s_f, r_f)
    q_f, s_f, r_f, _, _ = collect_mz_diagram_geometry(
        barras, nodos_dict, ipn_dims=ipn_dims, escala_seccion=escala_seccion, escala_diagrama_momento=escala_diagrama
    )
    _sub("05_Mz", q_f, s_f, r_f)
    q_f, s_f, r_f, _, _ = collect_mx_diagram_geometry(barras, nodos_dict, escala_diagrama)
    _sub("06_Mx", q_f, s_f, r_f)

    # Terna + fuerzas como líneas/tubos
    terna = pv.MultiBlock()
    O = np.zeros(3)
    for u, lab in zip(
        [np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])],
        ["Xp", "Yp", "Zp"],
    ):
        terna[lab] = pv.Line(O, O + float(longitud_vector) * u)
    root["07_terna_global"] = terna

    fuerzas: List[pv.PolyData] = []
    r_f = max(0.15, (max(ipn.bounds[1] - ipn.bounds[0], 1.0) * 0.0015) if ipn.n_points else 0.2)
    for barra in barras:
        for carga in getattr(barra, "cargas", []) or []:
            F = _vector_global_carga_puntual(carga)
            P_raw = np.array(
                [float(getattr(carga, "x", 0.0)), float(getattr(carga, "y", 0.0)), float(getattr(carga, "z", 0.0))],
                dtype=float,
            )
            P = _punto_carga_banda_superior_ipn(barra, P_raw, h)
            for i in range(3):
                if abs(F[i]) <= 1e-9:
                    continue
                u = np.zeros(3)
                u[i] = np.sign(F[i])
                tail = P - longitud_vector * u
                t = pv.Line(tail, P).tube(radius=r_f)
                if t.n_points:
                    fuerzas.append(t)
    _color_f_nodal = "#c83232"
    _color_m_nodal = "#7a3fbf"
    fuerzas_nodales_f: List[pv.PolyData] = []
    fuerzas_nodales_m: List[pv.PolyData] = []
    if cargas_nodales:
        for cn in cargas_nodales:
            nid = getattr(cn, "nodo_id", None)
            if nid is None:
                continue
            nodo = nodos_dict.get(nid)
            if nodo is None:
                continue
            P = np.array([float(nodo.x), float(nodo.y), float(nodo.z)])
            # Fuerzas
            Fv = np.array(
                [float(getattr(cn, "fx", 0.0) or 0.0), float(getattr(cn, "fy", 0.0) or 0.0), float(getattr(cn, "fz", 0.0) or 0.0)]
            )
            for i in range(3):
                if abs(Fv[i]) <= 1e-9:
                    continue
                u = np.zeros(3)
                u[i] = np.sign(Fv[i])
                tail = P - longitud_vector * u
                t = pv.Line(tail, P).tube(radius=r_f * 1.15)
                if t.n_points:
                    fuerzas_nodales_f.append(t)
            # Momentos
            Mv = np.array(
                [float(getattr(cn, "mx", 0.0) or 0.0), float(getattr(cn, "my", 0.0) or 0.0), float(getattr(cn, "mz", 0.0) or 0.0)]
            )
            for i in range(3):
                if abs(Mv[i]) <= 1e-9:
                    continue
                u = np.zeros(3)
                u[i] = np.sign(Mv[i])
                tail = P - longitud_vector * u
                t = pv.Line(tail, P).tube(radius=r_f)
                if t.n_points:
                    fuerzas_nodales_m.append(t)
                tail2 = P - 0.82 * longitud_vector * u
                tip2 = P - (0.82 - 0.18) * longitud_vector * u
                t2 = pv.Line(tail2, tip2).tube(radius=r_f)
                if t2.n_points:
                    fuerzas_nodales_m.append(t2)
    if fuerzas_nodales_f:
        root["08b_fuerzas_nodales"] = fuerzas_nodales_f[0].merge(fuerzas_nodales_f[1:]) if len(fuerzas_nodales_f) > 1 else fuerzas_nodales_f[0]
    else:
        root["08b_fuerzas_nodales"] = pv.PolyData()
    if fuerzas_nodales_m:
        root["08c_momentos_nodales"] = fuerzas_nodales_m[0].merge(fuerzas_nodales_m[1:]) if len(fuerzas_nodales_m) > 1 else fuerzas_nodales_m[0]
    else:
        root["08c_momentos_nodales"] = pv.PolyData()
    if fuerzas:
        root["08_fuerzas"] = fuerzas[0].merge(fuerzas[1:]) if len(fuerzas) > 1 else fuerzas[0]
    else:
        root["08_fuerzas"] = pv.PolyData()

    root.save(str(path_vtm))
