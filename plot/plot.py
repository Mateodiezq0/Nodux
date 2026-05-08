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
    from mpl_toolkits.mplot3d import proj3d
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from mpl_toolkits.mplot3d.axes3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MaxNLocator = None  # type: ignore
    Patch = None  # type: ignore
    Axes3D = None  # type: ignore
    proj3d = None  # type: ignore
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


def obtener_coordenadas_barra(barra, nodos_dict: Dict, solo_nodos_dict: bool = False):
    """Obtiene las coordenadas de inicio y fin de una barra.

    Si ``solo_nodos_dict`` es True, ignora ``nodo_i_obj`` / ``nodo_f_obj`` y usa solo
    ``nodos_dict`` (útil para proxies con coordenadas deformadas).
    """
    if solo_nodos_dict:
        nodo_i = nodos_dict.get(barra.nodo_i)
        nodo_f = nodos_dict.get(barra.nodo_f)
    else:
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
            if getattr(carga, "is_distributed", False):
                # Carga distribuida: dibujar peine de flechas entre inicio y fin
                F_int = np.asarray(
                    getattr(carga, "force_global_intensity", np.zeros(3)), dtype=float
                ).ravel()[:3]
                F_mag = np.linalg.norm(F_int)
                if F_mag <= tol:
                    continue
                F_dir = F_int / F_mag
                p_start = np.array(
                    [float(getattr(carga, "x", 0.0)),
                     float(getattr(carga, "y", 0.0)),
                     float(getattr(carga, "z", 0.0))], dtype=float
                )
                p_end = np.array(
                    [float(getattr(carga, "x_f", p_start[0])),
                     float(getattr(carga, "y_f", p_start[1])),
                     float(getattr(carga, "z_f", p_start[2]))], dtype=float
                )
                n_arrows = max(3, min(9, int(np.linalg.norm(p_end - p_start) / (longitud_vector * 0.7)) + 3))
                arrow_pts = [p_start + t * (p_end - p_start) for t in np.linspace(0, 1, n_arrows)]
                tips = []
                for pt in arrow_pts:
                    P = _punto_carga_banda_superior_ipn(barra, pt, altura_perfil_h)
                    tail = P - longitud_vector * F_dir
                    ax.quiver(
                        tail[0], tail[1], tail[2],
                        F_dir[0], F_dir[1], F_dir[2],
                        length=longitud_vector, normalize=True,
                        color=color, linewidth=1.35, arrow_length_ratio=0.22,
                    )
                    extras.append(P.copy())
                    extras.append(tail.copy())
                    tips.append(P.copy())
                # Línea superior que une las puntas (indica carga continua)
                if len(tips) >= 2:
                    tp = np.array(tips, dtype=float)
                    ax.plot(tp[:, 0], tp[:, 1], tp[:, 2], color=color, linewidth=1.2)
            else:
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

    color_fuerza_nodal = "#c83232"
    color_momento_nodal = "#7a3fbf"

    if cargas_nodales:
        for cn in cargas_nodales:
            nid = getattr(cn, "nodo_id", None)
            if nid is None:
                continue
            nodo = nodos_dict.get(nid)
            if nodo is None:
                continue
            P = np.array([float(nodo.x), float(nodo.y), float(nodo.z)], dtype=float)
            # --- Fuerzas (fx, fy, fz) — flecha roja simple ---
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
                    tail[0], tail[1], tail[2],
                    u[0], u[1], u[2],
                    length=longitud_vector,
                    normalize=True,
                    color=color_fuerza_nodal,
                    linewidth=1.7,
                    arrow_length_ratio=0.28,
                )
                extras.append(P.copy())
                extras.append(tail.copy())
            # --- Momentos (mx, my, mz) — flecha doble cabeza violeta ---
            M = np.array(
                [
                    float(getattr(cn, "mx", 0.0) or 0.0),
                    float(getattr(cn, "my", 0.0) or 0.0),
                    float(getattr(cn, "mz", 0.0) or 0.0),
                ],
                dtype=float,
            )
            for i in range(3):
                if abs(M[i]) <= tol:
                    continue
                u = np.zeros(3, dtype=float)
                u[i] = float(np.sign(M[i]))
                tail = P - longitud_vector * u
                # Cabeza principal
                ax.quiver(
                    tail[0], tail[1], tail[2],
                    u[0], u[1], u[2],
                    length=longitud_vector,
                    normalize=True,
                    color=color_momento_nodal,
                    linewidth=1.7,
                    arrow_length_ratio=0.28,
                )
                # Segunda cabeza (a 0.18 del extremo) → doble cabeza convención vectores de par
                tail2 = P - 0.82 * longitud_vector * u
                ax.quiver(
                    tail2[0], tail2[1], tail2[2],
                    u[0], u[1], u[2],
                    length=0.18 * longitud_vector,
                    normalize=True,
                    color=color_momento_nodal,
                    linewidth=1.7,
                    arrow_length_ratio=0.55,
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


def _diagrama_corte_local_barra(barra: Any, idx_corte: int) -> tuple:
    """
    Diagrama de la componente local idx_corte del esfuerzo cortante/normal:
      idx 0 = N_x,  1 = V_y,  2 = V_z.

    Cargas puntuales → salto vertical en x_c.
    Cargas distribuidas uniformes → rampa lineal entre x_local_start y x_local_end.

    Retorna (x_plot, v_plot, L, V_i, V_f).  El diagrama es ahora lineal a trozos.
    """
    if idx_corte not in (0, 1, 2):
        raise ValueError("idx_corte debe ser 0 (N_x), 1 (V_y) o 2 (V_z)")

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
    V_i = float(si[idx_corte]) if si.size > idx_corte else 0.0
    V_f = float(sf[idx_corte]) if sf.size > idx_corte else 0.0

    # Clasificar cargas: saltos puntuales vs. rampas distribuidas
    point_eventos: List = []   # (x_c, salto)
    ramp_eventos: List = []    # (x_a, x_b, intensidad_por_unidad_longitud)

    for carga in getattr(barra, "cargas", []) or []:
        f_local = np.asarray(getattr(carga, "f_local", np.zeros(3)), dtype=float).ravel()
        q_loc = float(f_local[idx_corte]) if f_local.size > idx_corte else 0.0

        if getattr(carga, "is_distributed", False):
            x_a = float(getattr(carga, "x_local_start", 0.0))
            x_b = float(getattr(carga, "x_local_end", L))
            c_len = max(abs(x_b - x_a), 1e-12)
            q_int = q_loc / c_len  # intensidad por unidad de longitud en coord. local
            if L > 0.0:
                x_a = max(0.0, min(L, x_a))
                x_b = max(0.0, min(L, x_b))
            if x_a > x_b:
                x_a, x_b = x_b, x_a
            ramp_eventos.append((x_a, x_b, q_int))
        else:
            p = np.asarray(
                [float(getattr(carga, "x", 0.0)),
                 float(getattr(carga, "y", 0.0)),
                 float(getattr(carga, "z", 0.0))],
                dtype=float,
            )
            x_c = _coord_local_x_sobre_barra(barra, p)
            if L > 0.0:
                x_c = max(0.0, min(L, x_c))
            point_eventos.append((x_c, q_loc))

    point_eventos.sort(key=lambda t: t[0])

    # V(x) justo ANTES de cualquier salto puntual en x (incluye contribución de rampas)
    def _V_at(x_query: float) -> float:
        V = V_i
        for x_c, q_j in point_eventos:
            if x_c < x_query - 1e-10:
                V += q_j
        for x_a, x_b, q_int in ramp_eventos:
            if x_query > x_a + 1e-10:
                V += q_int * (min(x_query, x_b) - x_a)
        return V

    # Puntos de quiebre: extremos de barras, saltos puntuales y límites de rampas
    xs_set: set = {0.0, float(L)}
    for xc, _ in point_eventos:
        xs_set.add(float(xc))
    for xa, xb, _ in ramp_eventos:
        xs_set.add(float(xa))
        xs_set.add(float(xb))
    breakpoints = sorted(xs_set)

    x_plot: List[float] = []
    v_plot: List[float] = []

    for xk in breakpoints:
        V_before = _V_at(xk)
        jumps = sum(q_j for xc, q_j in point_eventos if abs(xc - xk) < 1e-10)

        if abs(xk - float(L)) < 1e-10:
            # Cierre: V justo antes del apoyo final + reacción de apoyo
            V_with_jumps = V_before + jumps
            x_plot.extend([xk, xk])
            v_plot.extend([V_with_jumps, V_with_jumps + V_f])
        else:
            x_plot.append(xk)
            v_plot.append(V_before)
            if abs(jumps) > 1e-12:
                x_plot.append(xk)
                v_plot.append(V_before + jumps)

    return np.asarray(x_plot, dtype=float), np.asarray(v_plot, dtype=float), L, V_i, V_f


def _diagrama_corte_vy_local_barra(barra: Any) -> tuple:
    """Compatibilidad: equivale a idx_corte=1 (V_y)."""
    return _diagrama_corte_local_barra(barra, 1)


def _world_to_canvas_pixels_3d(ax, wx: float, wy: float, wz: float):
    """
    Proyecta un punto 3D de datos a píxeles de pantalla del canvas (misma
    convención que MouseEvent.x / .y) para comparar distancia al cursor.
    """
    if proj3d is None or Axes3D is None or not isinstance(ax, Axes3D):
        return None
    if getattr(ax, "M", None) is None:
        ax.M = ax.get_proj()
    xs, ys, zs, vis = proj3d._proj_transform_clip(
        [float(wx)],
        [float(wy)],
        [float(wz)],
        ax.M,
        ax._focal_length,
    )
    v0 = np.asarray(vis).ravel()[0]
    if hasattr(v0, "mask") and np.ma.getmask(v0):
        return None
    if not bool(v0):
        return None
    return ax.transData.transform((float(xs[0]), float(ys[0])))


# Colores globales del diagrama (valor mostrado): positivo / negativo / ~cero
_DIAG_COLOR_POS = "#27ae60"
_DIAG_COLOR_NEG = "#e74c3c"
_DIAG_COLOR_ZERO = "#95a5a6"


def _rellenar_franjas_diagrama_corte_3d(
    ax,
    origin: np.ndarray,
    x_local: np.ndarray,
    offset_local: np.ndarray,
    x_b: np.ndarray,
    v_b: np.ndarray,
    escala_v: float,
    color_pos: str = _DIAG_COLOR_POS,
    color_neg: str = _DIAG_COLOR_NEG,
    color_zero: str = _DIAG_COLOR_ZERO,
    alpha: float = 0.42,
) -> List[np.ndarray]:
    """
    Rellena el área entre la línea base (corte=0) y el diagrama en el plano
    X–offset (offset = y_local para V_y y N_x, z_local para V_z).
    Una cara por tramo horizontal; color según el signo del valor constante.
    """
    extras: List[np.ndarray] = []
    if x_b.size < 2:
        return extras
    caras_pos: List = []
    caras_neg: List = []
    caras_zero: List = []
    atol = 1e-9 * max(1.0, float(np.max(np.abs(v_b))) if v_b.size else 1.0)

    for k in range(len(x_b) - 1):
        xa, xb = float(x_b[k]), float(x_b[k + 1])
        va, vb = float(v_b[k]), float(v_b[k + 1])
        if abs(xb - xa) < 1e-12:
            continue
        base_a = origin + xa * x_local
        base_b = origin + xb * x_local
        top_a = base_a + va * escala_v * offset_local
        top_b = base_b + vb * escala_v * offset_local

        # Cruce de cero: dividir en dos triángulos
        if va * vb < 0 and abs(vb - va) > 1e-18:
            x_m = xa + abs(va) / abs(vb - va) * (xb - xa)
            x_m = float(np.clip(x_m, min(xa, xb), max(xa, xb)))
            base_m = origin + x_m * x_local
            tri1 = [base_a, base_m, top_a]   # lado de va
            tri2 = [base_m, base_b, top_b]   # lado de vb
            extras.extend([base_a, base_m, top_a, base_m, base_b, top_b])
            if abs(va) <= atol:
                caras_zero.append(tri1)
            elif va > 0:
                caras_pos.append(tri1)
            else:
                caras_neg.append(tri1)
            if abs(vb) <= atol:
                caras_zero.append(tri2)
            elif vb > 0:
                caras_pos.append(tri2)
            else:
                caras_neg.append(tri2)
        else:
            # Trapezoide sin cruce de cero (incluye el caso constante)
            quad = [base_a, base_b, top_b, top_a]
            extras.extend(quad)
            v_avg = (va + vb) / 2.0
            if abs(v_avg) <= atol:
                caras_zero.append(quad)
            elif v_avg > 0:
                caras_pos.append(quad)
            else:
                caras_neg.append(quad)

    for caras, col in (
        (caras_pos, color_pos),
        (caras_neg, color_neg),
        (caras_zero, color_zero),
    ):
        if not caras:
            continue
        poly = Poly3DCollection(
            caras,
            facecolors=col,
            edgecolors=col,
            linewidths=0.35,
            alpha=alpha,
        )
        ax.add_collection3d(poly)
    return extras


def _plot_polilinea_diagrama_coloreada(
    ax,
    pts: np.ndarray,
    v_vals: np.ndarray,
    color_pos: str = _DIAG_COLOR_POS,
    color_neg: str = _DIAG_COLOR_NEG,
    color_zero: str = _DIAG_COLOR_ZERO,
    lw: float = 2.0,
) -> None:
    """
    Dibuja la polilínea del diagrama coloreando por signo del valor mostrado.
    Si un segmento une valores de signo opuesto, parte en el cruce con el eje base.
    """
    vmax = float(np.max(np.abs(v_vals))) if v_vals.size else 1.0
    eps = max(1e-15, 1e-12 * max(vmax, 1.0))

    def color_for(v: float) -> str:
        if v > eps:
            return color_pos
        if v < -eps:
            return color_neg
        return color_zero

    n = len(pts)
    for k in range(n - 1):
        p0 = pts[k]
        p1 = pts[k + 1]
        v0 = float(v_vals[k])
        v1 = float(v_vals[k + 1])

        if abs(v0 - v1) > eps and v0 * v1 < 0:
            denom = v0 - v1
            if abs(denom) > 1e-18:
                t = v0 / denom
                t = max(0.0, min(1.0, t))
                pm = p0 + t * (p1 - p0)
                ax.plot(
                    [p0[0], pm[0]],
                    [p0[1], pm[1]],
                    [p0[2], pm[2]],
                    color=color_for(v0),
                    linewidth=lw,
                )
                ax.plot(
                    [pm[0], p1[0]],
                    [pm[1], p1[1]],
                    [pm[2], p1[2]],
                    color=color_for(v1),
                    linewidth=lw,
                )
                continue

        if abs(v0 - v1) <= eps:
            c = color_for(v0)
        else:
            c = color_for(0.5 * (v0 + v1))
        ax.plot(
            [p0[0], p1[0]],
            [p0[1], p1[1]],
            [p0[2], p1[2]],
            color=c,
            linewidth=lw,
        )


def dibujo_esfuerzos_corte(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    escala_diagrama_corte: float = 1.0,
    corte: str = "vy",
    ax=None,
):
    """
    **Esfuerzos de corte** — estructura 3D + diagrama de corte local sobre cada barra.

    - ``corte="vy"``: V_y (2.º componente Fy del vector local), plano X–Y local.
    - ``corte="vz"``: V_z (3.er componente Fz del vector local), plano X–Z local.
    - ``corte="nx"``: N_x — esfuerzo normal (1.er componente Fx local); el dibujo
      usa solo efectos visuales con **signo invertido** respecto al valor fisico
      (compresión → lado negativo del diagrama, tracción → positivo).

    Parameters
    ----------
    escala_diagrama_corte : float
        Factor multiplicativo sobre la escala gráfica del diagrama (ampliar > 1,
        achicar < 1). No altera los valores físicos, solo el dibujo.
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib no está instalado. Ejecuta: pip install matplotlib")

    if corte not in ("vy", "vz", "nx"):
        raise ValueError('corte debe ser "vy", "vz" o "nx"')
    idx_corte = {"vy": 1, "vz": 2, "nx": 0}[corte]

    h, b, tw, tf = _dims_perfil_ipn(ipn_dims, escala_seccion)

    created_fig = False
    if ax is None:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        created_fig = True

    all_points = _dibujo_geometria_estructura(
        ax, nodos, barras, nodos_dict, h, b, tw, tf, mostrar_ejes_locales, leyenda_vinculos=False
    )

    # Puntos para tooltip al pasar el mouse (se usa desde la pestaña Tk)
    ax._shear_hover_points = []  # type: ignore[attr-defined]

    # Escala grafica del corte para que se vea sobre la geometria.
    max_abs_v_global = 0.0
    Ls = []
    for barra in barras:
        x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, idx_corte)
        if x_b.size > 0:
            v_escala = -v_b if corte == "nx" else v_b
            max_abs_v_global = max(max_abs_v_global, float(np.max(np.abs(v_escala))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_v_global) if max_abs_v_global > 1e-12 else 1.0
    escala_v = escala_base * float(escala_diagrama_corte)

    color_pos = _DIAG_COLOR_POS
    color_neg = _DIAG_COLOR_NEG
    color_zero = _DIAG_COLOR_ZERO
    color_base = "#7f8c8d"

    if corte == "vy":
        lbl_diag = "Vy"
        titulo_ax = "Esfuerzos de corte — V_y local (verde + / rojo −)"
    elif corte == "vz":
        lbl_diag = "Vz"
        titulo_ax = "Esfuerzos de corte — V_z local (verde + / rojo −)"
    else:
        lbl_diag = "Nx"
        titulo_ax = "Esfuerzo normal N_x local — conv. visual (verde + / rojo −)"

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        y_local = np.asarray(getattr(barra, "y_local", [0.0, 1.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        nrm_x = max(np.linalg.norm(x_local), 1e-12)
        nrm_y = max(np.linalg.norm(y_local), 1e-12)
        nrm_z = max(np.linalg.norm(z_local), 1e-12)
        x_local = x_local / nrm_x
        y_local = y_local / nrm_y
        z_local = z_local / nrm_z

        # N_x se dibuja en plano X–Y local (misma geometría que V_y), separado por color
        offset_local = y_local if corte in ("vy", "nx") else z_local

        x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, idx_corte)
        if x_b.size == 0:
            continue

        v_dib = (-v_b) if corte == "nx" else v_b

        extras_fill = _rellenar_franjas_diagrama_corte_3d(
            ax,
            origin,
            x_local,
            offset_local,
            x_b,
            v_dib,
            escala_v,
            color_pos=color_pos,
            color_neg=color_neg,
            color_zero=color_zero,
        )
        all_points.extend(extras_fill)

        pts = np.array(
            [origin + xb * x_local + (vb * escala_v) * offset_local for xb, vb in zip(x_b, v_dib)],
            dtype=float,
        )
        _plot_polilinea_diagrama_coloreada(
            ax, pts, v_dib, color_pos=color_pos, color_neg=color_neg, color_zero=color_zero, lw=2.0
        )

        def _append_hover(x_loc: float, v_val: float, pt_xyz: np.ndarray) -> None:
            ax._shear_hover_points.append(  # type: ignore[attr-defined]
                {
                    "bar_id": getattr(barra, "id", None),
                    "x_local": float(x_loc),
                    "v": float(v_val),
                    "corte": corte,
                    "pos": (float(pt_xyz[0]), float(pt_xyz[1]), float(pt_xyz[2])),
                }
            )

        for k in range(len(x_b)):
            _append_hover(float(x_b[k]), float(v_dib[k]), pts[k])

        for k in range(len(x_b) - 1):
            xa, xb = float(x_b[k]), float(x_b[k + 1])
            va, vb = float(v_dib[k]), float(v_dib[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            if not np.isclose(va, vb, rtol=1e-9, atol=1e-12 * max(1.0, abs(va), abs(vb))):
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                pt = origin + xm * x_local + va * escala_v * offset_local
                _append_hover(xm, va, pt)

        # Linea base (corte=0) sobre el eje de la barra
        base_i = origin
        base_f = origin + L * x_local
        ax.plot(
            [base_i[0], base_f[0]],
            [base_i[1], base_f[1]],
            [base_i[2], base_f[2]],
            color=color_base,
            linewidth=0.8,
            linestyle="--",
            alpha=0.7,
        )

        pm = origin + 0.5 * L * x_local
        ax.text(
            pm[0],
            pm[1],
            pm[2],
            f"{lbl_diag} B{getattr(barra, 'id', '?')}",
            fontsize=8,
            color="#2c3e50",
        )
        all_points.extend([p for p in pts])

    _ajustar_vista_bbox_3d(ax, all_points, titulo_ax)

    if Patch is not None:
        try:
            ax.legend(
                handles=[
                    Patch(facecolor="#7fb3d5", edgecolor="#1b4f72", linewidth=0.35, label="Estructura"),
                    Patch(
                        facecolor=color_pos,
                        edgecolor=color_pos,
                        linewidth=0.35,
                        label="Diagrama valor > 0",
                    ),
                    Patch(
                        facecolor=color_neg,
                        edgecolor=color_neg,
                        linewidth=0.35,
                        label="Diagrama valor < 0",
                    ),
                    Patch(
                        facecolor=color_zero,
                        edgecolor=color_zero,
                        linewidth=0.35,
                        label="Diagrama ~ 0",
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


def _diagrama_momento_my_local_barra(barra: Any) -> tuple:
    """
    Momento flector local M_y (índice 4 en [Fx,Fy,Fz,Mx,My,Mz]) a lo largo de la barra.

    Se obtiene integrando el cortante V_z (índice 2) en el mismo orden que el diagrama
    escalonado: ``M(x) = M_y,i + ∫_0^x V_z(s) ds``, equivalente a los tramos
    ``M_y + V_z·x`` y, tras cada carga puntual, la contribución adicional del salto
    de cortante (``V_z·x₁ + Q·x₂`` en la notación habitual).
    """
    if hasattr(barra, "solicitacion_extremo_de_barra_local"):
        try:
            barra.solicitacion_extremo_de_barra_local()
        except Exception:
            pass

    si = np.asarray(getattr(barra, "solicitaciones_extremo_i_local", np.zeros(6)), dtype=float).ravel()
    My_i = float(si[4]) if si.size > 4 else 0.0

    x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, 2)
    if x_b.size == 0:
        return np.array([0.0]), np.array([My_i]), float(getattr(barra, "L", 0.0) or 0.0)

    xs: List[float] = [float(x_b[0])]
    ms: List[float] = [My_i]
    M_cur = My_i
    i = 0
    n = len(x_b)
    _N_RAMP = 8  # puntos intermedios para capturar la parábola en rampas
    while i < n - 1:
        xa = float(x_b[i])
        xb = float(x_b[i + 1])
        if abs(xb - xa) < 1e-12:
            i += 1
            continue
        va = float(v_b[i])
        vb = float(v_b[i + 1])
        if not np.isclose(va, vb, rtol=1e-6, atol=1e-9 * max(1.0, abs(va), abs(vb))):
            # Segmento con rampa: M varía parabólicamente; muestrear intermedios
            M_at_xa = M_cur
            dx = xb - xa
            for k in range(1, _N_RAMP + 1):
                t = k / _N_RAMP
                xi = xa + t * dx
                # M(xi) = M(xa) + integral_xa^xi V(t) dt  (V lineal: V = va + (vb-va)/dx * (t-xa))
                M_xi = M_at_xa + va * (xi - xa) + (vb - va) / (2.0 * dx) * (xi - xa) ** 2
                xs.append(xi)
                ms.append(M_xi)
            M_cur = ms[-1]
        else:
            M_cur = M_cur + va * (xb - xa)
            xs.append(xb)
            ms.append(M_cur)
        i += 1

    return np.asarray(xs, dtype=float), np.asarray(ms, dtype=float), float(L)


def _momento_polyline_con_cruces_cero(xs: np.ndarray, ms: np.ndarray) -> tuple:
    """Inserta vértices en M=0 cuando un tramo lineal cruza el eje."""
    if xs.size < 2:
        return xs.copy(), ms.copy()
    rx: List[float] = []
    rm: List[float] = []
    for k in range(xs.size - 1):
        xa, xb = float(xs[k]), float(xs[k + 1])
        Ma, Mb = float(ms[k]), float(ms[k + 1])
        if k == 0:
            rx.append(xa)
            rm.append(Ma)
        if abs(xb - xa) < 1e-14:
            continue
        if Ma * Mb < 0 and abs(Mb - Ma) > 1e-18:
            xm = xa - Ma * (xb - xa) / (Mb - Ma)
            lo, hi = min(xa, xb), max(xa, xb)
            if lo - 1e-9 <= xm <= hi + 1e-9:
                rx.append(xm)
                rm.append(0.0)
        rx.append(xb)
        rm.append(Mb)
    return np.asarray(rx, dtype=float), np.asarray(rm, dtype=float)


def _rellenar_franjas_diagrama_momento_lineal_3d(
    ax,
    origin: np.ndarray,
    x_local: np.ndarray,
    dir_local: np.ndarray,
    xa: float,
    xb: float,
    Ma: float,
    Mb: float,
    escala_m: float,
    color_pos: str = _DIAG_COLOR_POS,
    color_neg: str = _DIAG_COLOR_NEG,
    color_zero: str = _DIAG_COLOR_ZERO,
    alpha: float = 0.42,
    sign_draw: float = -1.0,
) -> List[np.ndarray]:
    """
    Área entre la fibra de referencia y el diagrama lineal de momento en un plano local.

    ``top = base + sign_draw * M * escala_m * dir_local`` (``dir_local`` unitario).
    M_y (plano X–Z): ``sign_draw=-1``, ``dir_local=z_local`` → ``+M_y`` hacia ``−z``.
    M_z (plano X–Y): ``sign_draw=+1``, ``dir_local=y_local`` → ``+M_z`` hacia ``+y``.
    """
    extras: List[np.ndarray] = []
    if abs(xb - xa) < 1e-12:
        return extras

    vmax = max(abs(Ma), abs(Mb), 1.0)
    eps_m = max(1e-15, 1e-12 * vmax)

    def _sign_region(M: float) -> int:
        if M > eps_m:
            return 1
        if M < -eps_m:
            return -1
        return 0

    sa, sb = _sign_region(Ma), _sign_region(Mb)

    if sa * sb < 0 and abs(Mb - Ma) > 1e-18:
        xm = xa - Ma * (xb - xa) / (Mb - Ma)
        xm = float(np.clip(xm, min(xa, xb), max(xa, xb)))
        extras.extend(
            _rellenar_franjas_diagrama_momento_lineal_3d(
                ax,
                origin,
                x_local,
                dir_local,
                xa,
                xm,
                Ma,
                0.0,
                escala_m,
                color_pos=color_pos,
                color_neg=color_neg,
                color_zero=color_zero,
                alpha=alpha,
                sign_draw=sign_draw,
            )
        )
        extras.extend(
            _rellenar_franjas_diagrama_momento_lineal_3d(
                ax,
                origin,
                x_local,
                dir_local,
                xm,
                xb,
                0.0,
                Mb,
                escala_m,
                color_pos=color_pos,
                color_neg=color_neg,
                color_zero=color_zero,
                alpha=alpha,
                sign_draw=sign_draw,
            )
        )
        return extras

    Mmid = 0.5 * (Ma + Mb)
    if abs(Mmid) <= eps_m:
        col = color_zero
    elif Mmid > 0:
        col = color_pos
    else:
        col = color_neg

    base_a = origin + xa * x_local
    base_b = origin + xb * x_local
    top_a = base_a + sign_draw * Ma * escala_m * dir_local
    top_b = base_b + sign_draw * Mb * escala_m * dir_local
    quad = [base_a, base_b, top_b, top_a]
    extras.extend(quad)
    poly = Poly3DCollection(
        [quad],
        facecolors=col,
        edgecolors=col,
        linewidths=0.35,
        alpha=alpha,
    )
    ax.add_collection3d(poly)
    return extras


def dibujo_momento_my_flexion(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    escala_diagrama_momento: float = 1.0,
    ax=None,
):
    """
    **Momento flector M_y** local: diagrama en el plano **X–Z** de cada barra.

    - Valor físico M_y del vector local (tracción inferior si M_y > 0 en tu convención).
    - **Dirección gráfica:** M_y > 0 se representa en sentido **opuesto** a ``z_local``.
    - ``M(x) = M_y,i + ∫ V_z`` con el mismo V_z escalonado que el diagrama de corte.
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

    ax._shear_hover_points = []  # type: ignore[attr-defined]

    max_abs_m = 0.0
    Ls = []
    for barra in barras:
        xs, ms, L = _diagrama_momento_my_local_barra(barra)
        if xs.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(ms))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    escala_m = escala_base * float(escala_diagrama_momento)

    color_pos = _DIAG_COLOR_POS
    color_neg = _DIAG_COLOR_NEG
    color_zero = _DIAG_COLOR_ZERO
    color_base = "#7f8c8d"
    titulo_ax = "Momento M_y local — plano X–Z (+M_y → −z_local; verde + / rojo −)"

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        nrm_x = max(np.linalg.norm(x_local), 1e-12)
        nrm_z = max(np.linalg.norm(z_local), 1e-12)
        x_local = x_local / nrm_x
        z_local = z_local / nrm_z

        xs, ms, L = _diagrama_momento_my_local_barra(barra)
        if xs.size == 0:
            continue

        for k in range(xs.size - 1):
            xa, xb = float(xs[k]), float(xs[k + 1])
            Ma, Mb = float(ms[k]), float(ms[k + 1])
            extras_q = _rellenar_franjas_diagrama_momento_lineal_3d(
                ax,
                origin,
                x_local,
                z_local,
                xa,
                xb,
                Ma,
                Mb,
                escala_m,
                color_pos=color_pos,
                color_neg=color_neg,
                color_zero=color_zero,
            )
            all_points.extend(extras_q)

        px, pm = _momento_polyline_con_cruces_cero(xs, ms)
        pts = np.array(
            [origin + xv * x_local - mv * escala_m * z_local for xv, mv in zip(px, pm)],
            dtype=float,
        )
        _plot_polilinea_diagrama_coloreada(
            ax, pts, pm, color_pos=color_pos, color_neg=color_neg, color_zero=color_zero, lw=2.0
        )

        def _append_hover(x_loc: float, M_val: float, pt_xyz: np.ndarray) -> None:
            ax._shear_hover_points.append(  # type: ignore[attr-defined]
                {
                    "bar_id": getattr(barra, "id", None),
                    "x_local": float(x_loc),
                    "v": float(M_val),
                    "corte": "my",
                    "pos": (float(pt_xyz[0]), float(pt_xyz[1]), float(pt_xyz[2])),
                }
            )

        for k in range(px.size):
            _append_hover(float(px[k]), float(pm[k]), pts[k])

        for k in range(xs.size - 1):
            xa, xb = float(xs[k]), float(xs[k + 1])
            Ma, Mb = float(ms[k]), float(ms[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                Mm = Ma + t * (Mb - Ma)
                pt = origin + xm * x_local - Mm * escala_m * z_local
                _append_hover(xm, Mm, pt)

        base_i = origin
        base_f = origin + L * x_local
        ax.plot(
            [base_i[0], base_f[0]],
            [base_i[1], base_f[1]],
            [base_i[2], base_f[2]],
            color=color_base,
            linewidth=0.8,
            linestyle="--",
            alpha=0.7,
        )

        pmid = origin + 0.5 * L * x_local
        ax.text(
            pmid[0],
            pmid[1],
            pmid[2],
            f"My B{getattr(barra, 'id', '?')}",
            fontsize=8,
            color="#2c3e50",
        )
        all_points.extend([p for p in pts])

    _ajustar_vista_bbox_3d(ax, all_points, titulo_ax)

    if Patch is not None:
        try:
            ax.legend(
                handles=[
                    Patch(facecolor="#7fb3d5", edgecolor="#1b4f72", linewidth=0.35, label="Estructura"),
                    Patch(
                        facecolor=color_pos,
                        edgecolor=color_pos,
                        linewidth=0.35,
                        label="M_y > 0",
                    ),
                    Patch(
                        facecolor=color_neg,
                        edgecolor=color_neg,
                        linewidth=0.35,
                        label="M_y < 0",
                    ),
                    Patch(
                        facecolor=color_zero,
                        edgecolor=color_zero,
                        linewidth=0.35,
                        label="M_y ~ 0",
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


def _diagrama_momento_mz_local_barra(barra: Any) -> tuple:
    """
    Momento flector local M_z (índice 5 en [Fx,Fy,Fz,Mx,My,Mz]) a lo largo de la barra.

    Los cortantes ``V_y`` vienen del mismo diagrama escalonado que ``dibujo_esfuerzos_corte``
    (``solicitaciones_extremo_*`` + saltos ``f_local[1]``). Con esa convención de vectores
    locales del modelo, la pendiente del momento cumple **``dM_z/dx = -V_y``**, es decir

    ``M_z(x) = M_{z,i} - \\int_0^x V_y(s)\\,ds``.

    Eso alinea el signo del diagrama con equilibrio tipo ``M_{z,i} + V_y\\,x_1 - Q_y\\,x_2``
    (salto de cortante por la carga puntual con el signo de ``f_local[1]``).
    """
    if hasattr(barra, "solicitacion_extremo_de_barra_local"):
        try:
            barra.solicitacion_extremo_de_barra_local()
        except Exception:
            pass

    si = np.asarray(getattr(barra, "solicitaciones_extremo_i_local", np.zeros(6)), dtype=float).ravel()
    Mz_i = float(si[5]) if si.size > 5 else 0.0

    x_b, v_b, L, _, _ = _diagrama_corte_local_barra(barra, 1)
    if x_b.size == 0:
        return np.array([0.0]), np.array([Mz_i]), float(getattr(barra, "L", 0.0) or 0.0)

    xs: List[float] = [float(x_b[0])]
    ms: List[float] = [Mz_i]
    M_cur = Mz_i
    i = 0
    n = len(x_b)
    _N_RAMP = 8  # puntos intermedios para capturar la parábola en rampas
    while i < n - 1:
        xa = float(x_b[i])
        xb = float(x_b[i + 1])
        if abs(xb - xa) < 1e-12:
            i += 1
            continue
        va = float(v_b[i])
        vb = float(v_b[i + 1])
        if not np.isclose(va, vb, rtol=1e-6, atol=1e-9 * max(1.0, abs(va), abs(vb))):
            # Segmento con rampa: M varía parabólicamente; muestrear intermedios
            M_at_xa = M_cur
            dx = xb - xa
            for k in range(1, _N_RAMP + 1):
                t = k / _N_RAMP
                xi = xa + t * dx
                # M(xi) = M(xa) - integral_xa^xi V(t) dt
                M_xi = M_at_xa - (va * (xi - xa) + (vb - va) / (2.0 * dx) * (xi - xa) ** 2)
                xs.append(xi)
                ms.append(M_xi)
            M_cur = ms[-1]
        else:
            M_cur = M_cur - va * (xb - xa)
            xs.append(xb)
            ms.append(M_cur)
        i += 1

    return np.asarray(xs, dtype=float), np.asarray(ms, dtype=float), float(L)


def dibujo_momento_mz_flexion(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    escala_diagrama_momento: float = 1.0,
    ax=None,
):
    """
    **Momento flector M_z** local: diagrama en el plano **X–Y** de cada barra.

    - Valor físico M_z del vector local (tracción **arriba** si M_z > 0 en tu convención).
    - **Dirección gráfica:** M_z > 0 se dibuja según **+y_local** (mismo sentido que Y positivo).
    - ``M_z(x) = M_{z,i} - \\int V_y`` (ver ``_diagrama_momento_mz_local_barra``): mismo escalón
      de ``V_y`` que el diagrama de corte, con **menos** integral para coincidir con
      ``dM_z/dx = -V_y`` en la convención de tus solicitaciones locales.
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

    ax._shear_hover_points = []  # type: ignore[attr-defined]

    max_abs_m = 0.0
    Ls = []
    for barra in barras:
        xs, ms, L = _diagrama_momento_mz_local_barra(barra)
        if xs.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(ms))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    escala_m = escala_base * float(escala_diagrama_momento)

    color_pos = _DIAG_COLOR_POS
    color_neg = _DIAG_COLOR_NEG
    color_zero = _DIAG_COLOR_ZERO
    color_base = "#7f8c8d"
    titulo_ax = "Momento M_z local — plano X–Y (+M_z → +y_local; verde + / rojo −)"

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        y_local = np.asarray(getattr(barra, "y_local", [0.0, 1.0, 0.0]), dtype=float).ravel()[:3]
        nrm_x = max(np.linalg.norm(x_local), 1e-12)
        nrm_y = max(np.linalg.norm(y_local), 1e-12)
        x_local = x_local / nrm_x
        y_local = y_local / nrm_y

        xs, ms, L = _diagrama_momento_mz_local_barra(barra)
        if xs.size == 0:
            continue

        for k in range(xs.size - 1):
            xa, xb = float(xs[k]), float(xs[k + 1])
            Ma, Mb = float(ms[k]), float(ms[k + 1])
            extras_q = _rellenar_franjas_diagrama_momento_lineal_3d(
                ax,
                origin,
                x_local,
                y_local,
                xa,
                xb,
                Ma,
                Mb,
                escala_m,
                color_pos=color_pos,
                color_neg=color_neg,
                color_zero=color_zero,
                sign_draw=1.0,
            )
            all_points.extend(extras_q)

        px, pm = _momento_polyline_con_cruces_cero(xs, ms)
        pts = np.array(
            [origin + xv * x_local + mv * escala_m * y_local for xv, mv in zip(px, pm)],
            dtype=float,
        )
        _plot_polilinea_diagrama_coloreada(
            ax, pts, pm, color_pos=color_pos, color_neg=color_neg, color_zero=color_zero, lw=2.0
        )

        def _append_hover(x_loc: float, M_val: float, pt_xyz: np.ndarray) -> None:
            ax._shear_hover_points.append(  # type: ignore[attr-defined]
                {
                    "bar_id": getattr(barra, "id", None),
                    "x_local": float(x_loc),
                    "v": float(M_val),
                    "corte": "mz",
                    "pos": (float(pt_xyz[0]), float(pt_xyz[1]), float(pt_xyz[2])),
                }
            )

        for k in range(px.size):
            _append_hover(float(px[k]), float(pm[k]), pts[k])

        for k in range(xs.size - 1):
            xa, xb = float(xs[k]), float(xs[k + 1])
            Ma, Mb = float(ms[k]), float(ms[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                Mm = Ma + t * (Mb - Ma)
                pt = origin + xm * x_local + Mm * escala_m * y_local
                _append_hover(xm, Mm, pt)

        base_i = origin
        base_f = origin + L * x_local
        ax.plot(
            [base_i[0], base_f[0]],
            [base_i[1], base_f[1]],
            [base_i[2], base_f[2]],
            color=color_base,
            linewidth=0.8,
            linestyle="--",
            alpha=0.7,
        )

        pmid = origin + 0.5 * L * x_local
        ax.text(
            pmid[0],
            pmid[1],
            pmid[2],
            f"Mz B{getattr(barra, 'id', '?')}",
            fontsize=8,
            color="#2c3e50",
        )
        all_points.extend([p for p in pts])

    _ajustar_vista_bbox_3d(ax, all_points, titulo_ax)

    if Patch is not None:
        try:
            ax.legend(
                handles=[
                    Patch(facecolor="#7fb3d5", edgecolor="#1b4f72", linewidth=0.35, label="Estructura"),
                    Patch(
                        facecolor=color_pos,
                        edgecolor=color_pos,
                        linewidth=0.35,
                        label="M_z > 0",
                    ),
                    Patch(
                        facecolor=color_neg,
                        edgecolor=color_neg,
                        linewidth=0.35,
                        label="M_z < 0",
                    ),
                    Patch(
                        facecolor=color_zero,
                        edgecolor=color_zero,
                        linewidth=0.35,
                        label="M_z ~ 0",
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


def _diagrama_mx_torsion_local_barra(barra: Any) -> tuple:
    """
    Diagrama escalonado del momento torsor local M_x (índice 3 en [Fx,Fy,Fz,Mx,My,Mz]).

    Parte de ``M_x`` en el nodo inicial y suma saltos por **momentos puntuales** en el tramo
    (``carga.mx_local`` en cada ``CargaPuntual``). Cierra como el cortante con el término
    del extremo final ``sf[3]`` en ``x = L``.
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
    Mi = float(si[3]) if si.size > 3 else 0.0
    Mf = float(sf[3]) if sf.size > 3 else 0.0

    eventos = []
    for carga in getattr(barra, "cargas", []) or []:
        mx_jump = float(getattr(carga, "mx_local", 0.0) or 0.0)
        p = np.asarray(
            [float(getattr(carga, "x", 0.0)), float(getattr(carga, "y", 0.0)), float(getattr(carga, "z", 0.0))],
            dtype=float,
        )
        x_c = _coord_local_x_sobre_barra(barra, p)
        if L > 0.0:
            x_c = max(0.0, min(L, x_c))
        eventos.append((x_c, mx_jump))

    eventos.sort(key=lambda t: t[0])

    x_plot = [0.0]
    m_plot = [Mi]
    M_actual = Mi

    for x_c, m_jump in eventos:
        x_plot.extend([x_c, x_c])
        m_plot.extend([M_actual, M_actual + m_jump])
        M_actual = M_actual + m_jump

    x_plot.append(L)
    m_plot.append(M_actual)

    x_plot.append(L)
    m_plot.append(M_actual + Mf)

    return np.asarray(x_plot, dtype=float), np.asarray(m_plot, dtype=float), L, Mi, Mf


def dibujo_momento_mx_torsion(
    nodos: List,
    barras: List,
    nodos_dict: Dict,
    ipn_dims: Optional[Dict[str, float]] = None,
    escala_seccion: float = 1.0,
    mostrar_ejes_locales: bool = False,
    escala_diagrama_mx: float = 1.0,
    ax=None,
):
    """
    **Momento torsor M_x** local: diagrama **escalonado** en el plano **X–Z** (eje de barra y ``z_local``).

    Origen del valor: solicitaciones locales en extremos + saltos ``mx_local`` en cargas puntuales.
    **M_x > 0** se dibuja en sentido **+z_local**; signos distintos usan los mismos colores que el resto.
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

    ax._shear_hover_points = []  # type: ignore[attr-defined]

    max_abs_m = 0.0
    Ls = []
    for barra in barras:
        x_b, m_b, L, _, _ = _diagrama_mx_torsion_local_barra(barra)
        if x_b.size > 0:
            max_abs_m = max(max_abs_m, float(np.max(np.abs(m_b))))
        if L > 0:
            Ls.append(float(L))
    L_ref = float(np.mean(Ls)) if Ls else 100.0
    escala_base = (0.18 * L_ref / max_abs_m) if max_abs_m > 1e-12 else 1.0
    escala_m = escala_base * float(escala_diagrama_mx)

    color_pos = _DIAG_COLOR_POS
    color_neg = _DIAG_COLOR_NEG
    color_zero = _DIAG_COLOR_ZERO
    color_base = "#7f8c8d"
    titulo_ax = "Momento torsor M_x — plano X–Z (+M_x → +z_local; verde + / rojo −)"

    for barra in barras:
        coord_i, coord_f = obtener_coordenadas_barra(barra, nodos_dict)
        if coord_i is None or coord_f is None:
            continue
        if hasattr(barra, "asegurar_terna_ejes_locales"):
            barra.asegurar_terna_ejes_locales()

        origin = np.asarray(coord_i, dtype=float)
        x_local = np.asarray(getattr(barra, "x_local", [1.0, 0.0, 0.0]), dtype=float).ravel()[:3]
        z_local = np.asarray(getattr(barra, "z_local", [0.0, 0.0, 1.0]), dtype=float).ravel()[:3]
        nrm_x = max(np.linalg.norm(x_local), 1e-12)
        nrm_z = max(np.linalg.norm(z_local), 1e-12)
        x_local = x_local / nrm_x
        z_local = z_local / nrm_z

        offset_local = z_local

        x_b, m_b, L, _, _ = _diagrama_mx_torsion_local_barra(barra)
        if x_b.size == 0:
            continue

        m_dib = m_b

        extras_fill = _rellenar_franjas_diagrama_corte_3d(
            ax,
            origin,
            x_local,
            offset_local,
            x_b,
            m_dib,
            escala_m,
            color_pos=color_pos,
            color_neg=color_neg,
            color_zero=color_zero,
        )
        all_points.extend(extras_fill)

        pts = np.array(
            [origin + xb * x_local + (vb * escala_m) * offset_local for xb, vb in zip(x_b, m_dib)],
            dtype=float,
        )
        _plot_polilinea_diagrama_coloreada(
            ax, pts, m_dib, color_pos=color_pos, color_neg=color_neg, color_zero=color_zero, lw=2.0
        )

        def _append_hover(x_loc: float, m_val: float, pt_xyz: np.ndarray) -> None:
            ax._shear_hover_points.append(  # type: ignore[attr-defined]
                {
                    "bar_id": getattr(barra, "id", None),
                    "x_local": float(x_loc),
                    "v": float(m_val),
                    "corte": "mx",
                    "pos": (float(pt_xyz[0]), float(pt_xyz[1]), float(pt_xyz[2])),
                }
            )

        for k in range(len(x_b)):
            _append_hover(float(x_b[k]), float(m_dib[k]), pts[k])

        for k in range(len(x_b) - 1):
            xa, xb = float(x_b[k]), float(x_b[k + 1])
            va, vb = float(m_dib[k]), float(m_dib[k + 1])
            if abs(xb - xa) < 1e-12:
                continue
            if not np.isclose(va, vb, rtol=1e-9, atol=1e-12 * max(1.0, abs(va), abs(vb))):
                continue
            for t in (0.25, 0.5, 0.75):
                xm = xa + t * (xb - xa)
                pt = origin + xm * x_local + va * escala_m * offset_local
                _append_hover(xm, va, pt)

        base_i = origin
        base_f = origin + L * x_local
        ax.plot(
            [base_i[0], base_f[0]],
            [base_i[1], base_f[1]],
            [base_i[2], base_f[2]],
            color=color_base,
            linewidth=0.8,
            linestyle="--",
            alpha=0.7,
        )

        pm = origin + 0.5 * L * x_local
        ax.text(
            pm[0],
            pm[1],
            pm[2],
            f"Mx B{getattr(barra, 'id', '?')}",
            fontsize=8,
            color="#2c3e50",
        )
        all_points.extend([p for p in pts])

    _ajustar_vista_bbox_3d(ax, all_points, titulo_ax)

    if Patch is not None:
        try:
            ax.legend(
                handles=[
                    Patch(facecolor="#7fb3d5", edgecolor="#1b4f72", linewidth=0.35, label="Estructura"),
                    Patch(
                        facecolor=color_pos,
                        edgecolor=color_pos,
                        linewidth=0.35,
                        label="M_x > 0",
                    ),
                    Patch(
                        facecolor=color_neg,
                        edgecolor=color_neg,
                        linewidth=0.35,
                        label="M_x < 0",
                    ),
                    Patch(
                        facecolor=color_zero,
                        edgecolor=color_zero,
                        linewidth=0.35,
                        label="M_x ~ 0",
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
                    label="Fuerza en barra (global X/Y/Z)",
                )
            )
        if cargas_nodales and any(
            any(abs(float(getattr(cn, a, 0) or 0)) > 1e-12 for a in ("fx", "fy", "fz"))
            for cn in cargas_nodales
        ):
            handles.append(
                Patch(facecolor="#c83232", edgecolor="#c83232", linewidth=0.35,
                      label="Fuerza en nodo (F, roja)")
            )
        if cargas_nodales and any(
            any(abs(float(getattr(cn, a, 0) or 0)) > 1e-12 for a in ("mx", "my", "mz"))
            for cn in cargas_nodales
        ):
            handles.append(
                Patch(facecolor="#7a3fbf", edgecolor="#7a3fbf", linewidth=0.35,
                      label="Momento en nodo (M, doble cabeza violeta)")
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
    titulo_app: str = "Dibujos — Estructura, Fuerzas, V_y, V_z, N_x, M_y, M_z y M_x",
):
    """
    Una sola ventana con pestañas: **Dibujo_Estructura**, **Dibujo_Fuerzas**,
    **Corte V_y**, **Corte V_z**, **N_x**, **Momento M_y**, **Momento M_z** y **Momento M_x**
    (Tkinter + matplotlib).

    Si Tkinter o el backend embebido no están disponibles, cae a ventanas
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
        fig_cy, _ = dibujo_esfuerzos_corte(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_corte=escala_diagrama_corte,
            corte="vy",
        )
        if fig_cy is not None:
            plt.show()
        fig_cz, _ = dibujo_esfuerzos_corte(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_corte=escala_diagrama_corte,
            corte="vz",
        )
        if fig_cz is not None:
            plt.show()
        fig_cn, _ = dibujo_esfuerzos_corte(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_corte=escala_diagrama_corte,
            corte="nx",
        )
        if fig_cn is not None:
            plt.show()
        fig_my, _ = dibujo_momento_my_flexion(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_momento=escala_diagrama_corte,
        )
        if fig_my is not None:
            plt.show()
        fig_mz, _ = dibujo_momento_mz_flexion(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_momento=escala_diagrama_corte,
        )
        if fig_mz is not None:
            plt.show()
        fig_mtx, _ = dibujo_momento_mx_torsion(
            nodos,
            barras,
            nodos_dict,
            ipn_dims=ipn_dims,
            escala_seccion=escala_seccion,
            mostrar_ejes_locales=mostrar_ejes_locales,
            escala_diagrama_mx=escala_diagrama_corte,
        )
        if fig_mtx is not None:
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

    # Tooltip compartido entre pestañas V_y, V_z, N_x, M_y, M_z y M_x
    tooltip_win = tk.Toplevel(root)
    tooltip_win.withdraw()
    tooltip_win.overrideredirect(True)
    tooltip_win.attributes("-topmost", True)
    tooltip_label = tk.Label(
        tooltip_win,
        text="",
        relief=tk.SOLID,
        borderwidth=1,
        padx=6,
        pady=4,
        bg="#fff8dc",
        justify=tk.LEFT,
    )
    tooltip_label.pack()

    def _hide_tooltip():
        try:
            tooltip_win.withdraw()
        except Exception:
            pass

    escala_vy_var = tk.DoubleVar(value=float(escala_diagrama_corte))
    escala_vz_var = tk.DoubleVar(value=float(escala_diagrama_corte))
    escala_nx_var = tk.DoubleVar(value=float(escala_diagrama_corte))
    escala_my_var = tk.DoubleVar(value=float(escala_diagrama_corte))
    escala_mz_var = tk.DoubleVar(value=float(escala_diagrama_corte))
    escala_mx_var = tk.DoubleVar(value=float(escala_diagrama_corte))

    def _add_pestana_diagrama_corte(
        titulo_pestana: str,
        modo_corte: str,
        escala_var: Any,
        texto_escala: str,
    ) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text=titulo_pestana)
        fig = Figure(figsize=(10, 7), dpi=100)
        ax_tab = fig.add_subplot(111, projection="3d")
        canvas = FigureCanvasTkAgg(fig, master=tab)

        def _redraw():
            ax_tab.clear()
            if modo_corte == "my":
                dibujo_momento_my_flexion(
                    nodos,
                    barras,
                    nodos_dict,
                    ipn_dims=ipn_dims,
                    escala_seccion=escala_seccion,
                    mostrar_ejes_locales=mostrar_ejes_locales,
                    escala_diagrama_momento=float(escala_var.get()),
                    ax=ax_tab,
                )
            elif modo_corte == "mz":
                dibujo_momento_mz_flexion(
                    nodos,
                    barras,
                    nodos_dict,
                    ipn_dims=ipn_dims,
                    escala_seccion=escala_seccion,
                    mostrar_ejes_locales=mostrar_ejes_locales,
                    escala_diagrama_momento=float(escala_var.get()),
                    ax=ax_tab,
                )
            elif modo_corte == "mx":
                dibujo_momento_mx_torsion(
                    nodos,
                    barras,
                    nodos_dict,
                    ipn_dims=ipn_dims,
                    escala_seccion=escala_seccion,
                    mostrar_ejes_locales=mostrar_ejes_locales,
                    escala_diagrama_mx=float(escala_var.get()),
                    ax=ax_tab,
                )
            else:
                dibujo_esfuerzos_corte(
                    nodos,
                    barras,
                    nodos_dict,
                    ipn_dims=ipn_dims,
                    escala_seccion=escala_seccion,
                    mostrar_ejes_locales=mostrar_ejes_locales,
                    escala_diagrama_corte=float(escala_var.get()),
                    corte=modo_corte,
                    ax=ax_tab,
                )
            _tight_layout_o_margenes_3d(fig)
            _ocultar_ticklabels_mpl3d_borde(ax_tab)
            canvas.draw_idle()

        ctrl = ttk.Frame(tab)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)
        ttk.Label(ctrl, text=texto_escala).pack(side=tk.LEFT, padx=(0, 8))
        lbl_val = ttk.Label(ctrl, width=6)

        def _actualizar_lbl(_arg=None):
            lbl_val.config(text=f"{float(escala_var.get()):.2f}")

        sc = ttk.Scale(
            ctrl,
            from_=0.2,
            to=10.0,
            orient=tk.HORIZONTAL,
            variable=escala_var,
            command=lambda _v: _actualizar_lbl(),
        )
        sc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        lbl_val.pack(side=tk.RIGHT)

        def _redraw_al_soltar(_evt=None):
            _redraw()
            _actualizar_lbl()

        sc.bind("<ButtonRelease-1>", _redraw_al_soltar)

        if modo_corte == "vy":
            etiqueta_v = "V_y"
        elif modo_corte == "vz":
            etiqueta_v = "V_z"
        elif modo_corte == "nx":
            etiqueta_v = "N_x"
        elif modo_corte == "my":
            etiqueta_v = "M_y"
        elif modo_corte == "mz":
            etiqueta_v = "M_z"
        elif modo_corte == "mx":
            etiqueta_v = "M_x"
        else:
            etiqueta_v = "?"

        def _on_hover(event):
            if event.inaxes != ax_tab:
                _hide_tooltip()
                return
            pts_hover = getattr(ax_tab, "_shear_hover_points", None) or []
            if not pts_hover:
                _hide_tooltip()
                return
            mx, my = float(event.x), float(event.y)
            best = None
            best_d = 28.0
            for p in pts_hover:
                wx, wy, wz = p["pos"]
                pr = _world_to_canvas_pixels_3d(ax_tab, wx, wy, wz)
                if pr is None:
                    continue
                px, py = float(pr[0]), float(pr[1])
                d = float(np.hypot(px - mx, py - my))
                if d < best_d:
                    best_d = d
                    best = p
            if best is None:
                _hide_tooltip()
                return
            v_val = float(best.get("v", best.get("vy", 0.0)))
            if modo_corte == "nx":
                sufijo = " (conv. visual: compresión → −, tracción → +)"
            elif modo_corte == "my":
                sufijo = " (local; +M_y → −z_local)"
            elif modo_corte == "mz":
                sufijo = " (local; +M_z → +y_local)"
            elif modo_corte == "mx":
                sufijo = " (local; +M_x → +z_local)"
            else:
                sufijo = " (local)"
            tooltip_label.config(
                text=(
                    f"Barra {best['bar_id']} | x_local = {best['x_local']:.2f} cm | "
                    f"{etiqueta_v} = {v_val:.6g}{sufijo}"
                )
            )
            x_root = int(root.winfo_pointerx()) + 14
            y_root = int(root.winfo_pointery()) + 14
            tooltip_win.geometry(f"+{x_root}+{y_root}")
            tooltip_win.deiconify()
            tooltip_win.lift()

        canvas.mpl_connect("motion_notify_event", _on_hover)
        canvas.mpl_connect("axes_leave_event", lambda _e: _hide_tooltip())

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        bar = ttk.Frame(tab)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        try:
            NavigationToolbar2Tk(canvas, bar)
        except Exception:
            pass

        _redraw()
        _actualizar_lbl()
        try:
            canvas.draw()
        except Exception as err:
            if "bboxes" not in str(err).lower():
                raise
            leg = ax_tab.get_legend()
            if leg is not None:
                leg.remove()
            canvas.draw()

    _add_pestana_diagrama_corte(
        "Esfuerzos de corte V_y",
        "vy",
        escala_vy_var,
        "Escala diagrama V_y:",
    )
    _add_pestana_diagrama_corte(
        "Esfuerzos de corte V_z",
        "vz",
        escala_vz_var,
        "Escala diagrama V_z:",
    )
    _add_pestana_diagrama_corte(
        "Esfuerzo normal N_x",
        "nx",
        escala_nx_var,
        "Escala diagrama N_x:",
    )
    _add_pestana_diagrama_corte(
        "Momento M_y",
        "my",
        escala_my_var,
        "Escala diagrama M_y:",
    )
    _add_pestana_diagrama_corte(
        "Momento M_z",
        "mz",
        escala_mz_var,
        "Escala diagrama M_z:",
    )
    _add_pestana_diagrama_corte(
        "Momento M_x (torsión)",
        "mx",
        escala_mx_var,
        "Escala diagrama M_x:",
    )

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

