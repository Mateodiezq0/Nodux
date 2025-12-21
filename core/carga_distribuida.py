from dataclasses import dataclass, field
from core.carga_puntual import CargaPuntual, matriz_rotacion_x, matriz_rotacion_y, matriz_rotacion_z
import numpy as np
from typing import List

class CargaDistribuida(CargaPuntual):
    
    id: int

    x: float  # Posición de inicio de la carga 
    y: float  # Posición de inicio de la carga 
    z: float  # Posición de inicio de la carga 

    q: float  # Magnitud de la carga (fuerza o momento) (En KN, teniendo en cuenta que si el numero es positivo, la carga es hacia arriba, y si es negativo, hacia abajo) 
    q_f: float  # Magnitud final de la carga (fuerza o momento) (En KN, teniendo en cuenta que si el numero es positivo, la carga es hacia arriba, y si es negativo, hacia abajo)

    alpha_x: float  # Rotación alrededor del eje X (grados, positivo = antihorario)
    alpha_y: float  # Rotación alrededor del eje Y (grados, positivo = antihorario)
    alpha_z: float  # Rotación alrededor del eje Z (grados, positivo = antihorario)


    x_f: float  # Posición de final de la carga 
    y_f: float  # Posición de final de la carga
    z_f: float  # Posición de final de la carga

    
