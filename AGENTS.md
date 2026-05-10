# Instrucciones para agentes (Cursor / IA)

## Antes de cambiar código

1. Leé **[docs/ai/02_ARCHITECTURE.md](docs/ai/02_ARCHITECTURE.md)** para saber dónde vive la lógica (core vs cli vs plot).
2. Si tocás el formato de entrada o materiales, leé **[docs/ai/03_MODEL_SPEC.md](docs/ai/03_MODEL_SPEC.md)** y el docstring de `build_estructura_from_spec` en `cli/loader.py`.
3. Para la ventana Ftool o PyVista, leé **[docs/ai/04_GUI_AND_VIZ.md](docs/ai/04_GUI_AND_VIZ.md)**.

## Setup

Seguí **[docs/ai/00_SETUP_AND_ENV.md](docs/ai/00_SETUP_AND_ENV.md)** y `requirements.txt`. No asumas paquetes globales: el proyecto debe instalarse con `pip install -r requirements.txt` en un venv.

## Normas de cambio

- **No romper** los comandos `python -m cli gui`, `run` e `interactive` sin actualizar `cli/__main__.py` y la documentación en `docs/ai/`.
- **`core/`** no debe depender de Qt, PyVista ni matplotlib.
- Preferí cambios **acotados** al pedido; evitá refactors masivos mezclados con features.
- Mensajes de UI y docs orientadas al usuario en **español** cuando el archivo ya esté en español.

## Visión rápida

Resumen de una página: **[docs/ai/01_PROJECT_OVERVIEW.md](docs/ai/01_PROJECT_OVERVIEW.md)**.
