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
        
    def calcular_alpha(self) -> Optional[float]:
        """
        Calcula el ángulo alpha (rotación alrededor del eje X) en grados.
        alpha = arctan(y/z) donde y y z son las componentes del vector unitario.
        """
        v_unit = self.obtener_vector_unitario()
        if v_unit is None:
            return None
        
        y = v_unit[1]  # Componente Y del vector unitario
        z = v_unit[2]  # Componente Z del vector unitario
        
        # Usar arctan2 para manejar correctamente todos los cuadrantes
        # alpha = arctan(y/z)
        if abs(z) < 1e-10:  # Evitar división por cero
            alpha = np.pi / 2 if y > 0 else -np.pi / 2
        else:
            alpha = np.arctan2(y, z)
        
        return np.rad2deg(alpha)
    
    def calcular_beta(self) -> Optional[float]:
        """
        Calcula el ángulo beta (rotación alrededor del eje Y) en grados.
        beta = arctan(z/x) donde z y x son las componentes del vector unitario.
        """
        v_unit = self.obtener_vector_unitario()
        if v_unit is None:
            return None
        
        z = v_unit[2]  # Componente Z del vector unitario
        x = v_unit[0]  # Componente X del vector unitario
        
        # Usar arctan2 para manejar correctamente todos los cuadrantes
        # beta = arctan(z/x)
        if abs(x) < 1e-10:  # Evitar división por cero
            beta = np.pi / 2 if z > 0 else -np.pi / 2
        else:
            beta = np.arctan2(z, x)
        
        return np.rad2deg(beta)
    
    def calcular_gamma(self) -> Optional[float]:
        """
        Calcula el ángulo gamma (rotación alrededor del eje Z) en grados.
        gamma = arctan(y/x) donde y y x son las componentes del vector unitario.
        """
        v_unit = self.obtener_vector_unitario()
        if v_unit is None:
            return None
        
        y = v_unit[1]  # Componente Y del vector unitario
        x = v_unit[0]  # Componente X del vector unitario
        
        # Usar arctan2 para manejar correctamente todos los cuadrantes
        # gamma = arctan(y/x)
        if abs(x) < 1e-10:  # Evitar división por cero
            gamma = np.pi / 2 if y > 0 else -np.pi / 2
        else:
            gamma = np.arctan2(y, x)
        
        return np.rad2deg(gamma)
    
    def calcular_rotacion_eje_z(self, gamma_deg: float) -> np.ndarray:
        """
        Calcula la matriz de rotación en torno al eje z, usando el ángulo gamma en grados.
        """
        gamma = np.deg2rad(gamma_deg)
        Rz = np.array([
            [np.cos(gamma), -np.sin(gamma), 0],
            [np.sin(gamma),  np.cos(gamma), 0],
            [0,              0,             1]
        ])
        return Rz

    def calcular_rotacion_eje_y(self, beta_deg: float) -> np.ndarray:
        """
        Calcula la matriz de rotación en torno al eje y, usando el ángulo beta en grados.
        """
        beta = np.deg2rad(beta_deg)
        Ry = np.array([
            [ np.cos(beta), 0, np.sin(beta)],
            [ 0,            1, 0           ],
            [-np.sin(beta), 0, np.cos(beta)]
        ])
        return Ry

    def calcular_rotacion_eje_x(self, alpha_deg: float) -> np.ndarray:
        """
        Calcula la matriz de rotación en torno al eje x, usando el ángulo alpha en grados.
        """
        alpha = np.deg2rad(alpha_deg)
        Rx = np.array([
            [1, 0,              0           ],
            [0, np.cos(alpha), -np.sin(alpha)],
            [0, np.sin(alpha),  np.cos(alpha)]
        ])
        return Rx

    def matriz_rotacion_general(self) -> np.ndarray:
        """
        Calcula la matriz de rotación general utilizando ángulos (en grados) alfa (X), beta (Y) y gamma (Z).
        El resultado es Rz * Ry * Rx (el orden clásico de Euler-ZYX).
        """
        alpha = self.calcular_alpha()
        beta = self.calcular_beta()
        gamma = self.calcular_gamma()
        
        if alpha is None or beta is None or gamma is None:
            return np.eye(3)
        
        Rx = self.calcular_rotacion_eje_x(alpha)
        Ry = self.calcular_rotacion_eje_y(beta)
        Rz = self.calcular_rotacion_eje_z(gamma)
        R = Rz @ Ry @ Rx
        return R
    
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
        
        # 2. Vector de referencia "up" (eje Z global)
        up = np.array([0.0, 0.0, 1.0], dtype=dtype)
        
        # 3. Calcular y_local = normalize(cross(up, x_local))
        y_temp = np.cross(up, self.x_local)
        norma_y = np.linalg.norm(y_temp)
        
        # Caso especial: si x_local es paralelo a up (barra vertical)
        if norma_y < tol:
            # Usar eje Y global como referencia alternativa
            up = np.array([0.0, 1.0, 0.0], dtype=dtype)
            y_temp = np.cross(up, self.x_local)
            norma_y = np.linalg.norm(y_temp)
            
            # Si aún es paralelo, usar eje X global
            if norma_y < tol:
                up = np.array([1.0, 0.0, 0.0], dtype=dtype)
                y_temp = np.cross(up, self.x_local)
                norma_y = np.linalg.norm(y_temp)
        
        if norma_y < tol:
            return False
        
        # Normalizar y_local
        self.y_local = y_temp / norma_y
        
        # 4. Calcular z_local = normalize(cross(x_local, y_local))
        z_temp = np.cross(self.x_local, self.y_local)
        norma_z = np.linalg.norm(z_temp)
        
        if norma_z < tol:
            return False
        
        # Normalizar z_local
        self.z_local = z_temp / norma_z
        
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
        
        # 6. Corrección final: asegurar que z_local = x_local × y_local (ortonormalidad exacta)
        z_corrected = np.cross(self.x_local, self.y_local)
        norma_z_corrected = np.linalg.norm(z_corrected)
        if norma_z_corrected > tol:
            self.z_local = z_corrected / norma_z_corrected
        
        # 7. Verificación final: normalizar todos los vectores
        norma_x = np.linalg.norm(self.x_local)
        if norma_x > tol:
            self.x_local = self.x_local / norma_x
        
        norma_y = np.linalg.norm(self.y_local)
        if norma_y > tol:
            self.y_local = self.y_local / norma_y
        
        norma_z = np.linalg.norm(self.z_local)
        if norma_z > tol:
            self.z_local = self.z_local / norma_z
        
        return True
    