"""
Tema Qt global alineado a los mismos theme_id que el visor 3D (regla 60-30-10).

Roles:
  dominant_60 / surface_* → ~60% superficies principales
  chrome_* / tab_inactive_* / dock_* → ~30% cromado secundario
  accent_* / selection_* / slider_handle → ~10% acento y foco
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AppColorTokens:
    """Tokens hex para QSS. Comentarios indican la regla 60-30-10 aproximada."""

    # --- 60%: ventana y superficies grandes ---
    win_bg: str
    win_fg: str
    surface: str
    surface_alt: str
    msgbox_bg: str
    msgbox_fg: str
    tooltip_bg: str
    tooltip_fg: str
    tooltip_border: str
    # --- 30%: barras, docks, pestañas inactivas, paneles ---
    toolbar_bg: str
    toolbar_border_bottom: str
    toolbar_sep: str
    left_panel_bg: str
    left_panel_border: str
    dock_border: str
    dock_title_bg: str
    dock_title_fg: str
    dock_title_border_bottom: str
    dock_bar_bg: str
    dock_bar_border_bottom: str
    dock_lbl: str
    tab_pane_border: str
    tab_pane_bg: str
    tab_inactive_bg: str
    tab_inactive_fg: str
    tab_inactive_border: str
    tab_hover_bg: str
    menubar_bg: str
    menubar_fg: str
    menubar_border_bottom: str
    menubar_item_selected: str
    menu_border: str
    menu_separator: str
    groove: str
    model_footer_bg: str
    model_footer_border: str
    mini_del_bg: str
    mini_del_fg: str
    mini_del_border: str
    mini_del_hover_bg: str
    mini_del_hover_border: str
    mini_del_pressed: str
    # --- 10%: acento, selección, CTA ---
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_border: str
    accent_soft: str
    accent_soft_border: str
    selection_bg: str
    selection_fg: str
    slider_handle: str
    slider_subpage: str
    tab_selected_bg: str
    tab_selected_fg: str
    tab_selected_border: str
    tab_selected_bottom: str
    mini_add_bg: str
    mini_add_fg: str
    mini_add_border: str
    mini_add_hover_bg: str
    mini_add_hover_border: str
    mini_add_pressed: str
    analyze_bg: str
    analyze_fg: str
    analyze_border: str
    analyze_hover: str
    analyze_pressed: str
    analyze_hover_border: str
    # --- Texto / inputs ---
    text_muted: str
    combo_bg: str
    combo_fg: str
    combo_border: str
    combo_hover_border: str
    combo_popup_bg: str
    combo_popup_fg: str
    combo_popup_border: str
    combo_item_hover_bg: str
    table_bg: str
    table_fg: str
    grid: str
    table_border: str
    header_bg: str
    header_fg: str
    header_border: str
    menu_bg: str
    menu_fg: str
    menu_sel_bg: str
    menu_sel_fg: str
    push_bg: str
    push_fg: str
    push_border: str
    push_hover_bg: str
    push_hover_border: str
    push_pressed: str
    # --- Barra de estado ---
    status_bg: str
    status_fg: str
    status_border_top: str
    status_legend: str
    status_summary: str
    # --- Otros ---
    danger_hover_bg: str
    danger_hover_border: str
    tool_hover_bg: str
    tool_hover_border: str
    tool_pressed: str
    ws_checked_bg: str
    ws_checked_border: str


def get_app_color_tokens(theme_id: str) -> AppColorTokens:
    tid = str(theme_id).strip().lower()
    return _TOKENS.get(tid, _TOKENS["dark"])


# Curado por tema: familia cromática alineada al visor (viewport_theme.py).
_TOKENS: Dict[str, AppColorTokens] = {
    "dark": AppColorTokens(
        win_bg="#2d2d30",
        win_fg="#e8e9eb",
        surface="#2d2d30",
        surface_alt="#323236",
        msgbox_bg="#3a3a3e",
        msgbox_fg="#ececec",
        tooltip_bg="#3a3a3e",
        tooltip_fg="#ececec",
        tooltip_border="#5a5a60",
        toolbar_bg="#3c3c40",
        toolbar_border_bottom="#1e1e20",
        toolbar_sep="#555558",
        left_panel_bg="#38383c",
        left_panel_border="#4a4a50",
        dock_border="#4a4a50",
        dock_title_bg="#313841",
        dock_title_fg="#e6ebf2",
        dock_title_border_bottom="#4f5b67",
        dock_bar_bg="#313841",
        dock_bar_border_bottom="#4f5b67",
        dock_lbl="#e6ebf2",
        tab_pane_border="#4a4a50",
        tab_pane_bg="#2d2d30",
        tab_inactive_bg="#40444b",
        tab_inactive_fg="#d2d8e2",
        tab_inactive_border="#4a4a50",
        tab_hover_bg="#4a4f57",
        menubar_bg="#2d2d30",
        menubar_fg="#e8e9eb",
        menubar_border_bottom="#3f3f42",
        menubar_item_selected="#3a3a3e",
        menu_border="#5a5a60",
        menu_separator="#5a5a60",
        groove="#2a2a2d",
        model_footer_bg="#30353d",
        model_footer_border="#4b5560",
        mini_del_bg="#3a4149",
        mini_del_fg="#c5d1de",
        mini_del_border="#616d79",
        mini_del_hover_bg="#444c55",
        mini_del_hover_border="#758392",
        mini_del_pressed="#343b43",
        accent="#7ea6d1",
        accent_hover="#93b8dc",
        accent_pressed="#5e8ab8",
        accent_border="#5a7aa0",
        accent_soft="#4a5568",
        accent_soft_border="#6a7a90",
        selection_bg="#4a5568",
        selection_fg="#f2f3f5",
        slider_handle="#7ea6d1",
        slider_subpage="#5a6570",
        tab_selected_bg="#2d2d30",
        tab_selected_fg="#f2f4f8",
        tab_selected_border="#4a4a50",
        tab_selected_bottom="#7ea6d1",
        mini_add_bg="#30465f",
        mini_add_fg="#9cc4ee",
        mini_add_border="#54759b",
        mini_add_hover_bg="#395273",
        mini_add_hover_border="#6c8fb7",
        mini_add_pressed="#2a3e57",
        analyze_bg="#2d6a45",
        analyze_fg="#f0fff4",
        analyze_border="#3a8a55",
        analyze_hover="#358a52",
        analyze_pressed="#255535",
        analyze_hover_border="#4a9a66",
        text_muted="#9d9fa3",
        combo_bg="#3a3a3e",
        combo_fg="#e8e9eb",
        combo_border="#4e4e52",
        combo_hover_border="#606068",
        combo_popup_bg="#3a3a3e",
        combo_popup_fg="#ececec",
        combo_popup_border="#5a5a60",
        combo_item_hover_bg="#4a5568",
        table_bg="#2d2d30",
        table_fg="#e0e1e5",
        grid="#3f3f44",
        table_border="#3f3f42",
        header_bg="#454a52",
        header_fg="#f0f3f8",
        header_border="#3f3f42",
        menu_bg="#3a3a3e",
        menu_fg="#ececec",
        menu_sel_bg="#4a5568",
        menu_sel_fg="#ffffff",
        push_bg="#3a3a3e",
        push_fg="#e8e9eb",
        push_border="#4e4e52",
        push_hover_bg="#45454a",
        push_hover_border="#606068",
        push_pressed="#323236",
        status_bg="#252528",
        status_fg="#c8c8cc",
        status_border_top="#3f3f42",
        status_legend="#9a9da4",
        status_summary="#d0d0d4",
        danger_hover_bg="#4a3030",
        danger_hover_border="#804040",
        tool_hover_bg="#45454a",
        tool_hover_border="#606068",
        tool_pressed="#353539",
        ws_checked_bg="#4a5568",
        ws_checked_border="#6a7a90",
    ),
    "light": AppColorTokens(
        win_bg="#f0f0f0",
        win_fg="#2c2c2c",
        surface="#ffffff",
        surface_alt="#f4f8fd",
        msgbox_bg="#ffffff",
        msgbox_fg="#1a1a1a",
        tooltip_bg="#fffff0",
        tooltip_fg="#1a1a1a",
        tooltip_border="#c8c8c8",
        toolbar_bg="#e8e8e8",
        toolbar_border_bottom="#d0d0d0",
        toolbar_sep="#c0c0c0",
        left_panel_bg="#e0e0e0",
        left_panel_border="#c8c8c8",
        dock_border="#d0d8e0",
        dock_title_bg="#cfd9e6",
        dock_title_fg="#12263d",
        dock_title_border_bottom="#b3c2d2",
        dock_bar_bg="#cfd9e6",
        dock_bar_border_bottom="#b3c2d2",
        dock_lbl="#12263d",
        tab_pane_border="#d4dae3",
        tab_pane_bg="#ffffff",
        tab_inactive_bg="#d8e0ea",
        tab_inactive_fg="#25364d",
        tab_inactive_border="#b9c5d3",
        tab_hover_bg="#c9d8ea",
        menubar_bg="#ebebeb",
        menubar_fg="#2c2c2c",
        menubar_border_bottom="#d0d0d0",
        menubar_item_selected="#d8e8f8",
        menu_border="#c8ccd4",
        menu_separator="#d8dde5",
        groove="#d0d0d0",
        model_footer_bg="#edf2f8",
        model_footer_border="#c7d2df",
        mini_del_bg="#eef1f5",
        mini_del_fg="#4a5a70",
        mini_del_border="#b7c2cf",
        mini_del_hover_bg="#e1e6ed",
        mini_del_hover_border="#9ba9ba",
        mini_del_pressed="#d4dce6",
        accent="#1a6fc4",
        accent_hover="#2280d8",
        accent_pressed="#145eb0",
        accent_border="#1460aa",
        accent_soft="#cce0f8",
        accent_soft_border="#6a9fd0",
        selection_bg="#cce0f8",
        selection_fg="#102040",
        slider_handle="#1a6fc4",
        slider_subpage="#80b4e8",
        tab_selected_bg="#ffffff",
        tab_selected_fg="#115ca8",
        tab_selected_border="#d4dae3",
        tab_selected_bottom="#115ca8",
        mini_add_bg="#dbe9f8",
        mini_add_fg="#124e90",
        mini_add_border="#8eb0d4",
        mini_add_hover_bg="#cee1f6",
        mini_add_hover_border="#6c96c5",
        mini_add_pressed="#bdd4ef",
        analyze_bg="#1a6fc4",
        analyze_fg="#ffffff",
        analyze_border="#1460aa",
        analyze_hover="#2280d8",
        analyze_pressed="#145eb0",
        analyze_hover_border="#0f58a0",
        text_muted="#6a6a6a",
        combo_bg="#ffffff",
        combo_fg="#1a1a1a",
        combo_border="#b8c0cc",
        combo_hover_border="#90b8e0",
        combo_popup_bg="#ffffff",
        combo_popup_fg="#1a1a1a",
        combo_popup_border="#c8ccd4",
        combo_item_hover_bg="#e8f2fc",
        table_bg="#ffffff",
        table_fg="#2c2c2c",
        grid="#e0e8f0",
        table_border="#d0d8e0",
        header_bg="#d7e0eb",
        header_fg="#1f2f45",
        header_border="#c2ccd9",
        menu_bg="#ffffff",
        menu_fg="#1a1a1a",
        menu_sel_bg="#cce0f8",
        menu_sel_fg="#102040",
        push_bg="#ffffff",
        push_fg="#2c2c2c",
        push_border="#c0c8d0",
        push_hover_bg="#d8e8f8",
        push_hover_border="#90b8e0",
        push_pressed="#c0d8f0",
        status_bg="#1a6fc4",
        status_fg="#ffffff",
        status_border_top="#145eaa",
        status_legend="rgba(255,255,255,0.85)",
        status_summary="#ffffff",
        danger_hover_bg="#fce8e8",
        danger_hover_border="#e0a0a0",
        tool_hover_bg="#d0e4f8",
        tool_hover_border="#90c0e8",
        tool_pressed="#b8d8f8",
        ws_checked_bg="#cce0f8",
        ws_checked_border="#6a9fd0",
    ),
    "red_white": AppColorTokens(
        win_bg="#3d0f0f",
        win_fg="#f5f0f0",
        surface="#4a1212",
        surface_alt="#5c1818",
        msgbox_bg="#5c1818",
        msgbox_fg="#fdfdfd",
        tooltip_bg="#4a1212",
        tooltip_fg="#fdfdfd",
        tooltip_border="#8b3a3a",
        toolbar_bg="#451010",
        toolbar_border_bottom="#2a0808",
        toolbar_sep="#6b2828",
        left_panel_bg="#401010",
        left_panel_border="#6b2828",
        dock_border="#6b2828",
        dock_title_bg="#501616",
        dock_title_fg="#fdeaea",
        dock_title_border_bottom="#7a3333",
        dock_bar_bg="#501616",
        dock_bar_border_bottom="#7a3333",
        dock_lbl="#fdeaea",
        tab_pane_border="#6b2828",
        tab_pane_bg="#3d0f0f",
        tab_inactive_bg="#5a1818",
        tab_inactive_fg="#f0d4d4",
        tab_inactive_border="#7a3333",
        tab_hover_bg="#6b2222",
        menubar_bg="#3d0f0f",
        menubar_fg="#f5f0f0",
        menubar_border_bottom="#5a1818",
        menubar_item_selected="#5a1818",
        menu_border="#7a3333",
        menu_separator="#7a3333",
        groove="#4a1212",
        model_footer_bg="#481212",
        model_footer_border="#6b2828",
        mini_del_bg="#5a1a1a",
        mini_del_fg="#f5e0e0",
        mini_del_border="#8b4545",
        mini_del_hover_bg="#6b2424",
        mini_del_hover_border="#a05555",
        mini_del_pressed="#401010",
        accent="#fdfdfd",
        accent_hover="#fff5f5",
        accent_pressed="#e8d4d4",
        accent_border="#c9a0a0",
        accent_soft="#8b4545",
        accent_soft_border="#a05555",
        selection_bg="#8b3a3a",
        selection_fg="#ffffff",
        slider_handle="#fdfdfd",
        slider_subpage="#6b2828",
        tab_selected_bg="#3d0f0f",
        tab_selected_fg="#ffffff",
        tab_selected_border="#7a3333",
        tab_selected_bottom="#fdfdfd",
        mini_add_bg="#6b2828",
        mini_add_fg="#ffffff",
        mini_add_border="#a05555",
        mini_add_hover_bg="#7a3333",
        mini_add_hover_border="#c06060",
        mini_add_pressed="#501616",
        analyze_bg="#b03030",
        analyze_fg="#ffffff",
        analyze_border="#8b2020",
        analyze_hover="#c84040",
        analyze_pressed="#901818",
        analyze_hover_border="#a02828",
        text_muted="#d4a8a8",
        combo_bg="#4a1212",
        combo_fg="#fdfdfd",
        combo_border="#7a3333",
        combo_hover_border="#a05555",
        combo_popup_bg="#4a1212",
        combo_popup_fg="#fdfdfd",
        combo_popup_border="#8b3a3a",
        combo_item_hover_bg="#6b2828",
        table_bg="#4a1212",
        table_fg="#fdfdfd",
        grid="#6b2828",
        table_border="#6b2828",
        header_bg="#5a1818",
        header_fg="#ffffff",
        header_border="#6b2828",
        menu_bg="#4a1212",
        menu_fg="#fdfdfd",
        menu_sel_bg="#8b3a3a",
        menu_sel_fg="#ffffff",
        push_bg="#5a1818",
        push_fg="#fdfdfd",
        push_border="#7a3333",
        push_hover_bg="#6b2828",
        push_hover_border="#a05555",
        push_pressed="#401010",
        status_bg="#2a0808",
        status_fg="#fdeaea",
        status_border_top="#5a1818",
        status_legend="#e8c0c0",
        status_summary="#ffffff",
        danger_hover_bg="#6b2020",
        danger_hover_border="#c04040",
        tool_hover_bg="#5a1818",
        tool_hover_border="#8b4545",
        tool_pressed="#401010",
        ws_checked_bg="#8b3a3a",
        ws_checked_border="#c06060",
    ),
    "blue_yellow": AppColorTokens(
        win_bg="#1a3a52",
        win_fg="#ecf4fc",
        surface="#1e4560",
        surface_alt="#244d6a",
        msgbox_bg="#244d6a",
        msgbox_fg="#fdfbf0",
        tooltip_bg="#1e4560",
        tooltip_fg="#fdfbf0",
        tooltip_border="#3d6a8a",
        toolbar_bg="#1e4560",
        toolbar_border_bottom="#153550",
        toolbar_sep="#3d6a8a",
        left_panel_bg="#1c415a",
        left_panel_border="#3d6a8a",
        dock_border="#3d6a8a",
        dock_title_bg="#153550",
        dock_title_fg="#f4e8a8",
        dock_title_border_bottom="#3d6a8a",
        dock_bar_bg="#153550",
        dock_bar_border_bottom="#3d6a8a",
        dock_lbl="#f4e8a8",
        tab_pane_border="#3d6a8a",
        tab_pane_bg="#1a3a52",
        tab_inactive_bg="#244d6a",
        tab_inactive_fg="#d8e8f4",
        tab_inactive_border="#3d6a8a",
        tab_hover_bg="#2d5a78",
        menubar_bg="#1a3a52",
        menubar_fg="#ecf4fc",
        menubar_border_bottom="#3d6a8a",
        menubar_item_selected="#244d6a",
        menu_border="#3d6a8a",
        menu_separator="#3d6a8a",
        groove="#153550",
        model_footer_bg="#1c415a",
        model_footer_border="#3d6a8a",
        mini_del_bg="#244d6a",
        mini_del_fg="#d8e8f4",
        mini_del_border="#4a7a9a",
        mini_del_hover_bg="#2d5a78",
        mini_del_hover_border="#5a8aac",
        mini_del_pressed="#153550",
        accent="#f4d03f",
        accent_hover="#f7dc6f",
        accent_pressed="#d4ac30",
        accent_border="#b7950b",
        accent_soft="#2d5a78",
        accent_soft_border="#4a7a9a",
        selection_bg="#2d5a78",
        selection_fg="#fffdf0",
        slider_handle="#f4d03f",
        slider_subpage="#3d6a8a",
        tab_selected_bg="#1a3a52",
        tab_selected_fg="#f4d03f",
        tab_selected_border="#3d6a8a",
        tab_selected_bottom="#f4d03f",
        mini_add_bg="#2d5a78",
        mini_add_fg="#f4d03f",
        mini_add_border="#4a7a9a",
        mini_add_hover_bg="#356688",
        mini_add_hover_border="#5a8aac",
        mini_add_pressed="#244d6a",
        analyze_bg="#2874a6",
        analyze_fg="#fffdf0",
        analyze_border="#1f5a82",
        analyze_hover="#3498db",
        analyze_pressed="#1a5276",
        analyze_hover_border="#5dade2",
        text_muted="#a8c4dc",
        combo_bg="#1e4560",
        combo_fg="#fdfbf0",
        combo_border="#3d6a8a",
        combo_hover_border="#f4d03f",
        combo_popup_bg="#1e4560",
        combo_popup_fg="#fdfbf0",
        combo_popup_border="#4a7a9a",
        combo_item_hover_bg="#2d5a78",
        table_bg="#1e4560",
        table_fg="#ecf4fc",
        grid="#3d6a8a",
        table_border="#3d6a8a",
        header_bg="#244d6a",
        header_fg="#f4e8a8",
        header_border="#3d6a8a",
        menu_bg="#1e4560",
        menu_fg="#fdfbf0",
        menu_sel_bg="#2d5a78",
        menu_sel_fg="#f4d03f",
        push_bg="#244d6a",
        push_fg="#fdfbf0",
        push_border="#4a7a9a",
        push_hover_bg="#2d5a78",
        push_hover_border="#f4d03f",
        push_pressed="#153550",
        status_bg="#153550",
        status_fg="#f4e8a8",
        status_border_top="#3d6a8a",
        status_legend="#a8c4dc",
        status_summary="#fdfbf0",
        danger_hover_bg="#6b2a2a",
        danger_hover_border="#c04040",
        tool_hover_bg="#2d5a78",
        tool_hover_border="#f4d03f",
        tool_pressed="#153550",
        ws_checked_bg="#2d5a78",
        ws_checked_border="#f4d03f",
    ),
}


def build_application_stylesheet(t: AppColorTokens) -> str:
    """Genera QSS completo (sin selector global QWidget)."""
    return f"""
