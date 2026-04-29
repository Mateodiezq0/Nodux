import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import json
from typing import List, Dict, Optional, Any, Callable
import importlib.util

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from mpl_toolkits.mplot3d.axes3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MaxNLocator = None  # type: ignore
    Patch = None  # type: ignore
    Axes3D = None  # type: ignore
    MATPLOTLIB_AVAILABLE = False

# Intentar importar Plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("ADVERTENCIA: Plotly no esta instalado.")
    print("   Ejecuta: pip install plotly")

# Intentar importar Dash
try:
    from dash import Dash, dcc, html, Input, Output, callback_context
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

# Importar funciones de carga
def _cargar_datos():
    """Carga nodos y barras desde los archivos en io/"""
    ruta_excel = Path(__file__).parent.parent / "io" / "Datos_template.xlsx"
    
    # Cargar nodos
    carga_nodos_path = Path(__file__).parent.parent / "io" / "carga_nodos.py"
    spec = importlib.util.spec_from_file_location("carga_nodos", carga_nodos_path)
    carga_nodos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carga_nodos)
    nodos = carga_nodos.cargar_nodos_desde_excel(str(ruta_excel), "Nodo")
    nodos_dict = {nodo.id: nodo for nodo in nodos}
    
    # Cargar barras
    carga_barra_path = Path(__file__).parent.parent / "io" / "carga_barra.py"
    spec = importlib.util.spec_from_file_location("carga_barra", carga_barra_path)
    carga_barra = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carga_barra)
    barras = carga_barra.cargar_barras_desde_excel(str(ruta_excel), "Barra", nodos_dict, "Nodo")
    
    return nodos, nodos_dict, barras


def obtener_coordenadas_barra(barra, nodos_dict: Dict):
    """Obtiene las coordenadas de inicio y fin de una barra"""
    # Primero intentar usar los objetos nodo directamente si están disponibles
    if hasattr(barra, 'nodo_i_obj') and barra.nodo_i_obj is not None:
        nodo_i = barra.nodo_i_obj
    else:
        nodo_i = nodos_dict.get(barra.nodo_i)
    
    if hasattr(barra, 'nodo_f_obj') and barra.nodo_f_obj is not None:
        nodo_f = barra.nodo_f_obj
    else:
        nodo_f = nodos_dict.get(barra.nodo_f)
    
    if nodo_i is None or nodo_f is None:
        # Si no hay objetos nodo, intentar usar los IDs directamente
        # Esto es un fallback, idealmente deberían estar cargados
        return None, None
    
    return (nodo_i.x, nodo_i.y, nodo_i.z), (nodo_f.x, nodo_f.y, nodo_f.z)


def crear_texto_propiedades_barra(barra) -> str:
    """Crea un texto formateado con las propiedades de la barra"""
    props = [
        f"<b>Barra ID: {barra.id}</b>",
        f"Nodo Inicial: {barra.nodo_i}",
        f"Nodo Final: {barra.nodo_f}",
        f"E (Módulo Elasticidad): {barra.E} Tn/cm²",
    ]
    
    if barra.A is not None:
        props.append(f"Área (A): {barra.A} cm²")
    if barra.I_y is not None:
        props.append(f"Inercia Y: {barra.I_y} cm⁴")
    if barra.I_z is not None:
        props.append(f"Inercia Z: {barra.I_z} cm⁴")
    if barra.G is not None:
        props.append(f"Módulo Corte (G): {barra.G} Tn/cm²")
    if barra.J is not None:
        props.append(f"Módulo Torsión (J): {barra.J} cm³")
    if barra.L is not None:
        props.append(f"Longitud: {barra.L} cm")
    if barra.tita is not None:
        props.append(f"Ángulo (θ): {barra.tita}°")
    
    return "<br>".join(props)


def crear_texto_propiedades_nodo(nodo) -> str:
    """Crea un texto formateado con las propiedades del nodo"""
    props = [
        f"<b>Nodo ID: {nodo.id}</b>",
        f"Coordenadas: ({nodo.x}, {nodo.y}, {nodo.z}) cm",
    ]
    
    # Restricciones
    rest_names = ["Desp_x", "Desp_y", "Desp_z", "Rot_x", "Rot_y", "Rot_z"]
    restricciones = []
    for i, name in enumerate(rest_names):
        if nodo.restricciones[i]:
            valor = nodo.valores_prescritos[i]
            restricciones.append(f"{name}: {valor} cm")
    
    if restricciones:
        props.append("<b>Restricciones:</b>")
        props.extend(restricciones)
    
    # Reacciones si existen
    if any(r != 0.0 for r in nodo.reaccion_global):
        props.append("<b>Reacciones:</b>")
        reacciones = []
        for i, name in enumerate(rest_names):
            if nodo.reaccion_global[i] != 0.0:
                reacciones.append(f"{name}: {nodo.reaccion_global[i]:.2f}")
        if reacciones:
            props.extend(reacciones)
    
    return "<br>".join(props)


