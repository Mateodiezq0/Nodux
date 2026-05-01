"""
Cliente por línea de comandos: definir nodos, barras y cargas; resolver y ver diagramas.

  python -m cli run modelo.json
  python -m cli interactive
  python -m cli gui
  python -m cli gui --ejemplo
"""

from .loader import build_estructura_from_spec
from .pipeline import run_pipeline

__all__ = ["run_pipeline", "build_estructura_from_spec"]
