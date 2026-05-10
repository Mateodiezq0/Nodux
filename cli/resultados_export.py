"""
Exportación de resultados numéricos (mismas tablas que ``supertesteo.exportar_resultados_excel``):
Excel y PDF para informe / visor embebido en la GUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Orden de hojas en Excel y en el PDF (misma información).
RESULTADOS_SHEET_ORDER: List[str] = [
    "Resumen_Barras",
    "Ejes_Locales",
    "K_locales",
    "F_locales_de_cargas",
    "R_locales_de_empotramiento_cargas",
    "Cargas_Nodales_Aplicadas",
    "Matriz_R_2D",
    "Matriz_Rotacion_T",
    "Cargas_nodales_equivalentes_Globales",
    "Vector_Nodal_Equivalente",
    "Sistema_reducido_Kll_Fl",
    "Desplazamientos_globales_D",
    "Solicitacion_extremo_de_barra_Globales",
    "Solicitacion_extremo_de_barra_Locales",
]


def collect_resultados_dataframes(estructura: Any, F_internas: Optional[List[np.ndarray]]) -> Dict[str, pd.DataFrame]:
    """
    Construye los mismos ``DataFrame`` que escribe ``supertesteo`` en Excel.
    ``F_internas`` es la lista devuelta por ``calcular_reacciones`` (12 valores por barra).
    """
    nombres_dofs = [
        "Fx_i",
        "Fy_i",
        "Fz_i",
        "Mx_i",
        "My_i",
        "Mz_i",
        "Fx_f",
        "Fy_f",
        "Fz_f",
        "Mx_f",
        "My_f",
        "Mz_f",
    ]

    def _safe_array(obj: Any, attr: str, length: int, dtype=float) -> np.ndarray:
        val = getattr(obj, attr, None)
        if val is None:
            return np.zeros(length, dtype=dtype)
        arr = np.asarray(val, dtype=dtype)
        if arr.size != length:
            out = np.zeros(length, dtype=dtype)
            out[: min(length, arr.size)] = arr.ravel()[:length]
            return out
        return arr

    def _coord_xyz(nodo_obj: Any) -> tuple[float, float, float]:
        if nodo_obj is None:
            return (0.0, 0.0, 0.0)
        x = float(getattr(nodo_obj, "x", 0.0) or 0.0)
        y = float(getattr(nodo_obj, "y", 0.0) or 0.0)
        z = float(getattr(nodo_obj, "z", 0.0) or 0.0)
        return (x, y, z)

    def _restricciones_txt(nodo_obj: Any) -> str:
        if nodo_obj is None:
            return "Libre"
        raw = getattr(nodo_obj, "restricciones", None)
        if raw is None:
            return "Libre"
        vals = list(raw)[:6]
        vals += [False] * (6 - len(vals))
        names = ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]
        fixed = [names[i] for i, v in enumerate(vals) if bool(v)]
        return ",".join(fixed) if fixed else "Libre"

    datos_resumen_barras = []
    for barra in getattr(estructura, "barras", []):
        ni_obj = getattr(barra, "nodo_i_obj", None)
        nf_obj = getattr(barra, "nodo_f_obj", None)
        xi, yi, zi = _coord_xyz(ni_obj)
        xf, yf, zf = _coord_xyz(nf_obj)
        i_y = getattr(barra, "I_y", 0.0)
        i_z = getattr(barra, "I_z", 0.0)
        datos_resumen_barras.append(
            {
                "Id": getattr(barra, "id", None),
                "Ubicación i - X": xi,
                "Ubicación i - Y": yi,
                "Ubicación i - Z": zi,
                "Ubicación f - X": xf,
                "Ubicación f - Y": yf,
                "Ubicación f - Z": zf,
                "Restricciones i": _restricciones_txt(ni_obj),
                "Restricciones f": _restricciones_txt(nf_obj),
                "Longitud (cm)": float(getattr(barra, "L", 0.0) or 0.0),
                "Área A (cm2)": float(getattr(barra, "A", 0.0) or 0.0),
                "Inercia I_y (cm4)": float(i_y or 0.0),
                "Inercia I_z (cm4)": float(i_z or 0.0),
                "G": float(getattr(barra, "G", 0.0) or 0.0),
                "E": float(getattr(barra, "E", 0.0) or 0.0),
                "v": float(getattr(barra, "nu", np.nan)),
                "Peso específico": float(getattr(barra, "gamma", np.nan)),
                "J": float(getattr(barra, "J", 0.0) or 0.0),
                "Material": str(getattr(barra, "material", "default")),
            }
        )
    df_resumen_barras = pd.DataFrame(datos_resumen_barras)

    datos_cargas_globales_nudos = []
    for barra in getattr(estructura, "barras", []):
        reacc_i_g = _safe_array(barra, "reaccion_nudo_i_equivalente_global", 6)
        reacc_f_g = _safe_array(barra, "reaccion_nudo_f_equivalente_global", 6)
        cargas_12 = np.concatenate([reacc_i_g, reacc_f_g])
        datos_cargas_globales_nudos.append(
            {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                **{nombres_dofs[i]: float(cargas_12[i]) for i in range(12)},
            }
        )
    # Cargas nodales aplicadas directamente — aportan al ensamble del vector
    # nodal equivalente como filas adicionales (lado i = nodo aplicado, lado f = 0).
    # Con esto, al sumar por nodo todas las filas de la tabla se reproduce el
    # ``vector_nodal_equivalente`` global.
    for cn in getattr(estructura, "cargas_nodales", []) or []:
        nid = int(getattr(cn, "nodo_id", 0) or 0)
        fila = {
            "Barra ID": f"Nodal#{getattr(cn, 'id', '?')}",
            "Nodo Inicial": nid,
            "Nodo Final": "—",
            "Fx_i": float(getattr(cn, "fx", 0.0) or 0.0),
            "Fy_i": float(getattr(cn, "fy", 0.0) or 0.0),
            "Fz_i": float(getattr(cn, "fz", 0.0) or 0.0),
            "Mx_i": float(getattr(cn, "mx", 0.0) or 0.0),
            "My_i": float(getattr(cn, "my", 0.0) or 0.0),
            "Mz_i": float(getattr(cn, "mz", 0.0) or 0.0),
            "Fx_f": 0.0, "Fy_f": 0.0, "Fz_f": 0.0,
            "Mx_f": 0.0, "My_f": 0.0, "Mz_f": 0.0,
        }
        datos_cargas_globales_nudos.append(fila)
    df_cargas_globales_nudos = pd.DataFrame(datos_cargas_globales_nudos)

    datos_reacciones_estructura = []
    for idx, barra in enumerate(getattr(estructura, "barras", [])):
        if F_internas is None or idx >= len(F_internas):
            F_interna = np.zeros(12)
        else:
            F_interna = np.asarray(F_internas[idx])
            if F_interna.size != 12:
                tmp = np.zeros(12)
                tmp[: min(12, F_interna.size)] = F_interna.ravel()[:12]
                F_interna = tmp
        datos_reacciones_estructura.append(
            {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                **{nombres_dofs[i]: float(F_interna[i]) for i in range(12)},
            }
        )
    df_reacciones_estructura_global = pd.DataFrame(datos_reacciones_estructura)

    datos_f_interna_locales = []
    for barra in getattr(estructura, "barras", []):
        if hasattr(barra, "solicitacion_extremo_de_barra_local"):
            try:
                barra.solicitacion_extremo_de_barra_local()
            except Exception:
                pass
        F_local = _safe_array(barra, "solicitaciones_extremos_local", 12)
        datos_f_interna_locales.append(
            {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                **{nombres_dofs[i]: float(F_local[i]) for i in range(12)},
            }
        )
    df_f_interna_locales = pd.DataFrame(datos_f_interna_locales)

    datos_f_locales_cargas = []
    for barra in getattr(estructura, "barras", []):
        for carga in getattr(barra, "cargas", []) or []:
            f_loc = np.asarray(getattr(carga, "f_local", np.zeros(3)), dtype=float).ravel()
            if f_loc.size < 3:
                tmp = np.zeros(3, dtype=float)
                tmp[: f_loc.size] = f_loc
                f_loc = tmp
            datos_f_locales_cargas.append(
                {
                    "Carga ID": getattr(carga, "id", None),
                    "Barra ID": getattr(barra, "id", None),
                    "Nodo Inicial": getattr(barra, "nodo_i", None),
                    "Nodo Final": getattr(barra, "nodo_f", None),
                    "Fx_local": float(f_loc[0]),
                    "Fy_local": float(f_loc[1]),
                    "Fz_local": float(f_loc[2]),
                }
            )
    df_f_locales_cargas = pd.DataFrame(datos_f_locales_cargas)

    datos_reacciones_locales_nodos = []
    for barra in getattr(estructura, "barras", []):
        reacc_i_local = _safe_array(barra, "reaccion_de_empotramiento_i_local", 6)
        reacc_f_local = _safe_array(barra, "reaccion_de_empotramiento_f_local", 6)
        reacc_12 = np.concatenate([reacc_i_local, reacc_f_local])
        datos_reacciones_locales_nodos.append(
            {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                **{nombres_dofs[i]: float(reacc_12[i]) for i in range(12)},
            }
        )
    df_reacciones_locales_nodos = pd.DataFrame(datos_reacciones_locales_nodos)

    datos_r_locales_emp_cargas = []
    nombres_reac = [
        "Rx_i",
        "Ry_i",
        "Rz_i",
        "RMx_i",
        "RMy_i",
        "RMz_i",
        "Rx_f",
        "Ry_f",
        "Rz_f",
        "RMx_f",
        "RMy_f",
        "RMz_f",
    ]
    for barra in getattr(estructura, "barras", []):
        for carga in getattr(barra, "cargas", []) or []:
            r_emp = np.asarray(getattr(carga, "r_empotramiento_local", np.zeros(12)), dtype=float).ravel()
            if r_emp.size < 12:
                tmp = np.zeros(12, dtype=float)
                tmp[: r_emp.size] = r_emp
                r_emp = tmp
            datos_r_locales_emp_cargas.append(
                {
                    "Carga ID": getattr(carga, "id", None),
                    "Barra ID": getattr(barra, "id", None),
                    "Nodo Inicial": getattr(barra, "nodo_i", None),
                    "Nodo Final": getattr(barra, "nodo_f", None),
                    **{nombres_reac[i]: float(r_emp[i]) for i in range(12)},
                }
            )
    df_r_locales_emp_cargas = pd.DataFrame(datos_r_locales_emp_cargas)

    datos_cargas_nodales_aplicadas = []
    for cn in getattr(estructura, "cargas_nodales", []) or []:
        datos_cargas_nodales_aplicadas.append(
            {
                "Carga ID": getattr(cn, "id", None),
                "Nodo ID": int(getattr(cn, "nodo_id", 0) or 0),
                "Fx": float(getattr(cn, "fx", 0.0) or 0.0),
                "Fy": float(getattr(cn, "fy", 0.0) or 0.0),
                "Fz": float(getattr(cn, "fz", 0.0) or 0.0),
                "Mx": float(getattr(cn, "mx", 0.0) or 0.0),
                "My": float(getattr(cn, "my", 0.0) or 0.0),
                "Mz": float(getattr(cn, "mz", 0.0) or 0.0),
            }
        )
    df_cargas_nodales_aplicadas = pd.DataFrame(datos_cargas_nodales_aplicadas)

    nombres_dofs_nodo = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
    vector_nodal = getattr(estructura, "vector_nodal_equivalente", None)
    n_nodos_total = len(getattr(estructura, "nodos", []))
    if vector_nodal is None:
        vector_nodal = np.zeros(n_nodos_total * 6)

    # Aporte solo de cargas nodales aplicadas directamente
    aporte_nodales = np.zeros(n_nodos_total * 6, dtype=float)
    for cn in getattr(estructura, "cargas_nodales", []) or []:
        nid = int(getattr(cn, "nodo_id", 0) or 0)
        if nid <= 0 or nid > n_nodos_total:
            continue
        base_cn = (nid - 1) * 6
        aporte_nodales[base_cn:base_cn + 6] += np.asarray(cn.vector(), dtype=float)

    datos_vector_nodal = []
    for nodo in getattr(estructura, "nodos", []):
        base = (nodo.id - 1) * 6
        fila = {"Nodo ID": nodo.id, "Origen": "Total"}
        for i, nombre in enumerate(nombres_dofs_nodo):
            fila[nombre] = float(vector_nodal[base + i]) if base + i < len(vector_nodal) else 0.0
        datos_vector_nodal.append(fila)

        fila_n = {"Nodo ID": nodo.id, "Origen": "  ↳ aporte cargas nodales"}
        for i, nombre in enumerate(nombres_dofs_nodo):
            fila_n[nombre] = float(aporte_nodales[base + i])
        datos_vector_nodal.append(fila_n)

        fila_b = {"Nodo ID": nodo.id, "Origen": "  ↳ aporte cargas en barras (equiv.)"}
        for i, nombre in enumerate(nombres_dofs_nodo):
            total_i = float(vector_nodal[base + i]) if base + i < len(vector_nodal) else 0.0
            fila_b[nombre] = total_i - float(aporte_nodales[base + i])
        datos_vector_nodal.append(fila_b)

    df_vector_nodal = pd.DataFrame(datos_vector_nodal)

    nombres_desp = ["Ux", "Uy", "Uz", "Rx", "Ry", "Rz"]
    D_vec = getattr(estructura, "desplazamientos", None)
    nodos_list = list(getattr(estructura, "nodos", []))
    ndof = max(len(nodos_list) * 6, 0)
    if D_vec is None:
        D_vec = np.zeros(ndof if ndof > 0 else 1)
    else:
        D_vec = np.asarray(D_vec, dtype=float).ravel()
    if ndof > 0 and D_vec.size < ndof:
        tmp = np.zeros(ndof)
        tmp[: D_vec.size] = D_vec
        D_vec = tmp
    datos_desplazamientos = []
    for nodo in nodos_list:
        base = (nodo.id - 1) * 6
        fila = {"Nodo ID": nodo.id}
        for i, nombre in enumerate(nombres_desp):
            fila[nombre] = float(D_vec[base + i]) if base + i < len(D_vec) else 0.0
        datos_desplazamientos.append(fila)
    df_desplazamientos = pd.DataFrame(datos_desplazamientos)

    idx_lib = getattr(estructura, "idx_libres", None)
    Kll = getattr(estructura, "Kll", None)
    Fl_vec = getattr(estructura, "Fl", None)
    datos_sistema_reducido = []
    if idx_lib is not None and Kll is not None and Fl_vec is not None and np.asarray(idx_lib).size > 0:
        idx_lib = np.asarray(idx_lib, dtype=int).ravel()
        Kll = np.asarray(Kll, dtype=float)
        Fl_vec = np.asarray(Fl_vec, dtype=float).ravel()
        n = idx_lib.size
        if Kll.shape == (n, n) and Fl_vec.size == n:
            for i in range(n):
                fila = {"DOF_global_fila": int(idx_lib[i])}
                for j in range(n):
                    fila[f"K_dof_{int(idx_lib[j])}"] = float(Kll[i, j])
                fila["Fl"] = float(Fl_vec[i])
                datos_sistema_reducido.append(fila)
    if not datos_sistema_reducido:
        datos_sistema_reducido.append(
            {
                "DOF_global_fila": None,
                "nota": "Sin datos: ejecutar resolver_desplazamientos antes del export o sin DOFs libres",
                "Fl": None,
            }
        )
    df_sistema_reducido = pd.DataFrame(datos_sistema_reducido)

    datos_ejes_locales = []
    for barra in getattr(estructura, "barras", []):
        try:
            if (
                getattr(barra, "x_local", None) is None
                or getattr(barra, "y_local", None) is None
                or getattr(barra, "z_local", None) is None
            ):
                if hasattr(barra, "calcular_terna_ejes_locales"):
                    barra.calcular_terna_ejes_locales()
        except Exception:
            pass

        xl = getattr(barra, "x_local", [0.0, 0.0, 0.0])
        yl = getattr(barra, "y_local", [0.0, 0.0, 0.0])
        zl = getattr(barra, "z_local", [0.0, 0.0, 0.0])

        xlx, xly, xlz = list(xl)[:3] if len(list(xl)) >= 3 else (0.0, 0.0, 0.0)
        ylx, yly, ylz = list(yl)[:3] if len(list(yl)) >= 3 else (0.0, 0.0, 0.0)
        zlx, zly, zlz = list(zl)[:3] if len(list(zl)) >= 3 else (0.0, 0.0, 0.0)

        datos_ejes_locales.append(
            {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                "tita (deg)": getattr(barra, "tita", 0.0) or 0.0,
                "x_local_x": xlx,
                "x_local_y": xly,
                "x_local_z": xlz,
                "y_local_x": ylx,
                "y_local_y": yly,
                "y_local_z": ylz,
                "z_local_x": zlx,
                "z_local_y": zly,
                "z_local_z": zlz,
            }
        )
    df_ejes_locales = pd.DataFrame(datos_ejes_locales)

    datos_matriz_T = []
    for barra in getattr(estructura, "barras", []):
        try:
            T = np.asarray(barra.construir_matriz_rotacion_T_12x12(), dtype=float)
            if T.shape != (12, 12):
                T = np.zeros((12, 12), dtype=float)
        except Exception:
            T = np.zeros((12, 12), dtype=float)

        for fila_idx in range(12):
            fila = {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                "Fila": fila_idx + 1,
            }
            for col_idx in range(12):
                fila[f"C{col_idx + 1}"] = float(T[fila_idx, col_idx])
            datos_matriz_T.append(fila)
    df_matriz_T = pd.DataFrame(datos_matriz_T)

    datos_k_locales = []
    for barra in getattr(estructura, "barras", []):
        try:
            Kloc = np.asarray(barra._calcular_K_local(), dtype=float)
            if Kloc.shape != (12, 12):
                Kloc = np.zeros((12, 12), dtype=float)
        except Exception:
            Kloc = np.zeros((12, 12), dtype=float)

        for fila_idx in range(12):
            fila = {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                "Fila": fila_idx + 1,
            }
            for col_idx in range(12):
                fila[f"C{col_idx + 1}"] = float(Kloc[fila_idx, col_idx])
            datos_k_locales.append(fila)
    df_k_locales = pd.DataFrame(datos_k_locales)

    datos_matriz_R = []
    for barra in getattr(estructura, "barras", []):
        try:
            R = np.asarray(barra.construir_matriz_rotacion_2d_12x12(), dtype=float)
            if R.shape != (12, 12):
                R = np.zeros((12, 12), dtype=float)
        except Exception:
            R = np.zeros((12, 12), dtype=float)

        for fila_idx in range(12):
            fila = {
                "Barra ID": getattr(barra, "id", None),
                "Nodo Inicial": getattr(barra, "nodo_i", None),
                "Nodo Final": getattr(barra, "nodo_f", None),
                "Fila": fila_idx + 1,
            }
            for col_idx in range(12):
                fila[f"C{col_idx + 1}"] = float(R[fila_idx, col_idx])
            datos_matriz_R.append(fila)
    df_matriz_R = pd.DataFrame(datos_matriz_R)

    return {
        "Resumen_Barras": df_resumen_barras,
        "Ejes_Locales": df_ejes_locales,
        "K_locales": df_k_locales,
        "Matriz_R_2D": df_matriz_R,
        "F_locales_de_cargas": df_f_locales_cargas,
        "R_locales_de_empotramiento_cargas": df_r_locales_emp_cargas,
        "Cargas_Nodales_Aplicadas": df_cargas_nodales_aplicadas,
        "Cargas_nodales_equivalentes_Globales": df_cargas_globales_nudos.copy(),
        "Vector_Nodal_Equivalente": df_vector_nodal,
        "Solicitacion_extremo_de_barra_Globales": df_reacciones_estructura_global.copy(),
        "reacciones_de_estructura_Globales": df_reacciones_estructura_global,
        "Solicitacion_extremo_de_barra_Locales": df_f_interna_locales,
        "Desplazamientos_globales_D": df_desplazamientos,
        "Sistema_reducido_Kll_Fl": df_sistema_reducido,
        "reacciones_locales_de_empotramiento": df_reacciones_locales_nodos,
        "Matriz_Rotacion_T": df_matriz_T,
    }


def export_sheets_to_csv_folder(dfs: Dict[str, pd.DataFrame], folder: Path) -> int:
    """Escribe un .csv por hoja (nombre seguro). Devuelve cantidad de archivos."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, df in dfs.items():
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in str(name))
        if not safe:
            safe = f"sheet_{n}"
        p = folder / f"{safe}.csv"
        df.to_csv(p, index=False, encoding="utf-8-sig")
        n += 1
    return n


