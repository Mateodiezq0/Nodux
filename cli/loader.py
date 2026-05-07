"""
Construye ``core.estructura.Estructura`` desde un dict (JSON/YAML) validado levemente.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any, Dict, List, Optional

import numpy as np

from core.barra import Barra
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

    bars_spec = spec.get("bars") or spec.get("barras")
    if not bars_spec:
        raise ValueError("Falta la lista 'bars' (o 'barras')")
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

    for barra in est.barras:
        for carga in barra.cargas:
            with contextlib.redirect_stdout(io.StringIO()):
                reacciones_de_empotramiento(carga, barra)
        barra.transformar_reacciones_empotramiento_a_global()

    return est