def plot_estructura_interactiva(nodos: List, barras: List, nodos_dict: Dict):
    """Crea una visualización 3D interactiva de la estructura"""
    
    # Crear figura 3D
    fig = go.Figure()
    
    # Agregar barras (líneas)
    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        
        if coord_i is None or coord_f is None:
            continue
        
        # Texto para hover
        hover_text = crear_texto_propiedades_barra(barra)
        
        # Agregar línea de la barra
        fig.add_trace(go.Scatter3d(
            x=[coord_i[0], coord_f[0]],
            y=[coord_i[1], coord_f[1]],
            z=[coord_i[2], coord_f[2]],
            mode='lines+markers',
            line=dict(
                color='#1f77b4',
                width=8
            ),
            marker=dict(
                size=4,
                color='#1f77b4'
            ),
            name=f'Barra {barra.id}',
            customdata=[barra.id],
            hovertemplate=hover_text + '<extra></extra>',
            showlegend=False
        ))
    
    # Agregar nodos (puntos)
    x_nodos = [nodo.x for nodo in nodos]
    y_nodos = [nodo.y for nodo in nodos]
    z_nodos = [nodo.z for nodo in nodos]
    ids_nodos = [nodo.id for nodo in nodos]
    
    # Determinar color según restricciones
    colores_nodos = []
    for nodo in nodos:
        if any(nodo.restricciones):
            # Nodo con restricciones - color rojo
            colores_nodos.append('#ff4444')
        else:
            # Nodo libre - color verde
            colores_nodos.append('#44ff44')
    
    # Textos hover para nodos
    hover_texts_nodos = [crear_texto_propiedades_nodo(nodo) for nodo in nodos]
    
    fig.add_trace(go.Scatter3d(
        x=x_nodos,
        y=y_nodos,
        z=z_nodos,
        mode='markers+text',
        marker=dict(
            size=12,
            color=colores_nodos,
            line=dict(width=2, color='black'),
            opacity=0.9
        ),
        text=[f'N{id}' for id in ids_nodos],
        textposition="middle center",
        textfont=dict(size=10, color='white'),
        name='Nodos',
        customdata=ids_nodos,
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=hover_texts_nodos,
        showlegend=True
    ))
    
    # Calcular rangos de los datos para agregar margen alrededor
    if nodos:
        x_min, x_max = min(x_nodos), max(x_nodos)
        y_min, y_max = min(y_nodos), max(y_nodos)
        z_min, z_max = min(z_nodos), max(z_nodos)
        
        # Calcular también rangos de las barras
        for barra in barras:
            coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
            if coord_i and coord_f:
                x_min = min(x_min, coord_i[0], coord_f[0])
                x_max = max(x_max, coord_i[0], coord_f[0])
                y_min = min(y_min, coord_i[1], coord_f[1])
                y_max = max(y_max, coord_i[1], coord_f[1])
                z_min = min(z_min, coord_i[2], coord_f[2])
                z_max = max(z_max, coord_i[2], coord_f[2])
        
        # Calcular rangos y agregar margen (20% o mínimo 0.5 unidades)
        x_range = x_max - x_min
        y_range = y_max - y_min
        z_range = z_max - z_min
        
        margin_x = max(x_range * 0.2, 0.5)
        margin_y = max(y_range * 0.2, 0.5)
        margin_z = max(z_range * 0.2, 0.5)
        
        # Asegurar que se vea el origen (0,0,0) si está cerca
        x_min_final = min(x_min - margin_x, -0.2)
        x_max_final = x_max + margin_x
        y_min_final = min(y_min - margin_y, -0.2)
        y_max_final = y_max + margin_y
        z_min_final = min(z_min - margin_z, -0.2)
        z_max_final = z_max + margin_z
    else:
        # Valores por defecto si no hay nodos
        x_min_final, x_max_final = -0.5, 3.5
        y_min_final, y_max_final = -0.5, 3.5
        z_min_final, z_max_final = -0.5, 3.5
    
    # Configurar layout con ejes según la imagen (X horizontal, Y diagonal, Z vertical)
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title=dict(text='X (cm)', font=dict(size=14, color='#2c3e50')),
                backgroundcolor='rgba(240,240,240,0.4)',
                gridcolor='rgba(100,100,100,0.9)',
                showbackground=True,
                showgrid=True,
                gridwidth=2,
                showline=True,
                linecolor='#000000',
                linewidth=3,
                showaxeslabels=True,
                showticklabels=True,
                tickfont=dict(size=11, color='#2c3e50'),
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.6)',
                zerolinewidth=2,
                nticks=10,
                range=[x_min_final, x_max_final] if nodos else None
            ),
            yaxis=dict(
                title=dict(text='Y (cm)', font=dict(size=14, color='#2c3e50')),
                backgroundcolor='rgba(240,240,240,0.4)',
                gridcolor='rgba(100,100,100,0.9)',
                showbackground=True,
                showgrid=True,
                gridwidth=2,
                showline=True,
                linecolor='#000000',
                linewidth=3,
                showaxeslabels=True,
                showticklabels=True,
                tickfont=dict(size=11, color='#2c3e50'),
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.6)',
                zerolinewidth=2,
                nticks=10,
                range=[y_min_final, y_max_final] if nodos else None
            ),
            zaxis=dict(
                title=dict(text='Z (cm)', font=dict(size=14, color='#2c3e50')),
                backgroundcolor='rgba(240,240,240,0.4)',
                gridcolor='rgba(100,100,100,0.9)',
                showbackground=True,
                showgrid=True,
                gridwidth=2,
                showline=True,
                linecolor='#000000',
                linewidth=3,
                showaxeslabels=True,
                showticklabels=True,
                tickfont=dict(size=11, color='#2c3e50'),
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.6)',
                zerolinewidth=2,
                nticks=10,
                range=[z_min_final, z_max_final] if nodos else None
            ),
            aspectmode='data',
            camera=dict(
                # Vista isométrica según Ejes.png:
                # X horizontal derecha, Y diagonal abajo-izquierda, Z vertical arriba
                eye=dict(x=1.5, y=-1.5, z=1.2),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)  # Z apunta hacia arriba
            ),
            bgcolor='rgba(255,255,255,1)',
            xaxis_showspikes=False,
            yaxis_showspikes=False,
            zaxis_showspikes=False
        ),
        hovermode='closest',
        template='plotly_white',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    return fig


def _box_faces_local(x0, x1, y0, y1, z0, z1):
    """Construye las 6 caras de un prisma rectangular en coordenadas locales."""
    p000 = np.array([x0, y0, z0], dtype=float)
    p001 = np.array([x0, y0, z1], dtype=float)
    p010 = np.array([x0, y1, z0], dtype=float)
    p011 = np.array([x0, y1, z1], dtype=float)
    p100 = np.array([x1, y0, z0], dtype=float)
    p101 = np.array([x1, y0, z1], dtype=float)
    p110 = np.array([x1, y1, z0], dtype=float)
    p111 = np.array([x1, y1, z1], dtype=float)
    return [
        [p000, p010, p011, p001],  # x = x0
        [p100, p101, p111, p110],  # x = x1
        [p000, p001, p101, p100],  # y = y0
        [p010, p110, p111, p011],  # y = y1
        [p001, p011, p111, p101],  # z = z1
        [p000, p100, p110, p010],  # z = z0
    ]


def _local_to_global(points_local, origin, x_local, y_local, z_local):
    """Transforma puntos locales (x,y,z) a coordenadas globales."""
    out = []
    for p in points_local:
        pg = origin + p[0] * x_local + p[1] * y_local + p[2] * z_local
        out.append(pg)
    return out


def _color_nodo_por_restricciones(nodo) -> str:
    """
    Color del nodo según cuántas componentes de restricción son True (6 DOF).

    - Verde: exactamente 1 True.
    - Amarillo: exactamente 3 True.
    - Rojo: exactamente 6 True (empotramiento total).
    - Gris: nodos con restricciones indefinidas (None) y/o cualquier otro caso.
    """
    raw = getattr(nodo, "restricciones", None)
    if raw is None:
        return "#7f7f7f"  # gris: restricciones no definidas

    rlist = list(raw)
    # Si hay algún None explícito, considerar nodo "indefinido" -> gris
    if any(x is None for x in rlist):
        return "#7f7f7f"

    # Normalizar a 6 entradas (faltantes se consideran False)
    while len(rlist) < 6:
        rlist.append(False)
    rlist = rlist[:6]
    n_true = sum(1 for x in rlist if x is True)
    if n_true == 1:
        return "#4daf4a"  # verde
    if n_true == 3:
        return "#ffcc00"  # amarillo (legible sobre fondo claro)
    if n_true == 6:
        return "#e41a1c"  # rojo
    return "#7f7f7f"  # gris


def _set_axes_equal_3d(ax):
    """Ajusta escalas iguales en ejes 3D de matplotlib."""
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])

    x_middle = np.mean(x_limits)
    y_middle = np.mean(y_limits)
    z_middle = np.mean(z_limits)

    plot_radius = 0.5 * max([x_range, y_range, z_range, 1e-9])
    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


def _aabb_escena_con_margen(pts: np.ndarray, margin: float = 0.03) -> tuple:
    """AABB de los puntos con margen relativo (para zoom y contención)."""
    lo = np.min(pts, axis=0)
    hi = np.max(pts, axis=0)
    span = np.maximum(hi - lo, 1e-9)
    lo = lo - margin * span
    hi = hi + margin * span
    return lo, hi