def write_resultados_excel(path: Path, dfs: Dict[str, pd.DataFrame]) -> None:
    """Escribe un .xlsx con las mismas hojas que ``supertesteo``."""
    path = Path(path)
    from openpyxl.utils import get_column_letter

    sheets_map = {name: dfs[name] for name in RESULTADOS_SHEET_ORDER if name in dfs}
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets_map.items():
            export_name = "Ternas_locales_en_Ejes_globales" if sheet_name == "Ejes_Locales" else sheet_name
            df.to_excel(writer, sheet_name=export_name, index=False)

        for sheet_name, df in sheets_map.items():
            export_name = "Ternas_locales_en_Ejes_globales" if sheet_name == "Ejes_Locales" else sheet_name
            worksheet = writer.sheets.get(export_name)
            if worksheet is None or df is None:
                continue
            for idx, col_name in enumerate(df.columns, 1):
                column_letter = get_column_letter(idx)
                max_length = max(
                    len(str(col_name)),
                    df[col_name].astype(str).map(len).max() if len(df) > 0 else 0,
                )
                adjusted_width = min(max_length + 2, 40)
                worksheet.column_dimensions[column_letter].width = adjusted_width


def _pdf_cell_txt(x: Any) -> str:
    if x is None:
        return ""
    try:
        if isinstance(x, float) and np.isnan(x):
            return ""
    except Exception:
        pass
    if isinstance(x, float):
        return f"{x:.6g}"
    s = str(x)
    return s[:80]


