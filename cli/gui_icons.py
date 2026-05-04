"""
Iconos vectoriales pixel-perfect para barra de herramientas estilo CAD/CAE (sin assets externos).
"""

from __future__ import annotations

from typing import Callable, Dict

_cache: Dict[str, object] = {}
# Incrementar al cambiar dibujos para invalidar caché en caliente (reload de módulo).
_ICONS_REVISION = 2


def _gui_modules():
    try:
        from PySide6.QtCore import QPointF, Qt, QSize
        from PySide6.QtGui import (
            QBrush,
            QColor,
            QIcon,
            QPainter,
            QPen,
            QPixmap,
            QPolygonF,
        )

        return QPointF, Qt, QSize, QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
    except ImportError:
        from PyQt5.QtCore import QPointF, Qt, QSize
        from PyQt5.QtGui import (
            QBrush,
            QColor,
            QIcon,
            QPainter,
            QPen,
            QPixmap,
            QPolygonF,
        )

        return QPointF, Qt, QSize, QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF


def _icon_from_paint(size: int, painter_fn: Callable[..., None]) -> "QIcon":
    _, _, _, _, QColor, QIcon, QPainter, _, QPixmap, _ = _gui_modules()
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter_fn(p, size)
    p.end()
    ic = QIcon(pm)
    return ic


