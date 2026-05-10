# GUI y visualización

## Ventana principal (Ftool)

- **Entrada**: `python -m cli gui` desde la raíz del repo ([cli/__main__.py](../../cli/__main__.py)).
- **Implementación**: [cli/gui_ftool.py](../../cli/gui_ftool.py) (`FtoolMainWindow`, PyVista embebido con `pyvistaqt.QtInteractor`).
- **Backend Qt**: se prefiere **PySide6**; si no está, se intenta **PyQt5** (misma lógica en varios `try/except`).

## Vistas del combo “Vista”

Claves internas (aprox.) y significado:

| Clave | Uso |
|-------|-----|
| `geom` | Geometría indeformada (perfiles). |
| `loads` | Cargas (puntuales, distribuidas, nodales). |
| `def` | Deformada (requiere **Analizar** antes). |
| `vy`, `vz`, `nx`, `my`, `mz`, `mx` | Diagramas de esfuerzos (con hover donde esté cableado). |

Tras editar el modelo, suele invalidarse la solución hasta volver a **Analizar**.

## Atajos útiles (no exhaustivo)

| Atajo | Acción |
|-------|--------|
| **F5** | Ejecutar análisis. |
| **G** | En vista **Deformada**, alternar mapa de color por magnitud de desplazamiento visual (`|u|`). |
| **T** | Ciclar tema del visor 3D (donde esté conectado). |
| **Escape** | Quitar resaltado de barra seleccionada (si aplica). |
| **Ctrl+Z / Ctrl+Y** | Deshacer / rehacer cambios del modelo (historial acotado). |

Leyenda en esquina: texto generado en [plot/pyvista_pestanas.py](../../plot/pyvista_pestanas.py) (`build_ftool_legend_lines`).

## PyVista vs matplotlib

- **`python -m cli run`**: usa principalmente **matplotlib** (Tk) en [plot/plot.py](../../plot/plot.py) vía `run_pipeline`.
- **GUI Ftool**: **PyVista** para el lienzo 3D; algunos diálogos pueden embeber **matplotlib** en Qt (editor de materiales / sección).

Cambios en diagramas 3D compartidos suelen tocar **tanto** la lógica geométrica en `plot/plot.py` como la rama PyVista en `plot/pyvista_pestanas.py` para mantener coherencia visual.

## Temas y estilo

- Tema claro/oscuro de la aplicación Qt: [cli/qt_app_theme.py](../../cli/qt_app_theme.py).
- Fondo y paleta del visor 3D: [cli/viewport_theme.py](../../cli/viewport_theme.py) y `viewport_style` pasado a funciones `_populate_*` en PyVista.
