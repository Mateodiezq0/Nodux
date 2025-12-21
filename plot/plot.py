import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import json
from typing import List, Dict, Optional
import importlib.util

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
    nodo_i = nodos_dict.get(barra.nodo_i)
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

