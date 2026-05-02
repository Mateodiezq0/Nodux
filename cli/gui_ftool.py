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
from cli.section_props import compute_section, section_summary
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


def _msg_yes_no_flags(MB: Any) -> Any:
    SB = getattr(MB, "StandardButton", None)
    if SB is not None:
        return SB.Yes | SB.No
    return MB.Yes | MB.No


def _msg_is_yes(MB: Any, reply: Any) -> bool:
    SB = getattr(MB, "StandardButton", None)
    if SB is not None:
        return reply == SB.Yes
    return reply == MB.Yes


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
        self._QWidget = QWidget
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
                QStackedWidget,
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
                QStackedWidget,
                QTabWidget,
                QTableWidget,
                QTableWidgetItem,
                QToolButton,
            )

            _hline = QFrame.HLine
            _tt_icon = Qt.ToolButtonIconOnly
            _tt_txt = Qt.ToolButtonTextBesideIcon

        self._QLineEdit = QLineEdit
        self._QStackedWidget = QStackedWidget

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

        self._IDX_TAB_INSPECTOR_MODELO = 0
        self._IDX_TAB_INSPECTOR_MAT = 1

        model_wrap = QWidget()
        mw_lay = QVBoxLayout(model_wrap)
        mw_lay.setContentsMargins(0, 0, 0, 0)
        mw_lay.addWidget(self._tabs_model)

        self._tbl_materials = QTableWidget()
        for tbl in (self._tbl_materials,):
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

        mat_toolbar = QHBoxLayout()
        btn_mat_new = QPushButton("+ Material")
        btn_mat_new.setToolTip("Definir material con sección paramétrica o propiedades manuales")
        btn_mat_new.clicked.connect(lambda: self._dlg_material_editor(None))
        btn_mat_ed = QPushButton("Editar")
        btn_mat_ed.clicked.connect(self._on_edit_material_toolbar)
        mat_toolbar.addWidget(btn_mat_new)
        mat_toolbar.addWidget(btn_mat_ed)
        mat_toolbar.addStretch(1)

        mat_wrap = QWidget()
        mat_lay = QVBoxLayout(mat_wrap)
        mat_lay.setContentsMargins(4, 4, 4, 4)
        mat_lay.addLayout(mat_toolbar)
        mat_lay.addWidget(self._tbl_materials)

        self._outer_inspector = QTabWidget()
        self._outer_inspector.setDocumentMode(True)
        self._outer_inspector.addTab(model_wrap, "Modelo")
        self._outer_inspector.addTab(mat_wrap, "Materiales y secciones")

        dock.setWidget(self._outer_inspector)
        left_dock = getattr(Qt, "LeftDockWidgetArea", None)
        if left_dock is None:
            left_dock = 1
        self.addDockWidget(left_dock, dock)
        dock.setMinimumWidth(460)

        self._tbl_materials.customContextMenuRequested.connect(self._materials_context_menu)
        self._tbl_materials.itemDoubleClicked.connect(self._on_materials_double_clicked)

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
        self._refresh_materials_table()

    def _refresh_materials_table(self) -> None:
        """Tabla del gestor de materiales y secciones."""
        ur = self._user_role
        TWI = self._QTableWidgetItem
        mats = self._spec.get("materials") or {}
        prev = self._tbl_materials.currentRow()
        self._tbl_materials.blockSignals(True)
        try:
            _qt = self._Qt
            _ro = (
                _qt.ItemFlag.ItemIsSelectable | _qt.ItemFlag.ItemIsEnabled
                if hasattr(_qt, "ItemFlag")
                else _qt.ItemIsSelectable | _qt.ItemIsEnabled
            )
            self._tbl_materials.setRowCount(0)
            self._tbl_materials.setColumnCount(7)
            self._tbl_materials.setHorizontalHeaderLabels(
                ["Nombre", "Tipo / forma", "E", "ν", "γ", "A (cm²)", "G"]
            )
            for name in sorted(mats.keys(), key=str.lower):
                raw = mats[name]
                r = self._tbl_materials.rowCount()
                self._tbl_materials.insertRow(r)
                sec = raw.get("section")
                tipo = section_summary(sec) if sec else "Manual"
                nu = raw.get("nu")
                nu_s = "" if nu is None else str(nu)
                ga = raw.get("gamma")
                ga_s = "" if ga is None else str(ga)
                try:
                    if sec:
                        gp = compute_section(sec)
                        a_s = f"{gp['A']:.4g}"
                        E = float(raw["E"])
                        nu_f = float(raw["nu"]) if raw.get("nu") is not None else None
                        G_v = (
                            float(raw["G"])
                            if raw.get("G") is not None
                            else (E / (2.0 * (1.0 + nu_f)) if nu_f is not None else float("nan"))
                        )
                        g_s = f"{G_v:.4g}" if nu_f is not None or raw.get("G") is not None else "—"
                    else:
                        a_s = f"{float(raw.get('A', 0)):.4g}"
                        g_s = f"{float(raw.get('G', 0)):.4g}"
                except Exception:
                    a_s = "—"
                    g_s = "—"
                vals = [
                    str(name),
                    tipo,
                    str(raw.get("E", "")),
                    nu_s,
                    ga_s,
                    a_s,
                    g_s,
                ]
                for c, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("material", str(name)))
                    self._tbl_materials.setItem(r, c, it)
            if 0 <= prev < self._tbl_materials.rowCount():
                self._tbl_materials.selectRow(prev)
            self._tbl_materials.resizeColumnsToContents()
        finally:
            self._tbl_materials.blockSignals(False)

    def _populate_material_combo(self, cb: Any, current: Optional[str]) -> None:
        cb.clear()
        for mk in sorted((self._spec.get("materials") or {}).keys(), key=str.lower):
            cb.addItem(mk, mk)
        if current and cb.findData(current) < 0:
            cb.addItem(str(current), current)
        if current:
            ix = cb.findData(current)
            if ix < 0:
                ix = cb.findText(str(current))
            if ix >= 0:
                cb.setCurrentIndex(ix)

    def _material_used_by_bars(self, mat_name: str) -> int:
        n = 0
        for b in self._spec.get("bars") or []:
            if str(b.get("material") or "default") == str(mat_name):
                n += 1
        return n

    def _ipn_dims_per_bar_from_spec(self) -> Dict[int, Dict[str, float]]:
        """Dimensiones IPN por id de barra según ``materials[*].viz`` (si no es global)."""
        out: Dict[int, Dict[str, float]] = {}
        mats = self._spec.get("materials") or {}
        for br in self._spec.get("bars") or []:
            if br.get("id") is None:
                continue
            mk = str(br.get("material") or "default")
            m = mats.get(mk) or {}
            vz = m.get("viz")
            if not isinstance(vz, dict):
                continue
            if vz.get("use_global", True):
                continue
            try:
                out[int(br["id"])] = {
                    "h": float(vz["h"]),
                    "b": float(vz["b"]),
                    "tw": float(vz.get("tw", IPN_DEFAULT["tw"])),
                    "tf": float(vz.get("tf", IPN_DEFAULT["tf"])),
                }
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def _tube_outer_radius_per_bar_from_spec(self) -> Dict[int, float]:
        """Radio exterior (cm) para barras con sección tubo circular y sin viz IPN propio."""
        out: Dict[int, float] = {}
        mats = self._spec.get("materials") or {}
        for br in self._spec.get("bars") or []:
            if br.get("id") is None:
                continue
            bid = int(br["id"])
            mk = str(br.get("material") or "default")
            m = mats.get(mk) or {}
            vz = m.get("viz")
            if isinstance(vz, dict) and not vz.get("use_global", True):
                if all(k in vz for k in ("h", "b", "tw", "tf")):
                    continue
            sec = m.get("section") or {}
            st = str(sec.get("type", "")).lower()
            if st in ("tube_circle", "tubo_circular", "pipe"):
                try:
                    out[bid] = float(sec["D"]) / 2.0
                except (KeyError, TypeError, ValueError):
                    pass
        return out

    def _dlg_material_editor(self, edit_name: Optional[str]) -> None:
        """edit_name None = nuevo material."""
        from cli.loader import _resolve_material_stiffness

        mats = self._spec.setdefault("materials", {})
        D = self._QDialog(self)
        D.setWindowTitle("Editar material" if edit_name else "Nuevo material")
        D.setMinimumWidth(560)
        form = self._QFormLayout(D)
        SW = self._QStackedWidget
        W = self._QWidget

        name_edit = self._QLineEdit()
        if edit_name:
            name_edit.setText(edit_name)
            name_edit.setReadOnly(True)
        form.addRow("Nombre (clave)", name_edit)

        existing = dict(mats.get(edit_name, {})) if edit_name else {}

        s_e = self._QDoubleSpinBox()
        s_e.setRange(1.0, 1e9)
        s_e.setDecimals(4)
        s_e.setValue(float(existing.get("E", 20000.0)))
        form.addRow("E (Tn/cm²)", s_e)

        s_nu = self._QDoubleSpinBox()
        s_nu.setRange(-0.49, 0.499)
        s_nu.setDecimals(4)
        s_nu.setValue(float(existing.get("nu", 0.3)))
        form.addRow("ν (Poisson)", s_nu)

        s_ga = self._QDoubleSpinBox()
        s_ga.setRange(0.0, 1.0)
        s_ga.setDecimals(6)
        s_ga.setValue(float(existing.get("gamma", 0.00785)))
        form.addRow("γ peso específico (Tn/cm³)", s_ga)

        chk_viz_global = self._QCheckBox("Vista 3D: usar dimensiones globales del visor (perfil IPN)")
        ex_vz = existing.get("viz")
        ex_vz = ex_vz if isinstance(ex_vz, dict) else {}
        has_full_viz = all(k in ex_vz for k in ("h", "b", "tw", "tf"))
        if "use_global" in ex_vz:
            use_global_viz = bool(ex_vz["use_global"])
        else:
            use_global_viz = not has_full_viz
        chk_viz_global.setChecked(use_global_viz)
        vh = self._QDoubleSpinBox()
        vh.setRange(1e-6, 1e6)
        vh.setDecimals(4)
        vh.setValue(float(ex_vz.get("h", IPN_DEFAULT["h"])))
        vb = self._QDoubleSpinBox()
        vb.setRange(1e-6, 1e6)
        vb.setDecimals(4)
        vb.setValue(float(ex_vz.get("b", IPN_DEFAULT["b"])))
        vtw = self._QDoubleSpinBox()
        vtw.setRange(1e-6, 1e6)
        vtw.setDecimals(4)
        vtw.setValue(float(ex_vz.get("tw", IPN_DEFAULT["tw"])))
        vtf = self._QDoubleSpinBox()
        vtf.setRange(1e-6, 1e6)
        vtf.setDecimals(4)
        vtf.setValue(float(ex_vz.get("tf", IPN_DEFAULT["tf"])))
        viz_box = W()
        fv = self._QFormLayout(viz_box)
        fv.addRow("h (cm)", vh)
        fv.addRow("b (cm)", vb)
        fv.addRow("tw alma (cm)", vtw)
        fv.addRow("tf patín (cm)", vtf)
        form.addRow("", chk_viz_global)
        form.addRow("Perfil IPN en vista", viz_box)

        def _sync_viz_spin_enabled(checked: bool) -> None:
            for w in (vh, vb, vtw, vtf):
                w.setEnabled(not checked)

        chk_viz_global.toggled.connect(_sync_viz_spin_enabled)
        _sync_viz_spin_enabled(chk_viz_global.isChecked())

        mode = self._QComboBox()
        mode.addItem("Sección paramétrica", "param")
        mode.addItem("Propiedades manuales (A, I, J, G)", "manual")
        has_sec = bool(existing.get("section"))
        has_man = not has_sec and any(k in existing for k in ("A", "I_y", "G"))
        mode.setCurrentIndex(0 if (has_sec or not has_man) else 1)
        form.addRow("Modo", mode)

        stack = SW()
        # --- página paramétrica ---
        page_p = W()
        fp = self._QFormLayout(page_p)
        sec_type = self._QComboBox()
        sec_map = [
            ("Rectangular", "rectangle"),
            ("Perfil I", "i_beam"),
            ("Tubo circular", "tube_circle"),
            ("Tubo rectangular", "tube_rect"),
        ]
        for lab, key in sec_map:
            sec_type.addItem(lab, key)
        sec_stack = SW()
        raw_sec = existing.get("section") or {}
        st0 = str(raw_sec.get("type", "rectangle")).lower()
        ix_t = 0
        for i, (_, k) in enumerate(sec_map):
            if st0 in (k, k.replace("_", "")):
                ix_t = i
                break
        sec_type.setCurrentIndex(ix_t)

        # rect
        w_rect = W()
        fr = self._QFormLayout(w_rect)
        sb = self._QDoubleSpinBox()
        sb.setRange(1e-6, 1e6)
        sb.setValue(float(raw_sec.get("b", 10)))
        sh = self._QDoubleSpinBox()
        sh.setRange(1e-6, 1e6)
        sh.setValue(float(raw_sec.get("h", 20)))
        fr.addRow("b (cm)", sb)
        fr.addRow("h (cm)", sh)

        w_i = W()
        fi = self._QFormLayout(w_i)
        si_h = self._QDoubleSpinBox()
        si_h.setRange(1e-6, 1e6)
        si_h.setValue(float(raw_sec.get("h", 20)))
        si_bf = self._QDoubleSpinBox()
        si_bf.setRange(1e-6, 1e6)
        si_bf.setValue(float(raw_sec.get("bf", 10)))
        si_tw = self._QDoubleSpinBox()
        si_tw.setRange(1e-6, 1e6)
        si_tw.setValue(float(raw_sec.get("tw", 0.6)))
        si_tf = self._QDoubleSpinBox()
        si_tf.setRange(1e-6, 1e6)
        si_tf.setValue(float(raw_sec.get("tf", 1.0)))
        fi.addRow("h total (cm)", si_h)
        fi.addRow("bf patín (cm)", si_bf)
        fi.addRow("tw alma (cm)", si_tw)
        fi.addRow("tf patín (cm)", si_tf)

        w_tc = W()
        ftc = self._QFormLayout(w_tc)
        sD = self._QDoubleSpinBox()
        sD.setRange(1e-6, 1e6)
        sD.setValue(float(raw_sec.get("D", 10)))
        stwall = self._QDoubleSpinBox()
        stwall.setRange(1e-6, 1e6)
        stwall.setValue(float(raw_sec.get("t", 0.5)))
        ftc.addRow("D exterior (cm)", sD)
        ftc.addRow("t pared (cm)", stwall)

        w_tr = W()
        ftr = self._QFormLayout(w_tr)
        sbo = self._QDoubleSpinBox()
        sbo.setRange(1e-6, 1e6)
        sbo.setValue(float(raw_sec.get("b", 12)))
        sho = self._QDoubleSpinBox()
        sho.setRange(1e-6, 1e6)
        sho.setValue(float(raw_sec.get("h", 12)))
        sto = self._QDoubleSpinBox()
        sto.setRange(1e-6, 1e6)
        sto.setValue(float(raw_sec.get("t", 0.5)))
        ftr.addRow("b exterior (cm)", sbo)
        ftr.addRow("h exterior (cm)", sho)
        ftr.addRow("t pared (cm)", sto)

        sec_stack.addWidget(w_rect)
        sec_stack.addWidget(w_i)
        sec_stack.addWidget(w_tc)
        sec_stack.addWidget(w_tr)

        def _sync_sec_page(i: int) -> None:
            sec_stack.setCurrentIndex(i)

        sec_type.currentIndexChanged.connect(_sync_sec_page)
        _sync_sec_page(sec_type.currentIndex())
        fp.addRow("Forma", sec_type)
        fp.addRow(sec_stack)

        # --- página manual ---
        page_m = W()
        fm = self._QFormLayout(page_m)
        sA = self._QDoubleSpinBox()
        sA.setRange(1e-12, 1e9)
        sA.setValue(float(existing.get("A", 100)))
        sIy = self._QDoubleSpinBox()
        sIy.setRange(1e-12, 1e9)
        sIy.setValue(float(existing.get("I_y", 833)))
        sIz = self._QDoubleSpinBox()
        sIz.setRange(1e-12, 1e9)
        sIz.setValue(float(existing.get("I_z", 833)))
        sJ = self._QDoubleSpinBox()
        sJ.setRange(1e-12, 1e9)
        sJ.setValue(float(existing.get("J", 1408)))
        sG = self._QDoubleSpinBox()
        sG.setRange(0.0, 1e9)
        sG.setDecimals(4)
        if existing.get("G") is not None:
            sG.setValue(float(existing["G"]))
        else:
            sG.setValue(0.0)
        fm.addRow("A (cm²)", sA)
        fm.addRow("I_y (cm⁴)", sIy)
        fm.addRow("I_z (cm⁴)", sIz)
        fm.addRow("J (cm⁴)", sJ)
        fm.addRow("G (Tn/cm²); si 0 se usa ν", sG)

        stack.addWidget(page_p)
        stack.addWidget(page_m)

        def _sync_mode(i: int) -> None:
            stack.setCurrentIndex(0 if i == 0 else 1)

        mode.currentIndexChanged.connect(_sync_mode)
        _sync_mode(mode.currentIndex())
        form.addRow(stack)

        preview_canvas = None
        preview_fig = None

        try:
            from matplotlib.figure import Figure

            try:
                from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FigCanvas
            except ImportError:
                from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as _FigCanvas

            try:
                from PySide6.QtWidgets import QSizePolicy as _QSP
            except ImportError:
                from PyQt5.QtWidgets import QSizePolicy as _QSP

            from cli.section_preview import draw_material_preview

            preview_fig = Figure(figsize=(4.2, 5.0), dpi=96)
            preview_canvas = _FigCanvas(preview_fig)
            preview_canvas.setMinimumHeight(320)
            preview_canvas.setSizePolicy(_QSP.Expanding, _QSP.MinimumExpanding)
        except ImportError:
            pass

        def _refresh_material_preview(*_: Any) -> None:
            if preview_fig is None or preview_canvas is None:
                return
            draw_material_preview(
                preview_fig,
                mode_is_param=mode.currentIndex() == 0,
                sec_index=int(sec_type.currentIndex()),
                rect_b=float(sb.value()),
                rect_h=float(sh.value()),
                i_h=float(si_h.value()),
                i_bf=float(si_bf.value()),
                i_tw=float(si_tw.value()),
                i_tf=float(si_tf.value()),
                tc_D=float(sD.value()),
                tc_t=float(stwall.value()),
                tr_b=float(sbo.value()),
                tr_h=float(sho.value()),
                tr_t=float(sto.value()),
                viz_use_global=bool(chk_viz_global.isChecked()),
                viz_h=float(vh.value()),
                viz_b=float(vb.value()),
                viz_tw=float(vtw.value()),
                viz_tf=float(vtf.value()),
            )
            preview_canvas.draw()

        if preview_canvas is not None:
            form.addRow("Previsualización", preview_canvas)
            _spin_refresh = (
                sb,
                sh,
                si_h,
                si_bf,
                si_tw,
                si_tf,
                sD,
                stwall,
                sbo,
                sho,
                sto,
                vh,
                vb,
                vtw,
                vtf,
            )
            for _sp in _spin_refresh:
                _sp.valueChanged.connect(_refresh_material_preview)
            sec_type.currentIndexChanged.connect(_refresh_material_preview)
            mode.currentIndexChanged.connect(_refresh_material_preview)
            chk_viz_global.toggled.connect(_refresh_material_preview)
            _refresh_material_preview()

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(D.accept)
        bb.rejected.connect(D.reject)
        if self._dialog_accepted(D) is False:
            return

        nm = name_edit.text().strip()
        if not nm:
            self._QMessageBox.warning(self, "Material", "El nombre no puede estar vacío.")
            return
        if edit_name is None and nm in mats:
            r = self._QMessageBox.question(
                self,
                "Material",
                f"Ya existe «{nm}». ¿Sobrescribir?",
                _msg_yes_no_flags(self._QMessageBox),
            )
            if not _msg_is_yes(self._QMessageBox, r):
                return

        entry: Dict[str, Any] = {"E": s_e.value(), "gamma": s_ga.value()}

        sec_keys = ["rectangle", "i_beam", "tube_circle", "tube_rect"]
        si = sec_type.currentIndex()
        k = sec_keys[si] if 0 <= si < len(sec_keys) else "rectangle"
        is_param = mode.currentIndex() == 0

        if is_param:
            entry["nu"] = s_nu.value()
            idx = sec_type.currentIndex()
            sec_stack.setCurrentIndex(idx)
            if k == "rectangle":
                entry["section"] = {"type": "rectangle", "b": sb.value(), "h": sh.value()}
            elif k == "i_beam":
                entry["section"] = {
                    "type": "i_beam",
                    "h": si_h.value(),
                    "bf": si_bf.value(),
                    "tw": si_tw.value(),
                    "tf": si_tf.value(),
                }
            elif k == "tube_circle":
                entry["section"] = {"type": "tube_circle", "D": sD.value(), "t": stwall.value()}
            else:
                entry["section"] = {
                    "type": "tube_rect",
                    "b": sbo.value(),
                    "h": sho.value(),
                    "t": sto.value(),
                }
            try:
                _resolve_material_stiffness(entry, nm)
            except Exception as ex:
                self._QMessageBox.critical(self, "Material", str(ex))
                return
        else:
            entry["A"] = sA.value()
            entry["I_y"] = sIy.value()
            entry["I_z"] = sIz.value()
            entry["J"] = sJ.value()
            Gv = sG.value()
            if Gv > 0:
                entry["G"] = Gv
            else:
                entry["nu"] = s_nu.value()
            try:
                _resolve_material_stiffness(dict(entry), nm)
            except Exception as ex:
                self._QMessageBox.critical(self, "Material", str(ex))
                return

        if chk_viz_global.isChecked():
            entry.pop("viz", None)
        else:
            entry["viz"] = {
                "use_global": False,
                "h": vh.value(),
                "b": vb.value(),
                "tw": vtw.value(),
                "tf": vtf.value(),
            }

        mats[nm] = entry
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _on_materials_double_clicked(self, item: Any) -> None:
        it = self._tbl_materials.item(item.row(), 0)
        if it is None:
            return
        self._dlg_material_editor(it.text())

    def _on_edit_material_toolbar(self) -> None:
        r = self._tbl_materials.currentRow()
        if r < 0:
            self._QMessageBox.information(self, "Materiales", "Seleccioná un material en la tabla.")
            return
        it = self._tbl_materials.item(r, 0)
        if it is None:
            return
        self._dlg_material_editor(it.text())

    def _materials_context_menu(self, pos: Any) -> None:
        item = self._tbl_materials.itemAt(pos)
        if item is None:
            return
        data = item.data(self._user_role)
        if not data or data[0] != "material":
            return
        menu = self._QMenu(self)
        act_e = menu.addAction("Editar…")
        act_e.triggered.connect(lambda: self._dlg_material_editor(str(data[1])))
        act_d = menu.addAction("Eliminar")
        act_d.triggered.connect(lambda: self._delete_material_key(str(data[1])))
        menu.exec(self._tbl_materials.viewport().mapToGlobal(pos))

    def _delete_material_key(self, mat_name: str) -> None:
        mats = self._spec.get("materials") or {}
        if mat_name not in mats:
            return
        def_key = str(self._spec.get("default_material") or "default")
        if mat_name == def_key:
            self._QMessageBox.warning(
                self,
                "Materiales",
                "No se puede eliminar el material por defecto. Cambiá «default_material» en el JSON o creá otro predeterminado.",
            )
            return
        nbar = self._material_used_by_bars(mat_name)
        if nbar > 0:
            self._QMessageBox.warning(
                self,
                "Materiales",
                f"Hay {nbar} barra(s) que usan «{mat_name}». Asigná otro material antes de eliminar.",
            )
            return
        MB = self._QMessageBox
        if not _msg_is_yes(
            MB,
            MB.question(
                self,
                "Eliminar material",
                f"¿Eliminar el material «{mat_name}»?",
                _msg_yes_no_flags(MB),
            ),
        ):
            return
        del mats[mat_name]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

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
        per_bar = self._ipn_dims_per_bar_from_spec()
        tube_bar = self._tube_outer_radius_per_bar_from_spec()

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
                ipn_dims_per_bar_id=per_bar,
                tube_outer_radius_per_bar_id=tube_bar,
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
                ipn_dims_per_bar_id=per_bar,
                tube_outer_radius_per_bar_id=tube_bar,
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
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
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
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "vy":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    "vy",
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "vz":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    "vz",
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "nx":
                self._hover_state["hover"] = _populate_corte(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    "nx",
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "my":
                self._hover_state["hover"] = _populate_my(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "mz":
                self._hover_state["hover"] = _populate_mz(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                )
            elif key == "mx":
                self._hover_state["hover"] = _populate_mx(
                    self._plotter,
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    True,
                    esc,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
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
        cb_mat = self._QComboBox()
        self._populate_material_combo(cb_mat, self._spec.get("default_material") or "default")
        form.addRow("ID barra", sp_id)
        form.addRow("Nodo i", cbi)
        form.addRow("Nodo j", cbj)
        form.addRow("Material", cb_mat)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        bid = sp_id.value()
        mname = cb_mat.currentData()
        if mname is None:
            mname = (cb_mat.currentText() or "").strip() or "default"
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] != bid]
        self._spec["bars"].append(
            {"id": bid, "i": cbi.currentData(), "j": cbj.currentData(), "material": str(mname)}
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
        cb_mat = self._QComboBox()
        self._populate_material_combo(cb_mat, str(bar.get("material") or "default"))
        form.addRow("ID barra", lid)
        form.addRow("Nodo i", cbi)
        form.addRow("Nodo j", cbj)
        form.addRow("Material", cb_mat)
        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        bar["i"] = int(cbi.currentData())
        bar["j"] = int(cbj.currentData())
        mm = cb_mat.currentData()
        if mm is None:
            mm = (cb_mat.currentText() or "").strip() or "default"
        bar["material"] = str(mm)
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
        elif kind == "material":
            self._delete_material_key(str(ident))

    def _on_delete_selection(self) -> None:
        if self._outer_inspector.currentIndex() == self._IDX_TAB_INSPECTOR_MAT:
            r = self._tbl_materials.currentRow()
            if r >= 0:
                it = self._tbl_materials.item(r, 0)
                if it is not None:
                    self._delete_material_key(it.text())
                    return
            self._QMessageBox.information(self, "Eliminar", "Seleccioná un material en la tabla.")
            return
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
            "Seleccioná una fila en Modelo (Nodos/Barras/Cargas) o un material.",
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
