# Visión general del proyecto

## Qué es

**Reticular** (repo `Hyperstatic_Structures`): análisis lineal de **pórticos / celosías 3D** por elementos tipo viga (Euler-Bernoulli), con cargas puntuales en barras, cargas distribuidas, cargas nodales y apoyos por grados de libertad.

## Unidades y convención

- En la documentación de la GUI y en muchos textos del código se habla de **coordenadas y longitudes en cm** (coherente con ejemplos y leyendas del visor).
- Fuerzas y momentos en tablas/export suelen seguir las mismas unidades que el modelo de datos del spec (revisar leyendas en diagramas: p. ej. Tn, Tn·cm donde aplique).

## Estructura de carpetas (alto nivel)

| Carpeta | Rol |
|--------|-----|
| [core/](../../core/) | Nodos, barras, cargas, ensamble y resolución del sistema (lógica de cálculo). |
| [cli/](../../cli/) | Línea de comandos, carga de JSON/YAML, pipeline, GUI Qt (`gui_ftool.py`), export a Excel/PDF/CSV. |
| [plot/](../../plot/) | Visualización matplotlib y PyVista (diagramas, deformada, utilidades VTK). |
| [io/](../../io/) | Utilidades de entrada/salida relacionadas con datos tabulares (p. ej. Excel) donde existan. |

## Archivos de modelo

- JSON/YAML describen nodos, barras, materiales y cargas. Ejemplo versionado: [cli/examples/supertesteo_like.json](../../cli/examples/supertesteo_like.json).
- La función [get_supertesteo_spec()](../../cli/supertesteo_spec.py) lee ese JSON (una sola fuente de verdad para el ejemplo `--ejemplo`).

## Qué no es (hoy)

- No es un pre/post procesador CAE genérico ni un comprobador normativo completo: el foco es **modelo → matrices → desplazamientos → esfuerzos** y **visualización/export** acotadas al reticular 3D lineal.