def _activar_zoom_ruedita_3d(ax, zoom_in_factor: float = 0.72, zoom_out_factor: float = 1.22):
    """
    Activa zoom in/out con la ruedita del mouse en ejes 3D de matplotlib.

    El ancla es el mismo punto 3D que matplotlib usa en la barra de estado
    (``Axes3D._calc_coord``): intersección del rayo de vista con el plano de
    eje más cercano. Luego se aplica zoom uniforme en datos alrededor de ese
    punto: lim' = A + f * (lim - A), de modo que A queda fijo en el espacio
    modelo (coherente con proyección ortográfica / uso típico de mplot3d).

    No se limita el acercamiento al AABB de la escena: podés seguir el zoom aunque
    parte del modelo quede fuera del cubo de ejes.
    """
    fig = ax.get_figure()
    if fig is None:
        return

    def _on_scroll(event):
        # Solo aplicar si el cursor está sobre este eje
        if event.inaxes != ax:
            return

        if Axes3D is None or not isinstance(ax, Axes3D):
            return

        x0, x1 = ax.get_xlim3d()
        y0, y1 = ax.get_ylim3d()
        z0, z1 = ax.get_zlim3d()

        if event.button == "up":
            factor = zoom_in_factor
        elif event.button == "down":
            factor = zoom_out_factor
        else:
            return

        # Matplotlib solo rellena invM / M tras un draw; hace falta para _calc_coord.
        if getattr(ax, "M", None) is None or getattr(ax, "invM", None) is None:
            fig.canvas.draw()

        xv = event.xdata
        yv = event.ydata
        if xv is None or yv is None or not (np.isfinite(xv) and np.isfinite(yv)):
            try:
                xv, yv = ax.transData.inverted().transform((event.x, event.y))
            except (ValueError, AttributeError):
                return

        try:
            renderer = fig.canvas.get_renderer()
            anchor = np.asarray(ax._calc_coord(float(xv), float(yv), renderer)[0], dtype=float).ravel()
        except Exception:
            return

        if anchor.size != 3 or not np.all(np.isfinite(anchor)):
            return

        ax_a, ay_a, az_a = anchor[0], anchor[1], anchor[2]

        f_use = float(factor)

        x0n = ax_a + f_use * (x0 - ax_a)
        x1n = ax_a + f_use * (x1 - ax_a)
        y0n = ay_a + f_use * (y0 - ay_a)
        y1n = ay_a + f_use * (y1 - ay_a)
        z0n = az_a + f_use * (z0 - az_a)
        z1n = az_a + f_use * (z1 - az_a)

        ax.set_xlim3d(sorted((x0n, x1n)))
        ax.set_ylim3d(sorted((y0n, y1n)))
        ax.set_zlim3d(sorted((z0n, z1n)))
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
        _actualizar_lineas_referencia_ejes_globales(ax)
        fig.canvas.draw_idle()

    # Guardar ID de conexión en el eje para evitar duplicados
    cid_prev = getattr(ax, "_scroll_zoom_cid", None)
    if cid_prev is not None:
        try:
            fig.canvas.mpl_disconnect(cid_prev)
        except Exception:
            pass
    ax._scroll_zoom_cid = fig.canvas.mpl_connect("scroll_event", _on_scroll)


def _dims_perfil_ipn(ipn_dims: Optional[Dict[str, float]], escala_seccion: float):
    dims = {
        "h": 20.0,
        "b": 10.0,
        "tw": 0.6,
        "tf": 1.0,
    }
    if ipn_dims:
        dims.update(ipn_dims)
    h = float(dims["h"]) * float(escala_seccion)
    b = float(dims["b"]) * float(escala_seccion)
    tw = float(dims["tw"]) * float(escala_seccion)
    tf = float(dims["tf"]) * float(escala_seccion)
    tw = min(tw, b)
    tf = min(tf, h / 2.0)
    return h, b, tw, tf


def _patches_leyenda_vinculos():
    if Patch is None:
        return []
    return [
        Patch(facecolor="#4daf4a", edgecolor="k", linewidth=0.35, label="1 restricción (1 True)"),
        Patch(facecolor="#ffcc00", edgecolor="k", linewidth=0.35, label="3 restricciones (3 True)"),
        Patch(facecolor="#e41a1c", edgecolor="k", linewidth=0.35, label="Empotrado total (6 True)"),
        Patch(facecolor="#7f7f7f", edgecolor="k", linewidth=0.35, label="Restricciones None / otros casos"),
    ]


def _dibujo_geometria_estructura(
    ax,
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    h: float,
    b: float,
    tw: float,
    tf: float,
    mostrar_ejes_locales: bool,
    leyenda_vinculos: bool = True,
) -> List[np.ndarray]:
    """
    Geometría compartida por Dibujo_Estructura y Dibujo_Fuerzas (IPN, ejes locales, nodos).
    Devuelve puntos 3D para calcular el encuadre.
    """
    all_points: List[np.ndarray] = []

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue

        origin = np.array(coord_i, dtype=float)
        end = np.array(coord_f, dtype=float)
        v = end - origin
        L = np.linalg.norm(v)
        if L < 1e-12:
            continue

        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        x_local = np.asarray(getattr(barra, "x_local", None), dtype=float) if getattr(barra, "x_local", None) is not None else v / L
        y_local = np.asarray(getattr(barra, "y_local", None), dtype=float) if getattr(barra, "y_local", None) is not None else np.array([0.0, 1.0, 0.0])
        z_local = np.asarray(getattr(barra, "z_local", None), dtype=float) if getattr(barra, "z_local", None) is not None else np.array([0.0, 0.0, 1.0])

        x_local = x_local / max(np.linalg.norm(x_local), 1e-12)
        y_local = y_local / max(np.linalg.norm(y_local), 1e-12)
        z_local = z_local / max(np.linalg.norm(z_local), 1e-12)

        boxes = [
            (0.0, L, -b / 2.0, b / 2.0, h / 2.0 - tf, h / 2.0),
            (0.0, L, -tw / 2.0, tw / 2.0, -h / 2.0 + tf, h / 2.0 - tf),
            (0.0, L, -b / 2.0, b / 2.0, -h / 2.0, -h / 2.0 + tf),
        ]

        for (x0, x1, y0, y1, z0, z1) in boxes:
            faces_local = _box_faces_local(x0, x1, y0, y1, z0, z1)
            faces_global = [
                _local_to_global(face, origin, x_local, y_local, z_local)
                for face in faces_local
            ]
            poly = Poly3DCollection(
                faces_global,
                facecolors="#7fb3d5",
                edgecolors="#1b4f72",
                linewidths=0.4,
                alpha=0.85,
            )
            ax.add_collection3d(poly)
            for face in faces_global:
                all_points.extend(face)

        ax.plot(
            [origin[0], end[0]],
            [origin[1], end[1]],
            [origin[2], end[2]],
            color="k",
            linewidth=0.7,
            alpha=0.7,
        )

        if mostrar_ejes_locales:
            c = origin
            s = max(h, b) * 0.8
            ax.quiver(c[0], c[1], c[2], x_local[0], x_local[1], x_local[2], length=s, color="r", normalize=True)
            ax.quiver(c[0], c[1], c[2], y_local[0], y_local[1], y_local[2], length=s, color="g", normalize=True)
            ax.quiver(c[0], c[1], c[2], z_local[0], z_local[1], z_local[2], length=s, color="b", normalize=True)

    if nodos:
        x_n = [n.x for n in nodos]
        y_n = [n.y for n in nodos]
        z_n = [n.z for n in nodos]
        colores = [_color_nodo_por_restricciones(n) for n in nodos]
        ax.scatter(x_n, y_n, z_n, c=colores, s=48, depthshade=True, edgecolors="k", linewidths=0.35)
        all_points.extend([np.array([x, y, z], dtype=float) for x, y, z in zip(x_n, y_n, z_n)])

        if leyenda_vinculos and Patch is not None:
            ax.legend(
                handles=_patches_leyenda_vinculos(),
                loc="upper right",
                fontsize=8,
                framealpha=0.9,
            )

    return all_points


def _fmt_tick_coord_eje_global(v: float, span: float) -> str:
    if not np.isfinite(v):
        return ""
    tol = max(1e-12, abs(span) * 1e-10)
    if abs(v) < tol:
        return "0"
    av = abs(v)
    if av >= 1000.0 or (av > 0.0 and av < 1e-3):
        return f"{v:.2e}"
    return f"{v:g}"


