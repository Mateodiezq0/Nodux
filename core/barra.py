from dataclasses import dataclass, field
import numpy as np
from core.carga_puntual import CargaPuntual
from core.nodos import Nodo
from typing import List, Optional
from math import radians, cos, sin, pi

@dataclass
class Barra:
    id: int
    nodo_i: int
    nodo_f: int
    E: float  # Módulo de elasticidad (Tn/cm^2)
    A: Optional[float] = None # Área de la sección transversal (si no se calcula automáticamente)
    I_y: float = None  # Momento de inercia en torno al eje Y
    I_z: float = None  # Momento de inercia en torno al eje Z
    G: float  = None # Módulo de corte
    J: float  = None # Módulo de torsión
    L: Optional[float] = None  # Longitud del perfil (si no se calcula automáticamente)
    tita: Optional[float] = None  # Ángulo de inclinación del perfil (en grados)

    x_local: Optional[np.ndarray] = None  # Cosenos directores x_local respecto a global
    y_local: Optional[np.ndarray] = None  # Cosenos directores y_local respecto a global
    z_local: Optional[np.ndarray] = None  # Cosenos directores z_local respecto a global
    
    cargas: list = field(default_factory=list)  # Cargas aplicadas a la barra


    # Nuevos atributos para guardar los objetos Nodo
    nodo_i_obj: Optional["Nodo"] = None     #Objeto de nodo inicial
    nodo_f_obj: Optional["Nodo"] = None     #Objeto de nodo final

    reaccion_de_empotramiento_local_total: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(12))    #Reaccion total de las barras LOCAL
    reaccion_de_empotramiento_i_local: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))          #Reaccion equivalente de nodo inicial LOCAL
    reaccion_de_empotramiento_f_local: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))          #Reaccion equivalente de nodo final LOCAL

    reaccion_de_empotramiento_rotado_eje: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(12))

    reaccion_de_empotramiento_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(12))           #Reaccion total de las barras GLOBAL
    reaccion_nudo_i_equivalente_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))          #Reaccion equivalente de nodo inicial GLOBAL
    reaccion_nudo_f_equivalente_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))          #Reaccion equivalente de nodo final GLOBAL
    
    k_global_dat : Optional[np.ndarray] = None  # Matriz de rigidez global (12x12)
    
    def p_eje(self):
        alpha = np.radians(self.tita or 0.0)
        A = self.matriz_A(alpha)
        A = self.bloque_diagonal_4x3(A)
        print("Matriz A extendida:\n", A)
        self.reaccion_de_empotramiento_rotado_eje = A @ self.reaccion_de_empotramiento_local_total
        print(self.reaccion_de_empotramiento_rotado_eje)
        return self.reaccion_de_empotramiento_rotado_eje

    def p_global(self):
        XD = self.p_eje()
        sm = self.calcular_submatriz_de_rotacion()
        T = self.bloque_diagonal_4x3(sm)
        self.reaccion_de_empotramiento_global = T.T @ self.reaccion_de_empotramiento_rotado_eje
        #print()
        #print("ID de la barra:", self.id)
        print("Reacción de empotramiento rotado en global:", self.reaccion_de_empotramiento_global)
        #print()
        self.reaccion_nudo_i_equivalente_global = -(self.reaccion_de_empotramiento_global[:6])
        #print(f"Reacción de nudo {self.nodo_i} rotado en global:", self.reaccion_nudo_i_equivalente_global)
        self.reaccion_nudo_f_equivalente_global = -(self.reaccion_de_empotramiento_global[6:])
        #print(f"Reacción de nudo {self.nodo_f} rotado en global:", self.reaccion_nudo_f_equivalente_global)
        return self.reaccion_de_empotramiento_global, self.reaccion_nudo_i_equivalente_global, self.reaccion_nudo_f_equivalente_global
    
    def actualizar_reacciones_global(self):
        self.p_global()

    def añadirCarga(self, carga): #ESTO LO AGREGUE YO
        """
        Añade una carga a la barra (y suma sus reacciones equivalentes).
        Este método asegura el ACUMULADO.
        """
        f_empotramiento = carga.reacciones_de_empotramiento(self)
        self.cargas = np.append(self.cargas, carga)
        # NO hace falta volver a sumar, ya se sumó dentro de la función
        return f_empotramiento
    
    def calcular_longitud_y_bases(self, debug=0):
        coord_i = self.nodo_i_obj.get_coord()
        coord_f = self.nodo_f_obj.get_coord()
        atol = 1e-3

        print(f"\n--- [Barra {self.id}] Calculo de bases ---")
        print(f"Nodo i: {coord_i}, Nodo f: {coord_f}")

        # 1. Xlocal: SIEMPRE del menor al mayor
        x_local = coord_f - coord_i
        self.L = np.linalg.norm(x_local)
        self.x_local = x_local / self.L
        print(f"[Barra {self.id}] Xlocal: {self.x_local}, L = {self.L:.4f}")

        # 2. "Up": SIEMPRE vertical global (+Y)
        up = np.array([0, 1, 0])
        if np.abs(np.dot(self.x_local, up)) > 1 - atol:
            up = np.array([0, 0, 1])
            print(f"[Barra {self.id}] Caso especial: barra ~ vertical, up cambiado a {up}")
            y_local = np.cross(up, self.x_local)
            self.y_local = y_local / np.linalg.norm(y_local)
            print(f"[Barra {self.id}] y_local corregido: {self.y_local}")
            print(f"[Barra {self.id}] x_local: {self.x_local}")
            z_local = np.cross(self.x_local, self.y_local)
            self.z_local = z_local / np.linalg.norm(z_local)
            print(f"[Barra {self.id}] z_local corregido: {self.z_local}")

        else:
            z_local = np.cross(self.x_local, up)
            z_local = z_local / np.linalg.norm(z_local)
            self.z_local = z_local
            self.y_local = np.cross(self.z_local, self.x_local)
            self.y_local = self.y_local / np.linalg.norm(self.y_local)

        print(f"[Barra {self.id}] Ylocal: {self.y_local}")
        print(f"[Barra {self.id}] Zlocal: {self.z_local}")

        # 5. Rotación antihoraria respecto del eje Xlocal (tita en grados)
        theta = np.radians(self.tita or 0.0)
        print(f"[Barra {self.id}] θ (rads): {theta}")
        if abs(theta) > 1e-8:
            print(f"[Barra {self.id}] y_local antes de rotar: {self.y_local}")
            print(f"[Barra {self.id}] z_local antes de rotar: {self.z_local}")
            base_yz = np.column_stack((self.y_local, self.z_local))
            print(f"[Barra {self.id}] Base YZ antes de rotar:\n{base_yz}")
            rot_2d = np.array([
                [np.cos(theta), -np.sin(theta)],
                [np.sin(theta),  np.cos(theta)]
            ])
            print(f"[Barra {self.id}] Matriz de rotación 2D:\n{rot_2d}")
            yz_rotados = base_yz @ rot_2d
            print(f"[Barra {self.id}] Base YZ rotada:\n{yz_rotados}")
            self.y_local = yz_rotados[:, 0]
            self.z_local = yz_rotados[:, 1]
            print(f"[Barra {self.id}] Ylocal rotado: {self.y_local}")
            print(f"[Barra {self.id}] Zlocal rotado: {self.z_local}")

        if debug:
            self.debug_bases()

    def debug_bases(self):
        print("x_local:", self.x_local)
        print("y_local:", self.y_local)
        print("z_local:", self.z_local)
        print("Normas:", np.linalg.norm(self.x_local), np.linalg.norm(self.y_local), np.linalg.norm(self.z_local))
        print("Ortogonalidad x·y:", np.dot(self.x_local, self.y_local))
        print("Ortogonalidad x·z:", np.dot(self.x_local, self.z_local))
        print("Ortogonalidad y·z:", np.dot(self.y_local, self.z_local))
        print("Determinante base (debe ser +1):", np.linalg.det(np.column_stack([self.x_local, self.y_local, self.z_local])))

    def Kloc(self):
        # Asegura que la longitud y las bases están listas
        self.calcular_longitud_y_bases()
        L = self.L
        # Calcula los parámetros de la sección transversal usando los datos del objeto y propiedades del material
        E = self.E
        A = self.A
        I_y = self.I_y
        I_z = self.I_z
        G = self.G
        J = self.J

        # Matriz de rigidez para 3D (12x12)
        Kloc = np.zeros((12, 12)) 

        Kloc[0, 0] = E * A / L  # Rigidez axial 
        Kloc[1, 1] = 12 * E * I_z / L**3  # Rigidez de flexión en Z
        Kloc[2, 2] = 12 * E * I_y / L**3  # Rigidez de flexión en Y
        Kloc[3, 3] = G * J / L  # Rigidez torsional
        Kloc[4, 4] = 4 * E * I_y / L  
        Kloc[5, 5] = 4 * E * I_z / L  
        Kloc[6, 6] = E * A / L  # Rigidez axial 
        Kloc[7, 7] = 12 * E * I_z / L**3  # Rigidez de flexión en Z
        Kloc[8, 8] = 12 * E * I_y / L**3  # Rigidez de flexión en Y
        Kloc[9, 9] = G * J / L  # Rigidez torsional
        Kloc[10, 10] = 4 * E * I_y / L 
        Kloc[11, 11] = 4 * E * I_z / L 

        Kloc[4, 2] = Kloc[2, 4] = -6 * E * I_y / L**2
        Kloc[1, 5] = Kloc[5, 1] = 6 * E * I_z / L**2 
        Kloc[6, 0] = Kloc[0, 6] = - E * A / L 
        Kloc[7, 1] = Kloc[1, 7] = - 12 * E * I_z / L**3  
        Kloc[7, 5] = Kloc[5, 7] = - 6 * E * I_z / L**2  
        Kloc[8, 2] = Kloc[2, 8] = - 12 * E * I_y / L**3 
        Kloc[8, 4] = Kloc[4, 8] = 6 * E * I_y / L**2 
        Kloc[9, 3] = Kloc[3, 9] = - G * J / L
        Kloc[10, 2] = Kloc[2, 10] = -6 * E * I_y / L**2
        Kloc[10, 4] = Kloc[4, 10] = 2 * E * I_y / L
        Kloc[10, 8] = Kloc[8, 10] = 6 * E * I_y / L**2
        Kloc[11, 1] = Kloc[1, 11] = 6 * E * I_z / L**2  
        Kloc[11, 5] = Kloc[5, 11] = 2 * E * I_z / L
        Kloc[11, 7] = Kloc[7, 11] = -6 * E * I_z / L**2  
        
        return Kloc

    def bloque_diagonal_4x3(self, M):
        res = np.zeros((12, 12))
        for i in range(4):
            res[i*3:(i+1)*3, i*3:(i+1)*3] = M
        return res

    def calcular_submatriz_de_rotacion(self):

        self.calcular_longitud_y_bases()
        if (self.x_local == np.array([0,0,1])).all():
                T = np.array([
                    [0, 0, 1],
                    [0, 1 , 0],
                    [-1, 0, 0]
                ])
                return T
        if (self.x_local == np.array([0,0,-1])).all():
                T = np.array([
                    [0, 0, -1],
                    [0, 1 , 0],
                    [1, 0, 0]
                ])
                return T
        l = self.x_local[0]
        m = self.x_local[1]
        n = self.x_local[2]
        d = (l**2+m**2)**0.5
        cxx = l
        cyx = m
        czx = n
        cxy = -m/d
        cyy = l/d
        czy = 0
        cxz = -l*n/d
        cyz = -m*n/d
        czz = d
        T = np.array([
            [cxx, cyx, czx],
            [cxy, cyy ,  czy],
            [cxz, cyz,  czz]
        ])
        print("T =", T)
        return T

    def Kglobal(self):
        alpha = np.radians(self.tita or 0.0)
        A = self.matriz_A(alpha)
        A = self.bloque_diagonal_4x3(A)
        k_global_rotado_eje = A @ self.Kloc() @ A.T
        sm = self.calcular_submatriz_de_rotacion()
        T = self.bloque_diagonal_4x3(sm)
        k_global_transformado = (T.T @ k_global_rotado_eje) @ T

        return k_global_transformado

    def matriz_A(self, alpha): 
        return np.array(
            [[1, 0, 0], 
            [0, np.cos(alpha), -np.sin(alpha)], 
            [0, np.sin(alpha), np.cos(alpha)] 
            ])
