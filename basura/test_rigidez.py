import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from core.barra import Barra
from core.nodos import Nodo

def calcular_K_local_viga_3D(E, A, I_y, I_z, G, J, L):
    """
    Calcula la matriz de rigidez local (12x12) para una viga 3D de Euler-Bernoulli.
    
    Parámetros:
    -----------
    E : float
        Módulo de elasticidad
    A : float
        Área de la sección
    I_y : float
        Momento de inercia alrededor del eje Y local
    I_z : float
        Momento de inercia alrededor del eje Z local
    G : float
        Módulo de corte
    J : float
        Momento de inercia torsional
    L : float
        Longitud de la barra
        
    Retorna:
    --------
    np.ndarray
        Matriz de rigidez local 12x12
    """
    # Inicializar matriz
    K = np.zeros((12, 12))
    
    # Constantes
    EA_L = E * A / L
    EIy_L = E * I_y / L
    EIy_L2 = E * I_y / (L**2)
    EIy_L3 = E * I_y / (L**3)
    
    EIz_L = E * I_z / L
    EIz_L2 = E * I_z / (L**2)
    EIz_L3 = E * I_z / (L**3)
    
    GJ_L = G * J / L
    
    # Fuerza axial (DOF 0 y 6)
    K[0, 0] = EA_L
    K[0, 6] = -EA_L
    K[6, 0] = -EA_L
    K[6, 6] = EA_L
    
    # Torsión (DOF 3 y 9)
    K[3, 3] = GJ_L
    K[3, 9] = -GJ_L
    K[9, 3] = -GJ_L
    K[9, 9] = GJ_L
    
    # Flexión en Y (DOF 1, 5, 7, 11)
    K[1, 1] = 12 * EIz_L3
    K[1, 5] = 6 * EIz_L2
    K[1, 7] = -12 * EIz_L3
    K[1, 11] = 6 * EIz_L2
    
    K[5, 1] = 6 * EIz_L2
    K[5, 5] = 4 * EIz_L
    K[5, 7] = -6 * EIz_L2
    K[5, 11] = 2 * EIz_L
    
    K[7, 1] = -12 * EIz_L3
    K[7, 5] = -6 * EIz_L2
    K[7, 7] = 12 * EIz_L3
    K[7, 11] = -6 * EIz_L2
    
    K[11, 1] = 6 * EIz_L2
    K[11, 5] = 2 * EIz_L
    K[11, 7] = -6 * EIz_L2
    K[11, 11] = 4 * EIz_L
    
    # Flexión en Z (DOF 2, 4, 8, 10)
    K[2, 2] = 12 * EIy_L3
    K[2, 4] = -6 * EIy_L2
    K[2, 8] = -12 * EIy_L3
    K[2, 10] = -6 * EIy_L2
    
    K[4, 2] = -6 * EIy_L2
    K[4, 4] = 4 * EIy_L
    K[4, 8] = 6 * EIy_L2
    K[4, 10] = 2 * EIy_L
    
    K[8, 2] = -12 * EIy_L3
    K[8, 4] = 6 * EIy_L2
    K[8, 8] = 12 * EIy_L3
    K[8, 10] = 6 * EIy_L2
    
    K[10, 2] = -6 * EIy_L2
    K[10, 4] = 2 * EIy_L
    K[10, 8] = 6 * EIy_L2
    K[10, 10] = 4 * EIy_L
    
    return K

