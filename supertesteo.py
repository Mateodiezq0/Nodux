import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from core.estructura import Estructura
from core.nodos import Nodo
from core.barra import Barra
from core.carga_puntual import CargaPuntual, reacciones_de_empotramiento

# Importar funciones de visualización
try:
    import plotly.graph_objects as go
    from plot.plot import plot_estructura_interactiva
    PLOTLY_AVAILABLE = True
except ImportError as e:
    PLOTLY_AVAILABLE = False
    print(f"ADVERTENCIA: No se pudo importar plotly o plot.plot: {e}")
    print("   Ejecuta: pip install plotly")

def crear_estructura_supertesteo():
    """
    Crea una estructura de prueba con:
    - 4 barras
    - 6 nodos
    - 3 cargas puntuales
    - Condiciones de borde específicas
    """
    
    # Crear estructura
    estructura = Estructura()
    
    # ========== CREAR NODOS ==========
    # Nodo 1: (0, 200, 0)
    nodo1 = Nodo(id=1, x=0.0, y=200.0, z=0.0)
    # Nodo 1 está fijo (restringido en X, Y, Z pero con todos los giros libres)
    nodo1.restricciones = [True, True, True, False, False, False]  # [Desp_x, Desp_y, Desp_z, Rot_x, Rot_y, Rot_z]
    nodo1.valores_prescritos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    estructura.agregar_nodo(nodo1)
    
    # Nodo 2: (0, 200, 300)
    nodo2 = Nodo(id=2, x=0.0, y=200.0, z=300.0)
    nodo2.restricciones = [None, None, None, None, None, None]
    estructura.agregar_nodo(nodo2)
    
    # Nodo 3: (100, 200, 0)
    nodo3 = Nodo(id=3, x=100.0, y=200.0, z=0.0)
    # Nodo 3 está restringido solo en el sentido VERTICAL (Y) de cargas, todo lo otro es libre
    nodo3.restricciones = [False, False, True, False, False, False]  # Solo Y restringido
    nodo3.valores_prescritos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    estructura.agregar_nodo(nodo3)
    
    # Nodo 4: (100, 200, 300)
    nodo4 = Nodo(id=4, x=100.0, y=200.0, z=300.0)
    nodo4.restricciones = [None, None, None, None, None, None]
    estructura.agregar_nodo(nodo4)
    
    # Nodo 5: (100, 0, 300) - según barra 3: nodo 5 (100,200,300) al nodo 6 (100,0,300)
    # Pero hay inconsistencia: barra 3 dice nodo 5 (100,200,300) que es el nodo 4
    # y barra 4 dice nodo 5 (0,200,300) que es el nodo 2
    # Interpretación correcta: hay 5 nodos únicos
    # - Nodo 5: (100, 0, 300) - el que falta según la descripción de barra 3
    nodo5 = Nodo(id=5, x=100.0, y=0.0, z=300.0)
    # Nodo 5 empotrado (todas las restricciones) - según la descripción: "Nodo 6 empotrado"
    # pero como hay 5 nodos, el nodo 5 es el empotrado
    nodo5.restricciones = [True, True, True, True, True, True]
    nodo5.valores_prescritos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    estructura.agregar_nodo(nodo5)
    
    # ========== CREAR BARRAS ==========
    # Propiedades de las barras (valores típicos para pruebas)
    E = 2100.0  # Tn/cm²
    A = 100.0   # cm²
    I_y = 1000.0  # cm⁴
    I_z = 1000.0  # cm⁴
    G = 800.0   # Tn/cm²
    J = 500.0   # cm⁴
    
    # Barra 1: del nodo 1 (0,200,0) al nodo 2 (0,200,300)
    barra1 = Barra(
        id=1,
        nodo_i=1,
        nodo_f=2,
        E=E,
        A=A,
        I_y=I_y,
        I_z=I_z,
        G=G,
        J=J,
        tita=None
    )
    barra1.nodo_i_obj = nodo1
    barra1.nodo_f_obj = nodo2
    estructura.agregar_barra(barra1)
    
    # Barra 2: del nodo 3 (100,200,0) al nodo 4 (100,200,300)
    barra2 = Barra(
        id=2,
        nodo_i=3,
        nodo_f=4,
        E=E,
        A=A,
        I_y=I_y,
        I_z=I_z,
        G=G,
        J=J,
        tita=None
    )
    barra2.nodo_i_obj = nodo3
    barra2.nodo_f_obj = nodo4
    estructura.agregar_barra(barra2)
    
    # Barra 3: del nodo 4 (100,200,300) al nodo 5 (100,0,300)
    # Nota: La descripción dice "nodo 5 (100,200,300)" pero ese es el nodo 4
    barra3 = Barra(
        id=3,
        nodo_i=4,
        nodo_f=5,
        E=E,
        A=A,
        I_y=I_y,
        I_z=I_z,
        G=G,
        J=J,
        tita=None
    )
    barra3.nodo_i_obj = nodo4
    barra3.nodo_f_obj = nodo5
    estructura.agregar_barra(barra3)
    
    # Barra 4: del nodo 2 (0,200,300) al nodo 4 (100,200,300)
    # Nota: La descripción dice "nodo 5 (0,200,300) al nodo 6 (100,200,300)"
    # pero nodo 5 (0,200,300) = nodo 2, y nodo 6 (100,200,300) = nodo 4
    # Usamos nodo 2 y nodo 4 para mantener consistencia
    barra4 = Barra(
        id=4,
        nodo_i=2,
        nodo_f=4,
        E=E,
        A=A,
        I_y=I_y,
        I_z=I_z,
        G=G,
        J=J,
        tita=None
    )
    barra4.nodo_i_obj = nodo2
    barra4.nodo_f_obj = nodo4
    estructura.agregar_barra(barra4)
    
    # ========== CREAR CARGAS PUNTUALES ==========
    # Carga 1: En barra 3, de -10 kN, paralela al eje Y
    # Para que sea paralela al eje Y global, necesitamos rotar el vector [q, 0, 0] para que apunte en Y
    # Vector inicial: [q, 0, 0] = [-10, 0, 0] (en dirección X)
    # Para que apunte en Y: rotación_z = 90 grados (rota X hacia Y)
    carga1 = CargaPuntual()
    carga1.id = 1
    # Posición en la barra 3: punto medio (aproximadamente)
    # Barra 3 va de (100, 200, 300) a (100, 0, 300)
    # Punto medio: (100, 100, 300)
    carga1.x = 100.0
    carga1.y = 100.0
    carga1.z = 300.0
    # Para que sea paralela al eje Z: 
    carga1.F_z = np.array([0.0, 0.0, -5.0]) #1000 kN en Z
    barra3.cargas.append(carga1)
    
    # Carga 2: En barra 2, de -5 kN, paralela al eje X
    # Para que sea paralela al eje X global, no necesita rotación (ya está en X)
    carga2 = CargaPuntual()
    carga2.id = 2
    # Posición en la barra 2: punto medio
    # Barra 2 va de (100, 200, 0) a (100, 200, 300)
    # Punto medio: (100, 200, 150)
    carga2.x = 100.0
    carga2.y = 200.0
    carga2.z = 150.0
    # Para que sea paralela al eje Y
    carga2.F_y = np.array([0.0, -5.0, 0.0]) #1000 kN en X
    barra2.cargas.append(carga2)
    
    # Carga 3: En barra 4, de -10 kN, paralela al eje Z
    # Para que sea paralela al eje Z global, necesitamos rotar el vector
    # Vector inicial: [q, 0, 0] = [-10, 0, 0] (en dirección X)
    # Para que apunte en Z: rotación_y = -90 grados (rota X hacia Z)
    carga3 = CargaPuntual()
    carga3.id = 3
    # Posición en la barra 4: punto medio
    # Barra 4 va de (0, 200, 300) a (100, 200, 300)
    # Punto medio: (50, 200, 300)
    carga3.x = 50.0
    carga3.y = 200.0
    carga3.z = 300.0
    # Para que sea paralela al eje Z
    carga3.F_z = np.array([0.0, 0.0, -10.0]) #1000 kN en Z
    barra4.cargas.append(carga3)
    
    # Calcular reacciones de empotramiento para cada carga
    for barra in estructura.barras:
        for carga in barra.cargas:
            reacciones_de_empotramiento(carga, barra)
        # Transformar reacciones a global
        barra.transformar_reacciones_empotramiento_a_global()
    
    return estructura

