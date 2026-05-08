"""
Temas de color del visor 3D (fondo + malla IPN) y persistencia en JSON del usuario.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

SETTINGS_VERSION = 1
DEFAULT_VIEWPORT_THEME_ID = "dark"

# Orden para ciclar con la tecla T
_THEME_ORDER: List[str] = ["dark", "light", "red_white", "blue_yellow"]


@dataclass(frozen=True)
class ViewportThemeSpec:
    id: str
    label: str
    background_color: str
    background_top: Optional[str]
    mesh_color: str
    mesh_edge_color: str


_THEMES: Dict[str, ViewportThemeSpec] = {
    "dark": ViewportThemeSpec(
        id="dark",
        label="Oscuro (predeterminado)",
        background_color="#1a1a1c",
        background_top="#2a2d32",
        mesh_color="#d8dde6",
        mesh_edge_color="#a8b0c0",
    ),
    "light": ViewportThemeSpec(
        id="light",
        label="Claro",
        background_color="#f8f9fa",
        background_top="#ffffff",
        mesh_color="#7fb3d5",
        mesh_edge_color="#1b4f72",
    ),
    "red_white": ViewportThemeSpec(
        id="red_white",
        label="Rojo y blanco",
        background_color="#4a0f0f",
        background_top="#6b1515",
        mesh_color="#f5f5f5",
        mesh_edge_color="#ffffff",
    ),
    "blue_yellow": ViewportThemeSpec(
        id="blue_yellow",
        label="Azul y amarillo",
        background_color="#154360",
        background_top="#1a5276",
        mesh_color="#f4d03f",
        mesh_edge_color="#b7950b",
    ),
}


def list_theme_ids() -> List[str]:
    return list(_THEME_ORDER)


def list_themes() -> List[ViewportThemeSpec]:
    return [_THEMES[k] for k in _THEME_ORDER if k in _THEMES]


def get_theme(theme_id: str) -> ViewportThemeSpec:
    tid = str(theme_id).strip().lower()
    if tid in _THEMES:
        return _THEMES[tid]
    return _THEMES[DEFAULT_VIEWPORT_THEME_ID]


def next_theme_id(current_id: str) -> str:
    cur = str(current_id).strip().lower()
    if cur not in _THEME_ORDER:
        cur = DEFAULT_VIEWPORT_THEME_ID
    i = _THEME_ORDER.index(cur)
    return _THEME_ORDER[(i + 1) % len(_THEME_ORDER)]


def theme_to_style_dict(spec: ViewportThemeSpec) -> Dict[str, Any]:
    """Diccionario pasado a plot/pyvista_pestanas (viewport_style)."""
    return {
        "background_color": spec.background_color,
        "background_top": spec.background_top,
        "mesh_color": spec.mesh_color,
        "mesh_edge_color": spec.mesh_edge_color,
    }


def settings_path() -> Path:
    return Path.home() / ".hyperstatic_structures" / "settings.json"


def _default_settings() -> Dict[str, Any]:
    return {
        "version": SETTINGS_VERSION,
        "viewport_theme_id": DEFAULT_VIEWPORT_THEME_ID,
    }


def load_app_settings() -> Dict[str, Any]:
    path = settings_path()
    base = _default_settings()
    if not path.is_file():
        return dict(base)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return dict(base)
        out = dict(base)
        for k, v in data.items():
            out[k] = v
        return out
    except Exception:
        return dict(base)


def save_app_settings(updates: Mapping[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_app_settings()
    merged: MutableMapping[str, Any] = dict(current)
    for k, v in updates.items():
        merged[k] = v
    merged["version"] = SETTINGS_VERSION
    text = json.dumps(dict(merged), indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(
        prefix="hyperstatic_settings_",
        suffix=".json",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_viewport_theme_id() -> str:
    data = load_app_settings()
    tid = data.get("viewport_theme_id", DEFAULT_VIEWPORT_THEME_ID)
    tid_s = str(tid).strip().lower()
    if tid_s not in _THEMES:
        return DEFAULT_VIEWPORT_THEME_ID
    return tid_s


def save_viewport_theme_id(theme_id: str) -> None:
    spec = get_theme(theme_id)
    save_app_settings({"viewport_theme_id": spec.id})


def apply_style_to_plotter_background(plotter: Any, style: Optional[Mapping[str, Any]]) -> None:
    """Solo fondo (útil si no se redibuja la escena)."""
    if style is None:
        return
    bg = str(style.get("background_color") or "#ffffff")
    top = style.get("background_top")
    if top:
        try:
            plotter.set_background(bg, top=str(top))
        except TypeError:
            plotter.set_background(bg)
    else:
        plotter.set_background(bg)