def imprimir_matriz_formato_excel(K, nombre_matriz="Matriz", precision=2):
    """
    Imprime una matriz en formato tipo Excel (tabla con encabezados de filas y columnas).
    
    Parámetros:
    -----------
    K : np.ndarray
        Matriz a imprimir (12x12)
    nombre_matriz : str
        Nombre de la matriz
    precision : int
        Número de decimales a mostrar
    """
    print(f"\n{'=' * 120}")
    print(f"{nombre_matriz} (12x12)")
    print(f"{'=' * 120}")
    
    # Crear DataFrame con encabezados descriptivos
    # DOFs: 0-2: Traslaciones nodo i (Fx, Fy, Fz)
    #       3-5: Rotaciones nodo i (Mx, My, Mz)
    #       6-8: Traslaciones nodo f (Fx, Fy, Fz)
    #       9-11: Rotaciones nodo f (Mx, My, Mz)
    nombres_dofs = [
        "Fx_i", "Fy_i", "Fz_i", "Mx_i", "My_i", "Mz_i",
        "Fx_f", "Fy_f", "Fz_f", "Mx_f", "My_f", "Mz_f"
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(K, index=nombres_dofs, columns=nombres_dofs)
    
    # Configurar formato de números
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    # Formatear números con separador de miles y decimales
    def formatear_numero(x):
        if abs(x) < 1e-10:
            return "0.00"
        return f"{x:,.{precision}f}"
    
    # Aplicar formato a todas las celdas
    df_formateado = df.map(formatear_numero)
    
    print(df_formateado.to_string())
    
    print(f"\nNota: i = nodo inicial, f = nodo final")
    print(f"      Fx, Fy, Fz = Fuerzas; Mx, My, Mz = Momentos")

def exportar_matrices_a_excel(K_local, K_global, barra, ruta_archivo="Matrices_Rigidez.xlsx", precision=6):
    """
    Exporta las matrices K_local y K_global a un archivo Excel con formato tipo tabla.
    
    Parámetros:
    -----------
    K_local : np.ndarray
        Matriz de rigidez local (12x12)
    K_global : np.ndarray
        Matriz de rigidez global (12x12)
    ruta_archivo : str
        Ruta del archivo Excel a crear
    precision : int
        Número de decimales a mostrar
    """
    # Nombres de DOFs
    nombres_dofs = [
        "Fx_i", "Fy_i", "Fz_i", "Mx_i", "My_i", "Mz_i",
        "Fx_f", "Fy_f", "Fz_f", "Mx_f", "My_f", "Mz_f"
    ]
    
    # Crear DataFrames
    df_k_local = pd.DataFrame(K_local, index=nombres_dofs, columns=nombres_dofs)
    df_k_global = pd.DataFrame(K_global, index=nombres_dofs, columns=nombres_dofs)
    
    # Redondear a la precisión especificada
    df_k_local = df_k_local.round(precision)
    df_k_global = df_k_global.round(precision)
    
    # Obtener cosenos directores de la barra
    # Asegurar que se han calculado los ejes locales
    if barra.x_local is None or barra.y_local is None or barra.z_local is None:
        barra.calcular_terna_ejes_locales()
    
    # Extraer cosenos directores
    cosenos_directores = {
        'cosalphax': barra.x_local[0] if barra.x_local is not None else 0.0,
        'cosalphay': barra.x_local[1] if barra.x_local is not None else 0.0,
        'cosalphaz': barra.x_local[2] if barra.x_local is not None else 0.0,
        'cosbetax': barra.y_local[0] if barra.y_local is not None else 0.0,
        'cosbetay': barra.y_local[1] if barra.y_local is not None else 0.0,
        'cosbetaz': barra.y_local[2] if barra.y_local is not None else 0.0,
        'cosgammax': barra.z_local[0] if barra.z_local is not None else 0.0,
        'cosgammay': barra.z_local[1] if barra.z_local is not None else 0.0,
        'cosgammaz': barra.z_local[2] if barra.z_local is not None else 0.0
    }
    
    # Crear DataFrame con cosenos directores
    df_cosenos = pd.DataFrame([cosenos_directores])
    
    # Crear archivo Excel con múltiples hojas
    with pd.ExcelWriter(ruta_archivo, engine='openpyxl') as writer:
        # Hoja 1: Cosenos Directores
        df_cosenos.to_excel(writer, sheet_name='Cosenos_Directores', index=False)
        
        # Hoja 2: K_LOCAL
        df_k_local.to_excel(writer, sheet_name='K_LOCAL', index=True)
        
        # Hoja 3: K_GLOBAL
        df_k_global.to_excel(writer, sheet_name='K_GLOBAL', index=True)
        
        # Ajustar ancho de columnas para ambas hojas
        from openpyxl.utils import get_column_letter
        
        for sheet_name in ['K_LOCAL', 'K_GLOBAL']:
            worksheet = writer.sheets[sheet_name]
            df = df_k_local if sheet_name == 'K_LOCAL' else df_k_global
            
            # Ajustar ancho de la columna de índice
            worksheet.column_dimensions['A'].width = 10
            
            # Ajustar ancho de las columnas de datos
            for col_idx, col_name in enumerate(df.columns, start=2):  # Empezar en columna B
                col_letter = get_column_letter(col_idx)
                # Calcular el ancho máximo necesario
                max_length = max(
                    len(str(col_name)),
                    max([len(f"{df.iloc[i, col_idx-2]:.{precision}f}") for i in range(len(df))])
                )
                worksheet.column_dimensions[col_letter].width = min(max_length + 2, 18)
    
    print(f"\nArchivo Excel exportado exitosamente: {ruta_archivo}")
    print(f"  - Hoja 'Cosenos_Directores': Cosenos directores de los ejes locales")
    print(f"  - Hoja 'K_LOCAL': Matriz de rigidez local (12x12)")
    print(f"  - Hoja 'K_GLOBAL': Matriz de rigidez global (12x12)")

def test_rigidez():
    """
    Test: Crea una barra entre (0,0,0) y (0,0,1) y compara K_local con K_global.
    La barra está alineada con el eje Z global.
    """
    print("=" * 80)
    print("TEST: Comparación de K_local y K_global")
    print("=" * 80)
    
    # Crear nodos
    nodo1 = Nodo(id=1, x=0.0, y=0.0, z=0.0)
    nodo2 = Nodo(id=2, x=0.0, y=0.0, z=1.0)
    
    print(f"\nNodo 1: ({nodo1.x}, {nodo1.y}, {nodo1.z})")
    print(f"Nodo 2: ({nodo2.x}, {nodo2.y}, {nodo2.z})")
    
    # Propiedades de la barra
    E = 2100.0  # Tn/cm²
    A = 100.0   # cm²
    I_y = 1000.0  # cm⁴
    I_z = 1000.0  # cm⁴
    G = 800.0   # Tn/cm²
    J = 500.0   # cm⁴
    L = 1.0     # cm
    
    # Crear barra
    barra = Barra(
        id=1,
        nodo_i=1,
        nodo_f=2,
        E=E,
        A=A,
        I_y=I_y,
        I_z=I_z,
        G=G,
        J=J,
        L=L,
        tita=None
    )
    
    # Asignar objetos nodo
    barra.nodo_i_obj = nodo1
    barra.nodo_f_obj = nodo2
    
    # Calcular longitud desde nodos
    dx = nodo2.x - nodo1.x
    dy = nodo2.y - nodo1.y
    dz = nodo2.z - nodo1.z
    L_calculada = np.sqrt(dx*dx + dy*dy + dz*dz)
    barra.L = L_calculada
    
    print(f"\nLongitud de la barra: {barra.L} cm")
    
    # Calcular K_local
    K_local = calcular_K_local_viga_3D(E, A, I_y, I_z, G, J, L)
    
    # Mostrar K_local en formato Excel
    imprimir_matriz_formato_excel(K_local, "K_LOCAL", precision=2)
    print(f"\nNorma de K_local: {np.linalg.norm(K_local):.6e}")
    
    # Transformar a K_global
    K_global = barra.transformar_K_local_a_global_con_Tx_Ty_Tz(K_local)
    
    # Mostrar K_global en formato Excel
    imprimir_matriz_formato_excel(K_global, "K_GLOBAL", precision=2)
    print(f"\nNorma de K_global: {np.linalg.norm(K_global):.6e}")
    
    # Exportar a Excel
    ruta_excel = "Matrices_Rigidez.xlsx"
    exportar_matrices_a_excel(K_local, K_global, barra, ruta_excel, precision=6)
    print(f"\n{'=' * 80}")
    print(f"Archivo Excel creado: {ruta_excel}")
    print(f"{'=' * 80}")
    
if __name__ == "__main__":
    test_rigidez()