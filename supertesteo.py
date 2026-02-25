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
    Incluye:
    - Reacciones de empotramiento (local y global) por barra
    - Fuerzas internas (F_interna) por barra (global)
    """
    # Nombres de los DOFs
    nombres_dofs = [
        "Fx_i", "Fy_i", "Fz_i", "Mx_i", "My_i", "Mz_i",
        "Fx_f", "Fy_f", "Fz_f", "Mx_f", "My_f", "Mz_f"
    ]
    
    # ========== REACCIONES DE EMPOTRAMIENTO ==========
    datos_reacciones_local = []
    datos_reacciones_global = []
    
    for barra in estructura.barras:
        # Reacciones en local
        reacc_local = barra.reaccion_de_empotramiento_local_total
        datos_reacciones_local.append({
            'Barra ID': barra.id,
            'Nodo Inicial': barra.nodo_i,
            'Nodo Final': barra.nodo_f,
            **{nombres_dofs[i]: reacc_local[i] for i in range(12)}
        })
        
        # Reacciones en global
        reacc_global = barra.reaccion_de_empotramiento_global
        datos_reacciones_global.append({
            'Barra ID': barra.id,
            'Nodo Inicial': barra.nodo_i,
            'Nodo Final': barra.nodo_f,
            **{nombres_dofs[i]: reacc_global[i] for i in range(12)}
        })
    
    df_reacciones_local = pd.DataFrame(datos_reacciones_local)
    df_reacciones_global = pd.DataFrame(datos_reacciones_global)
    
    # ========== FUERZAS INTERNAS (F_INTERNA) ==========
    datos_fuerzas_internas = []
    
    for idx, barra in enumerate(estructura.barras):
        F_interna = F_internas[idx]
        datos_fuerzas_internas.append({
            'Barra ID': barra.id,
            'Nodo Inicial': barra.nodo_i,
            'Nodo Final': barra.nodo_f,
            **{nombres_dofs[i]: F_interna[i] for i in range(12)}
        })
    
    df_fuerzas_internas = pd.DataFrame(datos_fuerzas_internas)
    
    # ========== RESUMEN POR BARRA ==========
    datos_resumen = []
    for idx, barra in enumerate(estructura.barras):
        F_interna = F_internas[idx]
        # Extraer fuerzas y momentos en nodo inicial y final
        datos_resumen.append({
            'Barra ID': barra.id,
            'Nodo Inicial': barra.nodo_i,
            'Nodo Final': barra.nodo_f,
            'Longitud (cm)': barra.L if barra.L is not None else 0.0,
            'Fx_i (kN)': F_interna[0],
            'Fy_i (kN)': F_interna[1],
            'Fz_i (kN)': F_interna[2],
            'Mx_i (kN·cm)': F_interna[3],
            'My_i (kN·cm)': F_interna[4],
            'Mz_i (kN·cm)': F_interna[5],
            'Fx_f (kN)': F_interna[6],
            'Fy_f (kN)': F_interna[7],
            'Fz_f (kN)': F_interna[8],
            'Mx_f (kN·cm)': F_interna[9],
            'My_f (kN·cm)': F_interna[10],
            'Mz_f (kN·cm)': F_interna[11],
        })
    
    df_resumen = pd.DataFrame(datos_resumen)
    
    # ========== REACCIONES DE EMPOTRAMIENTO POR NODO ==========
    datos_reacciones_nodo_i = []
    datos_reacciones_nodo_f = []
    
    for barra in estructura.barras:
        # Nodo inicial
        reacc_i_local = barra.reaccion_de_empotramiento_i_local
        reacc_i_global = barra.reaccion_nudo_i_equivalente_global
        datos_reacciones_nodo_i.append({
            'Barra ID': barra.id,
            'Nodo ID': barra.nodo_i,
            'Fx_local': reacc_i_local[0],
            'Fy_local': reacc_i_local[1],
            'Fz_local': reacc_i_local[2],
            'Mx_local': reacc_i_local[3],
            'My_local': reacc_i_local[4],
            'Mz_local': reacc_i_local[5],
            'Fx_global': reacc_i_global[0],
            'Fy_global': reacc_i_global[1],
            'Fz_global': reacc_i_global[2],
            'Mx_global': reacc_i_global[3],
            'My_global': reacc_i_global[4],
            'Mz_global': reacc_i_global[5],
        })
        
        # Nodo final
        reacc_f_local = barra.reaccion_de_empotramiento_f_local
        reacc_f_global = barra.reaccion_nudo_f_equivalente_global
        datos_reacciones_nodo_f.append({
            'Barra ID': barra.id,
            'Nodo ID': barra.nodo_f,
            'Fx_local': reacc_f_local[0],
            'Fy_local': reacc_f_local[1],
            'Fz_local': reacc_f_local[2],
            'Mx_local': reacc_f_local[3],
            'My_local': reacc_f_local[4],
            'Mz_local': reacc_f_local[5],
            'Fx_global': reacc_f_global[0],
            'Fy_global': reacc_f_global[1],
            'Fz_global': reacc_f_global[2],
            'Mx_global': reacc_f_global[3],
            'My_global': reacc_f_global[4],
            'Mz_global': reacc_f_global[5],
        })
    
    df_reacciones_nodo_i = pd.DataFrame(datos_reacciones_nodo_i)
    df_reacciones_nodo_f = pd.DataFrame(datos_reacciones_nodo_f)
    
    # ========== F_LOCAL Y REACCIÓN EMPOTRAMIENTO_I POR CARGA ==========
    datos_cargas_local = []
    for barra in estructura.barras:
        for carga in barra.cargas:
            datos_cargas_local.append({
                'Carga ID': carga.id,
                'Barra ID': barra.id,
                'Nodo Inicial': barra.nodo_i,
                'Nodo Final': barra.nodo_f,
                'f_local_x': carga.f_local[0],
                'f_local_y': carga.f_local[1],
                'f_local_z': carga.f_local[2],
                'Reacc_i_Fx_local': barra.reaccion_de_empotramiento_i_local[0],
                'Reacc_i_Fy_local': barra.reaccion_de_empotramiento_i_local[1],
                'Reacc_i_Fz_local': barra.reaccion_de_empotramiento_i_local[2],
                'Reacc_i_Mx_local': barra.reaccion_de_empotramiento_i_local[3],
                'Reacc_i_My_local': barra.reaccion_de_empotramiento_i_local[4],
                'Reacc_i_Mz_local': barra.reaccion_de_empotramiento_i_local[5],
                'Reacc_f_Fx_local': barra.reaccion_de_empotramiento_f_local[0],
                'Reacc_f_Fy_local': barra.reaccion_de_empotramiento_f_local[1],
                'Reacc_f_Fz_local': barra.reaccion_de_empotramiento_f_local[2],
                'Reacc_f_Mx_local': barra.reaccion_de_empotramiento_f_local[3],
                'Reacc_f_My_local': barra.reaccion_de_empotramiento_f_local[4],
                'Reacc_f_Mz_local': barra.reaccion_de_empotramiento_f_local[5],
            })
    df_cargas_local = pd.DataFrame(datos_cargas_local)

    # ========== VECTOR NODAL EQUIVALENTE ==========
    nombres_dofs_nodo = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
    datos_vector_nodal = []
    vector_nodal = estructura.vector_nodal_equivalente
    n_nodos = len(estructura.nodos)
    for nodo in estructura.nodos:
        base = (nodo.id - 1) * 6
        fila = {'Nodo ID': nodo.id}
        for i, nombre in enumerate(nombres_dofs_nodo):
            fila[nombre] = vector_nodal[base + i]
        datos_vector_nodal.append(fila)
    df_vector_nodal = pd.DataFrame(datos_vector_nodal)
    
    # ========== ESCRIBIR A EXCEL ==========
    ruta_excel = Path(__file__).parent / nombre_archivo
    
    with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
        # Hoja 1: Resumen
        df_resumen.to_excel(writer, sheet_name='Resumen_Fuerzas_Internas', index=False)
        
        # Hoja 2: Fuerzas Internas (completo)
        df_fuerzas_internas.to_excel(writer, sheet_name='F_Interna_Global', index=False)
        
        # Hoja 3: Reacciones de Empotramiento Local
        df_reacciones_local.to_excel(writer, sheet_name='Reacciones_Empot_Local', index=False)
        
        # Hoja 4: Reacciones de Empotramiento Global
        df_reacciones_global.to_excel(writer, sheet_name='Reacciones_Empot_Global', index=False)
        
        # Hoja 5: Reacciones por Nodo Inicial
        df_reacciones_nodo_i.to_excel(writer, sheet_name='Reacciones_Nodo_Inicial', index=False)
        
        # Hoja 6: Reacciones por Nodo Final
        df_reacciones_nodo_f.to_excel(writer, sheet_name='Reacciones_Nodo_Final', index=False)
        
        # Hoja 7: Vector Nodal Equivalente
        df_vector_nodal.to_excel(writer, sheet_name='Vector_Nodal_Equivalente', index=False)
        
        # Hoja 8: f_local y Reacción Empotramiento_i por Carga
        df_cargas_local.to_excel(writer, sheet_name='f_local_Reacc_i_por_Carga', index=False)
        
        # Ajustar ancho de columnas
        from openpyxl.utils import get_column_letter
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            df = None
            if sheet_name == 'Resumen_Fuerzas_Internas':
                df = df_resumen
            elif sheet_name == 'F_Interna_Global':
                df = df_fuerzas_internas
            elif sheet_name == 'Reacciones_Empot_Local':
                df = df_reacciones_local
            elif sheet_name == 'Reacciones_Empot_Global':
                df = df_reacciones_global
            elif sheet_name == 'Reacciones_Nodo_Inicial':
                df = df_reacciones_nodo_i
            elif sheet_name == 'Reacciones_Nodo_Final':
                df = df_reacciones_nodo_f
            elif sheet_name == 'Vector_Nodal_Equivalente':
                df = df_vector_nodal
            elif sheet_name == 'f_local_Reacc_i_por_Carga':
                df = df_cargas_local
            
            if df is not None:
                for idx, col_name in enumerate(df.columns, 1):
                    column_letter = get_column_letter(idx)
                    max_length = max(
                        len(str(col_name)),
                        df[col_name].astype(str).map(len).max() if len(df) > 0 else 0
                    )
                    adjusted_width = min(max_length + 2, 25)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"\nArchivo Excel creado: {ruta_excel}")
    print("\nHojas creadas:")
    print("  1. Resumen_Fuerzas_Internas - Resumen de fuerzas y momentos por barra")
    print("  2. F_Interna_Global - Fuerzas internas completas (12 DOFs) en global")
    print("  3. Reacciones_Empot_Local - Reacciones de empotramiento en coordenadas locales")
    print("  4. Reacciones_Empot_Global - Reacciones de empotramiento en coordenadas globales")
    print("  5. Reacciones_Nodo_Inicial - Reacciones en nodo inicial por barra")
    print("  6. Reacciones_Nodo_Final - Reacciones en nodo final por barra")
    print("  7. Vector_Nodal_Equivalente - Vector de cargas nodales equivalentes ensamblado (por nodo)")
    print("  8. f_local_Reacc_i_por_Carga - f_local (fuerza en local) y reacciones de empotramiento i/f por carga")

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
                print(f"✓ Visualización guardada en: {html_file}")
                
                # Intentar abrir en el navegador
                try:
                    import webbrowser
                    print("Abriendo en el navegador...")
                    webbrowser.open(f"file://{html_file.absolute()}")
                    print("✓ Archivo abierto en el navegador")
                except Exception as e:
                    print(f"⚠ No se pudo abrir automáticamente: {e}")
                    print(f"   Por favor, abre manualmente: {html_file.absolute()}")
                
                # También intentar show() como alternativa
                try:
                    print("\nTambién intentando mostrar con Plotly...")
                    fig.show(renderer='browser')
                except Exception as e:
                    print(f"⚠ No se pudo mostrar con Plotly directamente: {e}")
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