def _dataframe_to_pdf_pages(pdf: Any, sheet_title: str, df: pd.DataFrame, *, max_rows: int = 28, max_cols: int = 10) -> None:
    """Tablas en coordenadas de ejes fijas (evita PDF en blanco con bbox_inches='tight')."""
    import matplotlib.pyplot as plt

    if df is None or df.empty:
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.text(0.5, 0.92, sheet_title.replace("_", " "), ha="center", fontsize=12)
        ax.text(0.5, 0.5, "(vacío)", ha="center", va="center", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)
        return

    cols = list(df.columns)
    col_groups: List[List[Any]] = []
    for i in range(0, len(cols), max_cols):
        col_groups.append(cols[i : i + max_cols])

    for gi, col_sub in enumerate(col_groups):
        sub = df[col_sub]
        n_subcols = len(col_sub)
        for start in range(0, len(sub), max_rows):
            chunk = sub.iloc[start : start + max_rows]
            title = sheet_title.replace("_", " ")
            if len(col_groups) > 1:
                title += f" — cols {gi + 1}/{len(col_groups)}"
            if len(df) > max_rows:
                title += f" — filas {start + 1}-{start + len(chunk)} / {len(df)}"

            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.text(0.5, 0.97, title, ha="center", va="top", fontsize=10, transform=ax.transAxes)

            cell_text = [[_pdf_cell_txt(x) for x in row] for row in chunk.values]
            col_labels = [str(c) for c in chunk.columns]
            tbl = ax.table(
                cellText=cell_text,
                colLabels=col_labels,
                cellLoc="center",
                loc="center",
                bbox=[0.03, 0.05, 0.94, 0.88],
            )
            tbl.auto_set_font_size(False)
            fs = max(4.0, min(7.0, 240.0 / max(n_subcols * 2.5, 12.0)))
            tbl.set_fontsize(fs)
            tbl.scale(1.0, 1.08)
            pdf.savefig(fig)
            plt.close(fig)


def write_resultados_pdf(path: Path, dfs: Dict[str, pd.DataFrame], *, titulo: str = "Informe de resultados") -> None:
    """PDF multipágina (tablas). Requiere matplotlib."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.text(0.5, 0.55, titulo, ha="center", fontsize=18, weight="bold", transform=ax.transAxes)
        ax.text(
            0.5,
            0.44,
            "Tablas equivalentes al libro Excel de exportación (supertesteo).",
            ha="center",
            fontsize=10,
            transform=ax.transAxes,
        )
        pdf.savefig(fig)
        plt.close(fig)

        for key in RESULTADOS_SHEET_ORDER:
            df = dfs.get(key)
            if df is None:
                continue
            title = key
            _dataframe_to_pdf_pages(pdf, title, df)
