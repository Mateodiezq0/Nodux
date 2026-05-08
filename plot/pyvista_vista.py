"""
Visualización 3D con PyVista (VTK) y exportación para ParaView.

- Geometría IPN y diagramas alineados con ``plot.plot`` (sin eje negro en el alma
  de la barra ni esferas en nodos).
- **Pestañas** (estructura, fuerzas, deformada si hay D, V_y, V_z, N_x, M_y, M_z, M_x):
  ``mostrar_dibujos_pyvista_pestanas`` en ``plot.pyvista_pestanas`` (requiere
  ``pip install pyvista pyvistaqt PySide6`` o ``PyQt5``).
- Export solo M_z: ``export_estructura_multiblock_paraview``; export completo:
  ``export_paraview_todo`` (delega a ``plot.pyvista_pestanas``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np

# Raíz del proyecto (mismo patrón que plot.py)
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from plot.plot import (  # noqa: E402
    _DIAG_COLOR_NEG,
    _DIAG_COLOR_POS,
    _DIAG_COLOR_ZERO,
    _box_faces_local,
    _diagrama_momento_mz_local_barra,
    _dims_perfil_ipn,
    _local_to_global,
    _momento_polyline_con_cruces_cero,
    obtener_coordenadas_barra,
)

try:
    import pyvista as pv
except ImportError:  # pragma: no cover
    pv = None  # type: ignore


def _require_pyvista() -> None:
    if pv is None:
        raise ImportError(
            "PyVista no está instalado. Ejecuta: pip install pyvista"
        )


def _terna_seccion_desde_cuerda(
    x_chord: np.ndarray,
    y_ref: np.ndarray,
    z_ref: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eje x = cuerda; y,z ortonormales proyectando la terna de referencia (perfil IPN)."""
    xe = np.asarray(x_chord, dtype=float).ravel()[:3]
    xe = xe / max(float(np.linalg.norm(xe)), 1e-18)
    yr = np.asarray(y_ref, dtype=float).ravel()[:3]
    zr = np.asarray(z_ref, dtype=float).ravel()[:3]
    yp = yr - float(np.dot(yr, xe)) * xe
    ny = float(np.linalg.norm(yp))
    if ny < 1e-9:
        yp = np.cross(xe, np.array([0.0, 0.0, 1.0], dtype=float))
        ny = float(np.linalg.norm(yp))
    if ny < 1e-9:
        yp = np.cross(xe, np.array([0.0, 1.0, 0.0], dtype=float))
        ny = float(np.linalg.norm(yp))
    yp = yp / max(ny, 1e-18)
    zp = np.cross(xe, yp)
    zp = zp / max(float(np.linalg.norm(zp)), 1e-18)
    return xe, yp, zp


def _segment_length(p0: np.ndarray, p1: np.ndarray) -> float:
    a = np.asarray(p0, dtype=float).ravel()[:3]
    b = np.asarray(p1, dtype=float).ravel()[:3]
    return float(np.linalg.norm(b - a))


def _quad_to_polydata(quad: np.ndarray) -> "pv.PolyData":
    """quad: (4, 3) vértices en orden."""
    mesh = pv.PolyData(quad.astype(float))
    mesh.faces = np.array([4, 0, 1, 2, 3], dtype=np.int64)
    return mesh


def _merge_quad_meshes_same_color(
    quads: List[Tuple[np.ndarray, str]], target_color: str
) -> Optional["pv.PolyData"]:
    blocks = [_quad_to_polydata(q) for q, c in quads if c == target_color]
    if not blocks:
        return None
    return blocks[0].merge(blocks[1:]) if len(blocks) > 1 else blocks[0]


def _merge_line_tubes(
    segs: List[Tuple[np.ndarray, np.ndarray, str]], target_color: str, radius: float
) -> Optional["pv.PolyData"]:
    meshes: List[pv.PolyData] = []
    for p0, p1, c in segs:
        if c != target_color:
            continue
        if _segment_length(p0, p1) < 1e-9:
            continue
        p0a = np.asarray(p0, dtype=float).ravel()[:3]
        p1a = np.asarray(p1, dtype=float).ravel()[:3]
        tubed = pv.Line(p0a, p1a).tube(radius=radius)
        if tubed.n_points > 0:
            meshes.append(tubed)
    if not meshes:
        return None
    return meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]


