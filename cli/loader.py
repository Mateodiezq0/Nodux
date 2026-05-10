"""
Construye ``core.estructura.Estructura`` desde un dict (JSON/YAML) validado levemente.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any, Dict, List, Optional

import numpy as np

from core.barra import Barra
from core.carga_distribuida import CargaDistribuida
from core.carga_nodal import CargaNodal
from core.carga_puntual import CargaPuntual, reacciones_de_empotramiento
from core.estructura import Estructura
from core.nodos import Nodo

from cli.section_props import compute_section


def _as_bool6(raw: Any, label: str) -> List[bool]:
    if raw is None:
        return [False] * 6
    if isinstance(raw, list) and len(raw) == 6:
        out: List[bool] = []
        for i, v in enumerate(raw):
            if v is None or v is False:
                out.append(False)
            elif v is True:
                out.append(True)
            else:
                raise ValueError(f"{label}[{i}]: se esperaba bool o null, recibí {v!r}")
        return out
    raise ValueError(f"{label}: se esperaba lista de 6 valores bool/null, recibí {raw!r}")


def _resolve_material_stiffness(m: Dict[str, Any], label: str) -> Dict[str, float]:
    """
    Obtiene E, A, I_y, I_z, G, J para el análisis.
    - Si existe ``section``, calcula geometría con ``compute_section``.
    - Si falta G: se usa nu → G = E/(2(1+nu)).
    - Si no hay sección, deben estar todos los escalares explícitos (legacy).
    """
    m = dict(m)
    sec = m.get("section")
    if sec:
        geo = compute_section(sec)
        m["A"] = geo["A"]
        m["I_y"] = geo["I_y"]
        m["I_z"] = geo["I_z"]
        m["J"] = geo["J"]

    if "E" not in m:
        raise ValueError(f"Material {label}: falta E (módulo de elasticidad)")

    E = float(m["E"])
    for k in ("A", "I_y", "I_z", "J"):
        if k not in m:
            raise ValueError(
                f"Material {label}: falta {k}. Agregue una sección paramétrica ('section') "
                f"o valores explícitos."
            )

    G_raw = m.get("G")
    if G_raw is not None and G_raw != "":
        G = float(G_raw)
    elif m.get("nu") is not None:
        nu = float(m["nu"])
        G = E / (2.0 * (1.0 + nu))
    else:
        raise ValueError(
            f"Material {label}: defina G (módulo de corte) o nu (Poisson) para derivar G."
        )

    return {
        "E": E,
        "A": float(m["A"]),
        "I_y": float(m["I_y"]),
        "I_z": float(m["I_z"]),
        "G": G,
        "J": float(m["J"]),
    }


def _material_lookup(spec: Dict[str, Any], name: Optional[str]) -> Dict[str, float]:
    mats = spec.get("materials") or {}
    if not isinstance(mats, dict):
        raise ValueError("'materials' debe ser un objeto/diccionario")
    key = name or spec.get("default_material") or "default"
    if key not in mats:
        raise ValueError(f"Material no definido: {key!r}. Claves: {list(mats.keys())}")
    m = mats[key]
    out = _resolve_material_stiffness(m, key)
    # Metadatos útiles para reportes/exportaciones.
    out["material_name"] = str(key)
    nu_raw = m.get("nu")
    ga_raw = m.get("gamma")
    out["nu"] = float(nu_raw) if nu_raw is not None and nu_raw != "" else np.nan
    out["gamma"] = float(ga_raw) if ga_raw is not None and ga_raw != "" else np.nan
    return out


def _net_global_force(load: Dict[str, Any]) -> np.ndarray:
    """Vector fuerza global (3,); la suma F_x+F_y+F_z del modelo coincide con este vector."""
    if "force_global" in load:
        fg = load["force_global"]
        if not (isinstance(fg, list) and len(fg) == 3):
            raise ValueError("force_global debe ser [Fx, Fy, Fz]")
        return np.array([float(fg[0]), float(fg[1]), float(fg[2])], dtype=float)
    fx = float(load.get("Fx", load.get("fx", 0.0)))
    fy = float(load.get("Fy", load.get("fy", 0.0)))
    fz = float(load.get("Fz", load.get("fz", 0.0)))
    return np.array([fx, fy, fz], dtype=float)


def build_estructura_from_spec(spec: Dict[str, Any]) -> Estructura:
    """
    Especificación mínima::

        materials:
          default: { E, A, I_y, I_z, G, J }
        nodes:
          - { id, x, y, z, fix: [bool x6] }
        bars:
          - { id, i, j, material?: str, tita?: float }
        loads_point:
          - { bar_id, x, y, z, Fx?, Fy?, Fz? }   # o force_global: [fx,fy,fz]
        loads_distributed:
          - { bar_id, x, y, z, x_f, y_f, z_f, force_global: [qx,qy,qz] }
        loads_nodal:
          - { node_id, Fx?, Fy?, Fz?, Mx?, My?, Mz? }
    """
    est = Estructura()
    nodes_spec = spec.get("nodes") or spec.get("nodos")
    if not nodes_spec:
        raise ValueError("Falta la lista 'nodes' (o 'nodos')")
    nodos_list: List[Nodo] = []
    nodos_dict: Dict[int, Nodo] = {}
    for raw in nodes_spec:
        nid = int(raw["id"])
        n = Nodo(
            id=nid,
            x=float(raw["x"]),
            y=float(raw["y"]),
            z=float(raw["z"]),
        )
        fix = raw.get("fix") or raw.get("restricciones")
        n.restricciones = _as_bool6(fix, f"nodo {nid}.fix")
        vp = raw.get("prescribed") or raw.get("valores_prescritos")
        if vp is not None:
            if not (isinstance(vp, list) and len(vp) == 6):
                raise ValueError(f"nodo {nid}: valores_prescritos debe tener 6 números")
            n.valores_prescritos = [float(v) for v in vp]
        est.agregar_nodo(n)
        nodos_list.append(n)
        nodos_dict[nid] = n

    if "bars" in spec:
        bars_spec = spec["bars"]
    elif "barras" in spec:
        bars_spec = spec["barras"]
    else:
        raise ValueError("Falta la lista 'bars' (o 'barras')")
    if not isinstance(bars_spec, list):
        raise ValueError("'bars' (o 'barras') debe ser una lista")
    for raw in bars_spec:
        bid = int(raw["id"])
        ni = int(raw.get("i") or raw.get("nodo_i"))
        nf = int(raw.get("j") or raw.get("nodo_f"))
        mat = _material_lookup(spec, raw.get("material"))
        b = Barra(
            id=bid,
            nodo_i=ni,
            nodo_f=nf,
            E=mat["E"],
            A=mat["A"],
            I_y=mat["I_y"],
            I_z=mat["I_z"],
            G=mat["G"],
            J=mat["J"],
            tita=raw.get("tita"),
        )
        # Guardamos metadatos de material para tablas de resultados.
        b.material = mat.get("material_name", "default")
        b.nu = mat.get("nu", np.nan)
        b.gamma = mat.get("gamma", np.nan)
        b.nodo_i_obj = nodos_dict.get(ni)
        b.nodo_f_obj = nodos_dict.get(nf)
        if b.nodo_i_obj is None or b.nodo_f_obj is None:
            raise ValueError(f"Barra {bid}: nodo_i o nodo_f no existe en nodos ({ni}, {nf})")
        est.agregar_barra(b)

    loads = spec.get("loads_point") or spec.get("cargas_puntuales") or []
    bars_by_id = {bar.id: bar for bar in est.barras}
    for k, raw in enumerate(loads):
        bid = int(raw.get("bar_id") or raw["barra"])
        bar = bars_by_id.get(bid)
        if bar is None:
            raise ValueError(f"Carga {k}: bar_id {bid} no existe")
        cid = int(raw.get("id", k + 1))
        carga = CargaPuntual(
            id=cid,
            x=float(raw["x"]),
            y=float(raw["y"]),
            z=float(raw["z"]),
        )
        net = _net_global_force(raw)
        carga.F_x = np.asarray(net, dtype=float).ravel()[:3].copy()
        carga.F_y = np.zeros(3, dtype=float)
        carga.F_z = np.zeros(3, dtype=float)
        bar.cargas.append(carga)

    dist_loads = spec.get("loads_distributed") or spec.get("cargas_distribuidas") or []
    _dl_id_base = len(loads)
    for k, raw in enumerate(dist_loads):
        bid = int(raw.get("bar_id") or raw["barra"])
        bar = bars_by_id.get(bid)
        if bar is None:
            raise ValueError(f"Carga distribuida {k}: bar_id {bid} no existe")
        cid = int(raw.get("id", _dl_id_base + k + 1))

        net = _net_global_force(raw)  # intensidad por unidad de longitud [qx, qy, qz]

        # Si se proveen coordenadas globales de inicio/fin, usarlas.
        # Si no, usar los extremos de la barra.
        ni_obj = bar.nodo_i_obj
        nf_obj = bar.nodo_f_obj

        if "x" in raw and "x_f" in raw:
            xi, yi, zi = float(raw["x"]), float(raw.get("y", 0.0)), float(raw.get("z", 0.0))
            xf, yf, zf = float(raw["x_f"]), float(raw.get("y_f", 0.0)), float(raw.get("z_f", 0.0))
        elif "xi_local" in raw:
            # Coordenadas locales → convertir a globales
            bar.calcular_longitud_y_bases()
            xi_l = float(raw.get("xi_local", 0.0))
            xf_l = float(raw.get("xf_local", bar.L or 0.0))
            ni_c = ni_obj.get_coord()
            xi, yi, zi = (ni_c + xi_l * bar.x_local).tolist()
            xf, yf, zf = (ni_c + xf_l * bar.x_local).tolist()
        else:
            xi, yi, zi = float(ni_obj.x), float(ni_obj.y), float(ni_obj.z)
            xf, yf, zf = float(nf_obj.x), float(nf_obj.y), float(nf_obj.z)

        carga = CargaDistribuida(
            id=cid,
            x=xi, y=yi, z=zi,
            x_f=xf, y_f=yf, z_f=zf,
            force_global_intensity=net,
        )
        bar.cargas.append(carga)

    nodal_loads = spec.get("loads_nodal") or spec.get("cargas_nodales_aplicadas") or []
    for k, raw in enumerate(nodal_loads):
        nid_raw = raw.get("node_id") or raw.get("nodo_id")
        if nid_raw is None:
            raise ValueError(f"Carga nodal {k}: falta 'node_id'")
        nid = int(nid_raw)
        if nid not in nodos_dict:
            raise ValueError(f"Carga nodal {k}: node_id {nid} no existe en los nodos definidos")
        cn = CargaNodal(
            nodo_id=nid,
            fx=float(raw.get("Fx", raw.get("fx", 0.0))),
            fy=float(raw.get("Fy", raw.get("fy", 0.0))),
            fz=float(raw.get("Fz", raw.get("fz", 0.0))),
            mx=float(raw.get("Mx", raw.get("mx", 0.0))),
            my=float(raw.get("My", raw.get("my", 0.0))),
            mz=float(raw.get("Mz", raw.get("mz", 0.0))),
        )
        est.agregar_carga_nodal(cn)

    for barra in est.barras:
        for carga in barra.cargas:
            with contextlib.redirect_stdout(io.StringIO()):
                if getattr(carga, "is_distributed", False):
                    carga.reacciones_de_empotramiento(barra)
                else:
                    reacciones_de_empotramiento(carga, barra)
        barra.transformar_reacciones_empotramiento_a_global()

    return est
