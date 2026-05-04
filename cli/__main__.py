"""
  python -m cli run ruta/modelo.json
  python -m cli interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _cmd_run(args: argparse.Namespace) -> None:
    from .loader import build_estructura_from_spec
    from .pipeline import load_spec, run_pipeline

    spec = load_spec(Path(args.modelo))
    est = build_estructura_from_spec(spec)
    run_pipeline(
        est,
        escala_diagrama=float(args.escala_diagrama),
        show_matplotlib=not args.no_show,
        titulo=str(args.titulo),
    )
    if args.no_show:
        print(
            f"[OK] Modelo resuelto: {len(est.nodos)} nodos, {len(est.barras)} barras. "
            "Remove --no-show to open the Tk window (structure, loads, V/N/M diagrams)."
        )


def _cmd_interactive(_: argparse.Namespace) -> None:
    from .interactive import run_interactive_menu

    run_interactive_menu()


def _cmd_gui(args: argparse.Namespace) -> None:
    from .gui_ftool import run_ftool_gui

    run_ftool_gui(precargar_ejemplo=bool(getattr(args, "ejemplo", False)))


def main() -> None:
    p = argparse.ArgumentParser(
        description="Reticular — análisis de estructuras reticuladas 3D."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Cargar JSON/YAML y resolver + ventana con pestañas (geometría, fuerzas, diagramas).")
    pr.add_argument("modelo", type=Path, help="Archivo .json o .yaml")
    pr.add_argument(
        "--no-show",
        action="store_true",
        help="Solo resolver en memoria; no abrir matplotlib.",
    )
    pr.add_argument("--escala-diagrama", type=float, default=1.0, dest="escala_diagrama")
    pr.add_argument("--titulo", type=str, default="Reticular — estructura y esfuerzos")

    pi = sub.add_parser("interactive", help="Menú paso a paso para armar nodos, barras y cargas; luego graficar.")
    pg = sub.add_parser("gui", help="Ventana gráfica estilo Ftool (PyVista + Qt): modelo, análisis, diagramas.")
    pg.add_argument(
        "--ejemplo",
        action="store_true",
        help="Precargar el mismo modelo que supertesteo.crear_estructura_supertesteo() (nodos, barras, cargas).",
    )

    args = p.parse_args()
    if args.cmd == "run":
        _cmd_run(args)
    elif args.cmd == "interactive":
        _cmd_interactive(args)
    elif args.cmd == "gui":
        _cmd_gui(args)


if __name__ == "__main__":
    main()