def _collect_franja_quads_momento_linear(
    origin: np.ndarray,
    x_local: np.ndarray,
    dir_local: np.ndarray,
    xa: float,
    xb: float,
    Ma: float,
    Mb: float,
    escala_m: float,
    color_pos: str,
    color_neg: str,
    color_zero: str,
    sign_draw: float = 1.0,
) -> List[Tuple[np.ndarray, str]]:
    """
    Misma lógica que ``_rellenar_franjas_diagrama_momento_lineal_3d`` (M_y / M_z),
    pero devuelve lista de (quad 4x3, color_hex). ``dir_local`` unitario (p.ej. y_local o z_local).
    """
    out: List[Tuple[np.ndarray, str]] = []
    if abs(xb - xa) < 1e-12:
        return out

    vmax = max(abs(Ma), abs(Mb), 1.0)
    eps_m = max(1e-15, 1e-12 * vmax)

    def _sign_region(M: float) -> int:
        if M > eps_m:
            return 1
        if M < -eps_m:
            return -1
        return 0

    sa, sb = _sign_region(Ma), _sign_region(Mb)

    if sa * sb < 0 and abs(Mb - Ma) > 1e-18:
        xm = xa - Ma * (xb - xa) / (Mb - Ma)
        xm = float(np.clip(xm, min(xa, xb), max(xa, xb)))
        out.extend(
            _collect_franja_quads_momento_linear(
                origin,
                x_local,
                dir_local,
                xa,
                xm,
                Ma,
                0.0,
                escala_m,
                color_pos,
                color_neg,
                color_zero,
                sign_draw,
            )
        )
        out.extend(
            _collect_franja_quads_momento_linear(
                origin,
                x_local,
                dir_local,
                xm,
                xb,
                0.0,
                Mb,
                escala_m,
                color_pos,
                color_neg,
                color_zero,
                sign_draw,
            )
        )
        return out

    Mmid = 0.5 * (Ma + Mb)
    if abs(Mmid) <= eps_m:
        col = color_zero
    elif Mmid > 0:
        col = color_pos
    else:
        col = color_neg

    base_a = origin + xa * x_local
    base_b = origin + xb * x_local
    top_a = base_a + sign_draw * Ma * escala_m * dir_local
    top_b = base_b + sign_draw * Mb * escala_m * dir_local
    quad = np.vstack([base_a, base_b, top_b, top_a])
    out.append((quad, col))
    return out


def _iter_polilinea_segmentos(
    pts: np.ndarray,
    v_vals: np.ndarray,
    color_pos: str,
    color_neg: str,
    color_zero: str,
) -> Iterator[Tuple[np.ndarray, np.ndarray, str]]:
    """Segmentos coloreados (igual criterio que ``_plot_polilinea_diagrama_coloreada``)."""
    vmax = float(np.max(np.abs(v_vals))) if v_vals.size else 1.0
    eps = max(1e-15, 1e-12 * max(vmax, 1.0))

    def color_for(v: float) -> str:
        if v > eps:
            return color_pos
        if v < -eps:
            return color_neg
        return color_zero

    n = len(pts)
    for k in range(n - 1):
        p0 = pts[k]
        p1 = pts[k + 1]
        v0 = float(v_vals[k])
        v1 = float(v_vals[k + 1])

        if abs(v0 - v1) > eps and v0 * v1 < 0:
            denom = v0 - v1
            if abs(denom) > 1e-18:
                t = v0 / denom
                t = max(0.0, min(1.0, t))
                pm = p0 + t * (p1 - p0)
                yield (p0, pm, color_for(v0))
                yield (pm, p1, color_for(v1))
                continue

        if abs(v0 - v1) <= eps:
            c = color_for(v0)
        else:
            c = color_for(0.5 * (v0 + v1))
        yield (p0, p1, c)


