"""
Especificación dict del ejemplo ``supertesteo.crear_estructura_supertesteo`` (misma geometría y cargas).

El contenido se lee de ``cli/examples/supertesteo_like.json`` para una sola fuente verdad.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_PKG = Path(__file__).resolve().parent
_SUPERTESTEO_JSON = _PKG / "examples" / "supertesteo_like.json"


def get_supertesteo_spec() -> Dict[str, Any]:
    if not _SUPERTESTEO_JSON.is_file():
        raise FileNotFoundError(f"No está el ejemplo: {_SUPERTESTEO_JSON}")
    data = json.loads(_SUPERTESTEO_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("supertesteo_like.json debe ser un objeto JSON")
    return data
