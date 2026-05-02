"""
Propiedades geométricas de secciones paramétricas (cm, cm², cm⁴).
Convención alineada con barras 3D: I_y e I_z son inercias principales en el plano de la sección.
"""

from __future__ import annotations

import math
from typing import Any, Dict


def props_rectangle(b: float, h: float) -> Dict[str, float]:
    """Rectángulo b × h (cm). I_y = flexión alrededor del eje paralelo a b; I_z paralelo a h."""
    b = float(b)
    h = float(h)
    if b <= 0 or h <= 0:
        raise ValueError("b y h deben ser positivos")
    A = b * h
    I_y = b * (h**3) / 12.0
    I_z = h * (b**3) / 12.0
    J = _j_rectangle_st_venant(b, h)
    return {"A": A, "I_y": I_y, "I_z": I_z, "J": J}


def _j_rectangle_st_venant(b: float, h: float) -> float:
    """Constante torsional St. Venant para rectángulo sólido."""
    a = max(b, h)
    bb = min(b, h)
    if a <= 0 or bb <= 0:
        return 1e-12
    return bb * (a**3) * (16.0 / 3.0 - 3.36 * (bb / a) * (1.0 - (bb**3) / (12.0 * (a**3))))


def props_i_beam(h_tot: float, bf: float, tw: float, tf: float) -> Dict[str, float]:
    """
    Perfil I doblemente simétrico (cm).
    h_tot: altura total; bf: ancho patín; tw: espesor alma; tf: espesor patín.
    I_z = inercia fuerte (flexión en el plano del alma); I_y = débil.
    """
    h_tot = float(h_tot)
    bf = float(bf)
    tw = float(tw)
    tf = float(tf)
    if min(h_tot, bf, tw, tf) <= 0:
        raise ValueError("Dimensiones de perfil I deben ser positivas")
    hw = max(h_tot - 2.0 * tf, 0.0)
    A = 2.0 * bf * tf + hw * tw
    d_fc = (h_tot - tf) / 2.0
    I_strong = (tw * (hw**3)) / 12.0 + 2.0 * (
        (bf * (tf**3)) / 12.0 + bf * tf * (d_fc**2)
    )
    I_weak = 2.0 * (tf * (bf**3)) / 12.0 + (hw * (tw**3)) / 12.0
    I_y = I_weak
    I_z = I_strong
    J = (tw**3) * hw / 3.0 + 2.0 * (bf * (tf**3)) / 3.0
    return {"A": A, "I_y": I_y, "I_z": I_z, "J": max(J, 1e-12)}


def props_tube_circle(D: float, t: float) -> Dict[str, float]:
    """Tubo circular: D diámetro exterior, t espesor de pared (cm)."""
    D = float(D)
    t = float(t)
    if D <= 0 or t <= 0 or t >= D / 2.0:
        raise ValueError("Tubo circular: D > 0, 0 < t < D/2")
    Ro = D / 2.0
    Ri = Ro - t
    A = math.pi * (Ro**2 - Ri**2)
    I_y = math.pi * (Ro**4 - Ri**4) / 4.0
    I_z = I_y
    J = math.pi * (Ro**4 - Ri**4) / 2.0
    return {"A": A, "I_y": I_y, "I_z": I_z, "J": max(J, 1e-12)}


def props_tube_rect(b_out: float, h_out: float, t: float) -> Dict[str, float]:
    """Tubo rectangular hueco, espesor uniforme t (cm)."""
    b_out = float(b_out)
    h_out = float(h_out)
    t = float(t)
    if min(b_out, h_out, t) <= 0 or 2 * t >= min(b_out, h_out):
        raise ValueError("Tubo rectangular: dimensiones o espesor inválidos")
    bi = b_out - 2.0 * t
    hi = h_out - 2.0 * t
    A = b_out * h_out - bi * hi
    I_y = (b_out * (h_out**3) - bi * (hi**3)) / 12.0
    I_z = (h_out * (b_out**3) - hi * (bi**3)) / 12.0
    # J aproximado sección hueca delgada rectangular
    p = 2.0 * ((b_out - t) + (h_out - t))
    Am = (b_out - t) * (h_out - t)
    J = 4.0 * (t * (Am**2)) / p if p > 0 else min(I_y, I_z)
    return {"A": max(A, 1e-12), "I_y": I_y, "I_z": I_z, "J": max(J, 1e-12)}


def compute_section(section: Dict[str, Any]) -> Dict[str, float]:
    """Calcula A, I_y, I_z, J desde section.type y parámetros."""
    if not isinstance(section, dict):
        raise ValueError("section debe ser un objeto")
    st = str(section.get("type", "")).lower().strip()
    if st in ("rectangle", "rect", "rectangular"):
        return props_rectangle(float(section["b"]), float(section["h"]))
    if st in ("i_beam", "i", "ipe", "ipn"):
        return props_i_beam(
            float(section["h"]),
            float(section["bf"]),
            float(section["tw"]),
            float(section["tf"]),
        )
    if st in ("tube_circle", "tubo_circular", "pipe"):
        return props_tube_circle(float(section["D"]), float(section["t"]))
    if st in ("tube_rect", "tubo_rectangular", "box"):
        return props_tube_rect(float(section["b"]), float(section["h"]), float(section["t"]))
    raise ValueError(f"Tipo de sección no soportado: {st!r}")


def section_summary(section: Dict[str, Any]) -> str:
    """Texto corto para tabla inspector."""
    if not isinstance(section, dict):
        return ""
    st = str(section.get("type", "")).lower()
    try:
        if st in ("rectangle", "rect", "rectangular"):
            return f"Rect {section.get('b')}×{section.get('h')}"
        if st in ("i_beam", "i", "ipe", "ipn"):
            return f"I h={section.get('h')} bf={section.get('bf')} tw={section.get('tw')} tf={section.get('tf')}"
        if st in ("tube_circle", "tubo_circular", "pipe"):
            return f"Ø{section.get('D')} t={section.get('t')}"
        if st in ("tube_rect", "tubo_rectangular", "box"):
            return f"Cajón {section.get('b')}×{section.get('h')} t={section.get('t')}"
    except Exception:
        pass
    return st or "—"