def exportar_resultados_excel(estructura, F_internas, nombre_archivo):
    """
    Exporta los resultados de la estructura a un archivo Excel.
    Esta versión accede a atributos de forma segura (getattr), normaliza tamaños
    y crea hojas aún si algunos atributos cambiaron de nombre.
    """
    import numpy as _np
    from pathlib import Path as _Path

    nombres_dofs = [
        "Fx_i", "Fy_i", "Fz_i", "Mx_i", "My_i", "Mz_i",
        "Fx_f", "Fy_f", "Fz_f", "Mx_f", "My_f", "Mz_f"
    ]

    def _safe_array(obj, attr, length, dtype=float):
        val = getattr(obj, attr, None)
        if val is None:
            return _np.zeros(length, dtype=dtype)
        arr = _np.asarray(val, dtype=dtype)
        if arr.size != length:
            out = _np.zeros(length, dtype=dtype)
            out[:min(length, arr.size)] = arr.ravel()[:length]
            return out
        return arr

    # Cargas nodales equivalentes en global (por barra: nudo i + nudo f)
    datos_cargas_globales_nudos = []
    for barra in getattr(estructura, 'barras', []):
        reacc_i_g = _safe_array(barra, 'reaccion_nudo_i_equivalente_global', 6)
        reacc_f_g = _safe_array(barra, 'reaccion_nudo_f_equivalente_global', 6)
        cargas_12 = _np.concatenate([reacc_i_g, reacc_f_g])
        datos_cargas_globales_nudos.append({
            'Barra ID': getattr(barra, 'id', None),
            'Nodo Inicial': getattr(barra, 'nodo_i', None),
            'Nodo Final': getattr(barra, 'nodo_f', None),
            **{nombres_dofs[i]: float(cargas_12[i]) for i in range(12)}
        })
    df_cargas_globales_nudos = pd.DataFrame(datos_cargas_globales_nudos)

    # Fuerzas internas (F_internas puede tener formato diverso)
    datos_fuerzas_internas = []
    for idx, barra in enumerate(getattr(estructura, 'barras', [])):
        if F_internas is None or idx >= len(F_internas):
            F_interna = _np.zeros(12)
        else:
            F_interna = _np.asarray(F_internas[idx])
            if F_interna.size != 12:
                tmp = _np.zeros(12)
                tmp[:min(12, F_interna.size)] = F_interna.ravel()[:12]
                F_interna = tmp
        datos_fuerzas_internas.append({
            'Barra ID': getattr(barra, 'id', None),
            'Nodo Inicial': getattr(barra, 'nodo_i', None),
            'Nodo Final': getattr(barra, 'nodo_f', None),
            **{nombres_dofs[i]: float(F_interna[i]) for i in range(12)}
        })
    df_fuerzas_internas = pd.DataFrame(datos_fuerzas_internas)

    # Resumen por barra
    datos_resumen = []
    for idx, barra in enumerate(getattr(estructura, 'barras', [])):
        F_interna = _np.zeros(12)
        if F_internas is not None and idx < len(F_internas):
            arr = _np.asarray(F_internas[idx])
            F_interna[:min(12, arr.size)] = arr.ravel()[:12]
        datos_resumen.append({
            'Barra ID': getattr(barra, 'id', None),
            'Nodo Inicial': getattr(barra, 'nodo_i', None),
            'Nodo Final': getattr(barra, 'nodo_f', None),
            'Longitud (cm)': getattr(barra, 'L', 0.0) or 0.0,
            'Fx_i (kN)': float(F_interna[0]),
            'Fy_i (kN)': float(F_interna[1]),
            'Fz_i (kN)': float(F_interna[2]),
            'Mx_i (kN·cm)': float(F_interna[3]),
            'My_i (kN·cm)': float(F_interna[4]),
            'Mz_i (kN·cm)': float(F_interna[5]),
            'Fx_f (kN)': float(F_interna[6]),
            'Fy_f (kN)': float(F_interna[7]),
            'Fz_f (kN)': float(F_interna[8]),
            'Mx_f (kN·cm)': float(F_interna[9]),
            'My_f (kN·cm)': float(F_interna[10]),
            'Mz_f (kN·cm)': float(F_interna[11]),
        })
    df_resumen = pd.DataFrame(datos_resumen)

    # Reacciones locales por barra: nodo i (6) + nodo f (6), una fila por barra
    datos_reacciones_locales_nodos = []
    for barra in getattr(estructura, 'barras', []):
        reacc_i_local = _safe_array(barra, 'reaccion_de_empotramiento_i_local', 6)
        reacc_f_local = _safe_array(barra, 'reaccion_de_empotramiento_f_local', 6)
        reacc_12 = _np.concatenate([reacc_i_local, reacc_f_local])
        datos_reacciones_locales_nodos.append({
            'Barra ID': getattr(barra, 'id', None),
            'Nodo Inicial': getattr(barra, 'nodo_i', None),
            'Nodo Final': getattr(barra, 'nodo_f', None),
            **{nombres_dofs[i]: float(reacc_12[i]) for i in range(12)}
        })
    df_reacciones_locales_nodos = pd.DataFrame(datos_reacciones_locales_nodos)

    # f_local y reacciones por carga
    datos_cargas_local = []
    for barra in getattr(estructura, 'barras', []):
        for carga in getattr(barra, 'cargas', []):
            f_local = _safe_array(carga, 'f_local', 3)
            reacc_i = _safe_array(barra, 'reaccion_de_empotramiento_i_local', 6)
            reacc_f = _safe_array(barra, 'reaccion_de_empotramiento_f_local', 6)
            datos_cargas_local.append({
                'Carga ID': getattr(carga, 'id', None),
                'Barra ID': getattr(barra, 'id', None),
                'Nodo Inicial': getattr(barra, 'nodo_i', None),
                'Nodo Final': getattr(barra, 'nodo_f', None),
                'f_local_x': float(f_local[0]),
                'f_local_y': float(f_local[1]),
                'f_local_z': float(f_local[2]),
                'Reacc_i_Fx_local': float(reacc_i[0]),
                'Reacc_i_Fy_local': float(reacc_i[1]),
                'Reacc_i_Fz_local': float(reacc_i[2]),
                'Reacc_i_Mx_local': float(reacc_i[3]),
                'Reacc_i_My_local': float(reacc_i[4]),
                'Reacc_i_Mz_local': float(reacc_i[5]),
                'Reacc_f_Fx_local': float(reacc_f[0]),
                'Reacc_f_Fy_local': float(reacc_f[1]),
                'Reacc_f_Fz_local': float(reacc_f[2]),
                'Reacc_f_Mx_local': float(reacc_f[3]),
                'Reacc_f_My_local': float(reacc_f[4]),
                'Reacc_f_Mz_local': float(reacc_f[5]),
            })
    df_cargas_local = pd.DataFrame(datos_cargas_local)

    # Vector nodal equivalente
    nombres_dofs_nodo = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
    datos_vector_nodal = []
    vector_nodal = getattr(estructura, 'vector_nodal_equivalente', None)
    if vector_nodal is None:
        vector_nodal = _np.zeros(len(getattr(estructura, 'nodos', [])) * 6)
    for nodo in getattr(estructura, 'nodos', []):
        base = (nodo.id - 1) * 6
        fila = {'Nodo ID': nodo.id}
        for i, nombre in enumerate(nombres_dofs_nodo):
            fila[nombre] = float(vector_nodal[base + i]) if base + i < len(vector_nodal) else 0.0
        datos_vector_nodal.append(fila)
    df_vector_nodal = pd.DataFrame(datos_vector_nodal)

    # Terna ejes locales
    datos_ejes_locales = []
    for barra in getattr(estructura, 'barras', []):
        try:
            if getattr(barra, 'x_local', None) is None or getattr(barra, 'y_local', None) is None or getattr(barra, 'z_local', None) is None:
                if hasattr(barra, 'calcular_terna_ejes_locales'):
                    barra.calcular_terna_ejes_locales()
        except Exception:
            pass

        xl = getattr(barra, 'x_local', [0.0, 0.0, 0.0])
        yl = getattr(barra, 'y_local', [0.0, 0.0, 0.0])
        zl = getattr(barra, 'z_local', [0.0, 0.0, 0.0])

        xlx, xly, xlz = list(xl)[:3] if len(list(xl)) >= 3 else (0.0, 0.0, 0.0)
        ylx, yly, ylz = list(yl)[:3] if len(list(yl)) >= 3 else (0.0, 0.0, 0.0)
        zlx, zly, zlz = list(zl)[:3] if len(list(zl)) >= 3 else (0.0, 0.0, 0.0)

        datos_ejes_locales.append({
            'Barra ID': getattr(barra, 'id', None),
            'Nodo Inicial': getattr(barra, 'nodo_i', None),
            'Nodo Final': getattr(barra, 'nodo_f', None),
            'Longitud (cm)': getattr(barra, 'L', 0.0) or 0.0,
            'tita (deg)': getattr(barra, 'tita', 0.0) or 0.0,
            'x_local_x': xlx,
            'x_local_y': xly,
            'x_local_z': xlz,
            'y_local_x': ylx,
            'y_local_y': yly,
            'y_local_z': ylz,
            'z_local_x': zlx,
            'z_local_y': zly,
            'z_local_z': zlz,
        })
    df_ejes_locales = pd.DataFrame(datos_ejes_locales)

    # Matriz de rotacion T (12x12) por barra
    datos_matriz_T = []
    for barra in getattr(estructura, 'barras', []):
        try:
            T = _np.asarray(barra.construir_matriz_rotacion_T_12x12(), dtype=float)
            if T.shape != (12, 12):
                T = _np.zeros((12, 12), dtype=float)
        except Exception:
            T = _np.zeros((12, 12), dtype=float)

        for fila_idx in range(12):
            fila = {
                'Barra ID': getattr(barra, 'id', None),
                'Nodo Inicial': getattr(barra, 'nodo_i', None),
                'Nodo Final': getattr(barra, 'nodo_f', None),
                'Fila': fila_idx + 1
            }
            for col_idx in range(12):
                fila[f'C{col_idx + 1}'] = float(T[fila_idx, col_idx])
            datos_matriz_T.append(fila)
    df_matriz_T = pd.DataFrame(datos_matriz_T)

    # Escribir Excel
    ruta_excel = _Path(__file__).parent / nombre_archivo
    with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen_Fuerzas_Internas', index=False)
        df_fuerzas_internas.to_excel(writer, sheet_name='F_Interna_Global', index=False)
        df_cargas_globales_nudos.to_excel(writer, sheet_name='Cargas_Globales_en_nudos', index=False)
        df_reacciones_locales_nodos.to_excel(writer, sheet_name='reacciones_locales_de_empotramiento', index=False)
        df_vector_nodal.to_excel(writer, sheet_name='Vector_Nodal_Equivalente', index=False)
        df_cargas_local.to_excel(writer, sheet_name='f_local_Reacc_i_por_Carga', index=False)
        df_ejes_locales.to_excel(writer, sheet_name='Ejes_Locales', index=False)
        df_matriz_T.to_excel(writer, sheet_name='Matriz_Rotacion_T', index=False)

        # Ajustar anchos
        from openpyxl.utils import get_column_letter
        sheets_map = {
            'Resumen_Fuerzas_Internas': df_resumen,
            'F_Interna_Global': df_fuerzas_internas,
            'Cargas_Globales_en_nudos': df_cargas_globales_nudos,
            'reacciones_locales_de_empotramiento': df_reacciones_locales_nodos,
            'Vector_Nodal_Equivalente': df_vector_nodal,
            'f_local_Reacc_i_por_Carga': df_cargas_local,
            'Ejes_Locales': df_ejes_locales,
            'Matriz_Rotacion_T': df_matriz_T
        }
        for sheet_name, df in sheets_map.items():
            worksheet = writer.sheets.get(sheet_name)
            if worksheet is None or df is None:
                continue
            for idx, col_name in enumerate(df.columns, 1):
                column_letter = get_column_letter(idx)
                max_length = max(
                    len(str(col_name)),
                    df[col_name].astype(str).map(len).max() if len(df) > 0 else 0
                )
                adjusted_width = min(max_length + 2, 40)
                worksheet.column_dimensions[column_letter].width = adjusted_width

    print(f"\nArchivo Excel creado: {ruta_excel}")

