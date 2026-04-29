from dataclasses import dataclass, field
import numpy as np
from typing import List
from typing import List, Optional, Tuple
from math import radians, cos, sin, pi


def _str_vec6(etiqueta: str, v: np.ndarray) -> str:
    a = np.asarray(v, dtype=float).reshape(-1)[:6]
    return (
        f"  {etiqueta} [Fx, Fy, Fz, Mx, My, Mz]: "
        f"[{a[0]:.6g}, {a[1]:.6g}, {a[2]:.6g}, {a[3]:.6g}, {a[4]:.6g}, {a[5]:.6g}]"
    )


def _str_vec12_por_nodos(etiqueta: str, v: np.ndarray) -> str:
    a = np.asarray(v, dtype=float).reshape(-1)[:12]
    i, j = a[:6], a[6:]
    return (
        f"  {etiqueta} (12 DOF locales: nodo i, luego nodo j)\n"
        f"    nodo i: [{i[0]:.6g}, {i[1]:.6g}, {i[2]:.6g}, {i[3]:.6g}, {i[4]:.6g}, {i[5]:.6g}]\n"
        f"    nodo j: [{j[0]:.6g}, {j[1]:.6g}, {j[2]:.6g}, {j[3]:.6g}, {j[4]:.6g}, {j[5]:.6g}]"
    )


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
        # Momento torsor puntual local M_x (sobre el eje de barra); 0 si no hay.
        self.mx_local = 0.0


def reacciones_de_empotramiento(self, barra):

        # 1. Asegura la base local correcta siempre
        barra.calcular_longitud_y_bases()
        print(
            f"\n{'=' * 72}\n"
            f"Carga puntual id={self.id} | Barra id={barra.id} -- reacciones de empotramiento (debug)\n"
            f"{'=' * 72}"
        )
        print("  Base local (versores unitarios; componentes en ejes globales X, Y, Z):")
        print(f"    x_local (eje de la barra): {barra.x_local}")
        print(f"    y_local:                  {barra.y_local}")
        print(f"    z_local:                  {barra.z_local}")

        r_base = barra.construir_matriz_rotacion_R_3x3()

        print(
            "  Fuerza en globales: F_x, F_y, F_z son arrays (3,) por componente; "
            "la carga total es la suma (solo una componente suele ser no nula)."
        )
        print(f"    F_x = {np.asarray(self.F_x).ravel()}")
        print(f"    F_y = {np.asarray(self.F_y).ravel()}")
        print(f"    F_z = {np.asarray(self.F_z).ravel()}")
        
        v_carga_global = np.sum(np.array([self.F_x, self.F_y, self.F_z]), axis=0) #Dos siempre van a ser 0, por lo que aislo nomas
        print(f"  Fuerza neta en globales F_global = F_x+F_y+F_z: {v_carga_global}")

        f_local = r_base @ v_carga_global  # [Fx, Fy, Fz]
        self.f_local = f_local  # Guardar para exportación
    
        print(f"  Misma fuerza en ejes locales de barra [Fx_loc, Fy_loc, Fz_loc]: {f_local}")

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

        """ voy a hacer una prueba con lo que dije"""
        f_reaccion_local = - f_local   #esto hice para poder sacar la reaccion directamente nomás y no dar vuelta después

        reaccion_momento_local = np.cross(barra.x_local, f_reaccion_local)
        print(f"  Momento de r x F en globales (cross(x_local, -f_local)): {reaccion_momento_local}")
        reaccion_momento_local_unitario = reaccion_momento_local / np.linalg.norm(reaccion_momento_local)
        print(f"  Direccion unitaria de ese momento: {reaccion_momento_local_unitario}")
        signo_mz = np.sign(np.dot(reaccion_momento_local_unitario, barra.z_local)) or 1
        print(
            f"  signo_mz = sign(dot(direccion unitaria, z_local)) "
            f"(flexion en plano Y_loc-Z_loc): {signo_mz}"
        )
        Qi_y = Qy * ((lj / barra.L)**2) * (3 - 2 * (lj / barra.L))
        Qj_y = Qy * ((li / barra.L)**2) * (3 - 2 * (li / barra.L))
        Mi_z = signo_mz * (abs(Qy) * li * ((lj / barra.L)**2))
        print(f"  Momento flector local Mz en nodo i (por cortante Qy): {Mi_z}")
        Mj_z = - signo_mz * (abs(Qy) * lj * ((li / barra.L)**2))
        print(f"  Momento flector local Mz en nodo j: {Mj_z}")

        signo_my = np.sign(np.dot(reaccion_momento_local_unitario, barra.y_local)) or 1

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
        print(_str_vec6("Vector empotramiento nodo i (antes de acumular a la barra)", f_empotramiento[:6]))

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
        print("  Tras sumar esta carga al acumulado de la barra (coord. locales):")
        barra.reaccion_de_empotramiento_local_total += f_empotramiento
        print(_str_vec12_por_nodos("Reaccion de empotramiento local TOTAL (acumulado)", barra.reaccion_de_empotramiento_local_total))
        barra.reaccion_de_empotramiento_i_local += f_empotramiento[:6]
        print(_str_vec6("Acumulado solo nudo i", barra.reaccion_de_empotramiento_i_local))
        barra.reaccion_de_empotramiento_f_local += f_empotramiento[6:]
        print(_str_vec6("Acumulado solo nudo j", barra.reaccion_de_empotramiento_f_local))
        #print()
        #print()
        return barra.reaccion_de_empotramiento_local_total
    

