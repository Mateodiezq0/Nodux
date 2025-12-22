from dataclasses import dataclass, field
import numpy as np
from typing import List



class CargaPuntual:
    id: int

    x: float  # Posición de inicio de la carga 
    y: float  # Posición de inicio de la carga 
    z: float  # Posición de inicio de la carga 

    q: float  # Magnitud de la carga (fuerza o momento) (En KN, teniendo en cuenta que si el numero es positivo, la carga es hacia arriba, y si es negativo, hacia abajo) 

    rotacion_x: float  # Rotación alrededor del eje X (grados, positivo = antihorario)
    rotacion_y: float  # Rotación alrededor del eje Y (grados, positivo = antihorario)
    rotacion_z: float  # Rotación alrededor del eje Z (grados, positivo = antihorario)


    
    