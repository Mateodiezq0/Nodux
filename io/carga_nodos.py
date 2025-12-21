import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
from typing import List, Dict
from core.nodos import Nodo


def cargar_nodos_desde_excel(ruta_archivo: str, nombre_hoja: str = "Nodo") -> List[Nodo]:
    """
    Lee los datos de nodos desde una hoja de Excel y genera objetos Nodo.
    
    Args:
        ruta_archivo: Ruta al archivo Excel
        nombre_hoja: Nombre de la hoja que contiene los datos de nodos (default: "Nodo")
    
    Returns:
        Lista de objetos Nodo
    """
    # Leer la hoja de Excel, saltando la primera fila que tiene sub-encabezados
    df = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja, skiprows=1)
    
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
    
    nodos = []
    
    for idx, row in df.iterrows():
        try:
            # Campos requeridos
            id_nodo = int(row[columnas[0]])  # 'id'
            x = float(row[columnas[1]])      # 'x [cm]'
            y = float(row[columnas[2]])      # 'y [cm]'
            z = float(row[columnas[3]])      # 'z [cm]'
            
            # Restricciones (6 valores: Desp_x, Desp_y, Desp_z, Rot_x, Rot_y, Rot_z)
            restricciones = []
            for i in range(4, 10):  # Columnas 4-9 para restricciones
                if i < len(columnas):
                    val = row[columnas[i]]
                    # Convertir a bool: True si tiene valor (1, True, "1", etc.), False si es NaN o 0
                    if pd.isna(val):
                        restricciones.append(False)
                    else:
                        restricciones.append(bool(float(val)) if val != '' else False)
                else:
                    restricciones.append(False)
            
            # Asegurar que hay 6 restricciones
            while len(restricciones) < 6:
                restricciones.append(False)
            restricciones = restricciones[:6]
            
            # Valores prescritos (6 valores: Desp_x [cm], Desp_y [cm], Desp_z [cm], Rot_x [cm], Rot_y [cm], Rot_z [cm])
            valores_prescritos = []
            for i in range(10, 16):  # Columnas 10-15 para valores prescritos
                if i < len(columnas):
                    val = row[columnas[i]]
                    valores_prescritos.append(0.0 if pd.isna(val) else float(val))
                else:
                    valores_prescritos.append(0.0)
            
            # Asegurar que hay 6 valores prescritos
            while len(valores_prescritos) < 6:
                valores_prescritos.append(0.0)
            valores_prescritos = valores_prescritos[:6]
            
            # Crear objeto Nodo
            nodo = Nodo(
                id=id_nodo,
                x=x,
                y=y,
                z=z,
                restricciones=restricciones,
                valores_prescritos=valores_prescritos
            )
            
            nodos.append(nodo)
        except (ValueError, TypeError, IndexError) as e:
            print(f"Error procesando fila {idx}: {e}")
            continue
    
    #print(f"Se cargaron {len(nodos)} nodos:")
    for nodo in nodos:
        #print(nodo)
        pass # Para evitar warnings
    
    return nodos


def cargar_nodos_como_dict(ruta_archivo: str, nombre_hoja: str = "Nodo") -> Dict[int, Nodo]:
    """
    Carga los nodos desde Excel y los retorna como un diccionario indexado por id.
    
    Args:
        ruta_archivo: Ruta al archivo Excel
        nombre_hoja: Nombre de la hoja que contiene los datos de nodos (default: "Nodo")
    
    Returns:
        Diccionario con id_nodo como clave y objeto Nodo como valor
    """
    nodos = cargar_nodos_desde_excel(ruta_archivo, nombre_hoja)
    return {nodo.id: nodo for nodo in nodos}


if __name__ == "__main__":
    # Ejecutar la función cuando se ejecuta el script directamente
    ruta_excel = Path(__file__).parent / "Datos_template.xlsx"
    nodos = cargar_nodos_desde_excel(str(ruta_excel), "Nodo")

