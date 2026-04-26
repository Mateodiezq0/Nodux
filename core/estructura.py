from dataclasses import dataclass, field
import numpy as np
from core.carga_puntual import CargaPuntual
from core.barra import Barra
from core.carga_nodal import CargaNodal
from core.carga_puntual import CargaPuntual
from core.nodos import Nodo
from typing import List, Optional
from math import radians, cos, sin, pi

@dataclass
class Estructura:
    nodos: List[Nodo] = field(default_factory=list)
    barras: List[Barra] = field(default_factory=list)
    cargas_nodales: List[CargaNodal] = field(default_factory=list)
    cargas: List = field(default_factory=list)
    vector_nodal_equivalente: Optional[np.ndarray] = None
    desplazamientos: Optional[np.ndarray] = None
    K_global: Optional[np.ndarray] = None
    reacciones: Optional[np.ndarray] = None
    
    def agregar_nodo(self, nodo):
        self.nodos.append(nodo)

    def agregar_barra(self, barra: Barra):
        barra.calcular_longitud_y_bases()  # Asegura que la barra tenga su longitud y bases calculadas
        self.barras.append(barra)

    def agregar_carga_nodal(self, carga):
        self.cargas_nodales.append(carga)

    def agregar_carga(self, carga):
        self.cargas.append(carga)


    def ensamble_vector_cargas_nodales_equivalentes(self):
        """
        Ensambla los vectores nodales equivalentes (ya en global) de TODAS las barras.
        Suma cada barra en su nodo inicial y final.
        """
        n_nodos = len(self.nodos)
        dof_por_nodo = 6

        for barra in self.barras:
            barra.actualizar_reacciones_global()
        # Vector global de fuerzas nodales equivalentes (inicialmente en ceros)
        vector_global = np.zeros(n_nodos * dof_por_nodo)

        for barra in self.barras:
            #barra.conversion_local_global()
            # Suponiendo: barra.reaccion_total_global ya es vector 12, ya global
            #f_eq = barra.reaccion_total_global  # O el nombre que usás, pero ya GLOBAL

            # Ids de nodos
            idx_i = (barra.nodo_i - 1) * dof_por_nodo
            idx_j = (barra.nodo_f - 1) * dof_por_nodo

            # Sumo para cada nodo de la barra
            vector_global[idx_i:idx_i+6] += barra.reaccion_nudo_i_equivalente_global
            #print(f"Barra {barra.id} - Nodo inicial EQUIVALENTE GLOBAL {barra.nodo_i}: {barra.reaccion_nudo_i_equivalente_global}"
                  #f" (ESTO ES LO QUE QUIERO VER DEL ENSAMBLE INICIAL {idx_i}:{idx_i+6})")
            vector_global[idx_j:idx_j+6] += barra.reaccion_nudo_f_equivalente_global
            #print(f"Barra {barra.id} - Nodo final EQUIVALENTE GLOBAL {barra.nodo_f}: {barra.reaccion_nudo_f_equivalente_global}"
                  #f" (ESTO ES LO QUE QUIERO VER DEL ENSAMBLE FINAL {idx_j}:{idx_j+6})")
        
        for carga_nodal in self.cargas_nodales:
            nodo_id = (carga_nodal.nodo_id - 1) * dof_por_nodo
            carga = carga_nodal.vector()
            print(
                f"\n[Ensamble F global] Carga nodal en nodo {carga_nodal.nodo_id} "
                f"(DOFs globales {nodo_id} a {nodo_id + 5})"
            )
            print(
                f"  Incremento [Fx,Fy,Fz,Mx,My,Mz] = "
                f"[{carga[0]}, {carga[1]}, {carga[2]}, {carga[3]}, {carga[4]}, {carga[5]}]"
            )
            vector_global[nodo_id:nodo_id+6] += carga
            print(f"  Vector F global completo tras sumar: {vector_global}")

        self.vector_nodal_equivalente = vector_global
        #print("Vector nodal equivalente (global): IMPORTANTISIMO", vector_global)
        return vector_global
    
    def ensamble_matriz_global(self):
        """
        Ensambla la matriz global de rigidez K para toda la estructura.
        Devuelve la matriz K global (n_nodos*6 x n_nodos*6)
        """
        n_nodos = len(self.nodos)
        dof_por_nodo = 6
        size = n_nodos * dof_por_nodo
        K_global = np.zeros((size, size))

        for barra in self.barras:
            K_b = barra.Kglobal()  # Matriz 12x12, ya en global
            idx_i = (barra.nodo_i - 1) * dof_por_nodo
            idx_j = (barra.nodo_f - 1) * dof_por_nodo

            # Mapear los 12 DOFs de la barra a los DOFs globales
            dofs = [
                idx_i + 0, idx_i + 1, idx_i + 2, idx_i + 3, idx_i + 4, idx_i + 5,
                idx_j + 0, idx_j + 1, idx_j + 2, idx_j + 3, idx_j + 4, idx_j + 5,
            ]

            # Ensamblado (sumar K_b en la K_global)
            for a in range(12):
                for b in range(12):
                    K_global[dofs[a], dofs[b]] += K_b[a, b]
            
            #print(K_b)
            #print()

        self.K_global = K_global
        #print("==========XDXDXD=========")
        #print(K_global)
        return K_global

    def resolver_desplazamientos(self, debug=0):
        """
        Resuelve K*D=F eliminando ecuaciones (filas y columnas) con desplazamientos prescritos.
        ¡Debug incluido paso a paso!
        """
        # 1. Ensamblar matrices si hace falta
        if not hasattr(self, "K_global") or self.K_global is None:
            self.ensamble_matriz_global()
        if not hasattr(self, "vector_nodal_equivalente") or self.vector_nodal_equivalente is None:
            self.ensamble_vector_cargas_nodales_equivalentes()
        
        K = self.K_global
        F = self.vector_nodal_equivalente.copy()
        ndofs = len(F)
        dof_por_nodo = 6

        # 2. Identificar DOFs fijos (prescritos) y libres
        prescripciones = np.full(ndofs, np.nan)
        for nodo in self.nodos:
            base = (nodo.id - 1) * dof_por_nodo
            if hasattr(nodo, "restricciones") and nodo.restricciones is not None:
                for i in range(dof_por_nodo):
                    if nodo.restricciones[i]:
                        prescripciones[base + i] = nodo.valores_prescritos[i]
        idx_fijos = np.where(~np.isnan(prescripciones))[0]
        idx_libres = np.where(np.isnan(prescripciones))[0]
        if debug:
            print("\n--- Debug de restricciones ---")
            print("Prescripciones:", prescripciones)
            print("Índices fijos:", idx_fijos)
            print("Índices libres:", idx_libres)

        # 3. Formar el sistema reducido: Kll @ Dl = Fl
        Kll = K[np.ix_(idx_libres, idx_libres)]
        Fl = F[idx_libres]
        # Conservar para inspección / export (p. ej. Excel)
        self.idx_libres = np.asarray(idx_libres, dtype=np.int64).copy()
        self.Kll = np.asarray(Kll, dtype=np.float64).copy()
        self.Fl = np.asarray(Fl, dtype=np.float64).copy()
        if debug:
            print("\n--- Sistema reducido ---")
            print("Kll:\n", Kll)
            print("Fl:\n", Fl)
            print("Shape de Kll:", Kll.shape)

        # 4. Resolver el sistema reducido
        Dl = np.linalg.solve(Kll, Fl)
        if debug:
            print("\n--- Solución de desplazamientos libres ---")
            print("Dl (libres):", Dl)

        # 5. Armar el vector de desplazamientos globales
        D = np.zeros(ndofs)
        D[idx_libres] = Dl
        D[idx_fijos] = prescripciones[idx_fijos]
        if debug:
            print("\n--- Vector de desplazamientos global D ---")
            print(D)

        self.desplazamientos = D
        return D

    def calcular_reacciones(self, debug=0):
        """
        Calcula las fuerzas y momentos internos (vector de solicitaciones) en los extremos de cada barra,
        en coordenadas globales.
        Devuelve:
            lista_solicitaciones: Lista de np.ndarray (cada uno de 12,) con las solicitaciones de cada barra.
        """
        if self.desplazamientos is None:
            raise ValueError("Primero tenés que resolver la estructura (llamá a .resolver())")

        lista_solicitaciones = []
        dof_por_nodo = 6
        D = self.desplazamientos

        for barra in self.barras:
            #barra.conversion_local_global()  # Asegura reacciones en global

            D_barra = np.zeros(12)
            nodo_i_obj = barra.nodo_i_obj
            nodo_f_obj = barra.nodo_f_obj

            # Nodo inicial
            if nodo_i_obj is not None:
                idx_i = (barra.nodo_i - 1) * dof_por_nodo
                D_barra[:6] = D[idx_i:idx_i+6]

            # Nodo final
            if nodo_f_obj is not None:
                idx_j = (barra.nodo_f - 1) * dof_por_nodo
                D_barra[6:] = D[idx_j:idx_j+6]

            # Matriz global de la barra (12x12)
            K_barra = barra.Kglobal()

            # Vector de reacciones de empotramiento de barra #RE MAL
            #LE PUSE UN SIGNO MENOS PORQUE LO OTRO ERA PARA OBTENER EL NODAL
            f_reacciones_empotramiento_de_barra = - (barra.reaccion_de_empotramiento_global.copy())
            

            #print(f"vector de empotramiento de barra {barra.id}: {f_reacciones_empotramiento_de_barra}")

            # Solicitaciones internas (F = K*D + Femp)
            F_interna_sin_empotramiento = K_barra @ D_barra
            F_interna = F_interna_sin_empotramiento + f_reacciones_empotramiento_de_barra

            if debug:
                print(f"\nBarra {barra.id}:")
                print("D_barra:", D_barra)
                print("K_barra:\n", K_barra)
                print("F_emp_barra:", f_reacciones_empotramiento_de_barra)
                print("F_interna sin empotramiento:", F_interna_sin_empotramiento)
                print("F interna final:", F_interna)
                print("  --- fin debug barra ---")

            lista_solicitaciones.append(F_interna)
        self.reacciones = np.array(lista_solicitaciones)
        return lista_solicitaciones #No es solicitaciones, es reacciones xd
    
    def calcular_reacciones_locales(self):
        if not hasattr(self, "reacciones") or self.reacciones is None:
            self.calcular_reacciones()

        R = self.reacciones
        R_local = np.zeros((len(self.barras), 12))   # N cantidad de vectores de 3
        for idx_barra, barra in enumerate(self.barras):
            
            coso_rotacion = barra.matriz_A(np.radians(barra.tita or 0.0))
            coso_rotacion_4x3 = barra.bloque_diagonal_4x3(coso_rotacion)
            
            R_local_temp = coso_rotacion_4x3 @ R[idx_barra]

            submatriz_rotacion_xd = barra.calcular_submatriz_de_rotacion()
            submatriz_rotacion_xd_4x3 = barra.bloque_diagonal_4x3(submatriz_rotacion_xd)

            R_local[idx_barra, :] = submatriz_rotacion_xd_4x3 @ R_local_temp

        return R_local

            


       
       
       