def _ticks_1d_en_intervalo(lo: float, hi: float, nbins: int = 6) -> np.ndarray:
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo or MaxNLocator is None:
        return np.asarray([lo, hi], dtype=float)
    loc = MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10])
    raw = np.asarray(loc.tick_values(lo, hi), dtype=float).ravel()
    raw = raw[(raw >= lo - 1e-12) & (raw <= hi + 1e-12)]
    if lo <= 0.0 <= hi and raw.size > 0:
        span = hi - lo
        atol = max(1e-12, 1e-7 * span)
        if not np.any(np.isclose(raw, 0.0, atol=atol)):
            raw = np.sort(np.unique(np.append(raw, 0.0)))
            raw = raw[(raw >= lo - 1e-12) & (raw <= hi + 1e-12)]
    return raw


def _aplicar_estilo_paneles_y_ticks_mpl3d_en_origen(ax) -> None:
    """
    mplot3d coloca por defecto marcas y líneas de eje en las **caras** del cubo
    de vista, lejos del (0,0,0). Ocultamos esas marcas; las medidas se dibujan
    en ``_actualizar_lineas_referencia_ejes_globales`` sobre los rayos globales.
    """
    if getattr(ax, "_global_axes_style_applied", False):
        return
    ax._global_axes_style_applied = True
    try:
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            try:
                axis.line.set_visible(False)
            except Exception:
                pass
            try:
                axis.set_tick_params(which="both", length=0, width=0, pad=0)
            except Exception:
                pass
        # No usar visible=False en ticks 3D: en backend Tk + Python 3.13 suele dejar
        # bboxes vacíos y romper canvas.draw() / NavigationToolbar. Se ocultan abajo
        # con alpha=0 en ``_ocultar_ticklabels_mpl3d_borde``.
    except Exception:
        pass
    try:
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            pane = getattr(axis, "pane", None)
            if pane is not None:
                pane.set_facecolor((0.92, 0.92, 0.94, 0.2))
                pane.set_edgecolor((0.5, 0.5, 0.52, 0.5))
    except Exception:
        pass


def _ocultar_ticklabels_mpl3d_borde(ax) -> None:
    """
    Oculta las marcas por defecto del borde del cubo 3D sin ``visible=False``,
    que en algunas versiones de matplotlib deja textos con bbox vacío y falla
    el render (p. ej. ``'bboxes' cannot be empty`` con TkAgg).
    """
    try:
        labels = (
            list(ax.get_xticklabels())
            + list(ax.get_yticklabels())
            + list(ax.get_zticklabels())
        )
        for lbl in labels:
            try:
                lbl.set_visible(True)
                lbl.set_alpha(0.0)
            except Exception:
                pass
    except Exception:
        pass


def _wireframe_caja_limites_3d(ax, xl, yl, zl) -> List[Any]:
    """Aristas del paralelepípedo de límites actuales (referencia gris)."""
    x0, x1 = float(xl[0]), float(xl[1])
    y0, y1 = float(yl[0]), float(yl[1])
    z0, z1 = float(zl[0]), float(zl[1])
    corners = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    out: List[Any] = []
    for i, j in edges:
        xi, yi, zi = corners[i]
        xj, yj, zj = corners[j]
        (ln,) = ax.plot(
            [xi, xj],
            [yi, yj],
            [zi, zj],
            color="0.55",
            ls="-",
            lw=0.75,
            alpha=0.38,
            zorder=0.02,
        )
        out.append(ln)
    return out


def _actualizar_lineas_referencia_ejes_globales(ax) -> None:
    """
    Ejes de medida **desde la terna global** en (0,0,0): líneas negras sobre los
    rayos X/Y/Z globales, valores numéricos sobre esos rayos y aristas grises
    del volumen de vista. Reemplaza las marcas en el borde del cubo de mplot3d.
    """
    for ln in getattr(ax, "_ref_global_lines", []) or []:
        try:
            ln.remove()
        except Exception:
            pass
    ax._ref_global_lines = []
    for a in getattr(ax, "_ejes_desde_origen_artists", []) or []:
        try:
            a.remove()
        except Exception:
            pass
    ax._ejes_desde_origen_artists = []

    try:
        xl = sorted(ax.get_xlim3d())
        yl = sorted(ax.get_ylim3d())
        zl = sorted(ax.get_zlim3d())
    except Exception:
        return

    sx = max(xl[1] - xl[0], 1e-9)
    sy = max(yl[1] - yl[0], 1e-9)
    sz = max(zl[1] - zl[0], 1e-9)
    off = 0.02 * max(sx, sy, sz)
    tol0 = max(1e-12, 1e-8 * max(sx, sy, sz))

    artists: List[Any] = []
    artists.extend(_wireframe_caja_limites_3d(ax, xl, yl, zl))

    (lx,) = ax.plot(
        [xl[0], xl[1]],
        [0.0, 0.0],
        [0.0, 0.0],
        color="k",
        ls="-",
        lw=1.35,
        alpha=0.92,
        zorder=0.06,
    )
    (ly,) = ax.plot(
        [0.0, 0.0],
        [yl[0], yl[1]],
        [0.0, 0.0],
        color="k",
        ls="-",
        lw=1.35,
        alpha=0.92,
        zorder=0.06,
    )
    (lz,) = ax.plot(
        [0.0, 0.0],
        [0.0, 0.0],
        [zl[0], zl[1]],
        color="k",
        ls="-",
        lw=1.35,
        alpha=0.92,
        zorder=0.06,
    )
    ax._ref_global_lines = [lx, ly, lz]

    xt = _ticks_1d_en_intervalo(xl[0], xl[1])
    yt = _ticks_1d_en_intervalo(yl[0], yl[1])
    zt = _ticks_1d_en_intervalo(zl[0], zl[1])

    origin_has_zero = (xl[0] <= 0.0 <= xl[1]) and (yl[0] <= 0.0 <= yl[1]) and (zl[0] <= 0.0 <= zl[1])
    if origin_has_zero:
        t0 = ax.text(off * 0.65, off * 0.65, off * 0.65, "0", fontsize=7, color="k", zorder=0.08)
        artists.append(t0)

    for t in xt:
        if abs(t) < tol0:
            continue
        tx = ax.text(
            float(t),
            off,
            -0.35 * off,
            _fmt_tick_coord_eje_global(float(t), sx),
            fontsize=7,
            color="k",
            ha="center",
            va="center",
            zorder=0.08,
        )
        artists.append(tx)

    for t in yt:
        if abs(t) < tol0:
            continue
        ty = ax.text(
            off,
            float(t),
            -0.35 * off,
            _fmt_tick_coord_eje_global(float(t), sy),
            fontsize=7,
            color="k",
            ha="center",
            va="center",
            zorder=0.08,
        )
        artists.append(ty)

    for t in zt:
        if abs(t) < tol0:
            continue
        tz = ax.text(
            -0.45 * off,
            -0.35 * off,
            float(t),
            _fmt_tick_coord_eje_global(float(t), sz),
            fontsize=7,
            color="k",
            ha="center",
            va="center",
            zorder=0.08,
        )
        artists.append(tz)

    tnx = ax.text(
        xl[1] - 0.02 * sx,
        1.6 * off,
        -0.6 * off,
        "X global",
        fontsize=8,
        color="k",
        ha="right",
        va="center",
        zorder=0.09,
    )
    tny = ax.text(
        1.6 * off,
        yl[1] - 0.02 * sy,
        -0.6 * off,
        "Y global",
        fontsize=8,
        color="k",
        ha="center",
        va="bottom",
        zorder=0.09,
    )
    tnz = ax.text(
        -0.55 * off,
        -0.55 * off,
        zl[1] - 0.02 * sz,
        "Z global",
        fontsize=8,
        color="k",
        ha="center",
        va="bottom",
        zorder=0.09,
    )
    artists.extend([tnx, tny, tnz])
    ax._ejes_desde_origen_artists = artists
    _ocultar_ticklabels_mpl3d_borde(ax)