if __name__ == "__main__":
    print("=" * 80)
    print("SUPERTESTEO: Estructura de prueba")
    print("=" * 80)
    
    estructura = crear_estructura_supertesteo()
    
    print(f"\nNodos creados: {len(estructura.nodos)}")
    for nodo in estructura.nodos:
        print(f"  Nodo {nodo.id}: ({nodo.x}, {nodo.y}, {nodo.z}) - Restricciones: {nodo.restricciones}")
    
    print(f"\nBarras creadas: {len(estructura.barras)}")
    for barra in estructura.barras:
        print(f"  Barra {barra.id}: Nodo {barra.nodo_i} -> Nodo {barra.nodo_f}, Cargas: {len(barra.cargas)}")
        if barra.L is not None:
            print(f"    Longitud: {barra.L:.2f} cm")

    # Mostrar matriz de rotacion R (3x3) por barra
    print("\nMatriz de rotacion R (3x3) por barra:")
    for barra in estructura.barras:
        try:
            R = barra.construir_matriz_rotacion_R_3x3()
            print(f"\n  Barra {barra.id} (Nodo {barra.nodo_i} -> Nodo {barra.nodo_f}):")
            print(R)
        except Exception as e:
            print(f"\n  Barra {barra.id} (Nodo {barra.nodo_i} -> Nodo {barra.nodo_f}): ERROR al calcular R -> {e}")
    
    print(f"\nCargas puntuales:")
    for barra in estructura.barras:
        for carga in barra.cargas:
            print(f"  Carga {carga.id} en Barra {barra.id}")
            
    
    print("\n" + "=" * 80)
    print("Estructura creada exitosamente!")
    print("=" * 80)
    
    # ========== RESOLVER ESTRUCTURA ==========
    print("\n" + "=" * 80)
    print("RESOLVIENDO ESTRUCTURA...")
    print("=" * 80)
    
    # Ensamblar matriz global
    print("\nEnsamblando matriz global de rigidez...")
    estructura.ensamble_matriz_global()
    print(f"Matriz global: {estructura.K_global.shape}")
    
    # Ensamblar vector de cargas nodales equivalentes
    print("\nEnsamblando vector de cargas nodales equivalentes...")
    estructura.ensamble_vector_cargas_nodales_equivalentes()
    print(f"Vector de cargas: {len(estructura.vector_nodal_equivalente)} DOFs")
    
    # Resolver desplazamientos
    print("\nResolviendo desplazamientos...")
    estructura.resolver_desplazamientos(debug=0)
    print("Desplazamientos calculados")
    
    # Calcular fuerzas internas (F_interna)
    print("\nCalculando fuerzas internas...")
    F_internas = estructura.calcular_reacciones(debug=0)
    print(f"Fuerzas internas calculadas para {len(F_internas)} barras")
    
    # ========== EXPORTAR A EXCEL ==========
    print("\n" + "=" * 80)
    print("EXPORTANDO RESULTADOS A EXCEL...")
    print("=" * 80)
    
    exportar_resultados_excel(estructura, F_internas, "supertesteo_resultados.xlsx")
    
    # ========== VISUALIZAR ESTRUCTURA ==========
    if PLOTLY_AVAILABLE:
        try:
            print("\n" + "=" * 80)
            print("VISUALIZANDO ESTRUCTURA...")
            print("=" * 80)
            
            # Crear diccionario de nodos para la visualización
            nodos_dict = {nodo.id: nodo for nodo in estructura.nodos}
            
            # Verificar que tenemos datos
            if len(estructura.nodos) == 0:
                print("ADVERTENCIA: No hay nodos para visualizar")
            elif len(estructura.barras) == 0:
                print("ADVERTENCIA: No hay barras para visualizar")
            else:
                # Crear figura interactiva
                print(f"\nGenerando visualización 3D interactiva...")
                print(f"  - {len(estructura.nodos)} nodos")
                print(f"  - {len(estructura.barras)} barras")
                
                fig = plot_estructura_interactiva(estructura.nodos, estructura.barras, nodos_dict)
                
                print("\nAbriendo visualización en el navegador...")
                print("Instrucciones:")
                print("- Pasa el mouse sobre barras o nodos para ver sus propiedades")
                print("- Usa el mouse para rotar, hacer zoom y pan en la vista 3D")
                print("- Nodos rojos tienen restricciones, nodos verdes son libres")
                
                # Guardar HTML directamente (más confiable que show())
                html_file = Path(__file__).parent / "estructura_visualizacion.html"
                print(f"\nGuardando visualización en archivo HTML...")
                fig.write_html(str(html_file), include_plotlyjs='cdn')
                print(f"[OK] Visualizacion guardada en: {html_file}")
                
                # Intentar abrir en el navegador
                try:
                    import webbrowser
                    print("Abriendo en el navegador...")
                    webbrowser.open(f"file://{html_file.absolute()}")
                    print("[OK] Archivo abierto en el navegador")
                except Exception as e:
                    print(f"[AVISO] No se pudo abrir automaticamente: {e}")
                    print(f"   Por favor, abre manualmente: {html_file.absolute()}")
                
                # También intentar show() como alternativa
                try:
                    print("\nTambién intentando mostrar con Plotly...")
                    fig.show(renderer='browser')
                except Exception as e:
                    print(f"[AVISO] No se pudo mostrar con Plotly directamente: {e}")
                    print(f"   Usa el archivo HTML guardado: {html_file}")
        except Exception as e:
            print(f"\nERROR al generar visualización: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nNo se pudo generar la visualización (Plotly no disponible)")
    
    print("\n" + "=" * 80)
    print("¡Proceso completado exitosamente!")
    print("=" * 80)

    #parahacerpush#
    #para hacer otro push#