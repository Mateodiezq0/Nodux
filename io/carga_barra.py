import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from core.barra import Barra
from core.nodos import Nodo
import importlib.util

# Importar carga_nodos de forma dinámica para evitar conflictos con el módulo io estándar
def _cargar_nodos_como_dict(ruta_archivo: str, nombre_hoja: str = "Nodo") -> Dict[int, Nodo]:
    """Función auxiliar para cargar nodos."""
    carga_nodos_path = Path(__file__).parent / "carga_nodos.py"
    spec = importlib.util.spec_from_file_location("carga_nodos", carga_nodos_path)
    carga_nodos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carga_nodos)
    return carga_nodos.cargar_nodos_como_dict(ruta_archivo, nombre_hoja)


def cargar_barras_desde_excel(ruta_archivo: str, nombre_hoja: str = "Barra", nodos: Optional[Dict[int, Nodo]] = None, nombre_hoja_nodos: str = "Nodo") -> List[Barra]:
    """
    Lee los datos de barras desde una hoja de Excel y genera objetos Barra.
    
    Args:
        ruta_archivo: Ruta al archivo Excel
        nombre_hoja: Nombre de la hoja que contiene los datos de barras (default: "Barra")
        nodos: Diccionario opcional de nodos indexados por id. Si es None, se cargarán automáticamente.
        nombre_hoja_nodos: Nombre de la hoja que contiene los datos de nodos (default: "Nodo")
    
    Returns:
        Lista de objetos Barra con nodo_i_obj y nodo_f_obj asignados
    """
    # Cargar nodos si no se proporcionaron
    if nodos is None:
        try:
            nodos = _cargar_nodos_como_dict(ruta_archivo, nombre_hoja_nodos)
        except Exception as e:
            print(f"Advertencia: No se pudieron cargar los nodos: {e}")
            nodos = {}
    
    # Leer la hoja de Excel
    df = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja)
    
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        return []
    
    # Obtener los nombres de columnas exactos del DataFrame
    columnas = df.columns.tolist()
    
    # Filtrar filas vacías (donde el id es NaN)
    df = df.dropna(subset=[columnas[0]])  # Eliminar filas donde 'id' es NaN
    
    # Verificar que queden datos después de filtrar
    if df.empty:
        return []
    
    # Mapeo de índices de columnas (más robusto ante problemas de codificación)
    # Columnas esperadas en orden: id, Nodo_inicial, Nodo_Final, E, A, I_x, I_y, G, J, Tita
    barras = []
    
    for idx, row in df.iterrows():
        try:
            # Campos requeridos (usando índices para evitar problemas de codificación)
            id_barra = int(row[columnas[0]])  # 'id'
            nodo_i = int(row[columnas[1]])     # 'Nodo_inicial'
            nodo_f = int(row[columnas[2]])     # 'Nodo_Final'
            E = float(row[columnas[3]])        # 'E [Módulo de elasticidad] [t/cm2]'
            
            # Campos opcionales
            A = None if pd.isna(row[columnas[4]]) else float(row[columnas[4]])  # 'A [Área]'
            I_z = None if pd.isna(row[columnas[5]]) else float(row[columnas[5]])  # 'Inercia en X [cm4]'
            I_y = None if pd.isna(row[columnas[6]]) else float(row[columnas[6]])  # 'Inercia en Y [cm4]'
            G = None if pd.isna(row[columnas[7]]) else float(row[columnas[7]])  # 'G [Módulo de elasticidad transversal] [t/cm2]'
            J = None if pd.isna(row[columnas[8]]) else float(row[columnas[8]])  # 'J [Módulo de Torsión] [cm3]'
            tita = None if pd.isna(row[columnas[9]]) else float(row[columnas[9]])  # 'Tita (Ángulo de inclinación del perfil, rota el eje "x") [grados]'
            
            # Crear objeto Barra
            barra = Barra(
                id=id_barra,
                nodo_i=nodo_i,
                nodo_f=nodo_f,
                E=E,
                A=A,
                I_y=I_y,
                I_z=I_z,
                G=G,
                J=J,
                tita=tita
            )
            
            # Asignar objetos nodo si están disponibles
            if nodo_i in nodos:
                barra.nodo_i_obj = nodos[nodo_i]
            else:
                print(f"Advertencia: Nodo inicial {nodo_i} no encontrado para la barra {id_barra}")
            
            if nodo_f in nodos:
                barra.nodo_f_obj = nodos[nodo_f]
            else:
                print(f"Advertencia: Nodo final {nodo_f} no encontrado para la barra {id_barra}")
            
            # Calcular longitud L a partir de las coordenadas de los nodos
            if barra.nodo_i_obj is not None and barra.nodo_f_obj is not None:
                # Calcular distancia euclidiana en 3D
                dx = barra.nodo_f_obj.x - barra.nodo_i_obj.x
                dy = barra.nodo_f_obj.y - barra.nodo_i_obj.y
                dz = barra.nodo_f_obj.z - barra.nodo_i_obj.z
                barra.L = np.sqrt(dx**2 + dy**2 + dz**2)
            
            barras.append(barra)
        except (ValueError, TypeError) as e:
            print(f"Error procesando fila {idx}: {e}")
            continue
    
    
    #print(barras)
    return barras


if __name__ == "__main__":
    # Ejecutar la función cuando se ejecuta el script directamente
    ruta_excel = Path(__file__).parent / "Datos_template.xlsx"
    barras = cargar_barras_desde_excel(str(ruta_excel), "Barra")

