# Arquitectura y flujo de datos

## Resumen en una frase

Un **dict** (desde JSON/YAML) pasa por el **loader** a una **`Estructura`** en memoria; el **pipeline** resuelve y opcionalmente grafica o exporta; la **GUI** reutiliza el mismo loader y el mismo solver.

## Flujo principal

```mermaid
flowchart LR
  spec[Spec dict JSON/YAML]
  load[load_spec pipeline]
  build[build_estructura_from_spec]
  est[Estructura core]
  solve[solve_estructura / calcular]
  out[Tablas export GUI]
  spec --> load --> build --> est --> solve --> out
```

1. **`load_spec(path)`** ([cli/pipeline.py](../../cli/pipeline.py)): lee archivo `.json` o `.yaml` y devuelve `dict`.
2. **`build_estructura_from_spec(spec)`** ([cli/loader.py](../../cli/loader.py)): construye `core.estructura.Estructura` (nodos, barras, cargas, materiales).
3. **`solve_estructura(est)`** ([cli/pipeline.py](../../cli/pipeline.py)): ensambla, aplica cargas y obtiene desplazamientos y solicitaciones; devuelve lista de vectores internos por barra según el diseño actual del proyecto.
4. **Export / tablas**: [cli/resultados_export.py](../../cli/resultados_export.py) arma `DataFrame` y escribe Excel/PDF/CSV.
5. **GUI Ftool**: [cli/gui_ftool.py](../../cli/gui_ftool.py) mantiene un `_spec` dict editable, reconstruye vista previa con `build_estructura_from_spec`, y tras **Analizar** usa la `Estructura` resuelta y `desplazamientos` para vistas con resultados.

## Dónde tocar qué

| Objetivo | Archivos típicos |
|----------|-------------------|
| Formato o validación del modelo | [cli/loader.py](../../cli/loader.py), spec de ejemplo en [cli/examples/](../../cli/examples/) |
| Física / matrices / DOF | [core/barra.py](../../core/barra.py), [core/estructura.py](../../core/estructura.py), resto de `core/` |
| Comando `run` / `interactive` | [cli/__main__.py](../../cli/__main__.py), [cli/pipeline.py](../../cli/pipeline.py), [cli/interactive.py](../../cli/interactive.py) |
| Ventana principal y tablas | [cli/gui_ftool.py](../../cli/gui_ftool.py), [cli/gui_viz.py](../../cli/gui_viz.py), [cli/qt_app_theme.py](../../cli/qt_app_theme.py) |
| Vista 3D PyVista (deformada, diagramas) | [plot/pyvista_pestanas.py](../../plot/pyvista_pestanas.py), [plot/pyvista_vista.py](../../plot/pyvista_vista.py) |
| Diagramas / geometría matplotlib | [plot/plot.py](../../plot/plot.py) |

## Dependencias entre capas

- **`core/`** no debe importar `plot` ni `PySide6` (mantener el núcleo usable sin GUI).
- **`cli/`** puede importar `core` y `plot` según el comando.
- **`plot/`** puede importar utilidades de `plot.plot` y objetos del dominio solo como datos (evitar ciclos con `cli`).