def _ajustar_vista_bbox_3d(ax, all_points: List[np.ndarray], titulo: str) -> None:
    if all_points:
        pts = np.vstack(all_points)
        # Incluir siempre el origen global para encuadre y caja gris coherente con la terna
        pts = np.vstack([pts, np.zeros((1, 3), dtype=float)])
        lo_m, hi_m = _aabb_escena_con_margen(pts, margin=0.03)
        ax._scene_bbox_lo = lo_m
        ax._scene_bbox_hi = hi_m
        ax.set_xlim3d(float(lo_m[0]), float(hi_m[0]))
        ax.set_ylim3d(float(lo_m[1]), float(hi_m[1]))
        ax.set_zlim3d(float(lo_m[2]), float(hi_m[2]))
        _set_axes_equal_3d(ax)
    else:
        ax._scene_bbox_lo = None
        ax._scene_bbox_hi = None
    _aplicar_estilo_paneles_y_ticks_mpl3d_en_origen(ax)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")
    ax.set_title(titulo)
    _actualizar_lineas_referencia_ejes_globales(ax)
    try:
        ax.grid(True, alpha=0.22)
    except Exception:
        pass
    _activar_zoom_ruedita_3d(ax)


def _tight_layout_o_margenes_3d(fig) -> None:
    """
    En vistas 3D con ``Poly3DCollection`` y leyenda, ``tight_layout`` / un ``draw``
    previo pueden lanzar ``ValueError: 'bboxes' cannot be empty`` (motor de layout
    vs artistas sin bbox). Para estas figuras solo se ajustan márgenes a mano.
    """
    if fig is None:
        return
    try:
        fig.subplots_adjust(left=0.02, right=0.96, bottom=0.02, top=0.92)
    except Exception:
        pass


def _vector_global_carga_puntual(carga: Any) -> np.ndarray:
    fx = np.asarray(getattr(carga, "F_x", [0.0, 0.0, 0.0]), dtype=float).ravel()
    fy = np.asarray(getattr(carga, "F_y", [0.0, 0.0, 0.0]), dtype=float).ravel()
    fz = np.asarray(getattr(carga, "F_z", [0.0, 0.0, 0.0]), dtype=float).ravel()
    v = np.zeros(3, dtype=float)
    for a in (fx, fy, fz):
        if a.size >= 3:
            v += a[:3]
        elif a.size > 0:
            v[: a.size] += a
    return v


def _dibujo_terna_global_en_origen(ax, longitud: float) -> List[np.ndarray]:
    """
    Terna derecha X, Y, Z global dibujada en (0, 0, 0).
    Colores distintos de la terna local de barras para no confundir.
    """
    O = np.zeros(3, dtype=float)
    out: List[np.ndarray] = [O.copy()]
    specs = [
        (np.array([1.0, 0.0, 0.0], dtype=float), "#c0392b"),
        (np.array([0.0, 1.0, 0.0], dtype=float), "#27ae60"),
        (np.array([0.0, 0.0, 1.0], dtype=float), "#2980b9"),
    ]
    for u, col in specs:
        ax.quiver(
            O[0],
            O[1],
            O[2],
            u[0],
            u[1],
            u[2],
            length=longitud,
            normalize=True,
            color=col,
            linewidth=2.4,
            arrow_length_ratio=0.22,
        )
        out.append(O + u * longitud)
    return out


def _patches_leyenda_terna_global():
    if Patch is None:
        return []
    return [
        Patch(facecolor="#c0392b", edgecolor="k", linewidth=0.35, label="Global +X (origen)"),
        Patch(facecolor="#27ae60", edgecolor="k", linewidth=0.35, label="Global +Y (origen)"),
        Patch(facecolor="#2980b9", edgecolor="k", linewidth=0.35, label="Global +Z (origen)"),
    ]


def _punto_carga_banda_superior_ipn(barra: Any, P_raw: np.ndarray, altura_perfil_h: Optional[float]) -> np.ndarray:
    """
    Desplaza el punto de la carga hacia la **banda superior** del IPN:
    ``P_raw + (h/2) * z_local`` (misma convención que el dibujo del perfil).
    """
    if altura_perfil_h is None or float(altura_perfil_h) <= 0.0:
        return P_raw
    if hasattr(barra, "asegurar_terna_ejes_locales"):
        barra.asegurar_terna_ejes_locales()
    zl = getattr(barra, "z_local", None)
    if zl is None:
        return P_raw
    zl = np.asarray(zl, dtype=float).ravel()[:3]
    nrm = np.linalg.norm(zl)
    if nrm < 1e-12:
        return P_raw
    zl = zl / nrm
    return P_raw + 0.5 * float(altura_perfil_h) * zl


def _dibujo_vectores_fuerza_global(
    ax,
    barras: List,
    nodos_dict: Dict,
    cargas_nodales: Optional[List[Any]],
    longitud_vector: float,
    tol: float,
    altura_perfil_h: Optional[float] = None,
) -> List[np.ndarray]:
    """
    Fuerzas en ejes globales X,Y,Z: un quiver por componente no nula.
    Misma longitud gráfica para todas (no escala con magnitud).

    El punto de aplicación de la carga es el **extremo** de la flecha (punta);
    la cola queda en ``P - L * u`` con ``u`` el versor del sentido de la fuerza.

    En **cargas sobre barras**, la punta se muestra en la banda superior del IPN
    (desplazamiento ``h/2`` según ``z_local`` de la barra), no en el eje medio.
    """
    color = "k"
    extras: List[np.ndarray] = []

    for barra in barras:
        for carga in getattr(barra, "cargas", []) or []:
            F = _vector_global_carga_puntual(carga)
            P_raw = np.array(
                [
                    float(getattr(carga, "x", 0.0)),
                    float(getattr(carga, "y", 0.0)),
                    float(getattr(carga, "z", 0.0)),
                ],
                dtype=float,
            )
            P = _punto_carga_banda_superior_ipn(barra, P_raw, altura_perfil_h)
            for i in range(3):
                if abs(F[i]) <= tol:
                    continue
                u = np.zeros(3, dtype=float)
                u[i] = float(np.sign(F[i]))
                tail = P - longitud_vector * u
                ax.quiver(
                    tail[0],
                    tail[1],
                    tail[2],
                    u[0],
                    u[1],
                    u[2],
                    length=longitud_vector,
                    normalize=True,
                    color=color,
                    linewidth=1.35,
                    arrow_length_ratio=0.22,
                )
                extras.append(P.copy())
                extras.append(tail.copy())

    if cargas_nodales:
        for cn in cargas_nodales:
            nid = getattr(cn, "nodo_id", None)
            if nid is None:
                continue
            nodo = nodos_dict.get(nid)
            if nodo is None:
                continue
            P = np.array([float(nodo.x), float(nodo.y), float(nodo.z)], dtype=float)
            F = np.array(
                [
                    float(getattr(cn, "fx", 0.0) or 0.0),
                    float(getattr(cn, "fy", 0.0) or 0.0),
                    float(getattr(cn, "fz", 0.0) or 0.0),
                ],
                dtype=float,
            )
            for i in range(3):
                if abs(F[i]) <= tol:
                    continue
                u = np.zeros(3, dtype=float)
                u[i] = float(np.sign(F[i]))
                tail = P - longitud_vector * u
                ax.quiver(
                    tail[0],
                    tail[1],
                    tail[2],
                    u[0],
                    u[1],
                    u[2],
                    length=longitud_vector,
                    normalize=True,
                    color=color,
                    linewidth=1.35,
                    arrow_length_ratio=0.22,
                )
                extras.append(P.copy())
                extras.append(tail.copy())

    return extras


