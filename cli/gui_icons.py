"""
Iconos vectoriales pixel-perfect para barra de herramientas estilo CAD/CAE (sin assets externos).
"""

from __future__ import annotations

from typing import Callable, Dict

_cache: Dict[str, object] = {}
# Incrementar al cambiar dibujos para invalidar caché en caliente (reload de módulo).
_ICONS_REVISION = 11


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


def ftool_app_window_icon() -> "QIcon":
    """Icono multi-tamaño para ventana principal y barra de tareas (Windows/Qt)."""
    _, Qt, _, QBrush, QColor, QIcon, QPainter, QPen, QPixmap, _ = _gui_modules()

    def paint_app(p: QPainter, sz: int) -> None:
        _aa = getattr(getattr(QPainter, "RenderHint", QPainter), "Antialiasing", QPainter.Antialiasing)
        p.setRenderHint(_aa, True)
        p.setPen(QPen(QColor(0, 0, 0, 0)))
        p.setBrush(QBrush(QColor("#1a6fc4")))
        p.drawRoundedRect(1, 1, sz - 2, sz - 2, max(2.0, sz * 0.18), max(2.0, sz * 0.18))
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", None)
        if _solid is None:
            _solid = Qt.SolidLine
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setPen(QPen(QColor("#ffffff"), max(1.0, sz / 14.0), _solid))
        p.setBrush(_nobrush)
        m = max(2, int(sz * 0.12))
        x1, y1 = m, sz - m
        xm, ym = sz // 2, m + 1
        x2, y2 = sz - m, sz - m
        p.drawLine(x1, y1, xm, ym)
        p.drawLine(xm, ym, x2, y2)
        r = max(1.5, sz * 0.09)
        for cx, cy in ((x1, y1), (xm, ym), (x2, y2)):
            p.setBrush(QBrush(QColor("#e8f4ff")))
            p.setPen(QPen(QColor("#0d4a8a"), max(0.8, sz / 22.0), _solid))
            p.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)

    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        paint_app(p, size)
        p.end()
        ic.addPixmap(pm)
    return ic


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
    """Retorna dict con claves: node, bar, load, load_distributed, load_nodal, run, delete, new, open, save, undo, redo, view3d, viewtable."""
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

    def paint_load_distributed(p: QPainter, sz: int) -> None:
        """Flechas hacia abajo + viga solo en las puntas; dibujo centrado en el icono."""
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", None)
        if _solid is None:
            _solid = Qt.SolidLine
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        beam_pen = QPen(QColor("#8a93a0"), max(1.0, sz / 16.0), _solid)
        cx_mid = sz / 2.0
        wt = max(0.45, sz * 0.022)
        stem = sz * 0.22
        head_h = max(2.5, sz * 0.15)
        wh = max(1.55, sz * 0.062)
        dx = min(sz * 0.16, max(2.2, (sz / 2.0 - 1.6) - wh))
        pad_x = max(0.75, sz * 0.035)
        y_top = sz / 2.0 - (stem + head_h) / 2.0
        y1 = y_top + stem
        y2 = y1 + head_h
        x_left = max(1.5, cx_mid - dx - wh - pad_x)
        x_right = min(sz - 1.5, cx_mid + dx + wh + pad_x)
        stroke = QColor("#a87018")
        fill = QColor("#e89a28")
        p.setPen(QPen(stroke, max(1.0, sz / 22.0), _solid))
        p.setBrush(QBrush(fill))
        for cx in (cx_mid - dx, cx_mid, cx_mid + dx):
            shaft = QPolygonF(
                [
                    QPointF(cx - wt, y_top),
                    QPointF(cx + wt, y_top),
                    QPointF(cx + wt, y1),
                    QPointF(cx + wh, y1),
                    QPointF(cx, y2),
                    QPointF(cx - wh, y1),
                    QPointF(cx - wt, y1),
                ]
            )
            p.drawPolygon(shaft)
        p.setPen(beam_pen)
        p.setBrush(_nobrush)
        p.drawLine(int(x_left), int(y2), int(x_right), int(y2))

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

    def paint_undo(p: QPainter, sz: int) -> None:
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", Qt.SolidLine)
        _sq = getattr(getattr(Qt, "PenCapStyle", object), "SquareCap", getattr(Qt, "SquareCap", Qt.RoundCap))
        _miter = getattr(getattr(Qt, "PenJoinStyle", object), "MiterJoin", getattr(Qt, "MiterJoin", Qt.RoundJoin))
        p.setPen(QPen(QColor("#1f5d97"), 2.8, _solid, _sq, _miter))
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setBrush(_nobrush)
        # Flecha "u-turn" simple: línea superior, bajada y retorno
        p.drawLine(15, 6, 8, 6)
        p.drawLine(15, 6, 15, 12)
        p.drawLine(8, 12, 15, 12)
        p.setPen(QPen(QColor("#1f5d97"), 1.0, _solid))
        p.setBrush(QBrush(QColor("#2f74b7")))
        p.drawPolygon(QPolygonF([QPointF(3.5, 6.0), QPointF(8.2, 3.1), QPointF(8.2, 8.9)]))

    def paint_redo(p: QPainter, sz: int) -> None:
        _solid = getattr(getattr(Qt, "PenStyle", object), "SolidLine", Qt.SolidLine)
        _sq = getattr(getattr(Qt, "PenCapStyle", object), "SquareCap", getattr(Qt, "SquareCap", Qt.RoundCap))
        _miter = getattr(getattr(Qt, "PenJoinStyle", object), "MiterJoin", getattr(Qt, "MiterJoin", Qt.RoundJoin))
        p.setPen(QPen(QColor("#1f5d97"), 2.8, _solid, _sq, _miter))
        _nobrush = getattr(getattr(Qt, "BrushStyle", object), "NoBrush", Qt.NoBrush)
        p.setBrush(_nobrush)
        # Espejo horizontal de undo
        p.drawLine(5, 6, 12, 6)
        p.drawLine(5, 6, 5, 12)
        
        p.drawLine(12, 12, 5, 12)
        p.setPen(QPen(QColor("#1f5d97"), 1.0, _solid))
        p.setBrush(QBrush(QColor("#2f74b7")))
        p.drawPolygon(QPolygonF([QPointF(16.5, 6.0), QPointF(11.8, 3.1), QPointF(11.8, 8.9)]))

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

    def paint_load_nodal(p: QPainter, sz: int) -> None:
        # Flecha roja (carga nodal en nodo) con un círculo en la cola
        p.setPen(QPen(QColor("#c83232"), 1.5))
        p.setBrush(QBrush(QColor("#e04444")))
        arr = QPolygonF(
            [
                QPointF(6, sz * 0.55),
                QPointF(sz - 5, sz * 0.55),
                QPointF(sz - 9, sz * 0.42),
                QPointF(sz - 9, sz * 0.68),
                QPointF(sz - 5, sz * 0.55),
            ]
        )
        p.drawPolygon(arr)
        # Círculo en la cola para indicar "aplicada directamente en el nodo"
        p.setBrush(QBrush(QColor("#c83232")))
        r = max(2, int(sz * 0.15))
        p.drawEllipse(int(3 - r // 2), int(sz * 0.55 - r), r * 2, r * 2)

    _cache.clear()
    _cache.update(
        {
            "node": _icon_from_paint(s, paint_node),
            "bar": _icon_from_paint(s, paint_bar),
            "load": _icon_from_paint(s, paint_load),
            "load_distributed": _icon_from_paint(s, paint_load_distributed),
            "load_nodal": _icon_from_paint(s, paint_load_nodal),
            "run": _icon_from_paint(s, paint_run),
            "delete": _icon_from_paint(s, paint_delete),
            "new": _icon_from_paint(s, paint_new),
            "open": _icon_from_paint(s, paint_open),
            "save": _icon_from_paint(s, paint_save),
            "undo": _icon_from_paint(s, paint_undo),
            "redo": _icon_from_paint(s, paint_redo),
            "view3d": _icon_from_paint(s, paint_view3d),
            "viewtable": _icon_from_paint(s, paint_viewtable),
            "_revision": _ICONS_REVISION,
        }
    )
    return {k: v for k, v in _cache.items() if k != "_revision"}
