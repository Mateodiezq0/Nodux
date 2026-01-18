from dataclasses import dataclass, field
import numpy as np
from core.carga_puntual import CargaPuntual
from core.nodos import Nodo
from typing import List, Optional, Tuple
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
    
    def obtener_vector_unitario(self) -> Optional[np.ndarray]:
            """
            Calcula el vector unitario de la barra desde el nodo inicial al nodo final.
            Retorna None si los nodos no están disponibles.
            """
            if self.nodo_i_obj is None or self.nodo_f_obj is None:
                return None
            
            # Vector desde nodo inicial a nodo final
            dx = self.nodo_f_obj.x - self.nodo_i_obj.x
            dy = self.nodo_f_obj.y - self.nodo_i_obj.y
            dz = self.nodo_f_obj.z - self.nodo_i_obj.z
            
            # Calcular longitud si no está calculada
            if self.L is None or self.L == 0:
                self.L = np.sqrt(dx**2 + dy**2 + dz**2)
            
            if self.L == 0:
                return None
            
            # Vector unitario
            v_unitario = np.array([dx / self.L, dy / self.L, dz / self.L])
            return v_unitario
        
    
    def calcular_terna_ejes_locales(self) -> bool:
        """
        Calcula la terna de ejes locales (x_local, y_local, z_local) trabajando siempre con vectores unitarios.
        
        x_local: Vector unitario desde nodo inicial a nodo final
        y_local: Vector unitario perpendicular a x_local y al vector "up" (eje Z global)
        z_local: Vector unitario perpendicular a x_local y y_local (completa la terna ortonormal)
        
        Retorna True si se calcularon correctamente, False en caso contrario.
        """
        if self.nodo_i_obj is None or self.nodo_f_obj is None:
            return False
        
        # Precisión numérica
        dtype = np.float64
        tol = 1e-12
        
        # 1. Calcular x_local: vector unitario desde nodo inicial a nodo final
        dx = self.nodo_f_obj.x - self.nodo_i_obj.x
        dy = self.nodo_f_obj.y - self.nodo_i_obj.y
        dz = self.nodo_f_obj.z - self.nodo_i_obj.z
        
        # Calcular longitud
        self.L = np.sqrt(dx*dx + dy*dy + dz*dz)
        if self.L < tol:
            return False
        
        # Vector unitario x_local
        self.x_local = np.array([dx / self.L, dy / self.L, dz / self.L], dtype=dtype)
        
        # 2. Verificar si la barra es vertical (x_local paralelo a eje Z global)
        eje_z_global = np.array([0.0, 0.0, 1.0], dtype=dtype)
        producto_escalar_con_z = abs(np.dot(self.x_local, eje_z_global))
        es_vertical = producto_escalar_con_z > (1.0 - tol)  # Si cos(ángulo) ≈ 1, son paralelos
        
        # 3. Calcular y_local y z_local según el caso
        if not es_vertical:
            # CASO NORMAL: Barra no vertical
            # Vector de referencia "up" (eje Z global)
            up = np.array([0.0, 0.0, 1.0], dtype=dtype)
            
            # Calcular y_local = normalize(cross(up, x_local))
            y_temp = np.cross(up, self.x_local)
            norma_y = np.linalg.norm(y_temp)
            
            if norma_y < tol:
                return False
            
            # Normalizar y_local
            self.y_local = y_temp / norma_y
            
            # Calcular z_local = normalize(cross(x_local, y_local))
            z_temp = np.cross(self.x_local, self.y_local)
            norma_z = np.linalg.norm(z_temp)
            
            if norma_z < tol:
                return False
            
            # Normalizar z_local
            self.z_local = z_temp / norma_z
        else:
            # CASO ESPECIAL: Barra vertical (x_local paralelo a Z)
            # Vector de referencia: eje X global negativo
            up = np.array([1.0, 0.0, 0.0], dtype=dtype)
            
            # Calcular z_local = normalize(cross(x_local, up))
            y_temp = np.cross(self.x_local, up)
            norma_y = np.linalg.norm(y_temp)
            
            if norma_y < tol:
                return False
            
            # Normalizar z_local
            self.y_local = y_temp / norma_y
            print("y_local AAAAAAAAAAAAA", self.y_local)
            # Calcular y_local = normalize(cross(z_local, x_local))
            z_temp = np.cross(self.y_local, self.x_local)
            norma_z = np.linalg.norm(z_temp)
            
            if norma_z < tol:
                return False
            
            # Normalizar y_local
            self.z_local = z_temp / norma_y
            print("z_local BBBBBBBBBBBBBBBBB", self.z_local)
        
        # 5. Aplicar rotación tita si existe y es significativa (rotación alrededor del eje x_local)
        # Solo aplicar si tita es diferente de None y mayor a 1e-6 grados (evitar errores numéricos)
        if self.tita is not None and abs(self.tita) > 1e-6:
            theta = np.radians(self.tita)
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            
            # Matriz de rotación 2D en el plano y-z
            rot_2d = np.array([
                [cos_t, -sin_t],
                [sin_t,  cos_t]
            ], dtype=dtype)
            
            # Aplicar rotación: [y_new, z_new] = [y_old, z_old] @ rot_2d
            yz_matrix = np.column_stack((self.y_local, self.z_local))
            yz_rotated = yz_matrix @ rot_2d
            
            self.y_local = yz_rotated[:, 0]
            self.z_local = yz_rotated[:, 1]
            
            # Re-normalizar después de la rotación
            norma_y = np.linalg.norm(self.y_local)
            if norma_y > tol:
                self.y_local = self.y_local / norma_y
            
            norma_z = np.linalg.norm(self.z_local)
            if norma_z > tol:
                self.z_local = self.z_local / norma_z

        
        return True
    
    def construir_matriz_rotacion_R_3x3(self) -> np.ndarray:
        """
        Construye la matriz de rotación R de 3x3 usando los cosenos directores
        extraídos de x_local, y_local, z_local calculados en calcular_terna_ejes_locales.
        
        La matriz R tiene la forma:
        R = [cosalphax  cosbetax  cosgammax]
            [cosalphay  cosbetay  cosgammay]
            [cosalphaz  cosbetaz  cosgammaz]
        
        Donde:
        - x_local = [cosalphax, cosalphay, cosalphaz]
        - y_local = [cosbetax,  cosbetay,  cosbetaz]
        - z_local = [cosgammax, cosgammay, cosgammaz]
        
        Retorna:
        --------
        np.ndarray
            Matriz de rotación R de 3x3, o matriz identidad si no se puede calcular
        """
        # Asegurar que se han calculado los ejes locales
        if self.x_local is None or self.y_local is None or self.z_local is None:
            # Intentar calcular la terna de ejes locales
            if not self.calcular_terna_ejes_locales():
                return np.eye(3)
        
        # Extraer cosenos directores
        # x_local → cosalphax, cosalphay, cosalphaz
        cosalphax = self.x_local[0]
        cosalphay = self.x_local[1]
        cosalphaz = self.x_local[2]
        
        # y_local → cosbetax, cosbetay, cosbetaz
        cosbetax = self.y_local[0]
        cosbetay = self.y_local[1]
        cosbetaz = self.y_local[2]
        
        # z_local → cosgammax, cosgammay, cosgammaz
        cosgammax = self.z_local[0]
        cosgammay = self.z_local[1]
        cosgammaz = self.z_local[2]
        
        # Construir matriz R de 3x3
        R = np.array([
            [cosalphax, cosbetax, cosgammax],
            [cosalphay, cosbetay, cosgammay],
            [cosalphaz, cosbetaz, cosgammaz]
        ], dtype=np.float64)
        
        return R
    
    def construir_matriz_rotacion_T_12x12(self) -> np.ndarray:
        """
        Construye la matriz de rotación T de 12x12 usando la matriz R de 3x3.
        
        La matriz T tiene la forma:
        T = [R   0   0   0 ]
            [0   R   0   0 ]
            [0   0   R   0 ]
            [0   0   0   R ]
        
        Donde R es la matriz de rotación 3x3 calculada con construir_matriz_rotacion_R_3x3.
        Los bloques corresponden a: traslaciones nodo_i, rotaciones nodo_i, 
        traslaciones nodo_f, rotaciones nodo_f.
        
        Retorna:
        --------
        np.ndarray
            Matriz de rotación T de 12x12
        """
        # Obtener matriz R de 3x3
        R = self.construir_matriz_rotacion_R_3x3()
        
        # Construir matriz 12x12 con R en todos los bloques diagonales
        T = np.zeros((12, 12), dtype=np.float64)
        
        # Bloque 1: Traslaciones nodo inicial (0-2) -> R
        T[0:3, 0:3] = R
        
        # Bloque 2: Rotaciones nodo inicial (3-5) -> R
        T[3:6, 3:6] = R
        
        # Bloque 3: Traslaciones nodo final (6-8) -> R
        T[6:9, 6:9] = R
        
        # Bloque 4: Rotaciones nodo final (9-11) -> R
        T[9:12, 9:12] = R
        
        return T
    
    def transformar_K_local_a_global_con_Tx_Ty_Tz(self, K_local: np.ndarray) -> np.ndarray:
        """
        Transforma la matriz de rigidez local (12x12) a coordenadas globales usando
        la matriz de rotación T (12x12) construida a partir de los cosenos directores
        de x_local, y_local, z_local.
        
        La transformación se realiza mediante:
        K_global = T^T @ K_local @ T
        
        Parámetros:
        -----------
        K_local : np.ndarray
            Matriz de rigidez local de 12x12
            
        Retorna:
        --------
        np.ndarray
            Matriz de rigidez global de 12x12
        """
        if K_local.shape != (12, 12):
            raise ValueError(f"K_local debe ser una matriz 12x12, pero tiene forma {K_local.shape}")
        
        # Construir la matriz de rotación T de 12x12
        T = self.construir_matriz_rotacion_T_12x12()
        
        # Transformar: K_global = T^T @ K_local @ T
        K_global = T.T @ K_local @ T
        
        return K_global
    