def _coord_local_x_sobre_barra(barra: Any, punto_global: np.ndarray) -> float:
    """
    Coordenada local x (desde nodo i) de un punto global proyectado sobre la barra.
    """
    if hasattr(barra, "asegurar_terna_ejes_locales"):
        barra.asegurar_terna_ejes_locales()
    ni = getattr(barra, "nodo_i_obj", None)
    xl = getattr(barra, "x_local", None)
    if ni is None or xl is None:
        return 0.0
    p_i = np.asarray([float(ni.x), float(ni.y), float(ni.z)], dtype=float)
    x_local = np.asarray(xl, dtype=float).ravel()[:3]
    nrm = np.linalg.norm(x_local)
    if nrm < 1e-12:
        return 0.0
    x_local = x_local / nrm
    return float(np.dot(np.asarray(punto_global, dtype=float) - p_i, x_local))


def _diagrama_corte_vy_local_barra(barra: Any) -> tuple:
    """
    Construye el diagrama escalonado de corte local V_y para una barra.
    Retorna (x_plot, v_plot, L, V_i, V_f).
    """
    if hasattr(barra, "solicitacion_extremo_de_barra_local"):
        try:
            barra.solicitacion_extremo_de_barra_local()
        except Exception:
            pass

    L = float(getattr(barra, "L", 0.0) or 0.0)
    if L <= 0.0 and hasattr(barra, "calcular_longitud_y_bases"):
        try:
            barra.calcular_longitud_y_bases()
            L = float(getattr(barra, "L", 0.0) or 0.0)
        except Exception:
            L = 0.0

    si = np.asarray(getattr(barra, "solicitaciones_extremo_i_local", np.zeros(6)), dtype=float).ravel()
    sf = np.asarray(getattr(barra, "solicitaciones_extremo_f_local", np.zeros(6)), dtype=float).ravel()
    V_i = float(si[1]) if si.size >= 2 else 0.0
    V_f = float(sf[1]) if sf.size >= 2 else 0.0

    eventos = []
    for carga in getattr(barra, "cargas", []) or []:
        f_local = np.asarray(getattr(carga, "f_local", np.zeros(3)), dtype=float).ravel()
        qy_local = float(f_local[1]) if f_local.size >= 2 else 0.0
        p = np.asarray(
            [float(getattr(carga, "x", 0.0)), float(getattr(carga, "y", 0.0)), float(getattr(carga, "z", 0.0))],
            dtype=float,
        )
        x_c = _coord_local_x_sobre_barra(barra, p)
        if L > 0.0:
            x_c = max(0.0, min(L, x_c))
        eventos.append((x_c, qy_local))

    eventos.sort(key=lambda t: t[0])

    x_plot = [0.0]
    v_plot = [V_i]
    V_actual = V_i

    for x_c, qy in eventos:
        x_plot.extend([x_c, x_c])
        v_plot.extend([V_actual, V_actual + qy])
        V_actual = V_actual + qy

    x_plot.append(L)
    v_plot.append(V_actual)

    # Salto final con la solicitación de extremo del nodo final (cierre de equilibrio)
    x_plot.append(L)
    v_plot.append(V_actual + V_f)

    return np.asarray(x_plot, dtype=float), np.asarray(v_plot, dtype=float), L, V_i, V_f


def _rellenar_franjas_diagrama_vy_3d(
    ax,
    origin: np.ndarray,
    x_local: np.ndarray,
    y_local: np.ndarray,
    x_b: np.ndarray,
    v_b: np.ndarray,
    escala_v: float,
    color_cara: str = "#8e44ad",
    alpha: float = 0.42,
) -> List[np.ndarray]:
    """
    Rellena con cuadriláteros el área entre la línea base (V=0) y el diagrama
    en cada tramo horizontal (corte constante).
    """
    extras: List[np.ndarray] = []
    if x_b.size < 2:
        return extras
    caras = []
    for k in range(len(x_b) - 1):
        xa, xb = float(x_b[k]), float(x_b[k + 1])
        va, vb = float(v_b[k]), float(v_b[k + 1])
        if abs(xb - xa) < 1e-12:
            continue
        if not np.isclose(va, vb, rtol=1e-9, atol=1e-12 * max(1.0, abs(va), abs(vb))):
            continue
        base_a = origin + xa * x_local
        base_b = origin + xb * x_local
        top_a = origin + xa * x_local + va * escala_v * y_local
        top_b = origin + xb * x_local + vb * escala_v * y_local
        quad = [base_a, base_b, top_b, top_a]
        caras.append(quad)
        extras.extend(quad)
    if caras:
        poly = Poly3DCollection(
            caras,
            facecolors=color_cara,
            edgecolors=color_cara,
            linewidths=0.35,
            alpha=alpha,
        )
        ax.add_collection3d(poly)
    return extras