def build_ipn_mesh(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    *,
    coord_nodos_dict: Optional[Dict[Any, Any]] = None,
    ipn_dims_per_bar_id: Optional[Dict[int, Dict[str, float]]] = None,
    tube_outer_radius_per_bar_id: Optional[Dict[int, float]] = None,
    profile_polygon_yz_per_bar_id: Optional[Dict[int, Any]] = None,
) -> "pv.PolyData":
    """Malla cerrada de perfiles IPN (prismas), misma convención que ``_dibujo_geometria_estructura``."""
    _require_pyvista()
    meshes: List[pv.PolyData] = []
    nd = coord_nodos_dict if coord_nodos_dict is not None else nodos_dict
    solo = coord_nodos_dict is not None

    for barra in barras:
        bid = getattr(barra, "id", None)
        bid_int = int(bid) if bid is not None else None
        coord_i, coord_f = obtener_coordenadas_barra(barra, nd, solo_nodos_dict=solo)
        if coord_i is None or coord_f is None:
            continue
        origin = np.array(coord_i, dtype=float)
        end = np.array(coord_f, dtype=float)
        v = end - origin
        L = float(np.linalg.norm(v))
        if L < 1e-12:
            continue

        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        if coord_nodos_dict is not None:
            x_local = v / max(L, 1e-18)
            y_ref = (
                np.asarray(getattr(barra, "y_local", None), dtype=float)
                if getattr(barra, "y_local", None) is not None
                else np.array([0.0, 1.0, 0.0], dtype=float)
            )
            z_ref = (
                np.asarray(getattr(barra, "z_local", None), dtype=float)
                if getattr(barra, "z_local", None) is not None
                else np.array([0.0, 0.0, 1.0], dtype=float)
            )
            x_local, y_local, z_local = _terna_seccion_desde_cuerda(x_local, y_ref, z_ref)
        else:
            x_local = (
                np.asarray(getattr(barra, "x_local", None), dtype=float)
                if getattr(barra, "x_local", None) is not None
                else v / L
            )
            y_local = (
                np.asarray(getattr(barra, "y_local", None), dtype=float)
                if getattr(barra, "y_local", None) is not None
                else np.array([0.0, 1.0, 0.0])
            )
            z_local = (
                np.asarray(getattr(barra, "z_local", None), dtype=float)
                if getattr(barra, "z_local", None) is not None
                else np.array([0.0, 0.0, 1.0])
            )
            x_local = x_local / max(np.linalg.norm(x_local), 1e-12)
            y_local = y_local / max(np.linalg.norm(y_local), 1e-12)
            z_local = z_local / max(np.linalg.norm(z_local), 1e-12)

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
            mesh_p = extrude_polygon_yz_prism(P, L, origin, x_local, y_local, z_local)
            if mesh_p.n_points > 0:
                meshes.append(mesh_p)
            continue

        custom_ipn = (
            ipn_dims_per_bar_id is not None
            and bid_int is not None
            and bid_int in ipn_dims_per_bar_id
        )
        if custom_ipn:
            dims_src = ipn_dims_per_bar_id[bid_int]
        elif (
            bid_int is not None
            and tube_outer_radius_per_bar_id is not None
            and bid_int in tube_outer_radius_per_bar_id
        ):
            Ro = float(tube_outer_radius_per_bar_id[bid_int]) * float(escala_seccion)
            ln = pv.Line(origin, end)
            meshes.append(ln.tube(radius=max(Ro, 1e-12), n_sides=48))
            continue
        else:
            dims_src = None

        h, b, tw, tf = _dims_perfil_ipn(
            dims_src if custom_ipn else ipn_dims, escala_seccion
        )

        boxes = [
            (0.0, L, -b / 2.0, b / 2.0, h / 2.0 - tf, h / 2.0),
            (0.0, L, -tw / 2.0, tw / 2.0, -h / 2.0 + tf, h / 2.0 - tf),
            (0.0, L, -b / 2.0, b / 2.0, -h / 2.0, -h / 2.0 + tf),
        ]

        for (x0, x1, y0, y1, z0, z1) in boxes:
            for face in _box_faces_local(x0, x1, y0, y1, z0, z1):
                g = _local_to_global(face, origin, x_local, y_local, z_local)
                quad = np.array(g, dtype=float)
                meshes.append(_quad_to_polydata(quad))

    if not meshes:
        return pv.PolyData()
    return meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]


def build_nodos_cloud(
    nodos: List[Any],
    nodos_dict: Optional[Dict[Any, Any]] = None,
) -> "pv.PolyData":
    """Puntos nodales (coordenadas); el color por vínculo se aplica al plotear."""
    _require_pyvista()
    if not nodos:
        return pv.PolyData()
    pts = np.array([[n.x, n.y, n.z] for n in nodos], dtype=float)
    cloud = pv.PolyData(pts)
    return cloud


