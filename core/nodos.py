from dataclasses import dataclass, field
import numpy as np
from typing import List

@dataclass
class Nodo:
    id: int
    x: float
    y: float
    z: float
    restricciones: List[bool] = field(default_factory=lambda: [False]*6) # 6 restricciones: 3 translacionales y 3 rotacionales
    valores_prescritos: List[float] = field(default_factory=lambda: [0.0]*6) # 6 valores prescritos: 3 translacionales y 3 rotacionales
    reaccion_global: List[float] = field(default_factory=lambda: [0.0]*6) # Reaccion global del nodo

    def get_coord(self):
        return np.array([self.x, self.y, self.z])
