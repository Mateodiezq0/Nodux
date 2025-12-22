import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir imports
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
import numpy as np
import importlib.util
from typing import List, Dict

# Función para cargar nodos
def _cargar_nodos_como_dict(ruta_archivo: str, nombre_hoja: str = "Nodo"):
    """Función auxiliar para cargar nodos."""
    carga_nodos_path = Path(__file__).parent / "io" / "carga_nodos.py"
    spec = importlib.util.spec_from_file_location("carga_nodos", carga_nodos_path)
    carga_nodos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carga_nodos)
    return carga_nodos.cargar_nodos_como_dict(ruta_archivo, nombre_hoja)

# Función para cargar barras
def _cargar_barras(ruta_archivo: str, nodos_dict: Dict) -> List:
    """Función auxiliar para cargar barras."""
    carga_barra_path = Path(__file__).parent / "io" / "carga_barra.py"
    spec = importlib.util.spec_from_file_location("carga_barra", carga_barra_path)
    carga_barra = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carga_barra)
    return carga_barra.cargar_barras_desde_excel(ruta_archivo, "Barra", nodos_dict, "Nodo")


def calcular_angulos_barras(ruta_archivo: str, ruta_salida: str = None):
    """
    Lee el archivo Excel, calcula los ángulos alpha, beta y gamma de cada barra
    y los escribe en un nuevo Excel.
    
    Args:
        ruta_archivo: Ruta al archivo Excel con los datos
        ruta_salida: Ruta donde guardar el Excel con los resultados (opcional)
    """
    print("Cargando datos del archivo Excel...")
    
    # Cargar nodos
    nodos_dict = _cargar_nodos_como_dict(ruta_archivo, "Nodo")
    print(f"Cargados {len(nodos_dict)} nodos")
    
    # Cargar barras
    barras = _cargar_barras(ruta_archivo, nodos_dict)
    print(f"Cargadas {len(barras)} barras")
    
    if len(barras) == 0:
        print("No hay barras para procesar.")
        return
    
    # Preparar datos para los diferentes DataFrames por tema
    datos_basicos = []
    datos_angulos = []
    datos_ejes_locales = []
    datos_vectores = []
    
    for barra in barras:
        # Calcular ángulos
        alpha = barra.calcular_alpha()
        beta = barra.calcular_beta()
        gamma = barra.calcular_gamma()
        
        # Calcular terna de ejes locales
        terna_calculada = barra.calcular_terna_ejes_locales()
        
        # Obtener vector unitario para verificación
        v_unit = barra.obtener_vector_unitario()
        
        # 1. Datos básicos
        datos_basicos.append({
            'ID Barra': barra.id,
            'Nodo Inicial': barra.nodo_i,
            'Nodo Final': barra.nodo_f,
            'Longitud L (cm)': barra.L if barra.L is not None else 'N/A',
            'Terna Calculada': 'Sí' if terna_calculada else 'No'
        })
        
        # 2. Ángulos
        datos_angulos.append({
            'ID Barra': barra.id,
            'Alpha (grados)': round(alpha, 10) if alpha is not None and isinstance(alpha, (int, float)) else ('N/A' if alpha is None else alpha),
            'Beta (grados)': round(beta, 10) if beta is not None and isinstance(beta, (int, float)) else ('N/A' if beta is None else beta),
            'Gamma (grados)': round(gamma, 10) if gamma is not None and isinstance(gamma, (int, float)) else ('N/A' if gamma is None else gamma)
        })
        
        # 3. Ejes locales
        # Verificar que los vectores tengan la forma correcta (3 elementos)
        if barra.x_local is not None and hasattr(barra.x_local, '__len__') and len(barra.x_local) >= 3:
            x_local_x = barra.x_local[0]
            x_local_y = barra.x_local[1]
            x_local_z = barra.x_local[2]
        else:
            x_local_x = x_local_y = x_local_z = 0.0
        
        if barra.y_local is not None and hasattr(barra.y_local, '__len__') and len(barra.y_local) >= 3:
            y_local_x = barra.y_local[0]
            y_local_y = barra.y_local[1]
            y_local_z = barra.y_local[2]
        else:
            y_local_x = y_local_y = y_local_z = 0.0
        
        if barra.z_local is not None and hasattr(barra.z_local, '__len__') and len(barra.z_local) >= 3:
            z_local_x = barra.z_local[0]
            z_local_y = barra.z_local[1]
            z_local_z = barra.z_local[2]
        else:
            z_local_x = z_local_y = z_local_z = 0.0
        
        datos_ejes_locales.append({
            'ID Barra': barra.id,
            'x_local X': round(x_local_x, 10) if isinstance(x_local_x, (int, float)) else x_local_x,
            'x_local Y': round(x_local_y, 10) if isinstance(x_local_y, (int, float)) else x_local_y,
            'x_local Z': round(x_local_z, 10) if isinstance(x_local_z, (int, float)) else x_local_z,
            'y_local X': round(y_local_x, 10) if isinstance(y_local_x, (int, float)) else y_local_x,
            'y_local Y': round(y_local_y, 10) if isinstance(y_local_y, (int, float)) else y_local_y,
            'y_local Z': round(y_local_z, 10) if isinstance(y_local_z, (int, float)) else y_local_z,
            'z_local X': round(z_local_x, 10) if isinstance(z_local_x, (int, float)) else z_local_x,
            'z_local Y': round(z_local_y, 10) if isinstance(z_local_y, (int, float)) else z_local_y,
            'z_local Z': round(z_local_z, 10) if isinstance(z_local_z, (int, float)) else z_local_z
        })
        
        # 4. Vectores unitarios
        datos_vectores.append({
            'ID Barra': barra.id,
            'Vector Unitario X': round(v_unit[0], 10) if v_unit is not None else 0.0,
            'Vector Unitario Y': round(v_unit[1], 10) if v_unit is not None else 0.0,
            'Vector Unitario Z': round(v_unit[2], 10) if v_unit is not None else 0.0
        })
    
    # Crear DataFrames
    df_basicos = pd.DataFrame(datos_basicos)
    df_angulos = pd.DataFrame(datos_angulos)
    df_ejes_locales = pd.DataFrame(datos_ejes_locales)
    df_vectores = pd.DataFrame(datos_vectores)
    
    # Determinar ruta de salida (en la raíz del proyecto)
    if ruta_salida is None:
        ruta_salida = Path(__file__).parent / "Testeos.xlsx"
    
    # Escribir a Excel con múltiples pestañas
    print(f"\nEscribiendo resultados a: {ruta_salida}")
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        # Pestaña 1: Datos Básicos
        df_basicos.to_excel(writer, sheet_name='Datos_Basicos', index=False)
        worksheet = writer.sheets['Datos_Basicos']
        for idx, col in enumerate(df_basicos.columns):
            max_length = max(
                df_basicos[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 30)
        
        # Pestaña 2: Ángulos
        df_angulos.to_excel(writer, sheet_name='Angulos', index=False)
        worksheet = writer.sheets['Angulos']
        for idx, col in enumerate(df_angulos.columns):
            max_length = max(
                df_angulos[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 30)
            # Formato de números con alta precisión (10 decimales)
            if idx > 0:  # Saltar la columna ID
                for row in range(2, len(df_angulos) + 2):
                    cell = worksheet[f'{col_letter}{row}']
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '0.0000000000'
        
        # Pestaña 3: Ejes Locales
        df_ejes_locales.to_excel(writer, sheet_name='Ejes_Locales', index=False)
        worksheet = writer.sheets['Ejes_Locales']
        for idx, col in enumerate(df_ejes_locales.columns):
            max_length = max(
                df_ejes_locales[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 30)
            # Formato de números con alta precisión (10 decimales)
            if idx > 0:  # Saltar la columna ID
                for row in range(2, len(df_ejes_locales) + 2):
                    cell = worksheet[f'{col_letter}{row}']
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '0.0000000000'
        
        # Pestaña 4: Vectores Unitarios
        df_vectores.to_excel(writer, sheet_name='Vectores_Unitarios', index=False)
        worksheet = writer.sheets['Vectores_Unitarios']
        for idx, col in enumerate(df_vectores.columns):
            max_length = max(
                df_vectores[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 30)
            # Formato de números con alta precisión (10 decimales)
            if idx > 0:  # Saltar la columna ID
                for row in range(2, len(df_vectores) + 2):
                    cell = worksheet[f'{col_letter}{row}']
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '0.0000000000'
    
    print("¡Archivo Excel creado exitosamente con múltiples pestañas!")
    print("\nResumen de resultados:")
    print("\n--- Datos Básicos ---")
    print(df_basicos.to_string(index=False))
    print("\n--- Ángulos ---")
    print(df_angulos.to_string(index=False))
    print("\n--- Ejes Locales ---")
    print(df_ejes_locales.to_string(index=False))
    print("\n--- Vectores Unitarios ---")
    print(df_vectores.to_string(index=False))
    
    return {
        'basicos': df_basicos,
        'angulos': df_angulos,
        'ejes_locales': df_ejes_locales,
        'vectores': df_vectores
    }


if __name__ == "__main__":
    # Ruta al archivo Excel
    ruta_excel = Path(__file__).parent / "io" / "Datos_template.xlsx"
    
    if not ruta_excel.exists():
        print(f"Error: No se encontró el archivo {ruta_excel}")
    else:
        calcular_angulos_barras(str(ruta_excel))

