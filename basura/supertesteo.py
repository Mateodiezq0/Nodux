import os
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
    from plot.plot import mostrar_dibujos_matplotlib_pestanas
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
    # Nodo 3 está restringido solo en el sentido VERTICAL (Z) de cargas, todo lo otro es libre
    nodo3.restricciones = [False, False, True, False, False, False]  # Solo Z restringido
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
    E = 20000  # kN/cm²
    A = 100   # cm²
    I_y = 833  # cm⁴
    I_z = 833  # cm⁴
    G = 7720   # Tn/cm²
    J = 1408   # cm⁴
    
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
    from pathlib import Path as _Path

    from cli.resultados_export import collect_resultados_dataframes, write_resultados_excel

    ruta_excel = _Path(__file__).parent / nombre_archivo
    dfs = collect_resultados_dataframes(estructura, F_internas)
    write_resultados_excel(ruta_excel, dfs)

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

                # Guardar HTML por si querés ver la versión Plotly a mano (no se abre el navegador).
                html_file = Path(__file__).parent / "estructura_visualizacion.html"
                print(f"\nGuardando visualización Plotly en HTML (opcional)...")
                fig.write_html(str(html_file), include_plotlyjs='cdn')
                print(f"[OK] Archivo guardado: {html_file}")

                # Visualización matplotlib: pestañas Dibujo_Estructura + Dibujo_Fuerzas
                try:
                    print("\nAbriendo ventana con pestañas (Estructura / Fuerzas / V_y / V_z / N_x / M_y / M_z / M_x)...")
                    mostrar_dibujos_matplotlib_pestanas(
                        estructura.nodos,
                        estructura.barras,
                        nodos_dict,
                        cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
                        ipn_dims={"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0},
                        escala_seccion=1.0,
                        mostrar_ejes_locales=True,
                        longitud_vector=45.0,
                        escala_diagrama_corte=1.0,
                    )
                except Exception as e:
                    print(f"[AVISO] No se pudieron mostrar los dibujos matplotlib: {e}")

                # PyVista + export .vtm para ParaView (opcional: HYPERSTATIC_PYVISTA=1)
                _pv = os.environ.get("HYPERSTATIC_PYVISTA", "").strip().lower()
                if _pv in ("1", "true", "yes", "on"):
                    try:
                        from plot.pyvista_pestanas import (
                            export_paraview_todo,
                            mostrar_dibujos_pyvista_pestanas,
                        )

                        vtm_path = Path(__file__).parent / "supertesteo_paraview_todo.vtm"
                        print("\nExportando MultiBlock VTK completo para ParaView...")
                        export_paraview_todo(
                            vtm_path,
                            estructura.nodos,
                            estructura.barras,
                            nodos_dict,
                            cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
                            ipn_dims={"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0},
                            escala_seccion=1.0,
                            escala_diagrama=1.0,
                            longitud_vector=45.0,
                        )
                        print(f"[OK] Archivo (y bloques asociados): {vtm_path}")
                        print("  Abrí el .vtm en ParaView: File - Open - elegir supertesteo_paraview_todo.vtm")

                        print("\nAbriendo ventana PyVista con pestañas (todas las vistas)...")
                        mostrar_dibujos_pyvista_pestanas(
                            estructura.nodos,
                            estructura.barras,
                            nodos_dict,
                            cargas_nodales=getattr(estructura, "cargas_nodales", None) or [],
                            ipn_dims={"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0},
                            escala_seccion=1.0,
                            mostrar_ejes_locales=True,
                            longitud_vector=45.0,
                            escala_diagrama_corte=1.0,
                            desplazamientos=getattr(estructura, "desplazamientos", None),
                        )
                    except ImportError as ie:
                        print(f"[AVISO] PyVista no disponible: {ie}")
                    except Exception as e:
                        print(f"[AVISO] PyVista/ParaView export: {e}")
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