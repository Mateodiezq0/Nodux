# Setup y entorno reproducible

## Requisitos

- **Python 3.10 o superior** (3.11 es una buena referencia).
- Sistema con soporte gráfico para la GUI (Windows/Linux/macOS; en servidores sin display la GUI no aplica).

## Crear entorno virtual (recomendado)

Desde la **raíz del repositorio** (`Hyperstatic_Structures/`):

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Para tests con pytest:

```bash
pip install -r requirements-dev.txt
```

## Cómo ejecutar el proyecto

Siempre desde la **raíz del repo** (donde está la carpeta `cli/` y el paquete `core/`):

| Comando | Descripción |
|--------|-------------|
| `python -m cli gui` | Ventana principal estilo Ftool (PyVista + Qt). |
| `python -m cli gui --ejemplo` | Misma GUI con modelo de ejemplo precargado. |
| `python -m cli run ruta\modelo.json` | Carga JSON/YAML, resuelve y abre vistas matplotlib (salvo `--no-show`). |
| `python -m cli interactive` | Menú CLI para armar modelo paso a paso. |

No hace falta `PYTHONPATH` manual si usás `python -m cli ...`: [cli/__main__.py](../../cli/__main__.py) inserta la raíz del proyecto en `sys.path`.

## Backend Qt

El código intenta **PySide6** primero y cae a **PyQt5** si no está PySide6. El `requirements.txt` fija **PySide6**. Si instalás solo PyQt5, debe coexistir con `pyvistaqt` (mismas versiones que en `requirements.txt` salvo el binding Qt).

## YAML

Los modelos `.yaml` / `.yml` requieren **PyYAML** (ya listado en `requirements.txt`). Sin él, `load_spec` falla con mensaje explícito ([cli/pipeline.py](../../cli/pipeline.py)).

## Windows

Si la activación del venv da error de política de ejecución, ejecutar una vez en PowerShell (como usuario):

`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
