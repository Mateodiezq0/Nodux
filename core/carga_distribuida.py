from dataclasses import dataclass, field
from core.carga_puntual import CargaPuntual
import numpy as np
from typing import List

class CargaDistribuida(CargaPuntual):
    
    id: int

    x: float  # Posición de inicio de la carga 
    y: float  # Posición de inicio de la carga 
    z: float  # Posición de inicio de la carga 

    q: float  # Magnitud de la carga (fuerza o momento) (En KN, teniendo en cuenta que si el numero es positivo, la carga es hacia arriba, y si es negativo, hacia abajo) 
    q_f: float  # Magnitud final de la carga (fuerza o momento) (En KN, teniendo en cuenta que si el numero es positivo, la carga es hacia arriba, y si es negativo, hacia abajo)

    alpha_x: float  # Ángulo respecto al eje X
    alpha_y: float  # Ángulo respecto al eje Y
    alpha_z: float  # Ángulo respecto al eje Z


    x_f: float  # Posición de final de la carga 
    y_f: float  # Posición de final de la carga
    z_f: float  # Posición de final de la carga

    


    def reacciones_de_empotramiento(self, barra):
        if self.q == self.q_f:
            # Unificar criterio con carga puntual: asegurar base local y usar R(3x3)
            barra.calcular_longitud_y_bases()

            # Variables
            L = barra.L
            q = self.q
            c = np.linalg.norm(np.array([self.x_f, self.y_f, self.z_f]) - np.array([self.x, self.y, self.z]))
            
            # Determinar la distancia a los nodos
            if (np.linalg.norm(barra.nodo_i_obj.get_coord()) <= np.linalg.norm(barra.nodo_f_obj.get_coord())):  # Nodo más cercano al origen
                a = np.linalg.norm(np.array([self.x, self.y, self.z]) - barra.nodo_i_obj.get_coord()) + c / 2
            else:
                a = np.linalg.norm(np.array([self.x, self.y, self.z]) - barra.nodo_f_obj.get_coord()) + c / 2
            
            b = L - a

            print("L:", L)
            print("a:", a)
            print("b:", b)
            print("c:", c)

            # Proyección de la carga global a la local
            alpha_x = np.radians(self.alpha_x)
            alpha_y = np.radians(self.alpha_y)
            alpha_z = np.radians(self.alpha_z)
            
            # Resultante global equivalente de la distribuida uniforme: F = q * c
            # (misma dirección global definida por alpha_x/alpha_y/alpha_z)
            v_carga_global = (q * c) * np.array([np.cos(alpha_x), np.cos(alpha_y), np.cos(alpha_z)])
            print("v_carga_global:", v_carga_global)

            # Calcular la base local de la barra (misma matriz usada por carga puntual)
            r_base = barra.construir_matriz_rotacion_R_3x3()
            print("r_base:", r_base)
            
            # Proyección de la carga en el sistema local de la barra
            f_local = r_base @ v_carga_global  # [Fx, Fy, Fz]
            self.f_local = f_local.copy()
            print("f_local:", f_local)

            # Posición relativa de la carga
            nodo_i = barra.nodo_i_obj.get_coord()
            pos_carga = np.array([self.x, self.y, self.z])
            vec_ic = pos_carga - nodo_i
            li = np.dot(vec_ic, barra.x_local)  # Proyección sobre Xlocal (longitud)
            lj = barra.L - li  # Posición relativa sobre la barra

            # Reacciones de empotramiento (fuerzas y momentos) - Local
            N = f_local[0]
            Ni = N * (b / barra.L)
            Nj = N * (a / barra.L)

            Qy = f_local[1]
            print("Qy:", Qy)
            Qz = f_local[2]
            print("Qz:", Qz)

            # Momento en Z_local por Qy
            v_reaccion_global = -v_carga_global
            reaccion_momento_global = np.cross(barra.x_local, v_reaccion_global)
            reaccion_momento_global_unitario = reaccion_momento_global / np.linalg.norm(reaccion_momento_global)
            signo_mz = np.sign(np.dot(reaccion_momento_global_unitario, barra.z_local)) or 1
            print("signo_mz:", signo_mz)

            A0 = (Qy * b * c) / L
            B0 = (Qy * a * c) / L

            Mi_z = - (Qy * c / (12 * L ** 2)) * ((4 * L ** 2 - c ** 2) * (2 * b - a) - 4 * (2 * b ** 3 - a ** 3))
            print("Mi_z:", Mi_z)
            Mj_z = - (Qy * c / (12 * L ** 2)) * ((4 * L ** 2 - c ** 2) * (2 * a - b) - 4 * (2 * a ** 3 - b ** 3))
            print("Mj_z:", Mj_z)

            Qi_y = A0 + ((Mj_z - Mi_z) / L)
            Qj_y = B0 + ((Mi_z - Mj_z) / L)

            # Momento en Y_local por Qz
            signo_my = np.sign(np.dot(reaccion_momento_global_unitario, barra.y_local)) or 1
            print("signo_my:", signo_my)
            A0_z = (Qz * b * c) / L
            B0_z = (Qz * a * c) / L


            Mi_y = - (Qz * c / (12 * L ** 2)) * ((4 * L ** 2 - c ** 2) * (2 * b - a) - 4 * (2 * b ** 3 - a ** 3))
            Mj_y = - (Qz * c / (12 * L ** 2)) * ((4 * L ** 2 - c ** 2) * (2 * a - b) - 4 * (2 * a ** 3 - b ** 3))
            Qi_z = A0_z + (Mj_y - Mi_y) / L
            Qj_z = B0_z + (Mi_y - Mj_y) / L



            # Vector de fuerzas nodales equivalentes (12)
            f_empotramiento = np.zeros(12)

            # Nodo inicial (i)
            f_empotramiento[0] = -Ni        # Axial (X_local)
            f_empotramiento[1] = -Qi_y      # Cortante (Y_local)
            f_empotramiento[2] = -Qi_z      # Cortante (Z_local)
            f_empotramiento[4] =  signo_my * Mi_y      # Momento flexor en Y_local
            f_empotramiento[5] =  signo_mz  * Mi_z      # Momento flexor en Z_local

            # Nodo final (j)
            f_empotramiento[6] = -Nj
            f_empotramiento[7] = -Qj_y
            f_empotramiento[8] = -Qj_z
            f_empotramiento[10] = - signo_my * Mj_y
            f_empotramiento[11] = - signo_mz * Mj_z

            # Suma a la reacción total
            print(f"Reacciones de empotramiento de la carga distribuida {self.id} en barra {barra.id}:")
            barra.reaccion_de_empotramiento_local_total += f_empotramiento
            print("Reacción de empotramiento TOTAL:", barra.reaccion_de_empotramiento_local_total) 
            barra.reaccion_de_empotramiento_i_local += f_empotramiento[:6]
            print("Reacción de empotramiento del nudo i:", barra.reaccion_de_empotramiento_i_local) 
            barra.reaccion_de_empotramiento_f_local += f_empotramiento[6:]
            print("Reacción de empotramiento del nudo f:", barra.reaccion_de_empotramiento_f_local)

            return barra.reaccion_de_empotramiento_local_total


    def __init__(self, id: int, x: float, y: float, z: float, q: float,x_f: float, y_f: float, z_f: float, q_f: float, alpha_x: float = 0.0, alpha_y: float = 0.0, alpha_z: float = 0.0):
        self.id = id
        self.x = x
        self.y = y
        self.z = z
        self.q = q
        self.x_f = x_f
        self.y_f = y_f
        self.z_f = z_f
        self.q_f = q_f
        self.alpha_x = alpha_x
        self.alpha_y = alpha_y
        self.alpha_z = alpha_z