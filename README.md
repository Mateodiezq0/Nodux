# Hyperstatic_Structures

**Nodux** (p. ej. Nodux 1.0) es la aplicación de análisis: estructuras reticuladas 3D (pórticos / vigas espaciales) con modelo en JSON o YAML, resolución, visualización (matplotlib y/o PyVista + Qt) y exportación de resultados. Nombre y versión centralizados en `cli/app_info.py`.

## Inicio rápido

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

```bash
python -m cli gui
```

Otros comandos: `python -m cli run ruta\modelo.json`, `python -m cli interactive`, `python -m cli gui --ejemplo`.

Ejecutá siempre `python -m cli ...` **desde la raíz del repo** (el paquete ajusta `sys.path` solo en ese caso).

## Documentación para humanos e IA

En **[docs/ai/](docs/ai/)** hay guías cortas (setup, visión general, arquitectura, formato del modelo, GUI):

| Documento | Contenido |
|-----------|-----------|
| [docs/ai/00_SETUP_AND_ENV.md](docs/ai/00_SETUP_AND_ENV.md) | Entorno virtual, `pip install`, comandos CLI, Qt y YAML. |
| [docs/ai/01_PROJECT_OVERVIEW.md](docs/ai/01_PROJECT_OVERVIEW.md) | Qué hace el proyecto y layout de carpetas. |
| [docs/ai/02_ARCHITECTURE.md](docs/ai/02_ARCHITECTURE.md) | Flujo spec → loader → solver → export / GUI. |
| [docs/ai/03_MODEL_SPEC.md](docs/ai/03_MODEL_SPEC.md) | Claves del JSON/YAML y ejemplo en `cli/examples/`. |
| [docs/ai/04_GUI_AND_VIZ.md](docs/ai/04_GUI_AND_VIZ.md) | Vistas 3D, atajos, PyVista vs matplotlib. |

Para agentes automatizados en Cursor, ver también **[AGENTS.md](AGENTS.md)**.

## Desarrollo y tests

```bash
pip install -r requirements-dev.txt
pytest test_rigidez.py
```

Otros scripts en la raíz pueden no seguir convención `test_*` de pytest; ejecutalos con `python nombre.py` si corresponde.
