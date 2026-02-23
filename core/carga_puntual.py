from dataclasses import dataclass, field
import numpy as np
from typing import List
from typing import List, Optional, Tuple
from math import radians, cos, sin, pi



class CargaPuntual:

    id: int
    x: float  # Posición de inicio de la carga 
    y: float  # Posición de inicio de la carga 
    z: float  # Posición de inicio de la carga 
    F_x: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(3))  
    F_y: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(3))
    F_z: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(3))

    def __init__(self, id=None, x=0.0, y=0.0, z=0.0, q=0.0, F_x = [0,0,0], F_y = [0,0,0], F_z = [0,0,0]):
        self.id = id
        self.x = x  # Posición de inicio de la carga 
        self.y = y  # Posición de inicio de la carga 
        self.z = z  # Posición de inicio de la carga 
        self.F_x = F_x  # Fuerza en X
        self.F_y = F_y  # Fuerza en Y
        self.F_z = F_z  # Fuerza en Z
        self.f_local = np.zeros(3)  # Fuerza en coordenadas locales de la barra


def reacciones_de_empotramiento(self, barra):
        """
        Calcula las reacciones equivalentes en los extremos de la barra
        debidas a una carga puntual en cualquier parte de la barra, usando sistema local.
        Convención:
        - Xlocal = longitud de barra (de nodo_i a nodo_f)
        - Zlocal = "horizontal" (Yglobal si barra es Xglobal)
        - Ylocal = "vertical" (Zglobal si barra es Xglobal)
        Retorna un vector de fuerzas nodales equivalentes (12) en local.
        
        El vector de carga se calcula aplicando rotaciones alrededor de los ejes:
        - Rotaciones: alpha_z -> alpha_y -> alpha_x (orden Z, Y, X)
        - Rotación positiva = antihorario (regla de la mano derecha)
        """
        # 1. Asegura la base local correcta siempre
        barra.calcular_longitud_y_bases()

        r_base = barra.construir_matriz_rotacion_R_3x3()

        print("F_x:", np.shape(self.F_x))
        print("F_y:", np.shape(self.F_y))
        print("F_z:", np.shape(self.F_z))
        
        v_carga_global = np.sum(np.array([self.F_x, self.F_y, self.F_z]), axis=0) #Dos siempre van a ser 0, por lo que aislo nomas
        print("v_carga_global:", v_carga_global)

        f_local = r_base @ v_carga_global  # [Fx, Fy, Fz]
        self.f_local = f_local  # Guardar para exportación
    
        print("f_local:", f_local)  #RE BIEN

        # 3. Posición relativa de la carga
        nodo_i = barra.nodo_i_obj.get_coord()
        pos_carga = np.array([self.x, self.y, self.z])
        vec_ic = pos_carga - nodo_i
        #print("Vector desde nodo_i a carga:", vec_ic)
        li = np.dot(vec_ic, barra.x_local)  # Proyectado sobre Xlocal (longitud)
        lj = barra.L - li #bien

        # Axial (esto siempre igual)
        N = f_local[0]
        Ni = N * (lj / barra.L)
        Nj = N * (li / barra.L)

        # Cortantes locales
        Qy = f_local[1]
        #print("Qy:", Qy)
        Qz = f_local[2]
        #print("Qz:", Qz)

        # -------- FLEXIÓN POR Qy (Momento en Z_local) ----------
        # Fuerza local en Y

        #fy_prueba = f_local * self.y_local
        #fz_prueba = f_local * self.z_local
        #print("Proyección de la fuerza local en Yglobal:", fy_prueba)
        #print("Proyección de la fuerza local en Zglobal:", fz_prueba)  RE MAL

        #fuerza_y = -fy_prueba
        #fuerza_y = np.array([0, Qy, 0])
        
        
        #print("fuerza_y:", fuerza_y)
        #momento_z_vec = np.cross(self.x_local,fuerza_y)
        #print("momento_z_vec:", momento_z_vec)
        #print("eje_z_local:", self.z_local)
        #signo_mz = np.sign(np.dot(momento_z_vec, self.z_local)) or 1    
        #print("signo_mz:", signo_mz)
        """ voy a hacer una prueba con lo que dije"""
        v_reaccion_global = - v_carga_global

        reaccion_momento_global = np.cross(barra.x_local, v_reaccion_global)
        reaccion_momento_global_unitario = reaccion_momento_global / np.linalg.norm(reaccion_momento_global)
        signo_mz = np.sign(np.dot(reaccion_momento_global_unitario, barra.z_local)) or 1

        Qi_y = Qy * ((lj / barra.L)**2) * (3 - 2 * (lj / barra.L))
        Qj_y = Qy * ((li / barra.L)**2) * (3 - 2 * (li / barra.L))
        Mi_z = signo_mz * (abs(Qy) * li * ((lj / barra.L)**2))
        #print("Mi_z:", Mi_z)
        Mj_z = - signo_mz * (abs(Qy) * lj * ((li / barra.L)**2))
        #print("Mj_z:", Mj_z)

        # -------- FLEXIÓN POR Qz (Momento en Y_local) ----------
        
        #fuerza_z= -fz_prueba
        #fuerza_z = np.array([0, 0, Qz])
        
        
        #print("fuerza_z:", fuerza_z)
        #momento_y_vec = np.cross(self.x_local, fuerza_z)
        #print("momento_y_vec:", momento_y_vec)
        #signo_my = np.sign(np.dot(momento_y_vec, self.y_local)) or 1
        #print("signo_my:", signo_my)

        signo_my = np.sign(np.dot(reaccion_momento_global_unitario, barra.y_local)) or 1

        Qi_z = Qz * ((lj / barra.L)**2) * (3 - 2 * (lj / barra.L))
        Qj_z = Qz * ((li / barra.L)**2) * (3 - 2 * (li / barra.L))
        Mi_y = signo_my * (abs(Qz) * li * ((lj / barra.L)**2))
        #print("Mi_y:", Mi_y)
        Mj_y = - signo_my * (abs(Qz) * lj * ((li / barra.L)**2))
        #print("Mj_y:", Mj_y)

        # 5. Vector de fuerzas nodales equivalentes (12) - tu convención
        f_empotramiento = np.zeros(12)
        # Nodo inicial (i)
        f_empotramiento[0] = -Ni        # Axial (X_local)
        f_empotramiento[1] = -Qi_y      # Cortante (Y_local)
        f_empotramiento[2] = -Qi_z      # Cortante (Z_local)
        f_empotramiento[4] =  Mi_y      # Momento flexor en Y_local
        f_empotramiento[5] =  Mi_z      # Momento flexor en Z_local

        # Nodo final (j)
        f_empotramiento[6] = -Nj
        f_empotramiento[7] = -Qj_y
        f_empotramiento[8] = -Qj_z
        f_empotramiento[10] = Mj_y
        f_empotramiento[11] = Mj_z

        # (Si tenés que sumar torsión o momento puntual, agregar f_emp[3] y f_emp[9])

        # SUMA a la reacción total
        #print()
        #print()
        print(f"Reacciones de empotramiento de la carga {self.id} en barra {barra.id}:")
        barra.reaccion_de_empotramiento_local_total += f_empotramiento
        print("Reacción de empotramiento TOTAL:", barra.reaccion_de_empotramiento_local_total) #RE BIEN VERIFICADISIMO
        barra.reaccion_de_empotramiento_i_local += f_empotramiento[:6]
        print("Reacción de empotramiento del nudo i:", barra.reaccion_de_empotramiento_i_local) #RE BIEN VERIFICADISIMO
        barra.reaccion_de_empotramiento_f_local += f_empotramiento[6:]
        print("Reacción de empotramiento del nudo f:", barra.reaccion_de_empotramiento_f_local) #RE BIEN VERIFICADISIMO
        #print()
        #print()
        return barra.reaccion_de_empotramiento_local_total
    

