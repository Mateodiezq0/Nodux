"""
Ventana estilo Ftool: modelo en panel lateral, vista 3D PyVista (Qt), analisis y diagramas.

  python -m cli gui

Requiere: pip install pyvista pyvistaqt PySide6
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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

# QSS global: ver ``cli/qt_app_theme.py`` (temas alineados al visor, regla 60-30-10).
# Nota: no usar «QWidget { … }» global — en Windows pinta mal popups (combo, menús).


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
        "loads_distributed": [],
        "loads_nodal": [],
    }


IPN_DEFAULT = {"h": 20.0, "b": 10.0, "tw": 0.6, "tf": 1.0}

# Títulos cortos para pestañas del visor de resultados (mismas claves que ``cli/resultados_export``).
_RESULTADOS_TAB_TITLES = {
    "K_locales": "K locales",
    "Matriz_R_2D": "Matriz R (12×12)",
    "F_locales_de_cargas": "F locales (cargas)",
    "R_locales_de_empotramiento_cargas": "R locales de empot. (reacciones)",
    "Cargas_nodales_locales": "Cargas nodales locales",
    "Cargas_Nodales_Aplicadas": "Cargas nodales aplicadas (en nodo)",
    "Cargas_nodales_equivalentes_Globales": "Cargas nodales equivalentes Globales",
    "Vector_Nodal_Equivalente": "Vector nodal equivalente F (global)",
    "Solicitacion_extremo_de_barra_Globales": "Solicitación extremo de barra Globales",
    "Solicitacion_extremo_de_barra_Locales": "Solicitación extremo de barra Locales",
    "Desplazamientos_globales_D": "Desplazamientos D Globales",
    "Sistema_reducido_Kll_Fl": "Sistema reducido Kll, Fl",
    "Ejes_Locales": "Ternas locales en Ejes globales",
    "Matriz_Rotacion_T": "Matriz T (12×12)",
}


def _msg_yes_no_flags(MB: Any) -> Any:
    SB = getattr(MB, "StandardButton", None)
    if SB is not None:
        return SB.Yes | SB.No
    return MB.Yes | MB.No


def _startup_progress_tick(
    cb: Optional[Callable[[int, str], None]], pct: int, msg: str
) -> None:
    if cb is None:
        return
    try:
        cb(pct, msg)
    except Exception:
        pass


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
        startup_progress: Optional[Callable[[int, str], None]] = None,
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
        _startup_progress_tick(startup_progress, 6, "Iniciando ventana…")
        titulo = "Reticular — análisis de estructuras 3D (PyVista)"
        if precargar_ejemplo:
            from .supertesteo_spec import get_supertesteo_spec

            try:
                self._spec = copy.deepcopy(get_supertesteo_spec())
                titulo = "Reticular — ejemplo supertesteo (precargado)"
            except Exception:
                self._spec = _default_spec()
        else:
            self._spec = _default_spec()
        self.setWindowTitle(titulo)
        self.resize(1280, 780)
        from cli.viewport_theme import load_viewport_theme_id

        self._viewport_theme_id: str = load_viewport_theme_id()
        self._last_theme_cycle_ts: float = 0.0
        self._qt_backend = backend
        self._estructura: Optional[Estructura] = None
        self._solved = False
        self._F_internas: Optional[List[Any]] = None
        self._cached_resultados_dfs: Optional[Dict[str, Any]] = None
        self._resultados_sheet_key_order: List[str] = []
        self._resultados_combo_updating: bool = False
        self._hover_state: Dict[str, Any] = {"hover": []}
        self._selected_bar_id: Optional[int] = None
        self._viz_bb: Any = None
        self._viz_nodos_dict: Optional[Dict[Any, Any]] = None
        self._viz_hr: Optional[float] = None
        self._ftool_preserve_camera = False
        self._escala_diagrama = 1.0
        self._escala_deform = 1.0
        self._ipn_dims = IPN_DEFAULT.copy()
        self._longitud_vector = 45.0
        self._history_limit = 5
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []

        if backend == "PySide6":
            from PySide6.QtCore import QSize
            from PySide6.QtGui import QFont
            from PySide6.QtWidgets import (
                QAbstractItemView,
                QLineEdit,
                QSizePolicy,
                QStackedWidget,
                QTabWidget,
                QTableWidget,
                QTableWidgetItem,
                QToolButton,
            )

            _tt_icon = Qt.ToolButtonStyle.ToolButtonIconOnly
            _tt_txt = Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        else:
            from PyQt5.QtCore import QSize
            from PyQt5.QtGui import QFont
            from PyQt5.QtWidgets import (
                QAbstractItemView,
                QLineEdit,
                QSizePolicy,
                QStackedWidget,
                QTabWidget,
                QTableWidget,
                QTableWidgetItem,
                QToolButton,
            )

            _tt_icon = Qt.ToolButtonIconOnly
            _tt_txt = Qt.ToolButtonTextBesideIcon

        self._QLineEdit = QLineEdit
        self._QStackedWidget = QStackedWidget

        from cli.gui_icons import ftool_engineering_icons

        _ico = ftool_engineering_icons()
        _startup_progress_tick(startup_progress, 18, "Barra de herramientas…")

        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)

        # ── Top toolbar (QToolBar nativo de QMainWindow) ─────────────────
        self._top_toolbar = self.addToolBar("Principal")
        self._top_toolbar.setMovable(False)
        self._top_toolbar.setFloatable(False)
        self._top_toolbar.setIconSize(QSize(18, 18))

        def _mk_tb(key: str, tip: str, slot: Any, text: str = "") -> QToolButton:
            b = QToolButton()
            b.setIcon(_ico.get(key, _ico["node"]))
            b.setIconSize(QSize(18, 18))
            b.setToolTip(tip)
            if text:
                b.setText(text)
                b.setToolButtonStyle(_tt_txt)
            else:
                b.setToolButtonStyle(_tt_icon)
            b.clicked.connect(slot)
            return b

        self._top_toolbar.addWidget(_mk_tb("new",  "Nuevo modelo",    self._new_project))
        self._top_toolbar.addWidget(_mk_tb("open", "Abrir JSON…",     self._open_json))
        self._top_toolbar.addWidget(_mk_tb("save", "Guardar JSON…",   self._save_json))
        self._btn_undo = _mk_tb("undo", "Deshacer (Ctrl+Z)", self._undo_model_change)
        self._btn_redo = _mk_tb("redo", "Rehacer (Ctrl+Y)", self._redo_model_change)
        self._top_toolbar.addWidget(self._btn_undo)
        self._top_toolbar.addWidget(self._btn_redo)
        self._top_toolbar.addSeparator()

        self._btn_nodo  = _mk_tb("node",       "Agregar nodo",                   self._dlg_add_node)
        self._btn_barra = _mk_tb("bar",        "Agregar barra",                  self._dlg_add_bar)
        self._btn_carga = _mk_tb("load",       "Carga puntual en barra",         self._dlg_add_load)
        self._btn_carga_dist  = _mk_tb("load",       "Carga distribuida en barra",     self._dlg_add_distributed_load)
        self._btn_carga_nodal = _mk_tb("load_nodal", "Carga nodal en nodo",            self._dlg_add_nodal_load)
        self._btn_del   = QToolButton()
        self._btn_del.setObjectName("btnIconDanger")
        self._btn_del.setIcon(_ico["delete"])
        self._btn_del.setIconSize(QSize(18, 18))
        self._btn_del.setToolButtonStyle(_tt_icon)
        self._btn_del.setToolTip("Eliminar fila seleccionada")
        self._btn_del.clicked.connect(self._on_delete_selection)
        for _b in (self._btn_nodo, self._btn_barra, self._btn_carga, self._btn_carga_dist, self._btn_carga_nodal, self._btn_del):
            self._top_toolbar.addWidget(_b)
        self._top_toolbar.addSeparator()

        self._btn_analizar = QToolButton()
        self._btn_analizar.setObjectName("btnAnalyze")
        self._btn_analizar.setIcon(_ico["run"])
        self._btn_analizar.setText("Analizar")
        self._btn_analizar.setToolButtonStyle(_tt_txt)
        self._btn_analizar.setIconSize(QSize(18, 18))
        self._btn_analizar.setToolTip("Ejecutar análisis estructural (F5)")
        self._btn_analizar.clicked.connect(self._on_analyze)
        self._top_toolbar.addWidget(self._btn_analizar)
        self._top_toolbar.addSeparator()

        lbl_vista = QLabel("  Vista ")
        lbl_vista.setObjectName("mutedLabel")
        self._top_toolbar.addWidget(lbl_vista)
        self._combo_vista = QComboBox()
        for _key, _label in [
            ("geom",  "Geometría"),
            ("loads", "Cargas"),
            ("def",   "Deformada"),
            ("vy",    "Corte V_y"),
            ("vz",    "Corte V_z"),
            ("nx",    "Normal N_x"),
            ("my",    "Momento M_y"),
            ("mz",    "Momento M_z"),
            ("mx",    "Torsión M_x"),
        ]:
            self._combo_vista.addItem(_label, _key)
        self._combo_vista.setMinimumWidth(150)
        self._combo_vista.setMaximumWidth(210)
        if backend == "PySide6":
            self._combo_vista.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
            )
        else:
            self._combo_vista.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self._top_toolbar.addWidget(self._combo_vista)
        self._style_combo_popup()
        self._top_toolbar.addSeparator()

        lbl_sc = QLabel("  Escala ")
        lbl_sc.setObjectName("mutedLabel")
        self._top_toolbar.addWidget(lbl_sc)
        if backend == "PySide6":
            ori = Qt.Orientation.Horizontal
        else:
            ori = Qt.Horizontal
        self._slider_escala = QSlider(ori)
        self._slider_escala.setMinimum(20)
        self._slider_escala.setMaximum(1000)
        self._slider_escala.setValue(100)
        self._slider_escala.setMaximumWidth(200)
        self._slider_escala.setMinimumWidth(80)
        self._lbl_escala = QLabel("1.00")
        self._lbl_escala.setObjectName("scaleValue")
        self._lbl_escala.setMinimumWidth(38)
        _qt = self._Qt
        self._lbl_escala.setAlignment(_qt.AlignLeft | _qt.AlignVCenter)
        self._top_toolbar.addWidget(self._slider_escala)
        self._top_toolbar.addWidget(self._lbl_escala)

        # Espacio + conmutador Modelo 3D / Resultados (siempre visible)
        _sp = QWidget()
        if backend == "PySide6":
            _sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        else:
            _sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._top_toolbar.addWidget(_sp)
        self._btn_ws_3d = QToolButton()
        self._btn_ws_3d.setObjectName("wsToggle")
        self._btn_ws_3d.setCheckable(True)
        self._btn_ws_3d.setChecked(True)
        self._btn_ws_3d.setIcon(_ico.get("view3d", _ico["bar"]))
        self._btn_ws_3d.setIconSize(QSize(18, 18))
        self._btn_ws_3d.setToolButtonStyle(_tt_icon)
        self._btn_ws_3d.setToolTip("Vista Modelo 3D (diagramas, deformada)")
        self._btn_ws_3d.clicked.connect(lambda: self._set_workspace_page(0))
        self._btn_ws_res = QToolButton()
        self._btn_ws_res.setObjectName("wsToggle")
        self._btn_ws_res.setCheckable(True)
        self._btn_ws_res.setIcon(_ico.get("viewtable", _ico["bar"]))
        self._btn_ws_res.setIconSize(QSize(18, 18))
        self._btn_ws_res.setToolButtonStyle(_tt_icon)
        self._btn_ws_res.setToolTip("Vista Resultados (tablas)")
        self._btn_ws_res.clicked.connect(lambda: self._set_workspace_page(1))
        self._top_toolbar.addWidget(self._btn_ws_3d)
        self._top_toolbar.addWidget(self._btn_ws_res)

        # ── Área central: stacked 3D / Resultados (sin pestañas que ocultan la barra) ──
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        view_3d = QWidget(central)
        lay_3d = QVBoxLayout(view_3d)
        lay_3d.setContentsMargins(0, 0, 0, 0)
        lay_3d.setSpacing(0)
        _startup_progress_tick(startup_progress, 32, "Inicializando vista 3D (PyVista)…")
        self._plotter = QtInteractor(view_3d)
        lay_3d.addWidget(self._plotter.interactor, stretch=1)
        _startup_progress_tick(startup_progress, 58, "Motor de gráficos listo")

        self._wrap_resultados = QWidget(central)
        rl = QVBoxLayout(self._wrap_resultados)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(6)
        res_tb = QHBoxLayout()
        self._btn_res_refresh     = QPushButton("Actualizar tablas")
        self._btn_res_export      = QPushButton("Exportar como…")
        self._btn_res_csv_folder  = QPushButton("Exportar todas las hojas CSV…")
        self._btn_res_refresh.setToolTip("Recargar desde el último análisis")
        self._btn_res_export.setToolTip("Libro Excel (.xlsx), informe PDF o CSV de la hoja visible")
        self._btn_res_csv_folder.setToolTip("Un archivo .csv por tabla en la carpeta elegida")
        self._btn_res_refresh.clicked.connect(self._refresh_resultados_tables_ui)
        self._btn_res_export.clicked.connect(self._export_resultados_dialog)
        self._btn_res_csv_folder.clicked.connect(self._export_resultados_csv_folder)
        res_tb.addWidget(self._btn_res_refresh)
        res_tb.addWidget(self._btn_res_export)
        res_tb.addWidget(self._btn_res_csv_folder)
        res_tb.addStretch(1)
        rl.addLayout(res_tb)
        self._tabs_resultados_sheets = QTabWidget()
        self._tabs_resultados_sheets.setDocumentMode(True)
        try:
            self._tabs_resultados_sheets.tabBar().hide()
        except Exception:
            pass
        self._resultados_sheet_nav = QWidget()
        self._resultados_sheet_nav.setObjectName("resultadosSheetNav")
        self._resultados_sheet_nav.setToolTip(
            "Navegación entre hojas del último análisis.\n"
            "Atajos: Ctrl+Re Pág (siguiente), Ctrl+Av Pág (anterior) — solo en vista Resultados."
        )
        nav_lay = QHBoxLayout(self._resultados_sheet_nav)
        nav_lay.setContentsMargins(4, 4, 4, 4)
        nav_lay.setSpacing(8)
        self._btn_res_tab_prev = QPushButton("Anterior")
        self._btn_res_tab_prev.setObjectName("resultadosSheetNavBtn")
        self._btn_res_tab_prev.setMinimumHeight(28)
        self._btn_res_tab_prev.setToolTip(
            "Hoja anterior (Ctrl+Av Pág)\nSolo actúa en la vista Resultados."
        )
        self._btn_res_tab_prev.clicked.connect(lambda: self._shift_resultados_tab(-1))
        self._lbl_resultados_sheet_pos = QLabel("")
        self._lbl_resultados_sheet_pos.setObjectName("resultadosSheetNavLabel")
        self._lbl_resultados_sheet_pos.setMinimumWidth(180)
        if backend == "PySide6":
            self._lbl_resultados_sheet_pos.setSizePolicy(
                QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
            )
        else:
            self._lbl_resultados_sheet_pos.setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.Fixed
            )
        self._combo_resultados_sheet = QComboBox()
        self._combo_resultados_sheet.setObjectName("resultadosSheetNavCombo")
        self._combo_resultados_sheet.setMinimumHeight(28)
        self._combo_resultados_sheet.setMinimumWidth(240)
        if backend == "PySide6":
            self._combo_resultados_sheet.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        else:
            self._combo_resultados_sheet.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo_resultados_sheet.setEditable(False)
        self._combo_resultados_sheet.currentIndexChanged.connect(self._on_resultados_combo_sheet_changed)
        try:
            self._combo_resultados_sheet.showPopup.connect(self._style_resultados_sheet_combo)
        except Exception:
            pass
        self._btn_res_tab_next = QPushButton("Siguiente")
        self._btn_res_tab_next.setObjectName("resultadosSheetNavBtn")
        self._btn_res_tab_next.setMinimumHeight(28)
        self._btn_res_tab_next.setToolTip(
            "Hoja siguiente (Ctrl+Re Pág)\nSolo actúa en la vista Resultados."
        )
        self._btn_res_tab_next.clicked.connect(lambda: self._shift_resultados_tab(1))
        nav_lay.addWidget(self._btn_res_tab_prev)
        nav_lay.addWidget(self._lbl_resultados_sheet_pos, 1)
        nav_lay.addWidget(self._combo_resultados_sheet, 2)
        nav_lay.addWidget(self._btn_res_tab_next)
        self._tabs_resultados_sheets.currentChanged.connect(self._on_resultados_sheet_tab_changed)
        rl.addWidget(self._resultados_sheet_nav)
        rl.addWidget(self._tabs_resultados_sheets, stretch=1)

        self._workspace_stack = QStackedWidget(central)
        self._IDX_WORKSPACE_3D = 0
        self._IDX_WORKSPACE_RESULTADOS = 1
        self._workspace_stack.addWidget(view_3d)
        self._workspace_stack.addWidget(self._wrap_resultados)
        self._workspace_stack.setCurrentIndex(self._IDX_WORKSPACE_3D)
        self._workspace_stack.currentChanged.connect(self._on_workspace_page_changed)

        lay.addWidget(self._workspace_stack, stretch=1)

        # ── Inspector dock al lado DERECHO ───────────────────────────────
        self._QTableWidgetItem = QTableWidgetItem
        self._inspector_dock = QDockWidget("Tablas del modelo", self)
        self._tabs_model = QTabWidget()
        self._tabs_model.setDocumentMode(True)
        self._tabs_model.setMovable(False)
        try:
            self._tabs_model.tabBar().setExpanding(True)
        except Exception:
            pass

        self._tbl_nodes = QTableWidget()
        self._tbl_bars  = QTableWidget()
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

        def _mk_model_tab(table: Any, add_tip: str, add_slot: Any) -> Any:
            wrap = QWidget()
            lay_tab = QVBoxLayout(wrap)
            lay_tab.setContentsMargins(0, 0, 0, 0)
            lay_tab.setSpacing(0)
            lay_tab.addWidget(table, 1)
            footer_wrap = QWidget()
            footer_wrap.setObjectName("modelTableFooter")
            footer = QHBoxLayout(footer_wrap)
            footer.setContentsMargins(8, 6, 8, 6)
            footer.setSpacing(6)
            b_add = QPushButton("+")
            b_del = QPushButton("-")
            b_add.setObjectName("modelMiniAdd")
            b_del.setObjectName("modelMiniDel")
            if backend == "PySide6":
                _sp_exp = QSizePolicy.Policy.Expanding
                _sp_fix = QSizePolicy.Policy.Fixed
            else:
                _sp_exp = QSizePolicy.Expanding
                _sp_fix = QSizePolicy.Fixed
            b_add.setSizePolicy(_sp_exp, _sp_fix)
            b_del.setSizePolicy(_sp_exp, _sp_fix)
            b_add.setMinimumHeight(30)
            b_del.setMinimumHeight(30)
            b_add.setToolTip(add_tip)
            b_del.setToolTip("Eliminar fila seleccionada")
            b_add.setCursor(Qt.PointingHandCursor)
            b_del.setCursor(Qt.PointingHandCursor)
            _btn_font = b_add.font()
            _btn_font.setBold(True)
            _btn_font.setPointSize(max(int(_btn_font.pointSize()), 12))
            b_add.setFont(_btn_font)
            b_del.setFont(_btn_font)
            b_add.clicked.connect(add_slot)
            b_del.clicked.connect(self._on_delete_selection)
            footer.addWidget(b_add, 1)
            footer.addWidget(b_del, 1)
            lay_tab.addWidget(footer_wrap, 0)
            return wrap

        self._tabs_model.addTab(
            _mk_model_tab(self._tbl_nodes, "Añadir nodo", self._dlg_add_node), "Nodos"
        )
        self._tabs_model.addTab(
            _mk_model_tab(self._tbl_bars, "Añadir barra", self._dlg_add_bar), "Barras"
        )
        self._tabs_model.addTab(
            _mk_model_tab(self._tbl_loads, "Añadir carga puntual en barra", self._dlg_add_load), "Cargas"
        )

        self._IDX_TAB_INSPECTOR_MODELO = 0
        self._IDX_TAB_INSPECTOR_MAT    = 1

        model_wrap = QWidget()
        mw_lay = QVBoxLayout(model_wrap)
        mw_lay.setContentsMargins(0, 0, 0, 0)
        mw_lay.setSpacing(0)
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

        mat_wrap = QWidget()
        mat_lay = QVBoxLayout(mat_wrap)
        mat_lay.setContentsMargins(0, 0, 0, 0)
        mat_lay.setSpacing(0)
        mat_lay.addWidget(self._tbl_materials, 1)
        mat_footer_wrap = QWidget()
        mat_footer_wrap.setObjectName("modelTableFooter")
        mat_footer = QHBoxLayout(mat_footer_wrap)
        mat_footer.setContentsMargins(8, 6, 8, 6)
        mat_footer.setSpacing(6)
        self._btn_mat_add = QPushButton("+")
        self._btn_mat_delete = QPushButton("-")
        self._btn_mat_add.setObjectName("materialMiniAdd")
        self._btn_mat_delete.setObjectName("materialMiniDel")
        if backend == "PySide6":
            _sp_exp = QSizePolicy.Policy.Expanding
            _sp_fix = QSizePolicy.Policy.Fixed
        else:
            _sp_exp = QSizePolicy.Expanding
            _sp_fix = QSizePolicy.Fixed
        self._btn_mat_add.setSizePolicy(_sp_exp, _sp_fix)
        self._btn_mat_delete.setSizePolicy(_sp_exp, _sp_fix)
        self._btn_mat_add.setMinimumHeight(30)
        self._btn_mat_delete.setMinimumHeight(30)
        self._btn_mat_add.setToolTip("Nuevo material o sección")
        self._btn_mat_delete.setToolTip("Eliminar material seleccionado")
        self._btn_mat_add.setCursor(Qt.PointingHandCursor)
        self._btn_mat_delete.setCursor(Qt.PointingHandCursor)
        _btn_font_mat = self._btn_mat_add.font()
        _btn_font_mat.setBold(True)
        _btn_font_mat.setPointSize(max(int(_btn_font_mat.pointSize()), 12))
        self._btn_mat_add.setFont(_btn_font_mat)
        self._btn_mat_delete.setFont(_btn_font_mat)
        self._btn_mat_add.clicked.connect(lambda: self._dlg_material_editor(None))
        self._btn_mat_delete.clicked.connect(self._on_delete_selection)
        mat_footer.addWidget(self._btn_mat_add, 1)
        mat_footer.addWidget(self._btn_mat_delete, 1)
        mat_lay.addWidget(mat_footer_wrap, 0)

        self._outer_inspector = QTabWidget()
        self._outer_inspector.setDocumentMode(True)
        try:
            self._outer_inspector.tabBar().setExpanding(True)
        except Exception:
            pass
        self._outer_inspector.addTab(model_wrap, "Modelo")
        self._outer_inspector.addTab(mat_wrap, "Materiales y secciones")

        self._inspector_dock.setWidget(self._outer_inspector)
        dock_title_bar = QWidget()
        dock_title_bar.setObjectName("dockTitleBar")
        dock_title_lay = QHBoxLayout(dock_title_bar)
        dock_title_lay.setContentsMargins(0, 0, 0, 0)
        dock_title_lay.setSpacing(0)
        dock_title_lbl = QLabel("Tablas del modelo")
        dock_title_lbl.setObjectName("dockTitleLabel")
        dock_title_lay.addWidget(dock_title_lbl)
        self._inspector_dock.setTitleBarWidget(dock_title_bar)
        right_dock = getattr(Qt, "RightDockWidgetArea", None)
        if right_dock is None:
            right_dock = 2
        self.addDockWidget(right_dock, self._inspector_dock)
        self._inspector_dock.setMinimumWidth(380)
        self._inspector_dock.setMaximumWidth(540)
        _startup_progress_tick(startup_progress, 72, "Panel de tablas…")

        # ── Barra de estado ──────────────────────────────────────────────
        self._legend_status  = QLabel("")
        self._legend_status.setObjectName("statusLegend")
        self._summary_status = QLabel("")
        self._summary_status.setObjectName("statusSummary")
        self.statusBar().addWidget(self._summary_status, 1)
        self.statusBar().addPermanentWidget(self._legend_status)

        # ── Señales ──────────────────────────────────────────────────────
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
        self._tbl_bars.itemSelectionChanged.connect(self._on_bars_table_selection_changed)
        self._tbl_loads.itemDoubleClicked.connect(self._on_loads_table_double_clicked)
        self._combo_vista.currentIndexChanged.connect(lambda _: self._redraw())
        try:
            self._combo_vista.showPopup.connect(self._style_combo_popup)
        except Exception:
            pass
        self._slider_escala.valueChanged.connect(self._on_slider)

        self._base_font = QFont("Segoe UI", 9)
        self.setFont(self._base_font)
        self._apply_full_ui_theme()
        _startup_progress_tick(startup_progress, 82, "Menús y atajos…")

        # ── Menús ────────────────────────────────────────────────────────
        menu = self.menuBar().addMenu("Archivo")
        act_new = menu.addAction("Nuevo")
        act_new.triggered.connect(self._new_project)
        act_open = menu.addAction("Abrir JSON…")
        act_open.triggered.connect(self._open_json)
        act_save = menu.addAction("Guardar JSON…")
        act_save.triggered.connect(self._save_json)
        act_png = menu.addAction("Exportar vista PNG…")
        act_png.triggered.connect(self._export_viewport_png)

        menu_res = self.menuBar().addMenu("Resultados")
        act_res_tab = menu_res.addAction("Abrir pestaña Resultados")
        act_res_tab.setToolTip("Visor tipo Excel: tablas del último análisis")
        act_res_tab.triggered.connect(self._show_resultados_tab)
        act_res_export = menu_res.addAction("Exportar como…")
        act_res_export.setToolTip("Excel, PDF o CSV de la hoja visible")
        act_res_export.triggered.connect(self._export_resultados_dialog)

        menu_mod = self.menuBar().addMenu("Modelo")
        act_mat_new = menu_mod.addAction("Nuevo material…")
        act_mat_new.setToolTip("Misma acción que antes en el panel derecho")
        act_mat_new.triggered.connect(lambda: self._dlg_material_editor(None))
        act_mat_ed = menu_mod.addAction("Editar material seleccionado…")
        act_mat_ed.setToolTip("Seleccioná una fila en la pestaña Materiales del panel derecho")
        act_mat_ed.triggered.connect(self._on_edit_material_toolbar)

        menu_vista = self.menuBar().addMenu("Vista")
        act_v3d = menu_vista.addAction("Ir a Modelo 3D")
        act_v3d.triggered.connect(self._show_workspace_3d)
        act_vres = menu_vista.addAction("Ir a Resultados (tablas)")
        act_vres.triggered.connect(self._show_resultados_tab)
        menu_vista.addSeparator()
        from cli.viewport_theme import list_themes

        sub_vp = menu_vista.addMenu("Tema de la aplicación")
        for _spec in list_themes():
            _tid = _spec.id
            sub_vp.addAction(_spec.label).triggered.connect(
                lambda checked=False, tid=_tid: self._set_viewport_theme(tid)
            )
        sub_vp.addSeparator()
        sub_vp.addAction("Siguiente (T)").triggered.connect(self._cycle_viewport_theme)

        # ── Atajos de teclado ────────────────────────────────────────────
        try:
            if backend == "PySide6":
                from PySide6.QtGui import QKeySequence, QShortcut
            else:
                from PyQt5.QtGui import QKeySequence
                from PyQt5.QtWidgets import QShortcut

            _esc_sc = QShortcut(QKeySequence(Qt.Key_Escape), self)
            try:
                _esc_sc.setContext(Qt.ShortcutContext.WindowShortcut)
            except AttributeError:
                try:
                    _esc_sc.setContext(Qt.WindowShortcut)
                except Exception:
                    pass
            _esc_sc.activated.connect(self._on_escape_deselect_bar)

            _f5_sc = QShortcut(QKeySequence(Qt.Key_F5), self)
            _f5_sc.activated.connect(self._on_analyze)
            _undo_sc = QShortcut(QKeySequence("Ctrl+Z"), self)
            _undo_sc.activated.connect(self._undo_model_change)
            _redo_sc = QShortcut(QKeySequence("Ctrl+Y"), self)
            _redo_sc.activated.connect(self._redo_model_change)

            _del_sc = QShortcut(QKeySequence(Qt.Key_Delete), self)
            try:
                _del_sc.setContext(Qt.ShortcutContext.WindowShortcut)
            except AttributeError:
                try:
                    _del_sc.setContext(Qt.WindowShortcut)
                except Exception:
                    pass
            _del_sc.activated.connect(self._on_delete_selection)
            try:
                self._plotter.interactor.installEventFilter(self)
            except Exception:
                pass

            _t_vp_sc = QShortcut(QKeySequence(Qt.Key_T), self)
            try:
                _t_vp_sc.setContext(Qt.ShortcutContext.WindowShortcut)
            except AttributeError:
                try:
                    _t_vp_sc.setContext(Qt.WindowShortcut)
                except Exception:
                    pass
            _t_vp_sc.activated.connect(self._on_shortcut_cycle_viewport_theme)

            _res_pgdn = QShortcut(QKeySequence("Ctrl+PgDown"), self)
            _res_pgup = QShortcut(QKeySequence("Ctrl+PgUp"), self)
            for _sc in (_res_pgdn, _res_pgup):
                try:
                    _sc.setContext(Qt.ShortcutContext.WindowShortcut)
                except AttributeError:
                    try:
                        _sc.setContext(Qt.WindowShortcut)
                    except Exception:
                        pass
            _res_pgdn.activated.connect(self._on_shortcut_resultados_sheet_next)
            _res_pgup.activated.connect(self._on_shortcut_resultados_sheet_prev)
        except Exception:
            pass

        try:
            self._plotter.add_key_event("t", lambda: self._cycle_viewport_theme())
        except Exception:
            pass

        # ── Hover en diagramas ───────────────────────────────────────────
        try:
            from plot.pyvista_pestanas import _install_diagram_hover

            _install_diagram_hover(
                self._plotter,
                lambda: self._hover_state.get("hover") or [],
                lambda: str(self._combo_vista.currentData() or "vy"),
            )
        except Exception:
            pass

        # ── Estado inicial ───────────────────────────────────────────────
        if precargar_ejemplo:
            self.statusBar().showMessage(
                "Ejemplo supertesteo: 5 nodos, 4 barras, 3 cargas."
            )

        _startup_progress_tick(startup_progress, 90, "Cargando modelo y vista…")
        self._refresh_tree()
        self._redraw()
        self._sync_ws_toggle_buttons()
        self._on_workspace_page_changed(self._workspace_stack.currentIndex())
        self._refresh_resultados_tables_ui()
        self._update_undo_redo_buttons()
        _startup_progress_tick(startup_progress, 100, "Listo")

    def _snapshot_spec(self) -> Dict[str, Any]:
        return copy.deepcopy(self._spec)

    def _push_undo_snapshot(self) -> None:
        snap = self._snapshot_spec()
        if self._undo_stack and self._undo_stack[-1] == snap:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack = self._undo_stack[-self._history_limit :]
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _reset_history(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        try:
            self._btn_undo.setEnabled(bool(self._undo_stack))
            self._btn_redo.setEnabled(bool(self._redo_stack))
        except Exception:
            pass

    def _undo_model_change(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Deshacer: no hay más cambios.")
            self._update_undo_redo_buttons()
            return
        self._redo_stack.append(self._snapshot_spec())
        if len(self._redo_stack) > self._history_limit:
            self._redo_stack = self._redo_stack[-self._history_limit :]
        self._spec = self._undo_stack.pop()
        self._update_undo_redo_buttons()
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()
        self.statusBar().showMessage("Se deshizo el último cambio (Ctrl+Z).")

    def _redo_model_change(self) -> None:
        if not self._redo_stack:
            self.statusBar().showMessage("Rehacer: no hay cambios para rehacer.")
            self._update_undo_redo_buttons()
            return
        self._undo_stack.append(self._snapshot_spec())
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack = self._undo_stack[-self._history_limit :]
        self._spec = self._redo_stack.pop()
        self._update_undo_redo_buttons()
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()
        self.statusBar().showMessage("Se rehizo el cambio (Ctrl+Y).")

    def _ui_color_tokens(self):
        from cli.qt_app_theme import get_app_color_tokens

        return get_app_color_tokens(self._viewport_theme_id)

    def _apply_full_ui_theme(self) -> None:
        from cli.qt_app_theme import build_application_stylesheet, resultados_sheet_bar_stylesheet

        tok = self._ui_color_tokens()
        self.setStyleSheet(build_application_stylesheet(tok))
        self._apply_application_popup_palette()
        self._style_combo_popup()
        self._style_resultados_sheet_combo()
        nav = getattr(self, "_resultados_sheet_nav", None)
        if nav is not None:
            nav.setStyleSheet(resultados_sheet_bar_stylesheet(tok))

    def _apply_application_popup_palette(self) -> None:
        """Paleta global para tooltips y menús (Fusion en Windows ignora a veces solo el QSS)."""
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QPalette, QColor
        except ImportError:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QPalette, QColor

        app = QApplication.instance()
        if app is None:
            return
        t = self._ui_color_tokens()
        pal = app.palette()
        _CR = getattr(QPalette, "ColorRole", QPalette)
        pal.setColor(_CR.ToolTipBase, QColor(t.tooltip_bg))
        pal.setColor(_CR.ToolTipText, QColor(t.tooltip_fg))
        pal.setColor(_CR.Base, QColor(t.combo_popup_bg))
        pal.setColor(_CR.AlternateBase, QColor(t.surface_alt))
        pal.setColor(_CR.Text, QColor(t.combo_popup_fg))
        pal.setColor(_CR.Window, QColor(t.win_bg))
        pal.setColor(_CR.WindowText, QColor(t.win_fg))
        pal.setColor(_CR.Button, QColor(t.push_bg))
        pal.setColor(_CR.ButtonText, QColor(t.push_fg))
        _hl = getattr(_CR, "Highlight", None)
        if _hl is not None:
            pal.setColor(_hl, QColor(t.selection_bg))
        _hlt = getattr(_CR, "HighlightedText", None)
        if _hlt is not None:
            pal.setColor(_hlt, QColor(t.selection_fg))
        _mr = getattr(_CR, "Menu", None)
        if _mr is not None:
            pal.setColor(_mr, QColor(t.menu_bg))
        _mt = getattr(_CR, "MenuText", None)
        if _mt is not None:
            pal.setColor(_mt, QColor(t.menu_fg))
        app.setPalette(pal)

    def _style_combo_popup(self) -> None:
        """Lista del combo: sin marco negro del estilo nativo; colores coherentes con el tema."""
        combo = getattr(self, "_combo_vista", None)
        if combo is None:
            return
        view = combo.view()
        try:
            from PySide6.QtWidgets import QFrame
            from PySide6.QtGui import QPalette, QColor

            _no = QFrame.Shape.NoFrame
            _plain = QFrame.Shadow.Plain
        except ImportError:
            from PyQt5.QtWidgets import QFrame
            from PyQt5.QtGui import QPalette, QColor

            _no = QFrame.NoFrame
            _plain = QFrame.Plain
        try:
            view.setFrameShape(_no)
            view.setFrameShadow(_plain)
            view.setLineWidth(0)
        except Exception:
            pass
        t = self._ui_color_tokens()
        view.setStyleSheet(
            "QAbstractItemView { background-color: %s; color: %s; "
            "selection-background-color: %s; selection-color: %s; "
            "border: 1px solid %s; outline: none; }"
            % (
                t.combo_popup_bg,
                t.combo_popup_fg,
                t.selection_bg,
                t.selection_fg,
                t.combo_popup_border,
            )
        )
        view.setAutoFillBackground(True)
        vpal = view.palette()
        _CR = getattr(QPalette, "ColorRole", QPalette)
        vpal.setColor(_CR.Base, QColor(t.combo_popup_bg))
        vpal.setColor(_CR.Text, QColor(t.combo_popup_fg))
        vpal.setColor(_CR.Highlight, QColor(t.selection_bg))
        vpal.setColor(_CR.HighlightedText, QColor(t.selection_fg))
        view.setPalette(vpal)
        pop = view.parentWidget()
        if pop is not None:
            pop.setAutoFillBackground(True)
            pop.setStyleSheet(
                "background-color: %s; border: 1px solid %s;"
                % (t.combo_popup_bg, t.combo_popup_border)
            )

    def _style_resultados_sheet_combo(self) -> None:
        """Lista desplegable del selector de hoja (misma paleta que el combo de vista)."""
        combo = getattr(self, "_combo_resultados_sheet", None)
        if combo is None:
            return
        view = combo.view()
        try:
            from PySide6.QtWidgets import QFrame
            from PySide6.QtGui import QPalette, QColor

            _no = QFrame.Shape.NoFrame
            _plain = QFrame.Shadow.Plain
        except ImportError:
            from PyQt5.QtWidgets import QFrame
            from PyQt5.QtGui import QPalette, QColor

            _no = QFrame.NoFrame
            _plain = QFrame.Plain
        try:
            view.setFrameShape(_no)
            view.setFrameShadow(_plain)
            view.setLineWidth(0)
        except Exception:
            pass
        t = self._ui_color_tokens()
        view.setStyleSheet(
            "QAbstractItemView { background-color: %s; color: %s; "
            "selection-background-color: %s; selection-color: %s; "
            "border: 1px solid %s; outline: none; }"
            % (
                t.combo_popup_bg,
                t.combo_popup_fg,
                t.selection_bg,
                t.selection_fg,
                t.combo_popup_border,
            )
        )
        view.setAutoFillBackground(True)
        vpal = view.palette()
        _CR = getattr(QPalette, "ColorRole", QPalette)
        vpal.setColor(_CR.Base, QColor(t.combo_popup_bg))
        vpal.setColor(_CR.Text, QColor(t.combo_popup_fg))
        vpal.setColor(_CR.Highlight, QColor(t.selection_bg))
        vpal.setColor(_CR.HighlightedText, QColor(t.selection_fg))
        view.setPalette(vpal)
        pop = view.parentWidget()
        if pop is not None:
            pop.setAutoFillBackground(True)
            pop.setStyleSheet(
                "background-color: %s; border: 1px solid %s;"
                % (t.combo_popup_bg, t.combo_popup_border)
            )

    def _set_workspace_page(self, idx: int) -> None:
        if idx not in (0, 1):
            idx = 0
        self._workspace_stack.setCurrentIndex(idx)
        self._sync_ws_toggle_buttons()
        if idx == self._IDX_WORKSPACE_RESULTADOS:
            self._refresh_resultados_tables_ui()
        self._on_workspace_page_changed(idx)

    def _sync_ws_toggle_buttons(self) -> None:
        b3 = getattr(self, "_btn_ws_3d", None)
        br = getattr(self, "_btn_ws_res", None)
        if b3 is None or br is None:
            return
        i = self._workspace_stack.currentIndex()
        b3.setChecked(i == self._IDX_WORKSPACE_3D)
        br.setChecked(i == self._IDX_WORKSPACE_RESULTADOS)

    def _show_workspace_3d(self) -> None:
        self._set_workspace_page(self._IDX_WORKSPACE_3D)

    def _viewport_style_dict(self) -> Dict[str, Any]:
        from cli.viewport_theme import get_theme, theme_to_style_dict

        return theme_to_style_dict(get_theme(self._viewport_theme_id))

    def _set_viewport_theme(self, theme_id: str, *, persist: bool = True) -> None:
        from cli.viewport_theme import get_theme, save_viewport_theme_id

        spec = get_theme(theme_id)
        self._viewport_theme_id = spec.id
        if persist:
            save_viewport_theme_id(spec.id)
        self.statusBar().showMessage(f"Tema: {spec.label}")
        self._redraw()
        self._apply_full_ui_theme()

    def _cycle_viewport_theme(self) -> None:
        import time

        from cli.viewport_theme import get_theme, next_theme_id, save_viewport_theme_id

        now = time.monotonic()
        if now - float(getattr(self, "_last_theme_cycle_ts", 0.0)) < 0.2:
            return
        self._last_theme_cycle_ts = now
        nid = next_theme_id(self._viewport_theme_id)
        self._viewport_theme_id = nid
        save_viewport_theme_id(nid)
        sp = get_theme(nid)
        self.statusBar().showMessage(f"Tema: {sp.label} (T: siguiente)")
        self._redraw()
        self._apply_full_ui_theme()

    def _on_shortcut_cycle_viewport_theme(self) -> None:
        if self._workspace_stack.currentIndex() != self._IDX_WORKSPACE_3D:
            return
        self._cycle_viewport_theme()

    def _apply_viewport_background(self) -> None:
        """Fondo del visor 3D según el tema de color del visor (independiente del tema Qt)."""
        from cli.viewport_theme import apply_style_to_plotter_background

        apply_style_to_plotter_background(self._plotter, self._viewport_style_dict())

    def _apply_ftool_plotter_camera(self, prev_cam: Any) -> None:
        """
        Tras ``reset_camera``: el primer dibujo encuadra toda la estructura.
        Después se conserva la vista del usuario (antes restaurábamos la cámara
        previa al primer cuadro y se perdía el encuadre automático).
        """
        restore = bool(getattr(self, "_ftool_preserve_camera", False)) and prev_cam is not None
        if restore:
            try:
                self._plotter.camera_position = prev_cam
            except Exception:
                pass
        else:
            try:
                self._plotter.camera.zoom(0.9)
            except Exception:
                pass
        self._ftool_preserve_camera = True

    def _on_workspace_page_changed(self, index: int) -> None:
        """El panel derecho y la barra de herramientas permanecen visibles en 3D y en resultados."""
        dock = getattr(self, "_inspector_dock", None)
        if dock is not None:
            dock.show()
        if index == self._IDX_WORKSPACE_RESULTADOS:
            self._sync_resultados_sheet_nav()
            self._focus_resultados_table()

    def _update_status_summary(self) -> None:
        """Actualiza el resumen del modelo en la barra de estado inferior."""
        lbl = getattr(self, "_summary_status", None)
        if lbl is None:
            return
        spec = getattr(self, "_spec", {})
        nn = len(spec.get("nodes", []))
        nb = len(spec.get("bars", []))
        nc = len(spec.get("loads_point", [])) + len(spec.get("loads_distributed", [])) + len(spec.get("loads_nodal", []))
        nm = len(spec.get("materials", {}))
        solved = getattr(self, "_solved", False)
        vista_key = ""
        combo = getattr(self, "_combo_vista", None)
        if combo is not None:
            vista_key = str(combo.currentData() or "")
        escala = f"{getattr(self, '_escala_diagrama', 1.0):.2f}"
        estado = "Analizado" if solved else "Sin analizar"
        lbl.setText(
            f"  Nodos: {nn}  |  Barras: {nb}  |  Cargas: {nc}  |  Materiales: {nm}"
            f"  |  Vista: {vista_key}  |  Escala: {escala}  |  {estado}"
        )

    def _show_resultados_tab(self) -> None:
        self._set_workspace_page(self._IDX_WORKSPACE_RESULTADOS)

    def _shift_resultados_tab(self, step: int) -> None:
        tabs = self._tabs_resultados_sheets
        n = tabs.count()
        if n <= 0:
            return
        if n == 1 and tabs.tabText(0).strip() == "—":
            return
        i = tabs.currentIndex()
        if i < 0:
            i = 0
        j = max(0, min(n - 1, i + int(step)))
        if j != i:
            tabs.setCurrentIndex(j)

    def _focus_resultados_table(self) -> None:
        if self._workspace_stack.currentIndex() != self._IDX_WORKSPACE_RESULTADOS:
            return
        tw = self._tabs_resultados_sheets
        w = tw.currentWidget()
        if w is None:
            return
        if w.__class__.__name__ != "QTableWidget":
            return
        try:
            w.setFocus()
        except Exception:
            pass

    def _sync_resultados_sheet_nav(self) -> None:
        tabs = self._tabs_resultados_sheets
        combo = getattr(self, "_combo_resultados_sheet", None)
        lbl = getattr(self, "_lbl_resultados_sheet_pos", None)
        prev_b = getattr(self, "_btn_res_tab_prev", None)
        next_b = getattr(self, "_btn_res_tab_next", None)
        if combo is None or lbl is None:
            return
        n = tabs.count()
        placeholder = n == 1 and tabs.tabText(0).strip() == "—"
        if n <= 0 or placeholder:
            lbl.setText("")
            self._resultados_combo_updating = True
            try:
                combo.blockSignals(True)
                combo.clear()
            finally:
                combo.blockSignals(False)
                self._resultados_combo_updating = False
            for b in (prev_b, next_b):
                if b is not None:
                    b.setEnabled(False)
            combo.setEnabled(False)
            return
        ci = tabs.currentIndex()
        if ci < 0:
            ci = 0
        self._resultados_combo_updating = True
        try:
            combo.blockSignals(True)
            combo.clear()
            for i in range(n):
                combo.addItem(tabs.tabText(i))
            combo.setCurrentIndex(ci)
        finally:
            combo.blockSignals(False)
            self._resultados_combo_updating = False
        title = tabs.tabText(ci)
        lbl.setText(f"Hoja {ci + 1} de {n} — {title}")
        if prev_b is not None:
            prev_b.setEnabled(ci > 0)
        if next_b is not None:
            next_b.setEnabled(ci < n - 1)
        combo.setEnabled(n > 1)

    def _on_resultados_combo_sheet_changed(self, idx: int) -> None:
        if self._resultados_combo_updating or idx < 0:
            return
        tabs = self._tabs_resultados_sheets
        if tabs.currentIndex() != idx:
            tabs.setCurrentIndex(idx)

    def _on_resultados_sheet_tab_changed(self, _idx: int) -> None:
        self._sync_resultados_sheet_nav()
        self._focus_resultados_table()

    def _on_shortcut_resultados_sheet_prev(self) -> None:
        if self._workspace_stack.currentIndex() != self._IDX_WORKSPACE_RESULTADOS:
            return
        self._shift_resultados_tab(-1)

    def _on_shortcut_resultados_sheet_next(self) -> None:
        if self._workspace_stack.currentIndex() != self._IDX_WORKSPACE_RESULTADOS:
            return
        self._shift_resultados_tab(1)

    def _refresh_resultados_tables_ui(self) -> None:
        """Rellena las pestañas tipo Excel desde el último análisis."""
        if self._qt_backend == "PySide6":
            from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QVBoxLayout
        else:
            from PyQt5.QtWidgets import QAbstractItemView, QTableWidget, QVBoxLayout

        tabs = self._tabs_resultados_sheets
        tabs.blockSignals(True)
        tabs.clear()
        self._resultados_sheet_key_order = []
        try:
            dfs = self._get_resultados_dataframes()
            self._cached_resultados_dfs = dfs
            if dfs is None:
                w = self._QWidget()
                vl = QVBoxLayout(w)
                vl.setContentsMargins(12, 12, 12, 12)
                msg = self._QLabel(
                    "No hay resultados numéricos. Ejecutá Analizar con un modelo válido "
                    "para cargar las tablas (mismo contenido que el Excel de supertesteo)."
                )
                msg.setObjectName("mutedLabel")
                msg.setWordWrap(True)
                vl.addWidget(msg)
                tabs.addTab(w, "—")
                return

            from cli.resultados_export import RESULTADOS_SHEET_ORDER

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

            for key in RESULTADOS_SHEET_ORDER:
                if key not in dfs:
                    continue
                df = dfs[key]
                tbl = QTableWidget()
                tbl.setAlternatingRowColors(True)
                tbl.setSelectionBehavior(_sel_rows)
                tbl.setSelectionMode(_sel_single)
                tbl.setEditTriggers(_no_edit)
                tbl.setShowGrid(True)
                tbl.verticalHeader().setVisible(True)
                tbl.verticalHeader().setDefaultSectionSize(20)
                tbl.horizontalHeader().setStretchLastSection(True)
                tbl.horizontalHeader().setHighlightSections(False)
                self._populate_resultados_qtable(tbl, df, key)
                title = _RESULTADOS_TAB_TITLES.get(key, key.replace("_", " "))
                tabs.addTab(tbl, title)
                self._resultados_sheet_key_order.append(key)
        finally:
            tabs.blockSignals(False)
            self._sync_resultados_sheet_nav()

    def _populate_resultados_qtable(self, tbl: Any, df: Any, sheet_key: str = "") -> None:
        import pandas as pd

        tbl.clear()
        extra_group_row = 0
        tbl.setRowCount(len(df) + extra_group_row)
        tbl.setColumnCount(len(df.columns))
        tbl.setHorizontalHeaderLabels([str(c) for c in df.columns])
        TWI = self._QTableWidgetItem
        _qt = self._Qt
        if hasattr(_qt, "ItemFlag"):
            _ro = _qt.ItemFlag.ItemIsSelectable | _qt.ItemFlag.ItemIsEnabled
        else:
            _ro = _qt.ItemIsSelectable | _qt.ItemIsEnabled
        for r in range(len(df)):
            for c in range(len(df.columns)):
                val = df.iat[r, c]
                if pd.isna(val):
                    txt = ""
                elif isinstance(val, (float, np.floating)):
                    txt = f"{float(val):.6g}"
                elif isinstance(val, (int, np.integer)):
                    txt = str(int(val))
                else:
                    txt = str(val)
                it = TWI(txt)
                it.setFlags(_ro)
                tbl.setItem(r + extra_group_row, c, it)

    def _export_resultados_dialog(self) -> None:
        dfs = self._cached_resultados_dfs
        if dfs is None:
            dfs = self._get_resultados_dataframes()
        if dfs is None:
            self._QMessageBox.warning(self, "Exportar", "Ejecutá Analizar antes para generar resultados.")
            return
        self._cached_resultados_dfs = dfs

        path, selected_filter = self._QFileDialog.getSaveFileName(
            self,
            "Exportar resultados",
            str(_ROOT / "resultados.xlsx"),
            "Libro Excel (*.xlsx);;Informe PDF (*.pdf);;CSV — hoja visible (*.csv)",
        )
        if not path:
            return
        pth = Path(path)
        sel = (selected_filter or "").lower()
        if pth.suffix == "":
            if "pdf" in sel:
                pth = pth.with_suffix(".pdf")
            elif "csv" in sel:
                pth = pth.with_suffix(".csv")
            else:
                pth = pth.with_suffix(".xlsx")
        path = str(pth)
        low = path.lower()
        try:
            if low.endswith(".pdf"):
                from cli.resultados_export import write_resultados_pdf

                write_resultados_pdf(pth, dfs, titulo="Reticular — resultados")
            elif low.endswith(".csv"):
                idx = self._tabs_resultados_sheets.currentIndex()
                keys = self._resultados_sheet_key_order
                if idx < 0 or idx >= len(keys):
                    self._QMessageBox.warning(
                        self,
                        "Exportar CSV",
                        "Elegí una hoja con el selector «Hoja … de …» o el desplegable encima de la tabla.",
                    )
                    return
                k = keys[idx]
                sub = dfs.get(k)
                if sub is None:
                    return
                sub.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                if not low.endswith(".xlsx"):
                    path = str(pth.with_suffix(".xlsx"))
                    pth = Path(path)
                from cli.resultados_export import write_resultados_excel

                write_resultados_excel(pth, dfs)
            self.statusBar().showMessage(f"Exportado: {path}")
        except Exception as e:
            self._QMessageBox.critical(self, "Exportar", str(e))

    def _export_resultados_csv_folder(self) -> None:
        dfs = self._cached_resultados_dfs
        if dfs is None:
            dfs = self._get_resultados_dataframes()
        if dfs is None:
            self._QMessageBox.warning(self, "Exportar CSV", "Ejecutá Analizar antes para generar resultados.")
            return
        self._cached_resultados_dfs = dfs
        folder = self._QFileDialog.getExistingDirectory(self, "Carpeta para los CSV", str(_ROOT))
        if not folder:
            return
        try:
            from cli.resultados_export import export_sheets_to_csv_folder

            n = export_sheets_to_csv_folder(dfs, Path(folder))
            self.statusBar().showMessage(f"Exportados {n} archivos CSV en: {folder}")
        except Exception as e:
            self._QMessageBox.critical(self, "Exportar CSV", str(e))

    def _get_resultados_dataframes(self) -> Optional[Dict[str, Any]]:
        """DataFrames equivalentes al Excel de ``supertesteo`` (requiere análisis)."""
        if not self._solved or self._estructura is None:
            return None
        from cli.resultados_export import collect_resultados_dataframes

        F = self._F_internas
        if F is None:
            try:
                F = self._estructura.calcular_reacciones(debug=0)
                self._F_internas = F
            except Exception:
                return None
        try:
            return collect_resultados_dataframes(self._estructura, F)
        except Exception:
            return None

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
        esc = self._escala_actual()
        self._escala_diagrama = esc
        self._escala_deform   = esc
        self._lbl_escala.setText(f"{esc:.2f}")
        self._update_status_summary()
        key = self._combo_vista.currentData()
        if key in ("vy", "vz", "nx", "my", "mz", "mx", "def"):
            self._redraw()

    def _invalidate_solution(self) -> None:
        self._solved = False
        self._estructura = None
        self._F_internas = None
        self._ftool_preserve_camera = False
        self._cached_resultados_dfs = None
        self._refresh_resultados_tables_ui()

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

            loads_p = spec.get("loads_point") or []
            loads_d = spec.get("loads_distributed") or []
            loads_n = spec.get("loads_nodal") or []
            self._tbl_loads.setRowCount(0)
            self._tbl_loads.setColumnCount(5)
            self._tbl_loads.setHorizontalHeaderLabels(
                ["Nº", "Tipo", "Barra/Nodo", "Posición / Rango", "Fuerza / Intensidad"]
            )
            for _hci, _tip in (
                (3, "Punto (x,y,z) o rango inicio→fin (editar en ventana emergente)"),
                (4, "Fuerza puntual o intensidad por unidad de longitud (editar)"),
            ):
                _hh = self._tbl_loads.horizontalHeaderItem(_hci)
                if _hh is not None:
                    _hh.setToolTip(_tip)
            _row_n = 0
            for i, c in enumerate(loads_p):
                r = self._tbl_loads.rowCount()
                self._tbl_loads.insertRow(r)
                fg = c.get("force_global") or [c.get("Fx", 0), c.get("Fy", 0), c.get("Fz", 0)]
                fx, fy, fz = float(fg[0]), float(fg[1]), float(fg[2])
                coord = f"({c['x']},{c['y']},{c['z']})"
                fstr = f"({fx:g},{fy:g},{fz:g})"
                _row_n += 1
                vals = [str(_row_n), "Puntual", str(c.get("bar_id")), coord, fstr]
                for col, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("load", i))
                    self._tbl_loads.setItem(r, col, it)
            for i, c in enumerate(loads_d):
                r = self._tbl_loads.rowCount()
                self._tbl_loads.insertRow(r)
                fg = c.get("force_global") or [c.get("qx", 0), c.get("qy", 0), c.get("qz", 0)]
                qx, qy, qz = float(fg[0]), float(fg[1]), float(fg[2])
                xi = c.get("x", "?"); yi = c.get("y", "?"); zi = c.get("z", "?")
                xf = c.get("x_f", "?"); yf = c.get("y_f", "?"); zf = c.get("z_f", "?")
                rango = f"({xi},{yi},{zi})→({xf},{yf},{zf})"
                qstr = f"({qx:g},{qy:g},{qz:g})/u"
                _row_n += 1
                vals = [str(_row_n), "Distrib.", str(c.get("bar_id")), rango, qstr]
                for col, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("dist_load", i))
                    self._tbl_loads.setItem(r, col, it)
            for i, c in enumerate(loads_n):
                r = self._tbl_loads.rowCount()
                self._tbl_loads.insertRow(r)
                nid_val = c.get("node_id") or c.get("nodo_id", "?")
                fx = float(c.get("Fx", 0)); fy = float(c.get("Fy", 0)); fz = float(c.get("Fz", 0))
                mx = float(c.get("Mx", 0)); my = float(c.get("My", 0)); mz = float(c.get("Mz", 0))
                fstr_n = f"F({fx:g},{fy:g},{fz:g}) M({mx:g},{my:g},{mz:g})"
                _row_n += 1
                vals = [str(_row_n), "Nodal", f"nodo {nid_val}", "—", fstr_n]
                for col, txt in enumerate(vals):
                    it = TWI(txt)
                    it.setFlags(_ro)
                    it.setData(ur, ("nodal_load", i))
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
        self._update_status_summary()

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

    def _profile_polygon_yz_per_bar_from_spec(self) -> Dict[int, List[List[float]]]:
        out: Dict[int, List[List[float]]] = {}
        mats = self._spec.get("materials") or {}
        from cli.profile_polygon import normalize_polygon_yz

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
            poly = normalize_polygon_yz(m.get("profile_polygon_yz"))
            if poly:
                out[bid] = poly
        return out

    def _dlg_material_editor(self, edit_name: Optional[str]) -> None:
        """edit_name None = nuevo material."""
        from cli.loader import _resolve_material_stiffness

        mats = self._spec.setdefault("materials", {})
        D = self._QDialog(self)
        D.setWindowTitle("Editar material" if edit_name else "Nuevo material")
        D.setMinimumWidth(820)
        try:
            from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout
        except ImportError:
            from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout

        root_lay = QVBoxLayout(D)
        main_h = QHBoxLayout()
        left_w = self._QWidget()
        left_w.setMinimumWidth(340)
        form = self._QFormLayout(left_w)
        SW = self._QStackedWidget
        W = self._QWidget

        name_edit = self._QLineEdit()
        if edit_name:
            name_edit.setText(edit_name)
            name_edit.setReadOnly(True)
        form.addRow("Nombre (clave)", name_edit)

        existing = dict(mats.get(edit_name, {})) if edit_name else {}
        from cli.profile_polygon import normalize_polygon_yz as _norm_poly, polygon_area_yz as _poly_area

        _mp_load = _norm_poly(existing.get("profile_polygon_yz"))
        manual_poly_state: List[List[float]] = [list(p) for p in _mp_load] if _mp_load else []

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

        # --- página manual (solo propiedades; el dibujo va en el panel derecho) ---
        page_m = W()
        vm = QVBoxLayout(page_m)
        fw_man = W()
        fm = self._QFormLayout(fw_man)
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
        vm.addWidget(fw_man)
        vm.addStretch(0)

        stack.addWidget(page_p)
        stack.addWidget(page_m)
        try:
            stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        except AttributeError:
            stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        manual_draw_panel = None

        def _sync_mode(i: int) -> None:
            stack.setCurrentIndex(0 if i == 0 else 1)
            if manual_draw_panel is not None:
                manual_draw_panel.setVisible(i == 1)

        form.addRow(stack)

        manual_ax = None
        manual_canvas = None
        _ManFigCanvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _ManFigCanvas
        except ImportError:
            try:
                from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as _ManFigCanvas
            except ImportError:
                pass

        right_w = W()
        rv = QVBoxLayout(right_w)
        rv.setSpacing(8)
        lbl_prev_side = self._QLabel("Previsualización")
        lbl_prev_side.setObjectName("mutedLabel")
        rv.addWidget(lbl_prev_side)

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

            preview_fig = Figure(figsize=(4.2, 4.6), dpi=96)
            preview_canvas = _FigCanvas(preview_fig)
            preview_canvas.setMinimumWidth(300)
            preview_canvas.setMinimumHeight(260)
            preview_canvas.setMaximumHeight(420)
            preview_canvas.setSizePolicy(_QSP.Preferred, _QSP.Preferred)
            rv.addWidget(preview_canvas)
        except ImportError:
            pass

        manual_draw_panel = W()
        md_lay = QVBoxLayout(manual_draw_panel)
        lbl_draw = self._QLabel(
            "Dibujo de perfil (Y–Z, cm): clic izq. = vértice, clic der. = borrar último."
        )
        lbl_draw.setWordWrap(True)
        md_lay.addWidget(lbl_draw)

        if _ManFigCanvas is not None:
            from matplotlib.figure import Figure as _ManFigure

            _mfig = _ManFigure(figsize=(4.0, 3.6), dpi=96)
            manual_canvas = _ManFigCanvas(_mfig)
            manual_ax = _mfig.add_subplot(111)
            manual_canvas.setMinimumHeight(220)
            manual_canvas.setMaximumHeight(320)
            md_lay.addWidget(manual_canvas)

        row_man = QHBoxLayout()
        btn_poly_clear = QPushButton("Limpiar perfil")
        btn_poly_area = QPushButton("Estimar A desde polígono")
        row_man.addWidget(btn_poly_clear)
        row_man.addWidget(btn_poly_area)
        md_lay.addLayout(row_man)

        manual_draw_panel.setVisible(mode.currentIndex() == 1)
        rv.addWidget(manual_draw_panel)

        main_h.addWidget(left_w, stretch=52)
        main_h.addWidget(right_w, stretch=48)
        root_lay.addLayout(main_h)

        mode.currentIndexChanged.connect(_sync_mode)
        _sync_mode(mode.currentIndex())

        def _manual_axes_limits_yz(
            arr: np.ndarray,
        ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
            """
            Encuadre cuadrado en Y–Z con radio mínimo (cm) para que el primer clic
            no encoja la vista a pocos milímetros.
            """
            min_radius = 12.0
            margin = 1.08
            if arr.size == 0:
                return (-25.0, 25.0), (-25.0, 25.0)
            x0, x1 = float(np.min(arr[:, 0])), float(np.max(arr[:, 0]))
            y0, y1 = float(np.min(arr[:, 1])), float(np.max(arr[:, 1]))
            cx = 0.5 * (x0 + x1)
            cy = 0.5 * (y0 + y1)
            half_x = max(0.5 * (x1 - x0), min_radius)
            half_y = max(0.5 * (y1 - y0), min_radius)
            r = max(half_x, half_y) * margin
            return (cx - r, cx + r), (cy - r, cy + r)

        def redraw_manual_canvas() -> None:
            if manual_ax is None or manual_canvas is None:
                return
            manual_ax.clear()
            manual_ax.set_facecolor("#ececec")
            manual_ax.grid(True, linestyle=":", alpha=0.6)
            manual_ax.set_xlabel("Y local (cm)")
            manual_ax.set_ylabel("Z local (cm)")
            manual_ax.set_title("Dibujo de sección", fontsize=9, color="#2c3e50")
            if manual_poly_state:
                arr = np.asarray(manual_poly_state, dtype=float)
                if arr.shape[0] >= 1:
                    manual_ax.plot(
                        arr[:, 0], arr[:, 1], "o", color="#1b4f72", ms=7, zorder=3
                    )
                if arr.shape[0] >= 2:
                    manual_ax.plot(
                        arr[:, 0], arr[:, 1], "-", color="#1b4f72", lw=1.4, zorder=2
                    )
                if arr.shape[0] >= 3:
                    cl = np.vstack([arr, arr[:1]])
                    manual_ax.fill(cl[:, 0], cl[:, 1], alpha=0.35, color="#7fb3d5", zorder=1)
                xlim, ylim = _manual_axes_limits_yz(arr)
                manual_ax.set_xlim(xlim)
                manual_ax.set_ylim(ylim)
            else:
                manual_ax.set_xlim(-25, 25)
                manual_ax.set_ylim(-25, 25)
            manual_ax.set_aspect("equal", adjustable="box")
            manual_canvas.draw()

        def on_manual_canvas_click(event: Any) -> None:
            if manual_ax is None or getattr(event, "inaxes", None) != manual_ax:
                return
            if event.xdata is None or event.ydata is None:
                return
            if event.button == 1:
                manual_poly_state.append([float(event.xdata), float(event.ydata)])
            elif event.button == 3:
                if manual_poly_state:
                    manual_poly_state.pop()
            redraw_manual_canvas()
            _refresh_material_preview()

        def _clear_manual_poly() -> None:
            manual_poly_state.clear()
            redraw_manual_canvas()
            _refresh_material_preview()

        def _estimate_a_from_poly() -> None:
            a = _poly_area(manual_poly_state)
            if a > 1e-18:
                sA.setValue(a)

        btn_poly_clear.clicked.connect(_clear_manual_poly)
        btn_poly_area.clicked.connect(_estimate_a_from_poly)
        if manual_canvas is not None:
            manual_canvas.mpl_connect("button_press_event", on_manual_canvas_click)

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
                manual_polygon_yz=list(manual_poly_state)
                if mode.currentIndex() == 1
                else None,
            )
            preview_canvas.draw()

        if preview_canvas is not None:
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
                sA,
                sIy,
                sIz,
                sJ,
            )
            for _sp in _spin_refresh:
                _sp.valueChanged.connect(_refresh_material_preview)
            sec_type.currentIndexChanged.connect(_refresh_material_preview)
            mode.currentIndexChanged.connect(_refresh_material_preview)
            chk_viz_global.toggled.connect(_refresh_material_preview)
            _refresh_material_preview()
        redraw_manual_canvas()

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        root_lay.addWidget(bb)
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
            entry.pop("profile_polygon_yz", None)
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
            entry.pop("section", None)
            entry["A"] = sA.value()
            entry["I_y"] = sIy.value()
            entry["I_z"] = sIz.value()
            entry["J"] = sJ.value()
            Gv = sG.value()
            if Gv > 0:
                entry["G"] = Gv
            else:
                entry["nu"] = s_nu.value()
            pp_save = _norm_poly(manual_poly_state)
            if pp_save:
                entry["profile_polygon_yz"] = pp_save
            else:
                entry.pop("profile_polygon_yz", None)
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

        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
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
        it0 = self._tbl_loads.item(row, 0)
        if it0 is not None:
            role_data = it0.data(self._user_role)
            if role_data and role_data[0] == "dist_load":
                self._dlg_edit_distributed_load(role_data[1])
                return
        self._dlg_edit_load(row)

    def _export_viewport_png(self) -> None:
        """PNG fijo para informes (1920×1080); conserva la vista actual."""
        path, _ = self._QFileDialog.getSaveFileName(
            self,
            "Exportar vista PNG",
            str(_ROOT),
            "PNG (*.png)",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        w, h = 1920, 1080
        try:
            self._plotter.screenshot(path, return_img=False, window_size=(w, h))
            self.statusBar().showMessage(f"Vista exportada {w}×{h} px → {path}")
        except Exception as e:
            self._QMessageBox.warning(self, "Exportar PNG", str(e))

    def _cache_viz_highlight_params(self, bb: Any, nodos_dict: Dict[Any, Any], hr: float) -> None:
        """Copia de barras/nodos y radio para actualizar solo el tubo naranja sin redibujar todo."""
        self._viz_bb = bb
        self._viz_nodos_dict = nodos_dict
        self._viz_hr = float(hr)

    def _update_bar_highlight_only(self) -> None:
        """Quita y vuelve a dibujar el actor ``ftool_bar_highlight`` sin ``plotter.clear()``."""
        from plot.pyvista_pestanas import add_ftool_bar_selection_highlight

        bb = self._viz_bb
        nod = self._viz_nodos_dict
        hr = self._viz_hr
        if bb is None or nod is None or hr is None:
            self._redraw()
            return
        try:
            self._plotter.remove_actor("ftool_bar_highlight", reset_camera=False, render=False)
        except Exception:
            pass
        add_ftool_bar_selection_highlight(self._plotter, bb, nod, self._selected_bar_id, hr)
        try:
            self._plotter.render()
        except Exception:
            pass

    def eventFilter(self, watched: Any, event: Any) -> bool:
        """Suprimir en la vista 3D: VTK a veces no deja que el QShortcut de la ventana reciba la tecla."""
        iv = getattr(getattr(self, "_plotter", None), "interactor", None)
        if iv is None or watched is not iv:
            return False
        if self._qt_backend == "PySide6":
            from PySide6.QtCore import QEvent

            _kp = QEvent.Type.KeyPress
        else:
            from PyQt5.QtCore import QEvent

            _kp = QEvent.KeyPress
        if event.type() != _kp:
            return False
        if event.key() == self._Qt.Key_Delete:
            self._on_delete_selection()
            return True
        return False

    def _on_escape_deselect_bar(self) -> None:
        if self._selected_bar_id is None:
            return
        self._clear_bar_selection()

    def _clear_bar_selection(self) -> None:
        """Quita el resaltado 3D y la selección en la tabla Barras."""
        prev = self._selected_bar_id
        self._tbl_bars.blockSignals(True)
        try:
            self._selected_bar_id = None
            self._tbl_bars.clearSelection()
        finally:
            self._tbl_bars.blockSignals(False)
        if prev is not None:
            self._update_bar_highlight_only()

    def _on_bars_table_selection_changed(self) -> None:
        sm = self._tbl_bars.selectionModel()
        if sm is None:
            return
        rows = sm.selectedRows()
        bid: Optional[int] = None
        if rows:
            it = self._tbl_bars.item(rows[0].row(), 0)
            if it is not None:
                try:
                    bid = int(it.text())
                except ValueError:
                    bid = None
        if bid == self._selected_bar_id:
            return
        self._selected_bar_id = bid
        self._update_bar_highlight_only()

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
            add_ftool_bar_selection_highlight,
            add_ftool_viewport_legend,
            ftool_selection_highlight_radius,
        )

        key = self._combo_vista.currentData()
        esc = self._escala_actual()
        prev_cam = None
        if getattr(self, "_ftool_preserve_camera", False):
            try:
                prev_cam = self._plotter.camera_position
            except Exception:
                pass
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
        profile_bar = self._profile_polygon_yz_per_bar_from_spec()
        vp_style = self._viewport_style_dict()

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
                profile_polygon_yz_per_bar_id=profile_bar,
                viewport_style=vp_style,
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
                profile_polygon_yz_per_bar_id=profile_bar,
                viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
                )
                add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
                did_overlay = True
                _finish_plotter(self._plotter)
                self._apply_ftool_plotter_camera(prev_cam)
                self._apply_viewport_background()
                hr0 = ftool_selection_highlight_radius(
                    bb,
                    nodos_dict,
                    self._ipn_dims,
                    1.0,
                    ipn_dims_per_bar_id=per_bar,
                    tube_outer_radius_per_bar_id=tube_bar,
                    profile_polygon_yz_per_bar_id=profile_bar,
                )
                add_ftool_viewport_legend(self._plotter, key, esc)
                add_ftool_bar_selection_highlight(
                    self._plotter, bb, nodos_dict, self._selected_bar_id, hr0
                )
                self._cache_viz_highlight_params(bb, nodos_dict, hr0)
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
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
                    profile_polygon_yz_per_bar_id=profile_bar,
                    viewport_style=vp_style,
                )
            add_nodos_overlay_pyvista(self._plotter, list(nb), self._ipn_dims, 1.0)
            did_overlay = True
        _finish_plotter(self._plotter)
        self._apply_ftool_plotter_camera(prev_cam)
        self._apply_viewport_background()
        hr = ftool_selection_highlight_radius(
            bb,
            nodos_dict,
            self._ipn_dims,
            1.0,
            ipn_dims_per_bar_id=per_bar,
            tube_outer_radius_per_bar_id=tube_bar,
            profile_polygon_yz_per_bar_id=profile_bar,
        )
        add_ftool_viewport_legend(self._plotter, key, esc)
        add_ftool_bar_selection_highlight(
            self._plotter, bb, nodos_dict, self._selected_bar_id, hr
        )
        self._cache_viz_highlight_params(bb, nodos_dict, hr)
        self._legend_status.setText(NODOS_LEGEND_STATUS if did_overlay else "")
        self.statusBar().showMessage("OK")

    def _on_analyze(self) -> None:
        Qt = self._Qt
        if self._qt_backend == "PySide6":
            from PySide6.QtWidgets import QApplication, QProgressDialog
        else:
            from PyQt5.QtWidgets import QApplication, QProgressDialog

        prog = QProgressDialog(self)
        prog.setWindowTitle("Análisis estructural")
        try:
            _ic = self.windowIcon()
            if _ic is not None and not _ic.isNull():
                prog.setWindowIcon(_ic)
        except Exception:
            pass
        prog.setLabelText("Preparando…")
        prog.setRange(0, 100)
        prog.setValue(0)
        prog.setMinimumDuration(0)
        try:
            prog.setCancelButton(None)
        except Exception:
            pass
        try:
            prog.setWindowModality(Qt.WindowModality.ApplicationModal)
        except AttributeError:
            prog.setWindowModality(Qt.ApplicationModal)
        prog.show()
        QApplication.processEvents()

        est: Optional[Estructura] = None
        try:
            prog.setLabelText("Armando estructura desde el modelo…")
            prog.setValue(18)
            QApplication.processEvents()
            est = build_estructura_from_spec(self._spec)

            prog.setLabelText("Resolviendo sistema de ecuaciones…")
            prog.setValue(48)
            QApplication.processEvents()
            self._F_internas = solve_estructura(est)

            prog.setLabelText("Actualizando tablas y vista 3D…")
            prog.setValue(78)
            QApplication.processEvents()
        except Exception as e:
            self._QMessageBox.critical(self, "Analisis", str(e))
            return
        finally:
            try:
                prog.setValue(100)
            except Exception:
                pass
            prog.close()

        self._estructura = est
        self._solved = True
        self._refresh_resultados_tables_ui()
        self._update_status_summary()
        self.statusBar().showMessage("Análisis completado. Elegí una vista de esfuerzos o deformada.")
        self._redraw()

    def _new_project(self) -> None:
        self._spec = _default_spec()
        self._reset_history()
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
            self._spec.setdefault("loads_distributed", [])
            self._spec.setdefault("loads_nodal", [])
        except Exception as e:
            self._QMessageBox.critical(self, "Error", str(e))
            return
        self._reset_history()
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
        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
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
        self._push_undo_snapshot()
        c["bar_id"] = int(cb_bar.currentData())
        c["x"] = sx.value()
        c["y"] = sy.value()
        c["z"] = sz.value()
        c["force_global"] = [sfx.value(), sfy.value(), sfz.value()]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_add_distributed_load(self) -> None:
        bids = [b["id"] for b in self._spec["bars"]]
        if not bids:
            self._QMessageBox.warning(self, "Carga distribuida", "Agregá al menos una barra.")
            return
        d = self._QDialog(self)
        d.setWindowTitle("Carga distribuida uniforme global")
        form = self._QFormLayout(d)
        cb_bar = self._QComboBox()
        for bid in bids:
            cb_bar.addItem(str(bid), bid)

        def _make_sb(lo=-1e6, hi=1e6, val=0.0):
            sb = self._QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            return sb

        sxi = _make_sb(); syi = _make_sb(); szi = _make_sb()
        sxf = _make_sb(); syf = _make_sb(); szf = _make_sb()
        sqx = _make_sb(-1e9, 1e9); sqy = _make_sb(-1e9, 1e9); sqz = _make_sb(-1e9, 1e9)

        form.addRow("Barra", cb_bar)
        form.addRow(self._QLabel("— Inicio del tramo cargado (global) —"))
        form.addRow("xi (cm)", sxi); form.addRow("yi (cm)", syi); form.addRow("zi (cm)", szi)
        form.addRow(self._QLabel("— Fin del tramo cargado (global) —"))
        form.addRow("xf (cm)", sxf); form.addRow("yf (cm)", syf); form.addRow("zf (cm)", szf)
        form.addRow(self._QLabel("— Intensidad por unidad de longitud (global) —"))
        form.addRow("qx (kN/cm)", sqx); form.addRow("qy (kN/cm)", sqy); form.addRow("qz (kN/cm)", sqz)

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        self._push_undo_snapshot()
        self._spec.setdefault("loads_distributed", []).append(
            {
                "id": len(self._spec.get("loads_distributed") or []) + 1,
                "bar_id": cb_bar.currentData(),
                "x": sxi.value(), "y": syi.value(), "z": szi.value(),
                "x_f": sxf.value(), "y_f": syf.value(), "z_f": szf.value(),
                "force_global": [sqx.value(), sqy.value(), sqz.value()],
            }
        )
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_edit_distributed_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_distributed", [])
        if index < 0 or index >= len(loads):
            return
        c = loads[index]
        bids = [b["id"] for b in self._spec["bars"]]
        if not bids:
            self._QMessageBox.warning(self, "Carga distribuida", "Agregá al menos una barra.")
            return
        d = self._QDialog(self)
        d.setWindowTitle(f"Editar carga distribuida ({index + 1})")
        form = self._QFormLayout(d)
        cb_bar = self._QComboBox()
        for bid in bids:
            cb_bar.addItem(str(bid), bid)
        cur_b = int(c.get("bar_id", bids[0]))
        ix = cb_bar.findData(cur_b)
        if ix >= 0:
            cb_bar.setCurrentIndex(ix)

        def _make_sb(lo=-1e6, hi=1e6, val=0.0):
            sb = self._QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            return sb

        sxi = _make_sb(val=float(c.get("x", 0)))
        syi = _make_sb(val=float(c.get("y", 0)))
        szi = _make_sb(val=float(c.get("z", 0)))
        sxf = _make_sb(val=float(c.get("x_f", 0)))
        syf = _make_sb(val=float(c.get("y_f", 0)))
        szf = _make_sb(val=float(c.get("z_f", 0)))
        fg = c.get("force_global") or [c.get("qx", 0), c.get("qy", 0), c.get("qz", 0)]
        sqx = _make_sb(-1e9, 1e9, float(fg[0]))
        sqy = _make_sb(-1e9, 1e9, float(fg[1]))
        sqz = _make_sb(-1e9, 1e9, float(fg[2]))

        form.addRow("Barra", cb_bar)
        form.addRow(self._QLabel("— Inicio del tramo cargado (global) —"))
        form.addRow("xi (cm)", sxi); form.addRow("yi (cm)", syi); form.addRow("zi (cm)", szi)
        form.addRow(self._QLabel("— Fin del tramo cargado (global) —"))
        form.addRow("xf (cm)", sxf); form.addRow("yf (cm)", syf); form.addRow("zf (cm)", szf)
        form.addRow(self._QLabel("— Intensidad por unidad de longitud (global) —"))
        form.addRow("qx (kN/cm)", sqx); form.addRow("qy (kN/cm)", sqy); form.addRow("qz (kN/cm)", sqz)

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        self._push_undo_snapshot()
        c["bar_id"] = int(cb_bar.currentData())
        c["x"] = sxi.value(); c["y"] = syi.value(); c["z"] = szi.value()
        c["x_f"] = sxf.value(); c["y_f"] = syf.value(); c["z_f"] = szf.value()
        c["force_global"] = [sqx.value(), sqy.value(), sqz.value()]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_add_nodal_load(self) -> None:
        nids = [n["id"] for n in self._spec["nodes"]]
        if not nids:
            self._QMessageBox.warning(self, "Carga nodal", "Agregá al menos un nodo.")
            return
        d = self._QDialog(self)
        d.setWindowTitle("Carga nodal (fuerzas y momentos en nodo)")
        form = self._QFormLayout(d)
        cb_nodo = self._QComboBox()
        for nid in nids:
            cb_nodo.addItem(str(nid), nid)

        def _make_sb(lo=-1e9, hi=1e9, val=0.0):
            sb = self._QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            return sb

        sfx = _make_sb(); sfy = _make_sb(); sfz = _make_sb()
        smx = _make_sb(); smy = _make_sb(); smz = _make_sb()

        form.addRow("Nodo", cb_nodo)
        form.addRow(self._QLabel("— Fuerzas globales (kN) —"))
        form.addRow("Fx", sfx); form.addRow("Fy", sfy); form.addRow("Fz", sfz)
        form.addRow(self._QLabel("— Momentos globales (kN·cm) —"))
        form.addRow("Mx", smx); form.addRow("My", smy); form.addRow("Mz", smz)

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        self._push_undo_snapshot()
        self._spec.setdefault("loads_nodal", []).append(
            {
                "id": len(self._spec.get("loads_nodal") or []) + 1,
                "node_id": cb_nodo.currentData(),
                "Fx": sfx.value(), "Fy": sfy.value(), "Fz": sfz.value(),
                "Mx": smx.value(), "My": smy.value(), "Mz": smz.value(),
            }
        )
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _dlg_edit_nodal_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_nodal", [])
        if index < 0 or index >= len(loads):
            return
        c = loads[index]
        nids = [n["id"] for n in self._spec["nodes"]]
        if not nids:
            self._QMessageBox.warning(self, "Carga nodal", "Agregá al menos un nodo.")
            return
        d = self._QDialog(self)
        d.setWindowTitle(f"Editar carga nodal ({index + 1})")
        form = self._QFormLayout(d)
        cb_nodo = self._QComboBox()
        for nid in nids:
            cb_nodo.addItem(str(nid), nid)
        cur_n = int(c.get("node_id", nids[0]))
        ix = cb_nodo.findData(cur_n)
        if ix >= 0:
            cb_nodo.setCurrentIndex(ix)

        def _make_sb(lo=-1e9, hi=1e9, val=0.0):
            sb = self._QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setValue(val)
            return sb

        sfx = _make_sb(val=float(c.get("Fx", 0)))
        sfy = _make_sb(val=float(c.get("Fy", 0)))
        sfz = _make_sb(val=float(c.get("Fz", 0)))
        smx = _make_sb(val=float(c.get("Mx", 0)))
        smy = _make_sb(val=float(c.get("My", 0)))
        smz = _make_sb(val=float(c.get("Mz", 0)))

        form.addRow("Nodo", cb_nodo)
        form.addRow(self._QLabel("— Fuerzas globales (kN) —"))
        form.addRow("Fx", sfx); form.addRow("Fy", sfy); form.addRow("Fz", sfz)
        form.addRow(self._QLabel("— Momentos globales (kN·cm) —"))
        form.addRow("Mx", smx); form.addRow("My", smy); form.addRow("Mz", smz)

        DBB = self._QDialogButtonBox
        bb = DBB(DBB.StandardButton.Ok | DBB.StandardButton.Cancel)
        form.addRow(bb)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        if self._dialog_accepted(d) is False:
            return
        self._push_undo_snapshot()
        c["node_id"] = int(cb_nodo.currentData())
        c["Fx"] = sfx.value(); c["Fy"] = sfy.value(); c["Fz"] = sfz.value()
        c["Mx"] = smx.value(); c["My"] = smy.value(); c["Mz"] = smz.value()
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
            it = self._tbl_loads.item(row, 0)
            if it is not None:
                role_data = it.data(self._user_role)
                if role_data and role_data[0] == "dist_load":
                    self._dlg_edit_distributed_load(role_data[1])
                elif role_data and role_data[0] == "nodal_load":
                    self._dlg_edit_nodal_load(role_data[1])
                else:
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
        elif kind == "dist_load":
            self._delete_dist_load(int(ident))
        elif kind == "nodal_load":
            self._delete_nodal_load(int(ident))
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
        self._push_undo_snapshot()
        self._spec["loads_point"] = [
            c for c in self._spec.get("loads_point") or [] if c.get("bar_id") not in bars_drop
        ]
        self._spec["loads_distributed"] = [
            c for c in self._spec.get("loads_distributed") or [] if c.get("bar_id") not in bars_drop
        ]
        self._spec["loads_nodal"] = [
            c for c in self._spec.get("loads_nodal") or [] if int(c.get("node_id", -1)) != nid
        ]
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] not in bars_drop]
        self._spec["nodes"] = [n for n in self._spec["nodes"] if n["id"] != nid]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_bar(self, bid: int) -> None:
        self._push_undo_snapshot()
        self._spec["loads_point"] = [
            c for c in self._spec.get("loads_point") or [] if c.get("bar_id") != bid
        ]
        self._spec["loads_distributed"] = [
            c for c in self._spec.get("loads_distributed") or [] if c.get("bar_id") != bid
        ]
        self._spec["bars"] = [b for b in self._spec["bars"] if b["id"] != bid]
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_point", [])
        if 0 <= index < len(loads):
            self._push_undo_snapshot()
            loads.pop(index)
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_dist_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_distributed", [])
        if 0 <= index < len(loads):
            self._push_undo_snapshot()
            loads.pop(index)
        self._invalidate_solution()
        self._refresh_tree()
        self._redraw()

    def _delete_nodal_load(self, index: int) -> None:
        loads = self._spec.setdefault("loads_nodal", [])
        if 0 <= index < len(loads):
            self._push_undo_snapshot()
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

    from cli.gui_icons import ftool_app_window_icon

    _app_icon = ftool_app_window_icon()
    app.setWindowIcon(_app_icon)
    try:
        app.setApplicationDisplayName("Reticular")
    except Exception:
        pass

    if backend == "PySide6":
        from PySide6.QtWidgets import QProgressBar
    else:
        from PyQt5.QtWidgets import QProgressBar

    from cli.viewport_theme import load_viewport_theme_id
    from cli.qt_app_theme import get_app_color_tokens, splash_stylesheets

    _sp_tok = get_app_color_tokens(load_viewport_theme_id())
    _sp_dlg, _sp_title, _sp_msg = splash_stylesheets(_sp_tok)

    _splash = QDialog()
    _splash.setObjectName("reticularSplash")
    _splash.setStyleSheet(_sp_dlg)
    _splash.setWindowIcon(_app_icon)
    _splash.setWindowTitle("Reticular")
    _TS = getattr(Qt, "WindowType", Qt)
    _sp_flag = getattr(_TS, "SplashScreen", Qt.SplashScreen)
    _fr_flag = getattr(_TS, "FramelessWindowHint", Qt.FramelessWindowHint)
    _top_flag = getattr(_TS, "WindowStaysOnTopHint", Qt.WindowStaysOnTopHint)
    _splash.setWindowFlags(_sp_flag | _fr_flag | _top_flag)
    _sl = QVBoxLayout(_splash)
    _sl.setContentsMargins(22, 18, 22, 18)
    _sl.setSpacing(10)
    _lbl_title = QLabel("Reticular")
    _lbl_title.setStyleSheet(f"font-weight: 600; font-size: 15pt; {_sp_title}")
    _lbl_msg = QLabel("Cargando…")
    _lbl_msg.setStyleSheet(_sp_msg)
    _bar = QProgressBar()
    _bar.setRange(0, 100)
    _bar.setValue(0)
    _bar.setTextVisible(True)
    _sl.addWidget(_lbl_title)
    _sl.addWidget(_lbl_msg)
    _sl.addWidget(_bar)
    _splash.setLayout(_sl)
    _splash.setFixedSize(400, 138)
    _splash.show()
    QApplication.processEvents()
    _ps = app.primaryScreen()
    if _ps is not None:
        _fg = _splash.frameGeometry()
        _fg.moveCenter(_ps.availableGeometry().center())
        _splash.move(_fg.topLeft())

    def _startup_tick_ui(pct: int, text: str) -> None:
        _bar.setValue(pct)
        _lbl_msg.setText(text)
        QApplication.processEvents()

    _startup_tick_ui(2, "Iniciando…")
    try:
        w = FtoolMainWindow(
            backend,
            qt,
            precargar_ejemplo=precargar_ejemplo,
            startup_progress=_startup_tick_ui,
        )
    finally:
        _splash.close()
        QApplication.processEvents()

    w.setWindowIcon(_app_icon)
    w.show()
    app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    run_ftool_gui()
