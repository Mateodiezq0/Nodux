import numpy as np
from typing import Optional

from core.carga_puntual import CargaPuntual


class CargaDistribuida(CargaPuntual):
    """
    Carga distribuida uniforme sobre un tramo de barra.

    Atributos de posicion:
      (x, y, z)           - punto inicial global de la carga
      (x_f, y_f, z_f)     - punto final global de la carga

    Intensidad:
      force_global_intensity  - vector [qx, qy, qz] por unidad de longitud (kN/cm)
      (alternativa legacy: escalar q con angulos alpha_x/y/z)

    El campo ``is_distributed = True`` permite que las funciones de diagrama
    y dibujo distingan esta carga de las puntuales.

    Atributos calculados por ``reacciones_de_empotramiento``:
      x_local_start, x_local_end  - coord. locales x del tramo cargado
      f_local                     - resultante total en ejes locales (3,)
      r_empotramiento_local       - vector fijo de empotramiento (12,)
      carga_nodal_local           - opuesto de r_empotramiento_local (12,)
      F_x                         - resultante global para visualizacion (3,)
    """

    is_distributed = True

    def __init__(
        self,
        id: int,
        x: float,
        y: float,
        z: float,
        x_f: float,
        y_f: float,
        z_f: float,
        q: float = 0.0,
        q_f: float = 0.0,
        alpha_x: float = 0.0,
        alpha_y: float = 0.0,
        alpha_z: float = 0.0,
        force_global_intensity: Optional[np.ndarray] = None,
    ):
        super().__init__(id=id, x=x, y=y, z=z)
        self.x_f = x_f
        self.y_f = y_f
        self.z_f = z_f
        self.q = q
        self.q_f = q_f
        self.alpha_x = alpha_x
        self.alpha_y = alpha_y
        self.alpha_z = alpha_z

        if force_global_intensity is not None:
            self.force_global_intensity = (
                np.asarray(force_global_intensity, dtype=float).ravel()[:3].copy()
            )
        else:
            ax = np.radians(alpha_x)
            ay = np.radians(alpha_y)
            az = np.radians(alpha_z)
            self.force_global_intensity = q * np.array(
                [np.cos(ax), np.cos(ay), np.cos(az)], dtype=float
            )

        # Atributos calculados en reacciones_de_empotramiento
        self.x_local_start = 0.0
        self.x_local_end = 0.0

    def reacciones_de_empotramiento(self, barra):
        """
        Calcula las reacciones de empotramiento para una carga distribuida uniforme
        usando integrales exactas de las funciones de forma de Hermite.

        Convenio identico al de CargaPuntual:
            f_empotramiento = -(fuerzas nodales consistentes de la carga)
        """
        barra.calcular_longitud_y_bases()

        L = float(barra.L)
        if L < 1e-12:
            return barra.reaccion_de_empotramiento_local_total

        pos_i = np.array([self.x, self.y, self.z], dtype=float)
        pos_f = np.array([self.x_f, self.y_f, self.z_f], dtype=float)
        c = float(np.linalg.norm(pos_f - pos_i))

        if c < 1e-12:
            return barra.reaccion_de_empotramiento_local_total

        # Resultante global (total = intensidad * longitud del tramo)
        v_carga_global = self.force_global_intensity * c

        # Actualizar F_x para visualizacion de cargas (compatibilidad con point)
        self.F_x = v_carga_global.copy()
        self.F_y = np.zeros(3, dtype=float)
        self.F_z = np.zeros(3, dtype=float)

        # Proyeccion al sistema local de la barra
        r_base = barra.construir_matriz_rotacion_R_3x3()
        f_local = r_base @ v_carga_global
        self.f_local = f_local.copy()

        # Posicion local del tramo cargado (proyeccion sobre eje de la barra)
        nodo_i_coord = barra.nodo_i_obj.get_coord()
        li = float(np.dot(pos_i - nodo_i_coord, barra.x_local))
        lf = float(np.dot(pos_f - nodo_i_coord, barra.x_local))
        li = max(0.0, min(L, li))
        lf = max(0.0, min(L, lf))
        if li > lf:
            li, lf = lf, li

        self.x_local_start = li
        self.x_local_end = lf

        # Intensidades por unidad de longitud en coordenadas locales
        q_x = f_local[0] / c   # axial
        q_y = f_local[1] / c   # cortante y
        q_z = f_local[2] / c   # cortante z

        # ----------------------------------------------------------------
        # Integrales de las funciones de forma de Hermite sobre [xi1, xi2]
        # (xi = x/L, coordenada normalizada)
        #
        #   N1(xi) = 1 - 3xi^2 + 2xi^3        (desplaz. nodo i)
        #   N2(xi) = xi(1-xi)^2  (x L)        (giro nodo i, escalado L)
        #   N3(xi) = 3xi^2 - 2xi^3            (desplaz. nodo j)
        #   N4(xi) = xi^2(xi-1)  (x L)        (giro nodo j, escalado L)
        #
        # Antiderivadas:
        #   int N1 dxi = xi - xi^3 + xi^4/2
        #   int N2 dxi = xi^2/2 - 2xi^3/3 + xi^4/4
        #   int N3 dxi = xi^3 - xi^4/2
        #   int N4 dxi = xi^4/4 - xi^3/3
        #
        # Fuerzas nodales equivalentes (carga en +y, plano x-y):
        #   Fvi_y  = q_y * L * dI1   (fuerza en v_i, +y)
        #   Fthi_z = q_y * L^2 * dI2 (momento en theta_i, CCW+)
        #   Fvj_y  = q_y * L * dI3
        #   Fthj_z = q_y * L^2 * dI4
        #
        # Convenio: f_empotramiento = -(fuerzas consistentes)
        # Para la direccion z (plano x-z) el momento theta_y se toma con
        # signo opuesto al theta_z por la regla de la mano derecha.
        # ----------------------------------------------------------------
        xi1 = li / L
        xi2 = lf / L

        def _n1(xi): return xi - xi ** 3 + xi ** 4 / 2.0
        def _n2(xi): return xi ** 2 / 2.0 - 2.0 * xi ** 3 / 3.0 + xi ** 4 / 4.0
        def _n3(xi): return xi ** 3 - xi ** 4 / 2.0
        def _n4(xi): return xi ** 4 / 4.0 - xi ** 3 / 3.0

        # Integrales sobre el tramo cargado
        dI1 = _n1(xi2) - _n1(xi1)
        dI2 = _n2(xi2) - _n2(xi1)
        dI3 = _n3(xi2) - _n3(xi1)
        dI4 = _n4(xi2) - _n4(xi1)

        # Funciones lineales para la componente axial
        def _na1(xi): return xi - xi ** 2 / 2.0
        def _na2(xi): return xi ** 2 / 2.0

        dIa1 = _na1(xi2) - _na1(xi1)
        dIa2 = _na2(xi2) - _na2(xi1)

        # Vector de 12 DOF (convenio: f_emp = -fuerzas consistentes)
        f_empotramiento = np.zeros(12)

        # Axial
        f_empotramiento[0] = -(q_x * L * dIa1)
        f_empotramiento[6] = -(q_x * L * dIa2)

        # Plano x-y: cortante (V_y) y momento (M_z)
        f_empotramiento[1]  = -(q_y * L      * dI1)
        f_empotramiento[5]  = -(q_y * L ** 2 * dI2)
        f_empotramiento[7]  = -(q_y * L      * dI3)
        f_empotramiento[11] = -(q_y * L ** 2 * dI4)

        # Plano x-z: cortante (V_z) y momento (M_y)
        # signo opuesto en los momentos por la regla de la mano derecha
        f_empotramiento[2]  = -(q_z * L      * dI1)
        f_empotramiento[4]  =  (q_z * L ** 2 * dI2)
        f_empotramiento[8]  = -(q_z * L      * dI3)
        f_empotramiento[10] =  (q_z * L ** 2 * dI4)

        self.r_empotramiento_local = f_empotramiento.copy()
        self.carga_nodal_local = -f_empotramiento.copy()

        # Acumular en la barra
        barra.reaccion_de_empotramiento_local_total += f_empotramiento
        barra.reaccion_de_empotramiento_i_local += f_empotramiento[:6]
        barra.reaccion_de_empotramiento_f_local += f_empotramiento[6:]

        return barra.reaccion_de_empotramiento_local_total
