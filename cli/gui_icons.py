"""
Iconos vectoriales pixel-perfect para barra de herramientas estilo CAD/CAE (sin assets externos).
"""

from __future__ import annotations

from typing import Callable, Dict

_cache: Dict[str, object] = {}


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
    """Retorna dict con claves: node, bar, load, run, delete."""
    global _cache
    if _cache:
        return _cache

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

    _cache = {
        "node": _icon_from_paint(s, paint_node),
        "bar": _icon_from_paint(s, paint_bar),
        "load": _icon_from_paint(s, paint_load),
        "run": _icon_from_paint(s, paint_run),
        "delete": _icon_from_paint(s, paint_delete),
    }
    return _cache
