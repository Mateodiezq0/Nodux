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
    I_z: float = None  # Momento de inercia en tsorno al eje Z
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
    solicitaciones_extremos_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(12))             #Solicitaciones internas de barra [nodo_i(6), nodo_f(6)] en GLOBAL
    solicitaciones_extremo_i_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))             #Solicitaciones internas en extremo nodo inicial (GLOBAL)
    solicitaciones_extremo_f_global: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))             #Solicitaciones internas en extremo nodo final (GLOBAL)
    solicitaciones_extremos_local: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(12))              #Solicitaciones internas de barra [nodo_i(6), nodo_f(6)] en LOCAL
    solicitaciones_extremo_i_local: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))              #Solicitaciones internas en extremo nodo inicial (LOCAL)
    solicitaciones_extremo_f_local: Optional[np.ndarray] = field(default_factory=lambda: np.zeros(6))              #Solicitaciones internas en extremo nodo final (LOCAL)
    
    k_global_dat : Optional[np.ndarray] = None  # Matriz de rigidez global (12x12)

    def _ejes_locales_validos(self) -> bool:
        """
        Verifica que x_local, y_local y z_local existan y sean vectores de 3 componentes finitas.
        """
        for eje in (self.x_local, self.y_local, self.z_local):
            if eje is None:
                return False
            arr = np.asarray(eje, dtype=np.float64).ravel()
            if arr.size != 3 or not np.all(np.isfinite(arr)):
                return False
        return True

    def asegurar_terna_ejes_locales(self, forzar_recalculo: bool = False) -> bool:
        """
        Asegura que la terna local este disponible.
        - Si ya es valida y no se fuerza, reutiliza valores existentes.
        - Si falta o se fuerza, recalcula llamando a calcular_terna_ejes_locales().
        """
        if not forzar_recalculo and self._ejes_locales_validos():
            return True
        return self.calcular_terna_ejes_locales()
    
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
            up = np.array([0.0, 1.0, 0.0], dtype=dtype)
            
            # Calcular z_local = normalize(cross(x_local, up))
            z_temp = np.cross(self.x_local, up)
            norma_z = np.linalg.norm(z_temp)
            
            if norma_z < tol:
                return False
            
            # Normalizar z_local
            self.z_local = z_temp / norma_z
            print(
                f"[Barra {self.id}] Barra vertical: eje z_local "
                f"(cross(x_local, eje Y global positivo)): {self.z_local}"
            )
            # Calcular y_local = normalize(cross(z_local, x_local))
            y_temp = np.cross(self.z_local, self.x_local)
            norma_y = np.linalg.norm(y_temp)
            
            if norma_y < tol:
                return False
            
            # Normalizar y_local
            self.y_local = y_temp / norma_y
            print(
                f"[Barra {self.id}] Barra vertical: eje y_local (tras cross(z_local, x_local)): {self.y_local}"
            )

        
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
        # Asegurar que se han calculado (o recalcular si estan invalidos)
        if not self.asegurar_terna_ejes_locales():
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
            [cosalphax, cosalphay, cosalphaz],
            [cosbetax,  cosbetay,  cosbetaz],
            [cosgammax, cosgammay, cosgammaz]
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
    
    def construir_matriz_rotacion_2d_12x12(self) -> np.ndarray:
        """
        Construye la matriz de rotación 2D de 12x12 para rotar en el plano y-z.
        
        La matriz de rotación 2D en el plano y-z se aplica a las componentes Y y Z
        de cada bloque (traslaciones y rotaciones de ambos nodos), dejando X sin cambios.
        
        La matriz tiene la forma:
        R_2d_12x12 = [1    0    0    0    0    0    0    0    0    0    0    0 ]
                     [0  cos  -sin   0    0    0    0    0    0    0    0    0 ]
                     [0  sin   cos   0    0    0    0    0    0    0    0    0 ]
                     [0    0    0    1    0    0    0    0    0    0    0    0 ]
                     [0    0    0    0  cos  -sin   0    0    0    0    0    0 ]
                     [0    0    0    0  sin   cos   0    0    0    0    0    0 ]
                     [0    0    0    0    0    0    1    0    0    0    0    0 ]
                     [0    0    0    0    0    0    0  cos  -sin   0    0    0 ]
                     [0    0    0    0    0    0    0  sin   cos   0    0    0 ]
                     [0    0    0    0    0    0    0    0    0    1    0    0 ]
                     [0    0    0    0    0    0    0    0    0    0  cos  -sin]
                     [0    0    0    0    0    0    0    0    0    0  sin   cos ]
        
        Retorna:
        --------
        np.ndarray
            Matriz de rotación 2D de 12x12
        """
        # Verificar si tita está definido
        if self.tita is None or abs(self.tita) < 1e-6:
            # Si no hay rotación, retornar matriz identidad
            return np.eye(12, dtype=np.float64)
        
        # Calcular ángulo en radianes
        theta = np.radians(self.tita)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        
        # Matriz de rotación 2D en el plano y-z
        rot_2d = np.array([
            [cos_t, -sin_t],
            [sin_t,  cos_t]
        ], dtype=np.float64)
        
        # Construir matriz 12x12
        R_2d_12x12 = np.eye(12, dtype=np.float64)
        
        # Aplicar rotación 2D a los bloques Y-Z:
        # Bloque 1: Traslaciones nodo inicial (Y=1, Z=2)
        R_2d_12x12[1:3, 1:3] = rot_2d
        
        # Bloque 2: Rotaciones nodo inicial (Y=4, Z=5)
        R_2d_12x12[4:6, 4:6] = rot_2d
        
        # Bloque 3: Traslaciones nodo final (Y=7, Z=8)
        R_2d_12x12[7:9, 7:9] = rot_2d
        
        # Bloque 4: Rotaciones nodo final (Y=10, Z=11)
        R_2d_12x12[10:12, 10:12] = rot_2d
        
        return R_2d_12x12
    
    def transformar_reacciones_empotramiento_a_global(self) -> None:
        """
        Transforma las reacciones de empotramiento de coordenadas locales a globales.
        
        El proceso consta de dos rotaciones:
        1. Rotación 2D en el plano y-z (usando el ángulo tita)
        2. Rotación completa a coordenadas globales (usando la matriz T)
        
        Los resultados se guardan en:
        - reaccion_de_empotramiento_rotado_eje: Resultado de la primera rotación
        - reaccion_de_empotramiento_global: Resultado de la segunda rotación
        - reaccion_nudo_i_equivalente_global: Primeros 6 elementos del resultado global
        - reaccion_nudo_f_equivalente_global: Últimos 6 elementos del resultado global
        """
        # Verificar que existe reaccion_de_empotramiento_local_total
        if self.reaccion_de_empotramiento_local_total is None:
            return
        
        # Paso 1: Construir matriz de rotación 2D de 12x12
        R_2d_12x12 = self.construir_matriz_rotacion_2d_12x12()
        
        # Paso 2: Aplicar primera rotación (traspuesta de R_2d_12x12)
        # reaccion_rotada = R_2d_12x12^T @ reaccion_local_total
        # VER QUE ACÁ YA CAMBIA EL SIGNO PORQUE AHORA YA ES REACCIÓN DE NUDO  (CAMBIAR NOMBRE)
        self.reaccion_de_empotramiento_rotado_eje = -(R_2d_12x12.T @ self.reaccion_de_empotramiento_local_total)
        
        # Paso 3: Construir matriz de rotación T de 12x12
        T = self.construir_matriz_rotacion_T_12x12()
        
        # Paso 4: Aplicar segunda rotación (traspuesta de T)
        # reaccion_global = T^T @ reaccion_rotada
        #LO MISMO ACÁ, YA ES DE NUDO PORQUE EN REALIDAD YA HABÍAMOS CAMBIADO EL NOMBRE, (CAMBIAR NOMBRE)
        self.reaccion_de_empotramiento_global = T.T @ self.reaccion_de_empotramiento_rotado_eje
        
        # Paso 5: Separar según nudo
        # Primeros 6 elementos: nodo inicial
        self.reaccion_nudo_i_equivalente_global = self.reaccion_de_empotramiento_global[:6].copy()
        
        # Últimos 6 elementos: nodo final
        self.reaccion_nudo_f_equivalente_global = self.reaccion_de_empotramiento_global[6:].copy()
    
    def calcular_longitud_y_bases(self) -> bool:
        """
        Calcula la longitud de la barra y los ejes locales (bases).
        Retorna True si se calcularon correctamente, False en caso contrario.
        """
        if self.nodo_i_obj is None or self.nodo_f_obj is None:
            return False
        
        # Calcular longitud
        dx = self.nodo_f_obj.x - self.nodo_i_obj.x
        dy = self.nodo_f_obj.y - self.nodo_i_obj.y
        dz = self.nodo_f_obj.z - self.nodo_i_obj.z
        self.L = np.sqrt(dx*dx + dy*dy + dz*dz)
        
        if self.L == 0:
            return False
        
        # Calcular terna de ejes locales
        return self.calcular_terna_ejes_locales()
    
    def Kglobal(self) -> np.ndarray:
        """
        Calcula la matriz de rigidez global (12x12) de la barra.
        Retorna la matriz K global transformada desde coordenadas locales.
        """
        # Verificar que tenemos las propiedades necesarias
        if self.E is None or self.A is None or self.I_y is None or self.I_z is None:
            raise ValueError(f"Barra {self.id}: Faltan propiedades (E, A, I_y, I_z)")
        
        if self.L is None or self.L == 0:
            if not self.calcular_longitud_y_bases():
                raise ValueError(f"Barra {self.id}: No se pudo calcular la longitud")
        
        # Calcular K_local
        K_local = self._calcular_K_local()
        
        # Transformar a global
        K_global = self.transformar_K_local_a_global_con_Tx_Ty_Tz(K_local)
        
        # Guardar en k_global_dat
        self.k_global_dat = K_global
        
        return K_global
    
    def _calcular_K_local(self) -> np.ndarray:
        """
        Calcula la matriz de rigidez local (12x12) para una viga 3D de Euler-Bernoulli.
        """
        # Inicializar matriz
        K = np.zeros((12, 12))
        
        # Constantes
        EA_L = self.E * self.A / self.L
        EIy_L = self.E * self.I_y / self.L
        EIy_L2 = self.E * self.I_y / (self.L**2)
        EIy_L3 = self.E * self.I_y / (self.L**3)
        
        EIz_L = self.E * self.I_z / self.L
        EIz_L2 = self.E * self.I_z / (self.L**2)
        EIz_L3 = self.E * self.I_z / (self.L**3)
        
        GJ_L = (self.G * self.J / self.L) if (self.G is not None and self.J is not None) else 0.0
        
        # Fuerza axial (DOF 0 y 6)S
        K[0, 0] = EA_L
        K[0, 6] = -EA_L
        K[6, 0] = -EA_L
        K[6, 6] = EA_L
        
        # Torsión (DOF 3 y 9)
        if GJ_L > 0:
            K[3, 3] = GJ_L
            K[3, 9] = -GJ_L
            K[9, 3] = -GJ_L
            K[9, 9] = GJ_L
        
        # Flexión en Y (DOF 1, 5, 7, 11)
        K[1, 1] = 12 * EIz_L3
        K[1, 5] = 6 * EIz_L2
        K[1, 7] = -12 * EIz_L3
        K[1, 11] = 6 * EIz_L2
        
        K[5, 1] = 6 * EIz_L2
        K[5, 5] = 4 * EIz_L
        K[5, 7] = -6 * EIz_L2
        K[5, 11] = 2 * EIz_L
        
        K[7, 1] = -12 * EIz_L3
        K[7, 5] = -6 * EIz_L2
        K[7, 7] = 12 * EIz_L3
        K[7, 11] = -6 * EIz_L2
        
        K[11, 1] = 6 * EIz_L2
        K[11, 5] = 2 * EIz_L
        K[11, 7] = -6 * EIz_L2
        K[11, 11] = 4 * EIz_L
        
        # Flexión en Z (DOF 2, 4, 8, 10)
        K[2, 2] = 12 * EIy_L3
        K[2, 4] = -6 * EIy_L2
        K[2, 8] = -12 * EIy_L3
        K[2, 10] = -6 * EIy_L2
        
        K[4, 2] = -6 * EIy_L2
        K[4, 4] = 4 * EIy_L
        K[4, 8] = 6 * EIy_L2
        K[4, 10] = 2 * EIy_L
        
        K[8, 2] = -12 * EIy_L3
        K[8, 4] = 6 * EIy_L2
        K[8, 8] = 12 * EIy_L3
        K[8, 10] = 6 * EIy_L2
        
        K[10, 2] = -6 * EIy_L2
        K[10, 4] = 2 * EIy_L
        K[10, 8] = 6 * EIy_L2
        K[10, 10] = 4 * EIy_L
        
        return K
    
    def actualizar_reacciones_global(self) -> None:
        """
        Actualiza las reacciones de empotramiento transformándolas a coordenadas globales.
        """
        self.transformar_reacciones_empotramiento_a_global()
    
    def solicitacion_extremo_de_barra_local(self) -> np.ndarray:
        """
        Convierte las solicitaciones de extremo de barra desde GLOBAL a LOCAL.
        
        Se aplica la rotación en dos pasos, en este orden:
        1) Vector intermedio = R @ F_global
        2) Vector local      = T @ vector_intermedio
        
        Donde:
        - R es la matriz de rotación de 12x12 para el giro en el plano y-z.
        - T es la matriz de rotación de 12x12 basada en los cosenos directores.
        
        Retorna:
        --------
        np.ndarray
            Vector de 12 componentes con solicitaciones de extremos en coordenadas locales.
        """
        if self.solicitaciones_extremos_global is None:
            raise ValueError(
                f"Barra {self.id}: no hay solicitaciones globales. "
                "Primero ejecutá calcular_reacciones() en la estructura."
            )
        
        F_global = np.asarray(self.solicitaciones_extremos_global, dtype=np.float64).ravel()
        if F_global.size != 12:
            raise ValueError(
                f"Barra {self.id}: solicitaciones_extremos_global debe tener 12 componentes, "
                f"pero tiene {F_global.size}."
            )
        
        # Paso 1: rotación en el plano y-z (matriz R de 12x12)
        R = self.construir_matriz_rotacion_2d_12x12()
        F_rotado = R @ F_global
        
        # Paso 2: rotación con cosenos directores (matriz T de 12x12)
        T = self.construir_matriz_rotacion_T_12x12()
        F_local = T @ F_rotado
        
        # Guardar resultados locales completos y por extremo (6 + 6)
        self.solicitaciones_extremos_local = F_local.copy()
        self.solicitaciones_extremo_i_local = F_local[:6].copy()
        self.solicitaciones_extremo_f_local = F_local[6:].copy()
        
        return self.solicitaciones_extremos_local.copy()
    
     