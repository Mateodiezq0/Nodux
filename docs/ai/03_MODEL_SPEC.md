# Especificación del modelo (JSON / YAML)

Referencia canónica en código: docstring de **`build_estructura_from_spec`** en [cli/loader.py](../../cli/loader.py) (lista mínima de claves y alias en español).

## Raíz del documento

Objeto JSON (o mapping YAML) con al menos:

- **`materials`**: diccionario `nombre_material → propiedades`.
- **`nodes`** (o **`nodos`**): lista de nodos.
- **`bars`** (o **`barras`**): lista de barras.

Opcionales frecuentes:

- **`default_material`**: nombre del material por defecto para barras sin `material`.
- **`loads_point`** (o **`cargas_puntuales`**): cargas puntuales sobre barras.
- **`loads_distributed`** (o **`cargas_distribuidas`**): UDL en tramo definido por coordenadas globales o locales.
- **`loads_nodal`** (o **`cargas_nodales_aplicadas`**): fuerzas/momentos en nodos.

## Nodos

Cada elemento:

- `id` (int), `x`, `y`, `z` (floats).
- **`fix`** o **`restricciones`**: lista de **6 bool** (traslaciones x,y,z y rotaciones Rx,Ry,Rz). `null`/`false` = libre.
- Opcional: **`prescribed`** / **`valores_prescritos`**: 6 floats para DOF prescritos.

## Barras

- `id`, extremos **`i`** / **`j`** (o `nodo_i` / `nodo_f`).
- Opcional: **`material`** (clave en `materials`), **`tita`** (orientación local si aplica).

## Materiales

Cada entrada en `materials` debe permitir derivar **E, A, I_y, I_z, G, J**:

- O bien escalares explícitos en el dict.
- O bien **`section`** paramétrica: se completan A, I_y, I_z, J vía [cli/section_props.py](../../cli/section_props.py) (`compute_section`).
- **G** explícito o **`nu`** para obtener `G = E/(2(1+nu))`.

Ver `_resolve_material_stiffness` en [cli/loader.py](../../cli/loader.py).

## Cargas puntuales en barra (`loads_point`)

Por carga: `bar_id` (o `barra`), posición global `x,y,z`, y componentes de fuerza (`Fx`,`Fy`,`Fz` o alias minúsculas) o **`force_global`**: `[fx,fy,fz]`.

## Cargas distribuidas

`bar_id`, intensidad vía `force_global` / componentes; tramo con `x,y,z` y `x_f,y_f,z_f` en global, o `xi_local` / `xf_local` según docstring en loader.

## Cargas nodales

`node_id` (o `nodo_id`), componentes `Fx`…`Mz` opcionales.

## Ejemplo versionado en el repo

Archivo: [cli/examples/supertesteo_like.json](../../cli/examples/supertesteo_like.json)  
Carga programática equivalente: [cli/supertesteo_spec.py](../../cli/supertesteo_spec.py).

## Convención de idioma en claves

El loader acepta **inglés** (`nodes`, `bars`, …) y varios alias en **español** (`nodos`, `barras`, …). Para nuevas features, preferir **inglés** en el spec y mantener alias solo si hay compatibilidad hacia atrás.
