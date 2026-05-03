# ─────────────────────────────────────────────────────────────────────────────
# views/styles/theme_manager.py
#
# Builds the application-wide QSS stylesheet from palette tokens and exposes
# small factory helpers (make_label, h_line, …) used by every page/component.
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QLabel, QFrame, QProgressBar
from PyQt6.QtCore import Qt

from views.styles.palettes import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_ACTIVE, PRIMARY_LIGHT,
    SUCCESS, SUCCESS_BG, SUCCESS_FG,
    WARNING_BG, WARNING_FG, WARNING_BORDER,
    DANGER, DANGER_HOVER, DANGER_BG, DANGER_FG, DANGER_BORDER,
    BG_APP, BG_SURFACE, BG_MUTED,
    BORDER, BORDER_STRONG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_INVERSE,
    SIDEBAR_BG, SIDEBAR_HOVER, SIDEBAR_ACTIVE, SIDEBAR_TEXT, SIDEBAR_TEXT_ACT,
    SCROLLBAR_TRACK, SCROLLBAR_THUMB,
)


# ─────────────────────────── QSS ─────────────────────────────────────────────

APP_STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QWidget {{
    background-color: {BG_APP};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

/* ── Sidebar ── */
#sidebar {{
    background-color: {SIDEBAR_BG};
    border-right: 1px solid {BORDER_STRONG};
    min-width: 220px;
    max-width: 220px;
}}
#navBtn {{
    background: transparent;
    color: {SIDEBAR_TEXT};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    margin: 2px 8px;
}}
#navBtn:hover {{ background: {SIDEBAR_HOVER}; color: {TEXT_INVERSE}; }}
#navBtn[active="true"] {{
    background: {SIDEBAR_ACTIVE};
    color: {SIDEBAR_TEXT_ACT};
    font-weight: 600;
}}

/* ── Topbar / Header ── */
#topbar {{
    background-color: {BG_SURFACE};
    border-bottom: 1px solid {BORDER};
    padding: 0 24px;
    min-height: 60px;
    max-height: 60px;
}}
#topbar QLineEdit {{
    background: {BG_MUTED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 260px;
}}
#queueBadge {{
    background: {WARNING_BG};
    color: {WARNING_FG};
    border-radius: 10px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: bold;
}}

/* ── Content area ── */
#content {{
    background: {BG_APP};
    padding: 24px;
}}

/* ── GroupBox / Card ── */
QGroupBox {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px;
    margin-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ── Buttons – primary (default) ── */
QPushButton {{
    background: {PRIMARY};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover   {{ background: {PRIMARY_HOVER}; }}
QPushButton:pressed {{ background: {PRIMARY_ACTIVE}; }}

/* ── Buttons – variants ── */
QPushButton#btnOutline {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
}}
QPushButton#btnOutline:hover {{ background: {BG_MUTED}; }}

QPushButton#btnDanger {{ background: {DANGER}; }}
QPushButton#btnDanger:hover {{ background: {DANGER_HOVER}; }}

QPushButton#btnGhost {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: none;
}}
QPushButton#btnGhost:hover {{ background: {BG_MUTED}; color: {TEXT_PRIMARY}; }}

QPushButton#btnSmall {{ padding: 4px 10px; font-size: 12px; }}

QPushButton#btnIcon {{
    padding: 4px;
    min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px;
    border-radius: 6px;
    font-size: 14px;
}}

QPushButton#payMethodBtn {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
    border-radius: 10px;
    padding: 12px 8px;
    font-size: 12px;
    min-width: 80px;
}}
QPushButton#payMethodBtn[checked="true"] {{
    background: {PRIMARY};
    color: #ffffff;
    border-color: {PRIMARY};
}}

