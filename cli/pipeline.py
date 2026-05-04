"""
Resolución completa y visualización (misma idea que ``supertesteo.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Raíz del proyecto
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from .loader import build_estructura_from_spec
from core.estructura import Estructura


def _post_solicitaciones_locales(estructura: Estructura) -> None:
    for barra in estructura.barras:
        if hasattr(barra, "solicitacion_extremo_de_barra_local"):
            try:
                barra.solicitacion_extremo_de_barra_local()
            except Exception:
                pass


def solve_estructura(estructura: Estructura) -> List[np.ndarray]:
    """
    Ensamble, cargas, desplazamientos, reacciones y solicitaciones locales (sin ventanas).
    """
    estructura.ensamble_matriz_global()
    estructura.ensamble_vector_cargas_nodales_equivalentes()
    estructura.resolver_desplazamientos(debug=0)
    F_internas = estructura.calcular_reacciones(debug=0)
    _post_solicitaciones_locales(estructura)
    return F_internas


def run_pipeline(
    estructura: Estructura,
    *,
    escala_diagrama: float = 1.0,
    ipn_dims: Optional[Dict[str, float]] = None,
    titulo: str = "Reticular — estructura y esfuerzos",
    show_matplotlib: bool = True,
) -> List[np.ndarray]:
    """
    Ensamble → cargas → desplazamientos → reacciones/solicitaciones → gráficos matplotlib (pestañas).
    Devuelve la lista de vectores 12 (internas por barra) como ``calcular_reacciones``.
    """
    ipn_dims = ipn_dims or {"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0}

    F_internas = solve_estructura(estructura)

    if show_matplotlib:
        from plot.plot import mostrar_dibujos_matplotlib_pestanas

        nodos_dict = {n.id: n for n in estructura.nodos}
        mostrar_dibujos_matplotlib_pestanas(
            estructura.nodos,
            estructura.barras,
            nodos_dict,
            cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
            ipn_dims=ipn_dims,
            escala_seccion=1.0,
            mostrar_ejes_locales=True,
            longitud_vector=45.0,
            escala_diagrama_corte=escala_diagrama,
            titulo_app=titulo,
        )

    return F_internas


def load_spec(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Para archivos YAML instalá: pip install pyyaml"
            ) from e
        data = yaml.safe_load(text)
    elif suffix == ".json":
        import json

        data = json.loads(text)
    else:
        import json

        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("El archivo debe describir un objeto en la raíz (dict)")
    return data
