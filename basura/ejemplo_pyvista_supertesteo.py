"""
Ejemplo: misma estructura que ``supertesteo`` resuelta, pestañas PyVista y export completo a ParaView.

Uso:
  pip install pyvista pyvistaqt PySide6
  python ejemplo_pyvista_supertesteo.py              # exporta .vtm y abre pestañas PyVista
  python ejemplo_pyvista_supertesteo.py --no-show  # solo exporta para ParaView
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from supertesteo import crear_estructura_supertesteo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="PyVista / ParaView con supertesteo")
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="No abrir ventana PyVista; solo exportar .vtm",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "supertesteo_paraview_todo.vtm",
        help="Ruta del archivo .vtm (MultiBlock para ParaView)",
    )
    args = parser.parse_args()

    estructura = crear_estructura_supertesteo()
    estructura.ensamble_matriz_global()
    estructura.ensamble_vector_cargas_nodales_equivalentes()
    estructura.resolver_desplazamientos(debug=0)
    estructura.calcular_reacciones(debug=0)
    nodos_dict = {n.id: n for n in estructura.nodos}
    for barra in estructura.barras:
        if hasattr(barra, "solicitacion_extremo_de_barra_local"):
            try:
                barra.solicitacion_extremo_de_barra_local()
            except Exception:
                pass

    from plot.pyvista_pestanas import export_paraview_todo, mostrar_dibujos_pyvista_pestanas

    ipn_dims = {"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0}
    export_paraview_todo(
        args.output,
        estructura.nodos,
        estructura.barras,
        nodos_dict,
        cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
        ipn_dims=ipn_dims,
        escala_seccion=1.0,
        escala_diagrama=1.0,
        longitud_vector=45.0,
    )
    print(f"Exportado MultiBlock VTK: {args.output}")
    print("  En ParaView: File - Open - seleccionar el .vtm")

    if not args.no_show:
        mostrar_dibujos_pyvista_pestanas(
            estructura.nodos,
            estructura.barras,
            nodos_dict,
            cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
            ipn_dims=ipn_dims,
            escala_seccion=1.0,
            mostrar_ejes_locales=True,
            longitud_vector=45.0,
            escala_diagrama_corte=1.0,
            titulo_app="Supertesteo — PyVista (todas las pestañas)",
            desplazamientos=estructura.desplazamientos,
            escala_deform_inicial=1.0,
        )


if __name__ == "__main__":
    main()