/* ── Table ── */
QTableWidget {{
    border: none;
    gridline-color: {BG_MUTED};
    background: {BG_SURFACE};
    alternate-background-color: {BG_APP};
}}
QTableWidget::item {{ padding: 8px 12px; }}
QTableWidget::item:selected {{ background: {PRIMARY_LIGHT}; color: {PRIMARY_ACTIVE}; }}
QHeaderView::section {{
    background: {BG_APP};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 12px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ── ComboBox ── */
QComboBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    background: {BG_SURFACE};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ border: 1px solid {BORDER}; border-radius: 6px; }}

/* ── LineEdit ── */
QLineEdit {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    background: {BG_SURFACE};
}}
QLineEdit:focus {{ border-color: {PRIMARY}; }}

/* ── Tabs ── */
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent;
    border: none;
    padding: 8px 16px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
    border-radius: 8px;
    margin: 2px;
}}
QTabBar::tab:selected {{ background: {PRIMARY_LIGHT}; color: {PRIMARY}; font-weight: 600; }}
QTabBar::tab:hover    {{ background: {BG_MUTED}; color: {TEXT_PRIMARY}; }}

/* ── ProgressBar ── */
QProgressBar {{
    border: none;
    border-radius: 4px;
    background: {BORDER};
    height: 6px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{ border-radius: 4px; background: {PRIMARY}; }}

/* ── ScrollArea / ScrollBar ── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {SCROLLBAR_TRACK};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {SCROLLBAR_THUMB};
    border-radius: 3px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Horizontal separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {BORDER}; }}

/* ── CheckBox ── */
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {PRIMARY};
    border-color: {PRIMARY};
}}

/* ── StatusBar ── */
QStatusBar {{
    background: {BG_SURFACE};
    border-top: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

/* ── Dialog ── */
QDialog {{ background: {BG_SURFACE}; border-radius: 12px; }}
QDialogButtonBox QPushButton {{ min-width: 80px; }}
"""


def apply_theme(app) -> None:
    """Call once at startup: app.setStyle('Fusion') + apply QSS."""
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)


# ─────────────────────────── UI helpers ──────────────────────────────────────

def make_label(text: str, size: int = 13, bold: bool = False, color: str | None = None) -> QLabel:
    """Create a styled QLabel with optional font size, bold, and colour."""
    lbl = QLabel(text)
    f = lbl.font()
    f.setPointSize(size)
    if bold:
        f.setBold(True)
    lbl.setFont(f)
    if color:
        lbl.setStyleSheet(f"color: {color};")
    return lbl


def h_line() -> QFrame:
    """Return a thin horizontal separator line."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {BORDER};")
    return line


def card_style(radius: int = 10) -> str:
    """Inline style string for a white bordered card widget."""
    return (
        f"background:{BG_SURFACE}; border:1px solid {BORDER}; "
        f"border-radius:{radius}px; padding:14px;"
    )


def stock_badge_style(is_low: bool) -> str:
    """Return inline style for a stock count badge."""
    bg = DANGER_BG if is_low else SUCCESS_BG
    fg = DANGER_FG if is_low else SUCCESS_FG
    return (
        f"background:{bg}; color:{fg}; border-radius:6px; "
        f"padding:2px 8px; font-size:11px; font-weight:600;"
    )


def alert_style(kind: str = "warning") -> str:
    """Return inline style for an alert banner ('warning' | 'danger')."""
    if kind == "danger":
        return (
            f"background:{DANGER_BG}; color:{DANGER_FG}; "
            f"border:1px solid {DANGER_BORDER}; border-radius:8px; padding:10px 14px;"
        )
    return (
        f"background:{WARNING_BG}; color:{WARNING_FG}; "
        f"border:1px solid {WARNING_BORDER}; border-radius:8px; padding:10px 14px;"
    )


def tier_badge_style(fg: str, bg: str) -> str:
    """Return inline style for a loyalty-tier badge."""
    return (
        f"background:{bg}; color:{fg}; border-radius:6px; "
        f"padding:2px 8px; font-size:11px; font-weight:600;"
    )
