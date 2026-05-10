"""
Previsualización 2D de secciones y perfil IPN de vista (matplotlib), p. ej. editor de materiales.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np


def draw_material_preview(
    fig: Any,
    *,
    mode_is_param: bool,
    sec_index: int,
    rect_b: float,
    rect_h: float,
    i_h: float,
    i_bf: float,
    i_tw: float,
    i_tf: float,
    tc_D: float,
    tc_t: float,
    tr_b: float,
    tr_h: float,
    tr_t: float,
    viz_use_global: bool,
    viz_h: float,
    viz_b: float,
    viz_tw: float,
    viz_tf: float,
    manual_polygon_yz: Optional[list] = None,
    catalog_profile: Optional[dict] = None,
) -> None:
    """
    Dibuja dos paneles: sección paramétrica (cálculo) y contorno IPN de vista 3D.
    ``sec_index``: 0 rect, 1 I, 2 tubo circular, 3 tubo rectangular.

    Si ``catalog_profile`` viene seteado con un perfil válido del catálogo
    (dict con ``family``, ``d``, ``bf``, ``tf``, ``tw``), manda sobre ambos
    paneles y dibuja la forma real del perfil ignorando modo/viz globales.
    """
    fig.clf()
    ax_s = fig.add_subplot(2, 1, 1)
    ax_v = fig.add_subplot(2, 1, 2)
    for ax in (ax_s, ax_v):
        ax.set_facecolor("#ececec")
        ax.grid(True, linestyle=":", alpha=0.6)

    if _catalog_profile_valid(catalog_profile):
        _render_catalog_panels(ax_s, ax_v, catalog_profile)
        fig.subplots_adjust(hspace=0.35, left=0.12, right=0.95, top=0.93, bottom=0.08)
        return

    sec_keys = ["rectangle", "i_beam", "tube_circle", "tube_rect"]

    # --- Panel superior: sección de cálculo ---
    if not mode_is_param:
        mp = manual_polygon_yz if isinstance(manual_polygon_yz, list) else []
        if len(mp) >= 3:
            try:
                arr = np.asarray(mp, dtype=float)
                ax_s.plot(arr[:, 0], arr[:, 1], "o-", color="#1b4f72", ms=4, lw=1.2)
                ac = np.vstack([arr, arr[:1]])
                ax_s.fill(ac[:, 0], ac[:, 1], alpha=0.35, color="#7fb3d5")
                ax_s.set_title("Sección dibujada (manual, plano Y–Z)", fontsize=9, color="#2c3e50")
                ax_s.set_xlabel("Y (cm)")
                ax_s.set_ylabel("Z (cm)")
                ax_s.set_aspect("equal", adjustable="box")
                pad = float(max(np.ptp(arr[:, 0]), np.ptp(arr[:, 1]), 1.0) * 0.15)
                ax_s.set_xlim(float(arr[:, 0].min()) - pad, float(arr[:, 0].max()) + pad)
                ax_s.set_ylim(float(arr[:, 1].min()) - pad, float(arr[:, 1].max()) + pad)
            except Exception:
                ax_s.text(
                    0.5,
                    0.5,
                    "Polígono inválido",
                    ha="center",
                    va="center",
                    transform=ax_s.transAxes,
                    color="#a93226",
                )
        elif len(mp) >= 1:
            arr = np.asarray(mp, dtype=float)
            ax_s.plot(arr[:, 0], arr[:, 1], "o-", color="#1b4f72", ms=5)
            ax_s.set_title("Sección manual (≥ 3 puntos para cerrar)", fontsize=9, color="#2c3e50")
            ax_s.set_xlabel("Y (cm)")
            ax_s.set_ylabel("Z (cm)")
            ax_s.set_aspect("equal", adjustable="box")
        else:
            ax_s.text(
                0.5,
                0.55,
                "Modo manual:\nen la pestaña «Propiedades manuales»\ndibujá el perfil en el plano Y–Z\n(clic izq. = vértice, clic der. = borrar)",
                ha="center",
                va="center",
                transform=ax_s.transAxes,
                fontsize=9,
                color="#333",
            )
            ax_s.set_xticks([])
            ax_s.set_yticks([])
    else:
        key = sec_keys[sec_index] if 0 <= sec_index < len(sec_keys) else "rectangle"
        try:
            if key == "rectangle":
                _draw_rect(ax_s, rect_b, rect_h)
            elif key == "i_beam":
                _draw_i_beam(ax_s, i_h, i_bf, i_tw, i_tf)
            elif key == "tube_circle":
                _draw_tube_circle(ax_s, tc_D, tc_t)
            else:
                _draw_tube_rect(ax_s, tr_b, tr_h, tr_t)
        except (ValueError, ZeroDivisionError):
            ax_s.text(
                0.5,
                0.5,
                "Parámetros inválidos",
                ha="center",
                va="center",
                transform=ax_s.transAxes,
                color="#a93226",
            )
        ax_s.set_title("Sección (cálculo)", fontsize=9, color="#2c3e50")
        ax_s.set_aspect("equal", adjustable="box")

    # --- Panel inferior: perfil IPN en vista 3D ---
    if viz_use_global:
        ax_v.text(
            0.5,
            0.55,
            "Vista 3D: dimensiones\nglobales del visor",
            ha="center",
            va="center",
            transform=ax_v.transAxes,
            fontsize=10,
            color="#555",
        )
        ax_v.set_xticks([])
        ax_v.set_yticks([])
    else:
        try:
            _draw_ipn_outline(ax_v, viz_h, viz_b, viz_tw, viz_tf)
        except (ValueError, ZeroDivisionError):
            ax_v.text(
                0.5,
                0.5,
                "Perfil: valores inválidos",
                ha="center",
                va="center",
                transform=ax_v.transAxes,
                color="#a93226",
            )
        ax_v.set_aspect("equal", adjustable="box")
    ax_v.set_title("Vista 3D (perfil)", fontsize=9, color="#2c3e50")

    fig.subplots_adjust(hspace=0.35, left=0.12, right=0.95, top=0.93, bottom=0.08)


def _draw_rect(ax: Any, b: float, h: float) -> None:
    b, h = float(b), float(h)
    if b <= 0 or h <= 0:
        raise ValueError("b,h")
    from matplotlib.patches import Rectangle

    ax.add_patch(
        Rectangle((-b / 2, -h / 2), b, h, fill=True, facecolor="#aed6f1", edgecolor="#1b4f72", lw=1.2)
    )
    lim = max(b, h) * 0.65
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)


def _draw_i_beam(ax: Any, h: float, bf: float, tw: float, tf: float) -> None:
    h, bf, tw, tf = float(h), float(bf), float(tw), float(tf)
    if min(h, bf, tw, tf) <= 0 or tw >= bf or 2 * tf >= h:
        raise ValueError("I")
    # Contorno poligonal en y-z (z vertical local tipo IPN)
    zt = h / 2.0
    zb = -h / 2.0
    xL, xR = -bf / 2.0, bf / 2.0
    xm = tw / 2.0
    xs = [
        [xL, zt],
        [xR, zt],
        [xR, zt - tf],
        [xm, zt - tf],
        [xm, zb + tf],
        [xR, zb + tf],
        [xR, zb],
        [xL, zb],
        [xL, zb + tf],
        [-xm, zb + tf],
        [-xm, zt - tf],
        [xL, zt - tf],
        [xL, zt],
    ]
    arr = np.array(xs, dtype=float)
    ax.fill(arr[:, 0], arr[:, 1], color="#aed6f1", edgecolor="#1b4f72", lw=1.2, closed=True)
    lim = max(bf, h) * 0.65
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)


def _draw_tube_circle(ax: Any, D: float, t: float) -> None:
    D, t = float(D), float(t)
    if D <= 0 or t <= 0 or t >= D / 2.0:
        raise ValueError("tube")
    Ro = D / 2.0
    Ri = max(Ro - t, 1e-12)
    th = np.linspace(0.0, 2.0 * math.pi, 200)
    cx, sx = np.cos(th), np.sin(th)
    ax.fill(Ro * cx, Ro * sx, color="#aed6f1", edgecolor="#1b4f72", lw=1.3)
    ax.fill(Ri * cx, Ri * sx, color="#ececec", edgecolor="#566573", lw=1.0)
    lim = Ro * 1.15
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)


def _draw_tube_rect(ax: Any, b: float, h: float, t: float) -> None:
    b, h, t = float(b), float(h), float(t)
    if min(b, h, t) <= 0 or 2 * t >= min(b, h):
        raise ValueError("tube_rect")
    olo = (-b / 2, -h / 2)
    oli = (-b / 2 + t, -h / 2 + t)
    bi, hi = b - 2 * t, h - 2 * t
    from matplotlib.patches import Rectangle

    ax.add_patch(
        Rectangle(olo, b, h, fill=True, facecolor="#aed6f1", edgecolor="#1b4f72", lw=1.2)
    )
    ax.add_patch(
        Rectangle(oli, bi, hi, fill=True, facecolor="#ececec", edgecolor="#566573", lw=1.0)
    )
    lim = max(b, h) * 0.65
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)


def _draw_ipn_outline(ax: Any, h: float, b: float, tw: float, tf: float) -> None:
    """Contorno en Y-Z de un perfil doble-T alargado (misma convención que malla 3D)."""
    h, b, tw, tf = float(h), float(b), float(tw), float(tf)
    if min(h, b, tw, tf) <= 0 or tw >= b or 2 * tf >= h:
        raise ValueError("ipn")
    _draw_i_beam(ax, h, b, tw, tf)


def _draw_ipn_tapered(
    ax: Any,
    d: float,
    bf: float,
    tw: float,
    tf: float,
    *,
    taper: float = 0.14,
) -> None:
    """
    Contorno IPN con alas trapezoidales (cara interior inclinada ~14%).
    ``tf`` se interpreta como espesor medio del ala, en la mitad del voladizo
    (convención de tablas IPN). Si los parámetros son inválidos lanza ValueError.
    """
    d, bf, tw, tf = float(d), float(bf), float(tw), float(tf)
    if min(d, bf, tw, tf) <= 0 or tw >= bf:
        raise ValueError("ipn_tapered")
    overhang = max((bf - tw) / 2.0, 0.0)
    delta = 0.5 * taper * overhang
    tf_tip = max(tf - delta, 0.1 * tf)
    tf_root = tf + delta
    tf_root = min(tf_root, 0.45 * d)
    tf_tip = min(tf_tip, tf_root)

    zt = d / 2.0
    zb = -d / 2.0
    xL, xR = -bf / 2.0, bf / 2.0
    xm = tw / 2.0
    pts = [
        [xL, zt],
        [xR, zt],
        [xR, zt - tf_tip],
        [xm, zt - tf_root],
        [xm, zb + tf_root],
        [xR, zb + tf_tip],
        [xR, zb],
        [xL, zb],
        [xL, zb + tf_tip],
        [-xm, zb + tf_root],
        [-xm, zt - tf_root],
        [xL, zt - tf_tip],
    ]
    arr = np.array(pts, dtype=float)
    ax.fill(
        arr[:, 0],
        arr[:, 1],
        facecolor="#aed6f1",
        edgecolor="#1b4f72",
        lw=1.2,
        closed=True,
    )
    lim = max(bf, d) * 0.65
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)


def _catalog_profile_valid(cat: Optional[dict]) -> bool:
    """Valida que el perfil del catálogo tenga las claves mínimas para dibujarse."""
    if not isinstance(cat, dict):
        return False
    fam = str(cat.get("family", "")).strip().upper()
    if not fam:
        return False
    if fam == "IPN":
        try:
            d = float(cat.get("d", 0.0))
            bf = float(cat.get("bf", 0.0))
            tw = float(cat.get("tw", 0.0))
            tf = float(cat.get("tf", 0.0))
        except (TypeError, ValueError):
            return False
        return min(d, bf, tw, tf) > 0 and tw < bf
    return True


def _render_catalog_panels(ax_s: Any, ax_v: Any, cat: dict) -> None:
    """Dibuja el perfil de catálogo en ambos paneles, con títulos coherentes."""
    fam = str(cat.get("family", "")).strip().upper()
    desig = str(cat.get("designation", "")).strip()
    label = f"{fam} {desig}".strip() if desig else fam

    if fam == "IPN":
        for ax, title_prefix in (
            (ax_s, "Catálogo"),
            (ax_v, "Vista 3D (perfil)"),
        ):
            try:
                _draw_ipn_tapered(
                    ax,
                    float(cat["d"]),
                    float(cat["bf"]),
                    float(cat["tw"]),
                    float(cat["tf"]),
                )
                ax.set_title(f"{title_prefix}: {label}", fontsize=9, color="#2c3e50")
                ax.set_xlabel("Y (cm)")
                ax.set_ylabel("Z (cm)")
                ax.set_aspect("equal", adjustable="box")
            except (ValueError, ZeroDivisionError, TypeError):
                ax.clear()
                ax.set_facecolor("#ececec")
                ax.text(
                    0.5,
                    0.5,
                    f"Perfil {label}: parámetros inválidos",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    color="#a93226",
                )
                ax.set_xticks([])
                ax.set_yticks([])
        return

    for ax, title_prefix in (
        (ax_s, "Catálogo"),
        (ax_v, "Vista 3D (perfil)"),
    ):
        ax.text(
            0.5,
            0.55,
            f"Forma {fam}\naún no disponible",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=10,
            color="#555",
        )
        ax.set_title(f"{title_prefix}: {label}", fontsize=9, color="#2c3e50")
        ax.set_xticks([])
        ax.set_yticks([])