def ftool_engineering_icons() -> Dict[str, object]:
    """Retorna dict con claves: node, bar, load, run, delete, new, open, save, view3d, viewtable."""
    global _cache
    if _cache and _cache.get("_revision") == _ICONS_REVISION:
        return {k: v for k, v in _cache.items() if k != "_revision"}

    QPointF, Qt, _, QBrush, QColor, _, QPainter, QPen, _, QPolygonF = _gui_modules()
    s = 20

    def paint_node(p: QPainter, sz: int) -> None:
        p.setPen(QPen(QColor("#7a8fa3"), 1.2))
        p.setBrush(QBrush(QColor("#5c7a94")))
        p.drawEllipse(4, 4, sz - 8, sz - 8)

    def paint_bar(p: QPainter, sz: int) -> None:
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", None)
        if _solid is None:
            _solid = Qt.SolidLine
        p.setPen(QPen(QColor("#b8bcc4"), 2.0, _solid))
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setBrush(_nobrush)
        p.drawLine(3, sz - 3, sz - 3, 3)

    def paint_load(p: QPainter, sz: int) -> None:
        p.setPen(QPen(QColor("#c9a227"), 1.5))
        p.setBrush(QBrush(QColor("#d4af37")))
        arr = QPolygonF(
            [
                QPointF(3, sz * 0.55),
                QPointF(sz - 5, sz * 0.55),
                QPointF(sz - 9, sz * 0.42),
                QPointF(sz - 9, sz * 0.68),
                QPointF(sz - 5, sz * 0.55),
            ]
        )
        p.drawPolygon(arr)

    def paint_run(p: QPainter, sz: int) -> None:
        _nopen = getattr(getattr(Qt, "PenStyle", object), "NoPen", Qt.NoPen)
        p.setPen(QPen(_nopen))
        p.setBrush(QBrush(QColor("#4a8f6c")))
        tri = QPolygonF(
            [
                QPointF(5, 4),
                QPointF(5, sz - 4),
                QPointF(sz - 4, sz / 2),
            ]
        )
        p.drawPolygon(tri)

    def paint_delete(p: QPainter, sz: int) -> None:
        p.setPen(QPen(QColor("#b0706a"), 1.6))
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setBrush(_nobrush)
        p.drawRect(4, 5, sz - 8, sz - 10)
        p.drawLine(7, 8, sz - 7, sz - 8)

    def paint_new(p: QPainter, sz: int) -> None:
        # Hoja con esquina doblada + símbolo +
        p.setPen(QPen(QColor("#5080a0"), 1.3))
        p.setBrush(QBrush(QColor("#ddeeff")))
        fold = sz - 8
        pts = QPolygonF([
            QPointF(3, 2),
            QPointF(fold, 2),
            QPointF(sz - 2, 8),
            QPointF(sz - 2, sz - 2),
            QPointF(3, sz - 2),
        ])
        p.drawPolygon(pts)
        p.drawLine(fold, 2, fold, 8)
        p.drawLine(fold, 8, sz - 2, 8)
        p.setPen(QPen(QColor("#306090"), 1.8))
        cx, cy = sz // 2 - 1, sz // 2 + 2
        p.drawLine(cx - 3, cy, cx + 3, cy)
        p.drawLine(cx, cy - 3, cx, cy + 3)

    def paint_open(p: QPainter, sz: int) -> None:
        # Carpeta
        p.setPen(QPen(QColor("#907020"), 1.2))
        p.setBrush(QBrush(QColor("#f5c430")))
        p.drawRect(2, sz // 3, sz - 4, sz // 2)
        p.setBrush(QBrush(QColor("#f5d860")))
        p.drawRect(2, sz // 3 - 3, sz // 3 + 2, 4)

    def paint_save(p: QPainter, sz: int) -> None:
        # Flecha hacia abajo con bandeja (guardar)
        p.setPen(QPen(QColor("#4060a0"), 1.4))
        p.setBrush(QBrush(QColor("#6080c8")))
        arr = QPolygonF([
            QPointF(sz / 2, sz - 4),
            QPointF(sz / 2 - 4, sz / 2 - 1),
            QPointF(sz / 2 + 4, sz / 2 - 1),
        ])
        p.drawPolygon(arr)
        p.drawLine(int(sz / 2), 3, int(sz / 2), int(sz / 2))
        p.setPen(QPen(QColor("#4060a0"), 1.6))
        p.drawLine(3, sz - 3, sz - 3, sz - 3)

    def paint_view3d(p: QPainter, sz: int) -> None:
        """Cubo isométrico alámbrico (bloque 3D reconocible)."""
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setBrush(_nobrush)
        p.setPen(QPen(QColor("#2a5a90"), 1.35))
        x0, y0, w, h = 3, 9, 9, 8
        # Cara frontal
        p.drawRect(x0, y0, w, h)
        # Aristas del techo (perspectiva)
        p.drawLine(x0, y0, x0 + 5, 3)
        p.drawLine(x0 + w, y0, x0 + w + 5, 3)
        p.drawLine(x0 + 5, 3, x0 + w + 5, 3)
        # Cara lateral derecha (paralelogramo)
        p.drawLine(x0 + w + 5, 3, x0 + w + 5, 3 + h - 1)
        p.drawLine(x0 + w, y0 + h, x0 + w + 5, 3 + h - 1)
        # Línea de suelo / sombra breve (refuerza volumen)
        p.setPen(QPen(QColor("#8aa0c0"), 1.0))
        p.drawLine(x0, y0 + h, x0 + w + 3, y0 + h + 1)

    def paint_viewtable(p: QPainter, sz: int) -> None:
        """Hoja de cálculo: cabecera + rejilla (resultados tabulares)."""
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", None)
        if _solid is None:
            _solid = Qt.SolidLine
        p.setPen(QPen(QColor("#3a3a3a"), 1.15, _solid))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(2, 2, sz - 4, sz - 4, 1.5, 1.5)
        # Fila de encabezado
        p.setPen(QPen(QColor("#1a5080"), 1.0, _solid))
        p.setBrush(QBrush(QColor("#3d7ab8")))
        p.drawRect(3, 3, sz - 6, 5)
        y_sep = 8
        y1, y2 = (11, 15) if sz >= 20 else (9, 12)
        p.setPen(QPen(QColor("#888888"), 1.0, _solid))
        p.drawLine(3, y_sep, sz - 3, y_sep)
        p.drawLine(3, y1, sz - 3, y1)
        p.drawLine(3, y2, sz - 3, y2)
        cx1 = max(7, int(sz * 0.38))
        cx2 = max(11, int(sz * 0.62))
        p.drawLine(cx1, y_sep, cx1, sz - 3)
        p.drawLine(cx2, y_sep, cx2, sz - 3)
        # Celda activa (mini barra tipo selección)
        p.setPen(QPen(QColor("#b03030"), 1.0, _solid))
        p.setBrush(QBrush(QColor("#e07070")))
        cell_w = max(2, sz - cx2 - 5)
        p.drawRect(cx2 + 1, y1 + 1, cell_w, 2)

    _cache.clear()
    _cache.update(
        {
            "node": _icon_from_paint(s, paint_node),
            "bar": _icon_from_paint(s, paint_bar),
            "load": _icon_from_paint(s, paint_load),
            "run": _icon_from_paint(s, paint_run),
            "delete": _icon_from_paint(s, paint_delete),
            "new": _icon_from_paint(s, paint_new),
            "open": _icon_from_paint(s, paint_open),
            "save": _icon_from_paint(s, paint_save),
            "view3d": _icon_from_paint(s, paint_view3d),
            "viewtable": _icon_from_paint(s, paint_viewtable),
            "_revision": _ICONS_REVISION,
        }
    )
    return {k: v for k, v in _cache.items() if k != "_revision"}