QMainWindow {{
    font-family: "Segoe UI", "Roboto", "Inter", sans-serif;
    font-size: 9pt;
    color: {t.win_fg};
    background-color: {t.win_bg};
}}
QWidget#centralRoot {{
    font-family: "Segoe UI", "Roboto", "Inter", sans-serif;
    font-size: 9pt;
    color: {t.win_fg};
    background-color: {t.win_bg};
}}
QToolTip {{
    background-color: {t.tooltip_bg};
    color: {t.tooltip_fg};
    border: 1px solid {t.tooltip_border};
    padding: 4px 6px;
}}
QMessageBox {{ background-color: {t.msgbox_bg}; }}
QMessageBox QLabel {{ color: {t.msgbox_fg}; background-color: transparent; }}

QToolBar {{
    background-color: {t.toolbar_bg};
    border: none;
    border-bottom: 1px solid {t.toolbar_border_bottom};
    spacing: 2px;
    padding: 2px 4px;
}}
QToolBar::separator {{
    background: {t.toolbar_sep};
    width: 1px;
    margin: 3px 4px;
}}
QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px 6px;
    font-size: 9pt;
}}
QToolButton:hover {{
    background-color: {t.tool_hover_bg};
    border-color: {t.tool_hover_border};
}}
QToolButton:pressed {{ background-color: {t.tool_pressed}; }}
QToolButton#btnAnalyze {{
    background-color: {t.analyze_bg};
    color: {t.analyze_fg};
    border: 1px solid {t.analyze_border};
    border-radius: 3px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 9pt;
}}
QToolButton#btnAnalyze:hover {{
    background-color: {t.analyze_hover};
    border-color: {t.analyze_hover_border};
}}
QToolButton#btnAnalyze:pressed {{ background-color: {t.analyze_pressed}; }}
QToolButton#btnIconDanger:hover {{
    background-color: {t.danger_hover_bg};
    border-color: {t.danger_hover_border};
}}
QToolButton#leftTool {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 3px;
    margin: 1px;
}}
QToolButton#leftTool:hover {{
    background-color: {t.tool_hover_bg};
    border-color: {t.tool_hover_border};
}}
QToolButton#leftTool:pressed {{ background-color: {t.tool_pressed}; }}
QToolButton#wsToggle:checked {{
    background-color: {t.ws_checked_bg};
    border: 1px solid {t.ws_checked_border};
}}