def dibujo_esfuerzos_corte(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    escala_diagrama_corte: float = 1.0,
    ax=None,
):
    """
    **Esfuerzos de corte** — estructura 3D + diagrama V_y local sobre cada barra.
    El diagrama se dibuja en el plano local X-Y de cada elemento.

    Parameters
    ----------
    escala_diagrama_corte : float
        Factor multiplicativo sobre la escala gráfica del diagrama (ampliar > 1,
        achicar < 1). No altera los valores físicos, solo el dibujo.
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

    h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)

    created_fig = False
    if ax is None:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        created_fig = True

    all_points = _dibujo_geometria_estructura(
        ax, nodos, barras, nodos_dict, h, b, tw, tf, mostrar_ejes_locales, leyenda_vinculos=False
    )

    # Escala grafica de Vy para que se vea sobre la geometria.
    max_abs_v_global = 0.0
    Ls = []
    for barra in barras:
        x_b, v_b, L, _, _ = _diagrama_corte_vy_local_barra(barra)
        if x_b.size > 0:
            max_abs_v_global = max(max_abs_v_global, float(np.max(np.abs(v_b))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_v_global) if max_abs_v_global > 1e-12 else 1.0
    escala_v = escala_base * float(escala_diagrama_corte)

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        y_local = np.asarray(getattr(barra, "y_local", [0.0, 1.0, 0.0]), dtype=float).ravel()[:3]
        nx = max(np.linalg.norm(x_local), 1e-12)
        ny = max(np.linalg.norm(y_local), 1e-12)
        x_local = x_local / nx
        y_local = y_local / ny

        x_b, v_b, L, _, _ = _diagrama_corte_vy_local_barra(barra)
        if x_b.size == 0:
            continue

        extras_fill = _rellenar_franjas_diagrama_vy_3d(
            ax, origin, x_local, y_local, x_b, v_b, escala_v
        )
        all_points.extend(extras_fill)

        pts = np.array([origin + xb * x_local + (vb * escala_v) * y_local for xb, vb in zip(x_b, v_b)], dtype=float)
        ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], color="#5b2c6f", linewidth=2.0)

        # Linea base Vy=0 sobre el eje de la barra
        base_i = origin
        base_f = origin + L * x_local
        ax.plot(
            [base_i[0], base_f[0]],
            [base_i[1], base_f[1]],
            [base_i[2], base_f[2]],
            color="#8e44ad",
            linewidth=0.8,
            linestyle="--",
            alpha=0.7,
        )

        # Etiqueta de barra cerca del medio del diagrama
        pm = origin + 0.5 * L * x_local
        ax.text(pm[0], pm[1], pm[2], f"Vy B{getattr(barra, 'id', '?')}", fontsize=8, color="#6c3483")
        all_points.extend([p for p in pts])

    _ajustar_vista_bbox_3d(ax, all_points, "Esfuerzos de corte — V_y local sobre barras")

    if Patch is not None:
        try:
            ax.legend(
                handles=[
                    Patch(facecolor="#7fb3d5", edgecolor="#1b4f72", linewidth=0.35, label="Estructura"),
                    Patch(
                        facecolor="#8e44ad",
                        edgecolor="#6c3483",
                        linewidth=0.35,
                        label="V_y local (relleno + contorno; usa escala)",
                    ),
                ],
                loc="upper right",
                fontsize=7,
                framealpha=0.9,
            )
        except Exception:
            pass

    if created_fig:
        _tight_layout_o_margenes_3d(fig)
        return fig, ax
    return None, ax


def dibujo_estructura(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    longitud_terna_global: float = 45.0,
    ax=None,
):
    """
    **Dibujo_Estructura** — vista 3D dedicada de la malla (matplotlib).

    Incluye: perfiles IPN según terna local por barra, ejes locales opcionales,
    codificación de vínculos en nodos y **terna global** en (0,0,0).
    El encuadre incluye el origen; las marcas y la caja de ejes se referencian
    al sistema global (ver ``_ajustar_vista_bbox_3d``).

    Convención geométrica:
    - Eje local X: dirección de la barra (nodo inicial -> nodo final).
    - Sección transversal en plano local Y-Z.
    - El alto del perfil es paralelo a Z_local y el ancho a Y_local.
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

    h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)

    created_fig = False
    if ax is None:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        created_fig = True

    all_points = _dibujo_geometria_estructura(
        ax, nodos, barras, nodos_dict, h, b, tw, tf, mostrar_ejes_locales, leyenda_vinculos=False
    )
    all_points.extend(_dibujo_terna_global_en_origen(ax, float(longitud_terna_global)))

    _ajustar_vista_bbox_3d(ax, all_points, "Dibujo_Estructura — geometría, terna local y vínculos")

    if Patch is not None:
        try:
            ax.legend(
                handles=_patches_leyenda_vinculos() + _patches_leyenda_terna_global(),
                loc="upper right",
                fontsize=7,
                framealpha=0.9,
            )
        except Exception as exc:
            if "bboxes" not in str(exc).lower():
                raise

    if created_fig:
        _tight_layout_o_margenes_3d(fig)
        return fig, ax
    return None, ax


def dibujo_fuerzas(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    cargas_nodales: Optional[List[Any]] = None,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = True,
    longitud_vector: float = 45.0,
    tol_componente: float = 1e-9,
    ax=None,
):
    """
    **Dibujo_Fuerzas** — misma geometría que Dibujo_Estructura más vectores de fuerza.

    Incluye terna **global** X,Y,Z en el origen (0,0,0).
    Las fuerzas se dibujan en **negro**; la longitud en pantalla es **fija** para todas.
    La **punta** del vector coincide con el punto de aplicación: en nodos, en el nodo;
    en cargas puntuales sobre barras, en la **banda superior del IPN** (offset
    ``h/2`` en sentido ``+z_local`` desde la coordenada de la carga).

    Las fuerzas se suponen en ejes **globales** X, Y, Z (solo paralelas a esos ejes).
    El signo indica sentido.

    Fuentes de datos:
    - Cargas puntuales en ``barra.cargas`` (``F_x``, ``F_y``, ``F_z`` como en el modelo).
    - Opcional: ``cargas_nodales`` con ``fx``, ``fy``, ``fz`` en el nodo (solo traslaciones).
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

    h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)

    created_fig = False
    if ax is None:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        created_fig = True

    all_points = _dibujo_geometria_estructura(
        ax, nodos, barras, nodos_dict, h, b, tw, tf, mostrar_ejes_locales, leyenda_vinculos=False
    )
    puntos_terna_global = _dibujo_terna_global_en_origen(ax, longitud_vector)
    all_points.extend(puntos_terna_global)
    extras = _dibujo_vectores_fuerza_global(
        ax,
        barras,
        nodos_dict,
        cargas_nodales,
        longitud_vector,
        tol_componente,
        altura_perfil_h=h,
    )
    all_points.extend(extras)

    _ajustar_vista_bbox_3d(ax, all_points, "Dibujo_Fuerzas — estructura y fuerzas (global)")

    if Patch is not None:
        handles = (
            _patches_leyenda_vinculos()
            + _patches_leyenda_terna_global()
        )
        if extras:
            handles.append(
                Patch(
                    facecolor="k",
                    edgecolor="k",
                    linewidth=0.35,
                    label="Fuerza (global X/Y/Z, longitud fija)",
                )
            )
        try:
            ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.9)
        except Exception as exc:
            if "bboxes" not in str(exc).lower():
                raise

    if created_fig:
        _tight_layout_o_margenes_3d(fig)
        return fig, ax
    return None, ax


def mostrar_dibujos_matplotlib_pestanas(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    cargas_nodales: Optional[List[Any]] = None,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = True,
    longitud_vector: float = 45.0,
    escala_diagrama_corte: float = 1.0,
    titulo_app: str = "Dibujos — Dibujo_Estructura, Dibujo_Fuerzas y Esfuerzos de corte",
):
    """
    Una sola ventana con pestañas: **Dibujo_Estructura**, **Dibujo_Fuerzas** y
    **Esfuerzos de corte** (Tkinter + matplotlib).

    Si Tkinter o el backend embebido no están disponibles, cae a dos ventanas
    ``plt.show()`` seguidas.
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

    try:
        import tkinter as tk
        from tkinter import ttk
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    except Exception as exc:
        import matplotlib.pyplot as plt

        print(
            f"[AVISO] No se pudo abrir la ventana con pestañas ({exc}). "
            "Se abren dos ventanas de matplotlib seguidas."
        )
        fig_a, _ = dibujo_estructura(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            longitud_terna_global=longitud_vector,
        )
        if fig_a is not None:
            plt.show()
        fig_b, _ = dibujo_fuerzas(
            nodos,
            barras,
            nodos_dict,
            cargas_nodales=cargas_nodales,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            longitud_vector=longitud_vector,
        )
        if fig_b is not None:
            plt.show()
        fig_c, _ = dibujo_esfuerzos_corte(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_corte=escala_diagrama_corte,
        )
        if fig_c is not None:
            plt.show()
        return

    root = tk.Tk()
    root.title(titulo_app)
    root.geometry("1020x800")

    nb = ttk.Notebook(root)
    nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

    def _embed_pestana(title: str, dibujar_en_ax: Callable[[Any], None], es_3d: bool = True) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text=title)
        fig = Figure(figsize=(10, 7), dpi=100)
        ax = fig.add_subplot(111, projection="3d") if es_3d else fig.add_subplot(111)
        dibujar_en_ax(ax)
        if es_3d:
            _tight_layout_o_margenes_3d(fig)
        else:
            try:
                fig.tight_layout()
            except Exception:
                pass
        canvas = FigureCanvasTkAgg(fig, master=tab)
        try:
            canvas.draw()
        except Exception as err:
            if "bboxes" not in str(err).lower():
                raise
            leg = ax.get_legend()
            if leg is not None:
                leg.remove()
            canvas.draw()
        if es_3d:
            _ocultar_ticklabels_mpl3d_borde(ax)
        try:
            canvas.draw_idle()
        except Exception:
            pass
        bar = ttk.Frame(tab)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        try:
            NavigationToolbar2Tk(canvas, bar)
        except Exception:
            # Toolbar puede disparar el mismo fallo de bboxes al medir leyenda/ticks 3D.
            pass

    def _pest_estructura(ax):
        dibujo_estructura(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            longitud_terna_global=longitud_vector,
            ax=ax,
        )

    def _pest_fuerzas(ax):
        dibujo_fuerzas(
            nodos,
            barras,
            nodos_dict,
            cargas_nodales=cargas_nodales,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            longitud_vector=longitud_vector,
            ax=ax,
        )

    _embed_pestana("Dibujo_Estructura", _pest_estructura)
    _embed_pestana("Dibujo_Fuerzas", _pest_fuerzas)

    # Pestaña Esfuerzos de corte: escala del diagrama Vy ajustable con slider
    tab_corte = ttk.Frame(nb)
    nb.add(tab_corte, text="Esfuerzos de corte")
    fig_corte = Figure(figsize=(10, 7), dpi=100)
    ax_corte = fig_corte.add_subplot(111, projection="3d")
    canvas_corte = FigureCanvasTkAgg(fig_corte, master=tab_corte)

    escala_vy_var = tk.DoubleVar(value=float(escala_diagrama_corte))

    def _redraw_corte():
        ax_corte.clear()
        dibujo_esfuerzos_corte(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_corte=float(escala_vy_var.get()),
            ax=ax_corte,
        )
        _tight_layout_o_margenes_3d(fig_corte)
        _ocultar_ticklabels_mpl3d_borde(ax_corte)
        canvas_corte.draw_idle()

    ctrl_corte = ttk.Frame(tab_corte)
    ctrl_corte.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)
    ttk.Label(ctrl_corte, text="Escala diagrama Vy:").pack(side=tk.LEFT, padx=(0, 8))
    lbl_escala_vy = ttk.Label(ctrl_corte, width=6)

    def _actualizar_etiqueta_escala(_arg=None):
        lbl_escala_vy.config(text=f"{float(escala_vy_var.get()):.2f}")

    scale_corte = ttk.Scale(
        ctrl_corte,
        from_=0.2,
        to=10.0,
        orient=tk.HORIZONTAL,
        variable=escala_vy_var,
        command=lambda _v: _actualizar_etiqueta_escala(),
    )
    scale_corte.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    lbl_escala_vy.pack(side=tk.RIGHT)

    def _redraw_corte_al_soltar(_evt=None):
        _redraw_corte()
        _actualizar_etiqueta_escala()

    scale_corte.bind("<ButtonRelease-1>", _redraw_corte_al_soltar)

    canvas_corte.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    bar_corte = ttk.Frame(tab_corte)
    bar_corte.pack(side=tk.BOTTOM, fill=tk.X)
    try:
        NavigationToolbar2Tk(canvas_corte, bar_corte)
    except Exception:
        pass

    _redraw_corte()
    _actualizar_etiqueta_escala()
    try:
        canvas_corte.draw()
    except Exception as err:
        if "bboxes" not in str(err).lower():
            raise
        leg = ax_corte.get_legend()
        if leg is not None:
            leg.remove()
        canvas_corte.draw()

    root.mainloop()


