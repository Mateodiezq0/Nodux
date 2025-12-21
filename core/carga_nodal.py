from dataclasses import dataclass, field
import numpy as np
from typing import List

class CargaNodal:
    nodo_id: int
    fx: float = 0.0  # Fuerza en X
    fy: float = 0.0  # Fuerza en Y
    fz: float = 0.0  # Fuerza en Z
    mx: float = 0.0  # Momento en X
    my: float = 0.0  # Momento en Y
    mz: float = 0.0  # Momento en Z

    def __init__(self, nodo_id, fx=0.0, fy=0.0, fz=0.0, mx=0.0, my=0.0, mz=0.0):
        self.nodo_id = nodo_id
        self.fx = fx
        self.fy = fy
        self.fz = fz
        self.mx = mx
        self.my = my
        self.mz = mz
    
    def vector(self):
        """ Devuelve el vector de fuerzas y momentos aplicados en el nodo. """
        return np.array([self.fx, self.fy, self.fz, self.mx, self.my, self.mz])

    def __repr__(self):
        """ Representación de la carga nodal para visualizar fácilmente los valores. """
        return f"CargaNodal(nodo_id={self.nodo_id}, fx={self.fx}, fy={self.fy}, fz={self.fz}, mx={self.mx}, my={self.my}, mz={self.mz})"