QWidget#leftPanel {{
    background-color: {t.left_panel_bg};
    border-right: 1px solid {t.left_panel_border};
}}

QLabel#mutedLabel {{ color: {t.text_muted}; font-size: 9pt; }}
QLabel#scaleValue {{
    color: {t.win_fg};
    font-weight: 600;
    font-size: 9pt;
    min-width: 3em;
}}
QComboBox {{
    background-color: {t.combo_bg};
    color: {t.combo_fg};
    border: 1px solid {t.combo_border};
    border-radius: 3px;
    padding: 3px 8px;
    min-width: 150px;
    font-size: 9pt;
}}
QComboBox:hover {{ border-color: {t.combo_hover_border}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView,
QComboBox QListView {{
    background-color: {t.combo_popup_bg};
    color: {t.combo_popup_fg};
    selection-background-color: {t.selection_bg};
    selection-color: {t.selection_fg};
    outline: none;
    border: 1px solid {t.combo_popup_border};
    padding: 2px;
}}
QComboBox QAbstractItemView::item {{
    padding: 4px 8px;
    color: {t.combo_popup_fg};
    border: none;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {t.selection_bg};
    color: {t.selection_fg};
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {t.combo_item_hover_bg};
    color: {t.selection_fg};
}}
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {t.groove};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {t.slider_handle};
    border: none;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{
    background: {t.slider_subpage};
    border-radius: 2px;
}}
QDockWidget {{
    border: 1px solid {t.dock_border};
}}
QDockWidget::title {{
    background-color: {t.dock_title_bg};
    color: {t.dock_title_fg};
    padding: 7px 10px;
    font-weight: 700;
    font-size: 10pt;
    letter-spacing: 0.2px;
    border: none;
    border-bottom: 1px solid {t.dock_title_border_bottom};
}}
QWidget#dockTitleBar {{
    background-color: {t.dock_bar_bg};
    border-bottom: 1px solid {t.dock_bar_border_bottom};
}}
QLabel#dockTitleLabel {{
    color: {t.dock_lbl};
    font-size: 10pt;
    font-weight: 700;
    padding: 6px 10px;
}}
QTabWidget::pane {{
    border: 1px solid {t.tab_pane_border};
    background-color: {t.tab_pane_bg};
    margin: 0;
    padding: 0;
}}
QTabBar::tab {{
    background-color: {t.tab_inactive_bg};
    color: {t.tab_inactive_fg};
    padding: 5px 14px;
    margin-right: 2px;
    border: 1px solid {t.tab_inactive_border};
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    font-size: 9pt;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: {t.tab_selected_bg};
    color: {t.tab_selected_fg};
    border: 1px solid {t.tab_selected_border};
    border-bottom: 2px solid {t.tab_selected_bottom};
}}
QTabBar::tab:hover:!selected {{ background-color: {t.tab_hover_bg}; }}
QTableWidget {{
    background-color: {t.table_bg};
    alternate-background-color: {t.surface_alt};
    color: {t.table_fg};
    gridline-color: {t.grid};
    font-size: 9pt;
    selection-background-color: {t.selection_bg};
    selection-color: {t.selection_fg};
    border: 1px solid {t.table_border};
}}
QTableWidget::item {{ padding: 1px 6px; border: none; }}
QTableWidget::item:selected {{
    background-color: {t.selection_bg};
    color: {t.selection_fg};
}}
QHeaderView::section {{
    background-color: {t.header_bg};
    color: {t.header_fg};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {t.header_border};
    border-bottom: 1px solid {t.header_border};
    font-size: 9pt;
    font-weight: 600;
}}
QMenuBar {{
    background-color: {t.menubar_bg};
    color: {t.menubar_fg};
    padding: 1px 4px;
    font-size: 9pt;
    border-bottom: 1px solid {t.menubar_border_bottom};
}}
QMenuBar::item:selected {{ background-color: {t.menubar_item_selected}; }}
QMenu {{
    background-color: {t.menu_bg};
    color: {t.menu_fg};
    border: 1px solid {t.menu_border};
    font-size: 9pt;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 28px 5px 12px;
    color: {t.menu_fg};
    background-color: transparent;
}}
QMenu::item:selected {{
    background-color: {t.menu_sel_bg};
    color: {t.menu_sel_fg};
}}
QMenu::separator {{
    height: 1px;
    background: {t.menu_separator};
    margin: 4px 8px;
}}
QStatusBar {{
    background-color: {t.status_bg};
    color: {t.status_fg};
    border-top: 1px solid {t.status_border_top};
    font-size: 8pt;
}}
QStatusBar QLabel {{ color: {t.status_fg}; font-size: 8pt; padding: 0 6px; }}
QLabel#statusLegend {{
    color: {t.status_legend};
    font-size: 8pt;
    padding: 0px 8px;
}}
QLabel#statusSummary {{
    color: {t.status_summary};
    font-size: 8pt;
    padding: 0px 8px;
}}
QPushButton {{
    background-color: {t.push_bg};
    color: {t.push_fg};
    border: 1px solid {t.push_border};
    border-radius: 3px;
    padding: 4px 12px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background-color: {t.push_hover_bg};
    border-color: {t.push_hover_border};
}}
QPushButton:pressed {{ background-color: {t.push_pressed}; }}
QWidget#modelTableFooter {{
    background-color: {t.model_footer_bg};
    border-top: 1px solid {t.model_footer_border};
}}
QPushButton#modelMiniAdd, QPushButton#materialMiniAdd {{
    background-color: {t.mini_add_bg};
    color: {t.mini_add_fg};
    border: 1px solid {t.mini_add_border};
    border-radius: 8px;
    font-size: 14pt;
    font-weight: 700;
    padding: 0px 0px 5px 0px;
    text-align: center;
}}
QPushButton#modelMiniAdd:hover, QPushButton#materialMiniAdd:hover {{
    background-color: {t.mini_add_hover_bg};
    border-color: {t.mini_add_hover_border};
}}
QPushButton#modelMiniAdd:pressed, QPushButton#materialMiniAdd:pressed {{
    background-color: {t.mini_add_pressed};
}}
QPushButton#modelMiniDel, QPushButton#materialMiniDel {{
    background-color: {t.mini_del_bg};
    color: {t.mini_del_fg};
    border: 1px solid {t.mini_del_border};
    border-radius: 8px;
    font-size: 14pt;
    font-weight: 700;
    padding: 0px 0px 5px 0px;
    text-align: center;
}}
QPushButton#modelMiniDel:hover, QPushButton#materialMiniDel:hover {{
    background-color: {t.mini_del_hover_bg};
    border-color: {t.mini_del_hover_border};
}}
QPushButton#modelMiniDel:pressed, QPushButton#materialMiniDel:pressed {{
    background-color: {t.mini_del_pressed};
}}
"""


def resultados_nav_button_stylesheet(t: AppColorTokens) -> str:
    """Botones ◀ ▶ del visor de resultados (secundario + texto de selección)."""
    return (
        f"QToolButton {{ background:{t.accent_soft}; color:{t.selection_fg}; border:1px solid {t.accent_soft_border}; "
        f"border-radius:3px; padding:1px 6px; font-weight:700; }} "
        f"QToolButton:hover {{ background:{t.combo_item_hover_bg}; border-color:{t.combo_hover_border}; }} "
        f"QToolButton:pressed {{ background:{t.selection_bg}; }}"
    )


def splash_stylesheets(t: AppColorTokens) -> tuple[str, str, str]:
    """(dialog, title, message) QSS para splash de arranque."""
    dlg = (
        f"QDialog#reticularSplash {{ background-color: {t.surface}; "
        f"border: 2px solid {t.accent}; border-radius: 8px; }}"
    )
    title = f"font-weight: 600; font-size: 15pt; color: {t.accent};"
    msg = f"color: {t.win_fg};"
    return dlg, title, msg