def collect_mz_diagram_geometry(
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    escala_diagrama_momento: float = 1.0,
) -> Tuple[
    List[Tuple[np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray, str]],
    List[Tuple[np.ndarray, np.ndarray]],
    float,
    List[Dict[str, Any]],
]:
    """
    Devuelve:
    - quads_franja, segmentos_polilinea, lineas_referencia, escala_m,
    - hover_points: lista de dicts ``{bar_id, x_local, v, corte, pos}`` para tooltips.
    """
    h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)
    _ = h, b, tw, tf  # misma escala que matplotlib; diagrama no depende de IPN

    max_abs_m = 0.0
    Ls: List[float] = []
    for barra in barras:
        xs, ms, L = _diagrama_momento_mz_local_barra(barra)
        if xs.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(ms))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    escala_m = escala_base * float(escala_diagrama_momento)

    color_pos, color_neg, color_zero = _DIAG_COLOR_POS, _DIAG_COLOR_NEG, _DIAG_COLOR_ZERO

    quads_all: List[Tuple[np.ndarray, str]] = []
    segs_all: List[Tuple[np.ndarray, np.ndarray, str]] = []
    ref_lines: List[Tuple[np.ndarray, np.ndarray]] = []
    hover_all: List[Dict[str, Any]] = []

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        y_local = np.asarray(getattr(barra, "y_local", [0.0, 1.0, 0.0]), dtype=float).ravel()[:3]
        x_local = x_local / max(np.linalg.norm(x_local), 1e-12)
        y_local = y_local / max(np.linalg.norm(y_local), 1e-12)

        xs, ms, L = _diagrama_momento_mz_local_barra(barra)
        if xs.size == 0:
            continue

        for k in range(xs.size - 1):
            quads_all.extend(
                _collect_franja_quads_momento_linear(
                    origin,
                    x_local,
                    y_local,
                    float(xs[k]),
                    float(xs[k + 1]),
                    float(ms[k]),
                    float(ms[k + 1]),
                    escala_m,
                    color_pos,
                    color_neg,
                    color_zero,
                    sign_draw=1.0,
                )
            )

        px, pm = _momento_polyline_con_cruces_cero(xs, ms)
        pts = np.array(
            [origin + xv * x_local + mv * escala_m * y_local for xv, mv in zip(px, pm)],
            dtype=float,
        )
        for p0, p1, col in _iter_polilinea_segmentos(
            pts, pm, color_pos, color_neg, color_zero
        ):
            segs_all.append((p0, p1, col))

        for k in range(px.size):
            ptk = pts[k]
            hover_all.append(
                {
                    "bar_id": getattr(barra, "id", None),
                    "x_local": float(px[k]),
                    "v": float(pm[k]),
                    "corte": "mz",
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
                pt = origin + xm * x_local + Mm * escala_m * y_local
                hover_all.append(
                    {
                        "bar_id": getattr(barra, "id", None),
                        "x_local": float(xm),
                        "v": float(Mm),
                        "corte": "mz",
                        "pos": (float(pt[0]), float(pt[1]), float(pt[2])),
                    }
                )

        base_i = origin
        base_f = origin + L * x_local
        ref_lines.append((base_i, base_f))

    return quads_all, segs_all, ref_lines, escala_m, hover_all


def export_estructura_multiblock_paraview(
    path_vtm: Path,
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    escala_diagrama_momento: float = 1.0,
) -> None:
    """
    Escribe un archivo ``.vtm`` (VTK multiblock) para abrir en ParaView.

    Bloques: ``ipn_estructura``, franjas/borde M_z por signo, ``referencia``.
    """
    _require_pyvista()
    path_vtm = Path(path_vtm)
    path_vtm.parent.mkdir(parents=True, exist_ok=True)

    ipn = build_ipn_mesh(barras, nodos_dict, ipn_dims, escala_seccion)
    quads, segs, ref_lines, _, _ = collect_mz_diagram_geometry(
        barras,
        nodos_dict,
        ipn_dims=ipn_dims,
        escala_seccion=escala_seccion,
        escala_diagrama_momento=escala_diagrama_momento,
    )

    block = pv.MultiBlock()

    block["ipn_estructura"] = ipn

    for name, col in (
        ("mz_franja_pos", _DIAG_COLOR_POS),
        ("mz_franja_neg", _DIAG_COLOR_NEG),
        ("mz_franja_zero", _DIAG_COLOR_ZERO),
    ):
        fr = _merge_quad_meshes_same_color(quads, col)
        block[name] = fr if fr is not None else pv.PolyData()

    r_auto = 0.35
    if ipn.n_points > 0:
        bounds = ipn.bounds
        diag = float(
            np.linalg.norm(
                [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
            )
        )
        r_auto = max(diag * 0.002, 0.35)

    for name, col in (
        ("mz_borde_pos", _DIAG_COLOR_POS),
        ("mz_borde_neg", _DIAG_COLOR_NEG),
        ("mz_borde_zero", _DIAG_COLOR_ZERO),
    ):
        tb = _merge_line_tubes(segs, col, r_auto)
        block[name] = tb if tb is not None else pv.PolyData()

    ref_lines_pv: List[pv.PolyData] = []
    for a, b in ref_lines:
        ref_lines_pv.append(pv.Line(a, b))
    block["referencia"] = (
        ref_lines_pv[0].merge(ref_lines_pv[1:])
        if len(ref_lines_pv) > 1
        else (ref_lines_pv[0] if ref_lines_pv else pv.PolyData())
    )

    block.save(str(path_vtm))


def mostrar_estructura_y_mz_pyvista(
    nodos: List[Any],
    barras: List[Any],
    nodos_dict: Dict[Any, Any],
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    escala_diagrama_momento: float = 1.0,
    titulo: str = "Estructura + M_z (PyVista)",
    mostrar_ejes_barra: bool = False,
) -> None:
    """
    Ventana interactiva PyVista: IPN + franjas de momento M_z + polilínea + referencia.
    """
    _require_pyvista()

    ipn = build_ipn_mesh(barras, nodos_dict, ipn_dims, escala_seccion)
    quads, segs, ref_lines, _, _ = collect_mz_diagram_geometry(
        barras,
        nodos_dict,
        ipn_dims=ipn_dims,
        escala_seccion=escala_seccion,
        escala_diagrama_momento=escala_diagrama_momento,
    )

    plotter = pv.Plotter(window_size=(1024, 768))
    plotter.set_background("white")
    try:
        plotter.add_text(titulo, position="upper_edge", font_size=11, color="#2c3e50")
    except Exception:
        pass

    if ipn.n_points > 0:
        plotter.add_mesh(
            ipn,
            color="#7fb3d5",
            opacity=0.9,
            show_edges=True,
            edge_color="#1b4f72",
            line_width=1,
            label="Estructura",
        )

    for quad, col in quads:
        qm = _quad_to_polydata(quad)
        if qm.n_points > 0:
            plotter.add_mesh(
                qm,
                color=col,
                opacity=0.42,
                show_edges=True,
                edge_color=col,
                line_width=0.5,
            )

    r_tube = 0.35
    diag_model = 1.0
    if ipn.n_points > 0:
        bd = ipn.bounds
        diag_model = float(np.linalg.norm([bd[1] - bd[0], bd[3] - bd[2], bd[5] - bd[4]]))
        r_tube = max(diag_model * 0.0025, 0.25)

    seg_tol = max(1e-9, 1e-12 * diag_model)

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

    for a, b in ref_lines:
        if _segment_length(a, b) < seg_tol:
            continue
        aa = np.asarray(a, dtype=float).ravel()[:3]
        bb = np.asarray(b, dtype=float).ravel()[:3]
        ref_line = pv.Line(aa, bb)
        if ref_line.n_points > 0:
            plotter.add_mesh(ref_line, color="#7f8c8d", line_width=2)

    if mostrar_ejes_barra:
        s = 40.0
        for barra in barras:
            coord_i, _coord_f = obtener_coordenadas_barra(barra, nodos_dict)
            if coord_i is None:
                continue
            if hasattr(barra, "asegurar_terna_ejes_locales"):
                barra.asegurar_terna_ejes_locales()
            c = np.asarray(coord_i, dtype=float)
            xl = np.asarray(getattr(barra, "x_local", [1, 0, 0]), float).ravel()[:3]
            yl = np.asarray(getattr(barra, "y_local", [0, 1, 0]), float).ravel()[:3]
            zl = np.asarray(getattr(barra, "z_local", [0, 0, 1]), float).ravel()[:3]
            xl = xl / max(np.linalg.norm(xl), 1e-12)
            yl = yl / max(np.linalg.norm(yl), 1e-12)
            zl = zl / max(np.linalg.norm(zl), 1e-12)
            plotter.add_mesh(pv.Line(c, c + xl * s), color="red", line_width=2)
            plotter.add_mesh(pv.Line(c, c + yl * s), color="green", line_width=2)
            plotter.add_mesh(pv.Line(c, c + zl * s), color="blue", line_width=2)

    plotter.add_legend()
    try:
        plotter.show_grid(font_size=8, color="#888888")
    except Exception:
        try:
            plotter.show_bounds(grid=True, location="outer", all_edges=True)
        except Exception:
            pass
    plotter.show_axes()
    plotter.show()


def mostrar_dibujos_pyvista_pestanas(*args: Any, **kwargs: Any) -> None:
    """Delegación a ``plot.pyvista_pestanas`` (todas las pestañas)."""
    from plot.pyvista_pestanas import mostrar_dibujos_pyvista_pestanas as _fn

    _fn(*args, **kwargs)


def export_paraview_todo(*args: Any, **kwargs: Any) -> None:
    """Delegación a ``plot.pyvista_pestanas.export_paraview_todo``."""
    from plot.pyvista_pestanas import export_paraview_todo as _fn

    _fn(*args, **kwargs)