def mostrar_propiedades_seleccionado(fig, elemento_id: int, tipo: str, nodos_dict: Dict, barras: List):
    """Muestra las propiedades del elemento seleccionado en una anotación"""
    if tipo == 'nodo':
        nodo = next((n for n in nodos_dict.values() if n.id == elemento_id), None)
        if nodo:
            texto = crear_texto_propiedades_nodo(nodo)
            fig.add_annotation(
                text=texto,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor="left", yanchor="top",
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="black",
                borderwidth=2,
                font=dict(size=12)
            )
    elif tipo == 'barra':
        barra = next((b for b in barras if b.id == elemento_id), None)
        if barra:
            texto = crear_texto_propiedades_barra(barra)
            fig.add_annotation(
                text=texto,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor="left", yanchor="top",
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="black",
                borderwidth=2,
                font=dict(size=12)
            )


def crear_app_dash(nodos: List, barras: List, nodos_dict: Dict):
    """Crea una aplicación Dash interactiva"""
    app = Dash(__name__)
    
    # Estilos CSS personalizados
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>Visualización 3D - Estructura Hiperestática</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f5f5f5;
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    fig = plot_estructura_interactiva(nodos, barras, nodos_dict)
    
    app.layout = html.Div([
        # Header minimalista
        html.Div([
            html.H1("Visualización 3D Interactiva", 
                    style={
                        'color': '#2c3e50',
                        'textAlign': 'center',
                        'margin': '0',
                        'padding': '25px 20px 10px 20px',
                        'fontSize': '2.2rem',
                        'fontWeight': '400',
                        'letterSpacing': '1px'
                    }),
            html.P(f"Estructura con {len(nodos)} nodos y {len(barras)} barras",
                   style={
                       'color': '#7f8c8d',
                       'textAlign': 'center',
                       'margin': '0',
                       'paddingBottom': '20px',
                       'fontSize': '1rem',
                       'fontWeight': '300'
                   })
        ], style={
            'background': 'white',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'marginBottom': '0'
        }),
        
        # Contenedor principal centrado
        html.Div([
            # Gráfico 3D - Ocupa todo el espacio
            html.Div([
                dcc.Graph(
                    id='estructura-3d', 
                    figure=fig, 
                    style={
                        'height': 'calc(100vh - 150px)',
                        'width': '100%'
                    },
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'estructura_3d',
                            'height': 1080,
                            'width': 1920,
                            'scale': 2
                        }
                    }
                )
            ], style={
                'width': '100%',
                'maxWidth': '100%',
                'margin': '0 auto',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'
            })
        ], style={
            'padding': '0',
            'width': '100%',
            'margin': '0 auto',
            'overflow': 'hidden'
        })
    ], style={
        'minHeight': '100vh',
        'background': '#f5f5f5',
        'margin': '0',
        'padding': '0',
        'width': '100%',
        'overflow': 'hidden'
    })
    
    return app


def main():
    """Función principal para ejecutar el visualizador"""
    if not PLOTLY_AVAILABLE:
        print("\nERROR: Plotly no esta instalado.")
        print("   Por favor, instala las dependencias necesarias:")
        print("   pip install plotly dash")
        return
    
    print("Cargando datos de la estructura...")
    nodos, nodos_dict, barras = _cargar_datos()
    
    print(f"Cargados {len(nodos)} nodos y {len(barras)} barras")
    
    if len(nodos) == 0 and len(barras) == 0:
        print("No hay datos para visualizar. Por favor, carga nodos y barras en el Excel.")
        return
    
    if DASH_AVAILABLE:
        print("Generando aplicación interactiva con Dash...")
        app = crear_app_dash(nodos, barras, nodos_dict)
        print("\n" + "="*60)
        print("Aplicación iniciada!")
        print("Abre tu navegador en: http://127.0.0.1:8050")
        print("="*60 + "\n")
        app.run(debug=True, port=8050)
    else:
        print("Generando visualización 3D básica...")
        fig = plot_estructura_interactiva(nodos, barras, nodos_dict)
        
        print("Abriendo visualización en el navegador...")
        print("\nInstrucciones:")
        print("- Pasa el mouse sobre barras o nodos para ver sus propiedades")
        print("- Usa el mouse para rotar, hacer zoom y pan en la vista 3D")
        print("- Nodos rojos tienen restricciones, nodos verdes son libres")
        print("\nPara interactividad completa con click, instala Dash:")
        print("   pip install dash")
        
        fig.show()


if __name__ == "__main__":
    main()

