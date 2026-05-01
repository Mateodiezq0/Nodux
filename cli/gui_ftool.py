"""
Ventana estilo Ftool: modelo en panel lateral, vista 3D PyVista (Qt), analisis y diagramas.

  python -m cli gui

Requiere: pip install pyvista pyvistaqt PySide6
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from PySide6.QtWidgets import QMainWindow as _QMainWindow
except ImportError:
    from PyQt5.QtWidgets import QMainWindow as _QMainWindow

from core.estructura import Estructura

from cli.gui_viz import (
    NODOS_LEGEND_STATUS,
    add_nodos_overlay_pyvista,
    restricciones_texto_desde_spec,
)
from cli.loader import build_estructura_from_spec
from cli.pipeline import load_spec, solve_estructura

# Paleta técnica CAD/CAE: grises industriales, acento apagado (sin azul brillante).
_FTOOL_STYLESHEET = """
QMainWindow, QWidget { font-family: "Segoe UI", "Roboto", "Inter", sans-serif; font-size: 9pt; }
QMainWindow { background-color: #2d2d30; }
QWidget#centralRoot { background-color: #2d2d30; }
QWidget#ftoolToolbar {
    background-color: #333333;
    border: 1px solid #3f3f42;
    border-radius: 2px;
}
QLabel#mutedLabel { color: #9d9fa3; font-size: 9pt; }
QLabel#scaleValue {
    color: #c4c7cc;
    font-weight: 600;
    font-size: 9pt;
    min-width: 3em;
}
QFrame#toolbarSep {
    background-color: #404044;
    max-height: 1px;
    border: none;
}
QToolButton#btnIconTool {
    background-color: #3a3a3e;
    border: 1px solid #4a4a4f;
    border-radius: 2px;
    padding: 2px;
    margin: 0px;
}
QToolButton#btnIconTool:hover {
    background-color: #45454a;
    border-color: #5a5a60;
}
QToolButton#btnIconTool:pressed { background-color: #353539; }
QToolButton#btnIconDanger {
    background-color: #3a3535;
    border: 1px solid #6a4545;
    border-radius: 2px;
    padding: 2px;
}
QToolButton#btnIconDanger:hover {
    background-color: #4a3f3f;
    border-color: #804040;
}
QToolButton#btnAnalyze {
    background-color: #3a4540;
    color: #e8ebe9;
    border: 1px solid #4d6a58;
    border-radius: 2px;
    padding: 4px 10px 4px 8px;
    font-weight: 600;
    font-size: 9pt;
}
QToolButton#btnAnalyze:hover {
    background-color: #455248;
    border-color: #5a7a66;
}
QToolButton#btnAnalyze:pressed { background-color: #323c38; }
QComboBox {
    background-color: #3a3a3e;
    color: #e8e9eb;
    border: 1px solid #4e4e52;
    border-radius: 2px;
    padding: 3px 8px;
    min-width: 180px;
    font-size: 9pt;
}
QComboBox:hover { border-color: #606068; }
QComboBox::drop-down { border: none; width: 22px; }
QSlider::groove:horizontal {
    border: none;
    height: 5px;
    background: #2a2a2d;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #6d7d8c;
    border: none;
    width: 12px;
    margin: -4px 0;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #5a6570;
    border-radius: 2px;
}
QDockWidget::title {
    background-color: #333333;
    color: #b8babf;
    padding: 5px 8px;
    font-weight: 600;
    font-size: 9pt;
}
QTabWidget::pane {
    border: 1px solid #3f3f42;
    background-color: #2d2d30;
    top: -1px;
}
QTabBar::tab {
    background-color: #38383c;
    color: #a0a2a8;
    padding: 5px 14px;
    margin-right: 1px;
    border-top-left-radius: 2px;
    border-top-right-radius: 2px;
    font-size: 9pt;
}
QTabBar::tab:selected {
    background-color: #2d2d30;
    color: #e8e9eb;
    border-bottom: 2px solid #5a6570;
}
QTabBar::tab:hover:!selected { background-color: #3f3f44; }
QTableWidget {
    background-color: #2d2d30;
    alternate-background-color: #323236;
    color: #e0e1e5;
    gridline-color: #3f3f44;
    font-size: 9pt;
    selection-background-color: #4a5568;
    selection-color: #f2f3f5;
}
QTableWidget::item {
    padding: 1px 6px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #4a5568;
    color: #f2f3f5;
}
QHeaderView::section {
    background-color: #38383c;
    color: #a8aaaf;
    padding: 4px 6px;
    border: none;
    border-right: 1px solid #3f3f42;
    border-bottom: 1px solid #3f3f42;
    font-size: 9pt;
    font-weight: 600;
}
QMenuBar {
    background-color: #2d2d30;
    color: #e8e9eb;
    padding: 1px 4px;
    font-size: 9pt;
}
QMenuBar::item:selected { background-color: #3a3a3e; }
QMenu {
    background-color: #3a3a3e;
    color: #e8e9eb;
    border: 1px solid #4e4e52;
    font-size: 9pt;
}
QMenu::item:selected { background-color: #4a5568; }
QStatusBar {
    background-color: #2d2d30;
    color: #8e9198;
    border-top: 1px solid #3f3f42;
    font-size: 8pt;
}
QLabel#statusLegend {
    color: #9a9da4;
    font-size: 8pt;
    padding: 0px 8px;
}
"""


def _default_spec() -> Dict[str, Any]:
    return {
        "materials": {
            "default": {
                "E": 20000.0,
                "A": 100.0,
                "I_y": 833.0,
                "I_z": 833.0,
                "G": 7720.0,
                "J": 1408.0,
            }
        },
        "default_material": "default",
        "nodes": [],
        "bars": [],
        "loads_point": [],
    }


IPN_DEFAULT = {"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0}


def _try_qt():
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QDockWidget,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QMenu,
            QMessageBox,
            QPushButton,
            QSlider,
            QSpinBox,
            QDoubleSpinBox,
            QTreeWidget,
            QTreeWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        from pyvistaqt import QtInteractor

        return (
            "PySide6",
            Qt,
            QApplication,
            QMainWindow,
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QComboBox,
            QSlider,
            QDockWidget,
            QTreeWidget,
            QTreeWidgetItem,
            QFileDialog,
            QMessageBox,
            QMenu,
            QDialog,
            QFormLayout,
            QDialogButtonBox,
            QDoubleSpinBox,
            QSpinBox,
            QCheckBox,
            QtInteractor,
        )
    except ImportError:
        pass
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QDockWidget,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QMenu,
            QMessageBox,
            QPushButton,
            QSlider,
            QSpinBox,
            QDoubleSpinBox,
            QTreeWidget,
            QTreeWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        from pyvistaqt import QtInteractor

        return (
            "PyQt5",
            Qt,
            QApplication,
            QMainWindow,
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QComboBox,
            QSlider,
            QDockWidget,
            QTreeWidget,
            QTreeWidgetItem,
            QFileDialog,
            QMessageBox,
            QMenu,
            QDialog,
            QFormLayout,
            QDialogButtonBox,
            QDoubleSpinBox,
            QSpinBox,
            QCheckBox,
            QtInteractor,
        )
    except ImportError:
        return None


class FtoolMainWindow(_QMainWindow):
    def __init__(
        self,
        backend: str,
        qt_mod: tuple,
        *,
        precargar_ejemplo: bool = False,
        parent: Optional[Any] = None,
    ) -> None:
        (
            _,
            Qt,
            QApplication,
            QMainWindow,
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QComboBox,
            QSlider,
            QDockWidget,
            QTreeWidget,
            QTreeWidgetItem,
            QFileDialog,
            QMessageBox,
            QMenu,
            QDialog,
            QFormLayout,
            QDialogButtonBox,
            QDoubleSpinBox,
            QSpinBox,
            QCheckBox,
            QtInteractor,
        ) = qt_mod

        self._Qt = Qt
        self._QMessageBox = QMessageBox
        self._QMenu = QMenu
        self._user_role = getattr(Qt.ItemDataRole, "UserRole", getattr(Qt, "UserRole", 256))
        self._QFileDialog = QFileDialog
        self._QDialog = QDialog
        self._QFormLayout = QFormLayout
        self._QDialogButtonBox = QDialogButtonBox
        self._QDoubleSpinBox = QDoubleSpinBox
        self._QSpinBox = QSpinBox
        self._QCheckBox = QCheckBox
        self._QComboBox = QComboBox
        self._QLabel = QLabel
        self._widgets = qt_mod
        super().__init__(parent)
        titulo = "Hyperstatic — editor estilo Ftool (PyVista)"
        if precargar_ejemplo:
            from .supertesteo_spec import get_supertesteo_spec

            try:
                self._spec = copy.deepcopy(get_supertesteo_spec())
                titulo = "Hyperstatic — ejemplo supertesteo (precargado)"
            except Exception:
                self._spec = _default_spec()
        else:
            self._spec = _default_spec()
        self.setWindowTitle(titulo)
        self.resize(1280, 780)
        self._estructura: Optional[Estructura] = None
        self._solved = False
        self._hover_state: Dict[str, Any] = {"hover": []}
        self._escala_diagrama = 1.0
        self._escala_deform = 1.0
        self._ipn_dims = IPN_DEFAULT.copy()
        self._longitud_vector = 45.0

        if backend == "PySide6":
            from PySide6.QtCore import QSize
            from PySide6.QtGui import QFont
            from PySide6.QtWidgets import (
                QAbstractItemView,
                QFrame,
                QLineEdit,
                QSizePolicy,
                QTabWidget,
                QTableWidget,
                QTableWidgetItem,
                QToolButton,
            )

            _hline = QFrame.Shape.HLine
            _tt_icon = Qt.ToolButtonStyle.ToolButtonIconOnly
            _tt_txt = Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        else:
            from PyQt5.QtCore import QSize
            from PyQt5.QtGui import QFont
            from PyQt5.QtWidgets import (
                QAbstractItemView,
                QFrame,
                QLineEdit,
                QSizePolicy,
                QTabWidget,
                QTableWidget,
                QTableWidgetItem,
                QToolButton,
            )

            _hline = QFrame.HLine
            _tt_icon = Qt.ToolButtonIconOnly
            _tt_txt = Qt.ToolButtonTextBesideIcon

        self._QLineEdit = QLineEdit

        from cli.gui_icons import ftool_engineering_icons

        _ico = ftool_engineering_icons()

        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        toolbar = QWidget()
        toolbar.setObjectName("ftoolToolbar")
        tb = QVBoxLayout(toolbar)
        tb.setContentsMargins(8, 6, 8, 6)
        tb.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        lbl_vista = QLabel("Vista")
        lbl_vista.setObjectName("mutedLabel")
        self._combo_vista = QComboBox()
        for key, label in [
            ("geom", "Geometria"),
            ("loads", "Cargas"),
            ("def", "Deformada"),
            ("vy", "Corte V_y"),
            ("vz", "Corte V_z"),
            ("nx", "Normal N_x"),
            ("my", "Momento M_y"),
            ("mz", "Momento M_z"),
            ("mx", "Momento M_x"),
        ]:
            self._combo_vista.addItem(label, key)
        self._combo_vista.setMinimumWidth(200)
        self._combo_vista.setMaximumWidth(300)
        self._combo_vista.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        row1.addWidget(lbl_vista)
        row1.addWidget(self._combo_vista)
        row1.addStretch(1)
        self._btn_analizar = QToolButton()
        self._btn_analizar.setObjectName("btnAnalyze")
        self._btn_analizar.setIcon(_ico["run"])
        self._btn_analizar.setText("Analizar")
        self._btn_analizar.setToolButtonStyle(_tt_txt)
        self._btn_analizar.setIconSize(QSize(18, 18))
        self._btn_analizar.setToolTip("Ejecutar analisis estructural")
        self._btn_analizar.clicked.connect(self._on_analyze)
        row1.addWidget(self._btn_analizar)

        sep1 = QFrame()
        sep1.setObjectName("toolbarSep")
        sep1.setFrameShape(_hline)
        sep1.setFixedHeight(1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        lbl_add = QLabel("Modelo")
        lbl_add.setObjectName("mutedLabel")

        def _mk_icon_tb(key: str, tip: str, slot: Any) -> QToolButton:
            b = QToolButton()
            b.setObjectName("btnIconTool")
            b.setIcon(_ico[key])
            b.setIconSize(QSize(18, 18))
            b.setFixedSize(26, 26)
            b.setToolButtonStyle(_tt_icon)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        self._btn_nodo = _mk_icon_tb("node", "Agregar nodo", self._dlg_add_node)
        self._btn_barra = _mk_icon_tb("bar", "Agregar barra", self._dlg_add_bar)
        self._btn_carga = _mk_icon_tb("load", "Carga puntual en barra", self._dlg_add_load)
        self._btn_del = QToolButton()
        self._btn_del.setObjectName("btnIconDanger")
        self._btn_del.setIcon(_ico["delete"])
        self._btn_del.setIconSize(QSize(18, 18))
        self._btn_del.setFixedSize(26, 26)
        self._btn_del.setToolButtonStyle(_tt_icon)
        self._btn_del.setToolTip("Eliminar fila seleccionada (inspector)")
        self._btn_del.clicked.connect(self._on_delete_selection)
        row2.addWidget(lbl_add)
        row2.addWidget(self._btn_nodo)
        row2.addWidget(self._btn_barra)
        row2.addWidget(self._btn_carga)
        row2.addStretch(1)
        row2.addWidget(self._btn_del)

        sep2 = QFrame()
        sep2.setObjectName("toolbarSep")
        sep2.setFrameShape(_hline)
        sep2.setFixedHeight(1)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        lbl_sc = QLabel("Escala diagrama / deformacion")
        lbl_sc.setObjectName("mutedLabel")
        if backend == "PySide6":
            ori = Qt.Orientation.Horizontal
        else:
            ori = Qt.Horizontal
        self._slider_escala = QSlider(ori)
        self._slider_escala.setMinimum(20)
        self._slider_escala.setMaximum(1000)
        self._slider_escala.setValue(100)
        self._slider_escala.setMaximumWidth(360)
        self._slider_escala.setMinimumWidth(160)
        self._lbl_escala = QLabel("1.00")
        self._lbl_escala.setObjectName("scaleValue")
        self._lbl_escala.setMinimumWidth(40)
        _qt = self._Qt
        self._lbl_escala.setAlignment(_qt.AlignRight | _qt.AlignVCenter)
        row3.addWidget(lbl_sc, 0)
        row3.addWidget(self._slider_escala, 0)
        row3.addWidget(self._lbl_escala, 0)
        row3.addStretch(1)

        tb.addLayout(row1)
        tb.addWidget(sep1)
        tb.addLayout(row2)
        tb.addWidget(sep2)
        tb.addLayout(row3)

        lay.addWidget(toolbar, 0)

        self._plotter = QtInteractor(central)
        lay.addWidget(self._plotter.interactor, stretch=1)

        self._combo_vista.currentIndexChanged.connect(lambda _: self._redraw())
        self._slider_escala.valueChanged.connect(self._on_slider)

        self._QTableWidgetItem = QTableWidgetItem
        dock = QDockWidget("Inspector del modelo", self)
        self._tabs_model = QTabWidget()
        self._tabs_model.setDocumentMode(True)
        self._tabs_model.setMovable(False)

        self._tbl_nodes = QTableWidget()
        self._tbl_bars = QTableWidget()
        self._tbl_loads = QTableWidget()
        _sel_rows = getattr(
            QAbstractItemView.SelectionBehavior,
            "SelectRows",
            QAbstractItemView.SelectRows,
        )
        _sel_single = getattr(
            QAbstractItemView.SelectionMode,
            "SingleSelection",
            QAbstractItemView.SingleSelection,
        )
        _no_edit = getattr(
            QAbstractItemView.EditTrigger,
            "NoEditTriggers",
            QAbstractItemView.NoEditTriggers,
        )
        for tbl in (self._tbl_nodes, self._tbl_bars, self._tbl_loads):
            tbl.setAlternatingRowColors(True)
            tbl.setSelectionBehavior(_sel_rows)
            tbl.setSelectionMode(_sel_single)
            tbl.setEditTriggers(_no_edit)
            tbl.setShowGrid(True)
            tbl.verticalHeader().setVisible(False)
            tbl.verticalHeader().setDefaultSectionSize(20)
            tbl.setContextMenuPolicy(Qt.CustomContextMenu)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.horizontalHeader().setHighlightSections(False)

        self._tabs_model.addTab(self._tbl_nodes, "Nodos")
        self._tabs_model.addTab(self._tbl_bars, "Barras")
        self._tabs_model.addTab(self._tbl_loads, "Cargas")
        dock.setWidget(self._tabs_model)
        left_dock = getattr(Qt, "LeftDockWidgetArea", None)
        if left_dock is None:
            left_dock = 1
        self.addDockWidget(left_dock, dock)
        dock.setMinimumWidth(420)

        self._tbl_nodes.customContextMenuRequested.connect(
            lambda pos: self._table_context_menu(self._tbl_nodes, pos)
        )
        self._tbl_bars.customContextMenuRequested.connect(
            lambda pos: self._table_context_menu(self._tbl_bars, pos)
        )
        self._tbl_loads.customContextMenuRequested.connect(
            lambda pos: self._table_context_menu(self._tbl_loads, pos)
        )

        self._tbl_nodes.itemDoubleClicked.connect(self._on_nodes_table_double_clicked)
        self._tbl_bars.itemDoubleClicked.connect(self._on_bars_table_double_clicked)
        self._tbl_loads.itemDoubleClicked.connect(self._on_loads_table_double_clicked)

        self._legend_status = QLabel("")
        self._legend_status.setObjectName("statusLegend")
        self.statusBar().addPermanentWidget(self._legend_status)

        self._base_font = QFont("Segoe UI", 9)
        self.setFont(self._base_font)

        self._apply_ftool_theme()

        menu = self.menuBar().addMenu("Archivo")
        act_new = menu.addAction("Nuevo")
        act_new.triggered.connect(self._new_project)
        act_open = menu.addAction("Abrir JSON...")
        act_open.triggered.connect(self._open_json)
        act_save = menu.addAction("Guardar JSON...")
        act_save.triggered.connect(self._save_json)

        self._refresh_tree()
        self._redraw()

        try:
            from plot.pyvista_pestanas import _install_diagram_hover

            _install_diagram_hover(self._plotter, lambda: self._hover_state.get("hover") or [], "vy")
        except Exception:
            pass

        if precargar_ejemplo:
            self.statusBar().showMessage(
                "Ejemplo supertesteo: 5 nodos, 4 barras, 3 cargas (equivalente a crear_estructura_supertesteo)."
            )

    def _apply_ftool_theme(self) -> None:
        self.setStyleSheet(_FTOOL_STYLESHEET)
        try:
            self._apply_viewport_background()
        except Exception:
            pass

    def _apply_viewport_background(self) -> None:
        """Degradado suave en el visor 3D (evita blanco plano)."""
        try:
            self._plotter.set_background("#c9d0d9", top="#eef1f5")
        except TypeError:
            self._plotter.set_background("#dce1e8")

    def _dialog_accepted(self, d: Any) -> bool:
        if callable(getattr(d, "exec", None)):
            r = d.exec()
        else:
            r = d.exec_()
        acc = getattr(self._QDialog, "Accepted", 1)
        try:
            return int(r) == int(acc)
        except Exception:
            return bool(r)

    def _escala_actual(self) -> float:
        return self._slider_escala.value() / 100.0

    def _on_slider(self, _: int = 0) -> None:
        self._lbl_escala.setText(f"{self._escala_actual():.2f}")
        key = self._combo_vista.currentData()
        if key in ("vy", "vz", "nx", "my", "mz", "mx", "def"):
            self._redraw()

    def _invalidate_solution(self) -> None:
        self._solved = False
        self._estructura = None

    def _refresh_tree(self) -> None:
        """Actualiza tablas del inspector (nodos, barras, cargas)."""
        ur = self._user_role
        TWI = self._QTableWidgetItem
        spec = self._spec
        prev = (
            self._tbl_nodes.currentRow(),
            self._tbl_bars.currentRow(),
            self._tbl_loads.currentRow(),
        )

        _qt = self._Qt
        if hasattr(_qt, "ItemFlag"):
            _ro = _qt.ItemFlag.ItemIsSelectable | _qt.ItemFlag.ItemIsEnabled
        else:
            _ro = _qt.ItemIsSelectable | _qt.ItemIsEnabled

        for tbl in (self._tbl_nodes, self._tbl_bars, self._tbl_loads):
            tbl.blockSignals(True)

        try:
            self._tbl_nodes.setRowCount(0)
            self._tbl_nodes.setColumnCount(5)
            self._tbl_nodes.setHorizontalHeaderLabels(
                ["ID", "X (cm)", "Y (cm)", "Z (cm)", "Restricciones"]
            )
            _hn = self._tbl_nodes.horizontalHeaderItem(4)
            if _hn is not None:
                _hn.setToolTip("Doble clic en la fila o clic derecho → Editar.")
            for n in sorted(spec["nodes"], key=lambda x: int(x["id"])):
                r = self._tbl_nodes.rowCount()
                self._tbl_nodes.insertRow(r)
                nid = int(n["id"])
                vals = [
                    str(nid),
                    str(n["x"]),
                    str(n["y"]),
                    str(n["z"]),
                    restricciones_texto_desde_spec(n),
                ]
                for c, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("node", nid))
                    self._tbl_nodes.setItem(r, c, it)

            self._tbl_bars.setRowCount(0)
            self._tbl_bars.setColumnCount(4)
            self._tbl_bars.setHorizontalHeaderLabels(["ID", "Nodo i", "Nodo j", "Material"])
            for b in sorted(spec["bars"], key=lambda x: int(x["id"])):
                r = self._tbl_bars.rowCount()
                self._tbl_bars.insertRow(r)
                bid = int(b["id"])
                vals = [
                    str(bid),
                    str(b["i"]),
                    str(b["j"]),
                    str(b.get("material") or "default"),
                ]
                for c, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("bar", bid))
                    self._tbl_bars.setItem(r, c, it)

            loads = spec.get("loads_point") or []
            self._tbl_loads.setRowCount(0)
            self._tbl_loads.setColumnCount(4)
            self._tbl_loads.setHorizontalHeaderLabels(
                ["Nº", "Barra", "Coord. (x,y,z)", "Fuerza (Fx,Fy,Fz)"]
            )
            for _hci, _tip in (
                (2, "Tres numeros: ej. 10, 20, 30 (editar en ventana emergente)"),
                (3, "Fx, Fy, Fz (editar en ventana emergente)"),
            ):
                _hh = self._tbl_loads.horizontalHeaderItem(_hci)
                if _hh is not None:
                    _hh.setToolTip(_tip)
            for i, c in enumerate(loads):
                r = self._tbl_loads.rowCount()
                self._tbl_loads.insertRow(r)
                fg = c.get("force_global") or [
                    c.get("Fx", 0),
                    c.get("Fy", 0),
                    c.get("Fz", 0),
                ]
                fx, fy, fz = (float(fg[0]), float(fg[1]), float(fg[2]))
                coord = f"({c['x']},{c['y']},{c['z']})"
                fstr = f"({fx:g},{fy:g},{fz:g})"
                vals = [str(i + 1), str(c.get("bar_id")), coord, fstr]
                for col, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("load", i))
                    self._tbl_loads.setItem(r, col, it)

            for tbl, pr in (
                (self._tbl_nodes, prev[0]),
                (self._tbl_bars, prev[1]),
                (self._tbl_loads, prev[2]),
            ):
                if 0 <= pr < tbl.rowCount():
                    tbl.selectRow(pr)
                tbl.resizeColumnsToContents()
        finally:
            for tbl in (self._tbl_nodes, self._tbl_bars, self._tbl_loads):
                tbl.blockSignals(False)

    def _node_row_dict(self, nid: int) -> Optional[Dict[str, Any]]:
        for n in self._spec["nodes"]:
            if int(n["id"]) == int(nid):
                return n
        return None

    def _on_nodes_table_double_clicked(self, item: Any) -> None:
        if item is None:
            return
        it0 = self._tbl_nodes.item(item.row(), 0)
        if it0 is None:
            return
        try:
            nid = int(it0.text())
        except ValueError:
            return
        self._dlg_edit_node(nid)

    def _on_bars_table_double_clicked(self, item: Any) -> None:
        if item is None:
            return
        it0 = self._tbl_bars.item(item.row(), 0)
        if it0 is None:
            return
        try:
            bid = int(it0.text())
        except ValueError:
            return
        self._dlg_edit_bar(bid)

    def _on_loads_table_double_clicked(self, item: Any) -> None:
        if item is None:
            return
        row = item.row()
        self._dlg_edit_load(row)

    def _build_est_preview(self) -> Estructura:
        return build_estructura_from_spec(self._spec)

    def _redraw(self) -> None:
        from plot.pyvista_pestanas import (
            _finish_plotter,
            _populate_corte,
            _populate_deformada,
            _populate_estructura,
            _populate_fuerzas,
            _populate_mx,
            _populate_my,
            _populate_mz,
        )

        key = self._combo_vista.currentData()
        esc = self._escala_actual()
        self._plotter.clear()
        self._hover_state["hover"] = []
        self._legend_status.setText("")
        did_overlay = False

        nodos_dict: Dict[Any, Any] = {}
        est: Optional[Estructura] = None

        try:
            est = self._build_est_preview()
            nodos_dict = {n.id: n for n in est.nodos}
        except Exception as e:
            self.statusBar().showMessage(f"Modelo incompleto: {e}")
            _finish_plotter(self._plotter)
            self._apply_viewport_background()
            return

        nb = est.nodos
        bb = est.barras
        cargas_nodales = getattr(est, "cargas_nodales", None) or []

        if key == "geom":
            _populate_estructura(
                self._plotter,
                nb,
                bb,
                nodos_dict,
                self._ipn_dims,
                1.0,
                True,
                self._longitud_vector,
            )
            add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
            did_overlay = True
        elif key == "loads":
            _populate_fuerzas(
                self._plotter,
                nb,
                bb,
                nodos_dict,
                cargas_nodales,
                self._ipn_dims,
                1.0,
                True,
                self._longitud_vector,
                1e-9,
            )
            add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
            did_overlay = True
        elif key in ("def", "vy", "vz", "nx", "my", "mz", "mx"):
            if not self._solved or self._estructura is None:
                self.statusBar().showMessage("Ejecutá Analizar antes (vista con resultados).")
                _populate_estructura(
                    self._plotter,
                    nb,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    self._longitud_vector,
                )
                add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
                did_overlay = True
                _finish_plotter(self._plotter)
                self._apply_viewport_background()
                self._legend_status.setText(NODOS_LEGEND_STATUS if did_overlay else "")
                return
            nb = self._estructura.nodos
            bb = self._estructura.barras
            nodos_dict = {n.id: n for n in nb}
            D = self._estructura.desplazamientos
            if key == "def":
                _populate_deformada(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    self._longitud_vector,
                    np.asarray(D),
                    esc,
                )
            elif key == "vy":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, "vy", esc
                )
            elif key == "vz":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, "vz", esc
                )
            elif key == "nx":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, "nx", esc
                )
            elif key == "my":
                self._hover_state["hover"] = _populate_my(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, esc
                )
            elif key == "mz":
                self._hover_state["hover"] = _populate_mz(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, esc
                )
            elif key == "mx":
                self._hover_state["hover"] = _populate_mx(
                    self._plotter, bb, nodos_dict, self._ipn_dims, 1.0, True, esc
                )
            add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
            did_overlay = True
        _finish_plotter(self._plotter)
        self._apply_viewport_background()
        self._legend_status.setText(NODOS_LEGEND_STATUS if did_overlay else "")
        self.statusBar().showMessage("OK")

    def _on_analyze(self) -> None:
        try:
            est = build_estructura_from_spec(self._spec)
            solve_estructura(est)
        except Exception as e:
            self._QMessageBox.critical(self, "Analisis", str(e))
            return
        self._estructura = est
        self._solved = True
        self._QMessageBox.information(self, "Analisis", "Sistema resuelto. Elegi vista de esfuerzos o deformada.")
        self._redraw()

    def _new_project(self) -> None:
        self._spec = _default_spec()
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _open_json(self) -> None:
        path, _ = self._QFileDialog.getOpenFileName(self, "Abrir modelo", str(_ROOT), "JSON (*.json)")
        if not path:
            return
        try:
            self._spec = load_spec(Path(path))
            self._spec.setdefault("materials", _default_spec()["materials"])
            self._spec.setdefault("nodes", [])
            self._spec.setdefault("bars", [])
            self._spec.setdefault("loads_point", [])
        except Exception as e:
            self._QMessageBox.critical(self, "Error", str(e))
            return
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _save_json(self) -> None:
        path, _ = self._QFileDialog.getSaveFileName(self, "Guardar modelo", str(_ROOT / "modelo_ftool.json"), "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(json.dumps(self._spec, indent=2), encoding="utf-8")
        self.statusBar().showMessage(path)

    def _dlg_add_node(self) -> None:
        d = self._QDialog(self)
        d.setWindowTitle("Nuevo nodo")
        form = self._QFormLayout(d)
        sp_id = self._QSpinBox()
        sp_id.setRange(1, 9999)
        sp_id.setValue(max([n["id"] for n in self._spec["nodes"]] or [0]) + 1)
        sx = self._QDoubleSpinBox()
        sx.setRange(-1e6, 1e6)
        sy = self._QDoubleSpinBox()
        sy.setRange(-1e6, 1e6)
        sz = self._QDoubleSpinBox()
        sz.setRange(-1e6, 1e6)
        checks = [self._QCheckBox() for _ in range(6)]
        labels = ["Fijar Ux", "Fijar Uy", "Fijar Uz", "Fijar Rx", "Fijar Ry", "Fijar Rz"]
        form.addRow("ID", sp_id)
        form.addRow("x (cm)", sx)
        form.addRow("y (cm)", sy)
        form.addRow("z (cm)", sz)
        for lb, cb in zip(labels, checks):
            form.addRow(lb, cb)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        fix = [cb.isChecked() for cb in checks]
        nid = sp_id.value()
        self._spec["nodes"] = [n for n in self._spec["nodes"] if n["id"] != nid]
        self._spec["nodes"].append(
            {"id": nid, "x": sx.value(), "y": sy.value(), "z": sz.value(), "fix": fix}
        )
        self._spec["nodes"].sort(key=lambda x: x["id"])
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_add_bar(self) -> None:
        ids = [n["id"] for n in self._spec["nodes"]]
        if len(ids) < 2:
            self._QMessageBox.warning(self, "Barras", "Agregá al menos dos nodos.")
            return
        d = self._QDialog(self)
        d.setWindowTitle("Nueva barra")
        form = self._QFormLayout(d)
        sp_id = self._QSpinBox()
        sp_id.setRange(1, 9999)
        sp_id.setValue(max([b["id"] for b in self._spec["bars"]] or [0]) + 1)
        cbi = self._QComboBox()
        cbj = self._QComboBox()
        for i in ids:
            cbi.addItem(str(i), i)
            cbj.addItem(str(i), i)
        form.addRow("ID barra", sp_id)
        form.addRow("Nodo i", cbi)
        form.addRow("Nodo j", cbj)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        bid = sp_id.value()
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] != bid]
        self._spec["bars"].append(
            {"id": bid, "i": cbi.currentData(), "j": cbj.currentData(), "material": "default"}
        )
        self._spec["bars"].sort(key=lambda x: x["id"])
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_add_load(self) -> None:
        bids = [b["id"] for b in self._spec["bars"]]
        if not bids:
            self._QMessageBox.warning(self, "Carga", "Agregá al menos una barra.")
            return
        d = self._QDialog(self)
        d.setWindowTitle("Carga puntual global")
        form = self._QFormLayout(d)
        cb_bar = self._QComboBox()
        for bid in bids:
            cb_bar.addItem(str(bid), bid)
        sx = self._QDoubleSpinBox()
        sx.setRange(-1e6, 1e6)
        sy = self._QDoubleSpinBox()
        sy.setRange(-1e6, 1e6)
        sz = self._QDoubleSpinBox()
        sz.setRange(-1e6, 1e6)
        sfx = self._QDoubleSpinBox()
        sfx.setRange(-1e9, 1e9)
        sfy = self._QDoubleSpinBox()
        sfy.setRange(-1e9, 1e9)
        sfz = self._QDoubleSpinBox()
        sfz.setRange(-1e9, 1e9)
        form.addRow("Barra", cb_bar)
        form.addRow("x (cm)", sx)
        form.addRow("y (cm)", sy)
        form.addRow("z (cm)", sz)
        form.addRow("Fx", sfx)
        form.addRow("Fy", sfy)
        form.addRow("Fz", sfz)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        self._spec.setdefault("loads_point", []).append(
            {
                "id": len(self._spec.get("loads_point") or []) + 1,
                "bar_id": cb_bar.currentData(),
                "x": sx.value(),
                "y": sy.value(),
                "z": sz.value(),
                "force_global": [sfx.value(), sfy.value(), sfz.value()],
            }
        )
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_edit_node(self, nid: int) -> None:
        node = self._node_row_dict(nid)
        if node is None:
            return
        d = self._QDialog(self)
        d.setWindowTitle(f"Editar nodo {nid}")
        form = self._QFormLayout(d)
        L = self._QLabel
        lid = L(str(nid))
        sx = self._QDoubleSpinBox()
        sx.setRange(-1e6, 1e6)
        sx.setValue(float(node["x"]))
        sy = self._QDoubleSpinBox()
        sy.setRange(-1e6, 1e6)
        sy.setValue(float(node["y"]))
        sz = self._QDoubleSpinBox()
        sz.setRange(-1e6, 1e6)
        sz.setValue(float(node["z"]))
        raw_fix = node.get("fix") or node.get("restricciones") or []
        fix_list = list(raw_fix)[:6]
        while len(fix_list) < 6:
            fix_list.append(False)
        checks = [self._QCheckBox() for _ in range(6)]
        labels = ["Fijar Ux", "Fijar Uy", "Fijar Uz", "Fijar Rx", "Fijar Ry", "Fijar Rz"]
        for i, cb in enumerate(checks):
            cb.setChecked(bool(fix_list[i]))
        form.addRow("ID", lid)
        form.addRow("x (cm)", sx)
        form.addRow("y (cm)", sy)
        form.addRow("z (cm)", sz)
        for lb, cb in zip(labels, checks):
            form.addRow(lb, cb)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        node["x"] = sx.value()
        node["y"] = sy.value()
        node["z"] = sz.value()
        node["fix"] = [cb.isChecked() for cb in checks]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_edit_bar(self, bid: int) -> None:
        bar = next((b for b in self._spec["bars"] if int(b["id"]) == bid), None)
        if bar is None:
            return
        ids = [int(n["id"]) for n in self._spec["nodes"]]
        if len(ids) < 1:
            self._QMessageBox.warning(self, "Barras", "No hay nodos en el modelo.")
            return
        d = self._QDialog(self)
        d.setWindowTitle(f"Editar barra {bid}")
        form = self._QFormLayout(d)
        L = self._QLabel
        lid = L(str(bid))
        cbi = self._QComboBox()
        cbj = self._QComboBox()
        for i in ids:
            cbi.addItem(str(i), i)
            cbj.addItem(str(i), i)
        ni, nf = int(bar["i"]), int(bar["j"])
        cbi.setCurrentIndex(max(0, cbi.findData(ni)))
        cbj.setCurrentIndex(max(0, cbj.findData(nf)))
        mat = self._QLineEdit()
        mat.setText(str(bar.get("material") or "default"))
        form.addRow("ID barra", lid)
        form.addRow("Nodo i", cbi)
        form.addRow("Nodo j", cbj)
        form.addRow("Material", mat)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        bar["i"] = int(cbi.currentData())
        bar["j"] = int(cbj.currentData())
        bar["material"] = mat.text().strip() or "default"
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_edit_load(self, row: int) -> None:
        loads = self._spec.setdefault("loads_point", [])
        if row < 0 or row >= len(loads):
            return
        c = loads[row]
        bids = [b["id"] for b in self._spec["bars"]]
        if not bids:
            self._QMessageBox.warning(self, "Carga", "Agregá al menos una barra.")
            return
        d = self._QDialog(self)
        d.setWindowTitle(f"Editar carga ({row + 1})")
        form = self._QFormLayout(d)
        cb_bar = self._QComboBox()
        for bid in bids:
            cb_bar.addItem(str(bid), bid)
        cur_b = int(c.get("bar_id"))
        ix = cb_bar.findData(cur_b)
        if ix >= 0:
            cb_bar.setCurrentIndex(ix)
        sx = self._QDoubleSpinBox()
        sx.setRange(-1e6, 1e6)
        sx.setValue(float(c["x"]))
        sy = self._QDoubleSpinBox()
        sy.setRange(-1e6, 1e6)
        sy.setValue(float(c["y"]))
        sz = self._QDoubleSpinBox()
        sz.setRange(-1e6, 1e6)
        sz.setValue(float(c["z"]))
        fg = c.get("force_global") or [c.get("Fx", 0), c.get("Fy", 0), c.get("Fz", 0)]
        sfx = self._QDoubleSpinBox()
        sfx.setRange(-1e9, 1e9)
        sfx.setValue(float(fg[0]))
        sfy = self._QDoubleSpinBox()
        sfy.setRange(-1e9, 1e9)
        sfy.setValue(float(fg[1]))
        sfz = self._QDoubleSpinBox()
        sfz.setRange(-1e9, 1e9)
        sfz.setValue(float(fg[2]))
        form.addRow("Barra", cb_bar)
        form.addRow("x (cm)", sx)
        form.addRow("y (cm)", sy)
        form.addRow("z (cm)", sz)
        form.addRow("Fx", sfx)
        form.addRow("Fy", sfy)
        form.addRow("Fz", sfz)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        c["bar_id"] = int(cb_bar.currentData())
        c["x"] = sx.value()
        c["y"] = sy.value()
        c["z"] = sz.value()
        c["force_global"] = [sfx.value(), sfy.value(), sfz.value()]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _open_inspector_edit(self, table: Any, row: int) -> None:
        if table is self._tbl_nodes:
            it = self._tbl_nodes.item(row, 0)
            if it is not None:
                try:
                    self._dlg_edit_node(int(it.text()))
                except ValueError:
                    pass
        elif table is self._tbl_bars:
            it = self._tbl_bars.item(row, 0)
            if it is not None:
                try:
                    self._dlg_edit_bar(int(it.text()))
                except ValueError:
                    pass
        elif table is self._tbl_loads:
            self._dlg_edit_load(row)

    def _table_context_menu(self, table: Any, pos: Any) -> None:
        item = table.itemAt(pos)
        if item is None:
            return
        data = item.data(self._user_role)
        if not data:
            return
        row = item.row()
        menu = self._QMenu(self)
        act_ed = menu.addAction("Editar…")
        act_ed.triggered.connect(
            lambda checked=False, t=table, r=row: self._open_inspector_edit(t, r)
        )
        act = menu.addAction("Eliminar")
        role = data
        act.triggered.connect(lambda checked=False, r=role: self._apply_delete_role(r))
        menu.exec(table.viewport().mapToGlobal(pos))

    def _apply_delete_role(self, data: tuple) -> None:
        kind, ident = data
        if kind == "node":
            self._delete_node(int(ident))
        elif kind == "bar":
            self._delete_bar(int(ident))
        elif kind == "load":
            self._delete_load(int(ident))

    def _on_delete_selection(self) -> None:
        idx = self._tabs_model.currentIndex()
        tables = (self._tbl_nodes, self._tbl_bars, self._tbl_loads)
        if 0 <= idx < len(tables):
            tbl = tables[idx]
            r = tbl.currentRow()
            if r >= 0:
                it = tbl.item(r, 0)
                if it is not None:
                    data = it.data(self._user_role)
                    if data:
                        self._apply_delete_role(data)
                        return
        self._QMessageBox.information(
            self,
            "Eliminar",
            "Seleccioná una fila en la pestaña activa del inspector (Nodos, Barras o Cargas).",
        )

    def _delete_node(self, nid: int) -> None:
        bars_drop = {b["id"] for b in self._spec["bars"] if b["i"] == nid or b["j"] == nid}
        if bars_drop:
            MB = self._QMessageBox
            r = MB.question(
                self,
                "Eliminar nodo",
                f"Tambien se quitaran {len(bars_drop)} barra(s) y las cargas sobre ellas. Continuar?",
                MB.Yes | MB.No,
            )
            if r != MB.Yes:
                return
        self._spec["loads_point"] = [
            c for c in self._spec.get("loads_point") or [] if c.get("bar_id") not in bars_drop
        ]
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] not in bars_drop]
        self._spec["nodes"] = [n for n in self._spec["nodes"] if n["id"] != nid]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_bar(self, bid: int) -> None:
        self._spec["loads_point"] = [
            c for c in self._spec.get("loads_point") or [] if c.get("bar_id") != bid
        ]
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] != bid]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_point", [])
        if 0 <= index < len(loads):
            loads.pop(index)
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()


def run_ftool_gui(*, precargar_ejemplo: bool = False) -> None:
    qt = _try_qt()
    if qt is None:
        raise ImportError("Instalá: pip install pyvista pyvistaqt PySide6")

    (
        backend,
        Qt,
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QComboBox,
        QSlider,
        QDockWidget,
        QTreeWidget,
        QTreeWidgetItem,
        QFileDialog,
        QMessageBox,
        QMenu,
        QDialog,
        QFormLayout,
        QDialogButtonBox,
        QDoubleSpinBox,
        QSpinBox,
        QCheckBox,
        QtInteractor,
    ) = qt

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    w = FtoolMainWindow(backend, qt, precargar_ejemplo=precargar_ejemplo)
    w.show()
    app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    run_ftool_gui()
