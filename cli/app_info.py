"""
Identidad de la aplicación (nombre y versión).

Bump de versión: editar solo APP_VERSION (y, si hace falta, APP_NAME).
El resto del proyecto debe usar app_display_name() / main_window_title() / windows_app_user_model_id() / etc.
"""

from __future__ import annotations

APP_NAME = "Nodux"
APP_VERSION = "1.0"


def app_display_name() -> str:
    """Nombre visible con versión, p. ej. «Nodux 1.0»."""
    return f"{APP_NAME} {APP_VERSION}"


def windows_app_user_model_id() -> str:
    """ID estable para la barra de tareas de Windows (asociar icono a esta app, no a python.exe)."""
    return f"HyperstaticStructures.{APP_NAME}.{APP_VERSION}"


def main_window_title() -> str:
    """Título de la ventana principal: solo marca y versión (sin sufijos; evita duplicar con Qt/Windows)."""
    return app_display_name()


def cli_description() -> str:
    """Texto corto para argparse / ayuda."""
    return f"{app_display_name()} — análisis de estructuras reticuladas 3D."


def default_run_window_title() -> str:
    """Título por defecto de la ventana matplotlib en ``cli run``."""
    return f"{app_display_name()} — estructura y esfuerzos"


def default_pdf_results_title() -> str:
    return f"{app_display_name()} — resultados"


def pyvista_tabs_window_title() -> str:
    """Ventana auxiliar de pestañas PyVista."""
    return f"{app_display_name()} — PyVista (todas las vistas)"


def interactive_pipeline_title() -> str:
    return f"{app_display_name()} — CLI interactivo"
