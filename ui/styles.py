# -*- coding: utf-8 -*-
"""
Industrial-grade dark QSS stylesheet for JaliMaker.
Aesthetic: precision engineering – dark steel with amber accents.
"""

MAIN_STYLESHEET = """
/* ── Global ──────────────────────────────────────────────────────── */
QWidget {
    background-color: #1a1e24;
    color: #d8dce4;
    font-family: "Segoe UI", "Liberation Sans", sans-serif;
    font-size: 12px;
}

QMainWindow, QDialog {
    background-color: #141720;
}

/* ── Header bar ──────────────────────────────────────────────────── */
#headerWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a1e24, stop:0.5 #232830, stop:1 #1a1e24);
    border-bottom: 2px solid #f59e0b;
}

#appTitle {
    color: #f8fafc;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
}

#versionLabel {
    color: #f59e0b;
    font-size: 11px;
    font-style: italic;
}

#companyLabel {
    color: #64748b;
    font-size: 10px;
}

/* ── Tab Widget ───────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2d3340;
    border-top: 2px solid #f59e0b;
    background: #1a1e24;
}

QTabBar::tab {
    background: #232830;
    color: #94a3b8;
    padding: 8px 20px;
    border: 1px solid #2d3340;
    border-bottom: none;
    margin-right: 2px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QTabBar::tab:selected {
    background: #1a1e24;
    color: #f59e0b;
    border-top: 2px solid #f59e0b;
}

QTabBar::tab:hover:!selected {
    background: #2a3040;
    color: #cbd5e1;
}

/* ── GroupBox ─────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #2d3340;
    border-radius: 4px;
    margin-top: 18px;
    padding: 8px 6px 6px 6px;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1px;
    color: #94a3b8;
    text-transform: uppercase;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    background: #1a1e24;
    color: #f59e0b;
    border-radius: 2px;
}

/* ── QLabel ───────────────────────────────────────────────────────── */
QLabel {
    color: #94a3b8;
    font-size: 11px;
}

QLabel#sectionLabel {
    color: #cbd5e1;
    font-weight: 700;
    font-size: 12px;
}

/* ── LineEdit ─────────────────────────────────────────────────────── */
QLineEdit {
    background: #0f1117;
    border: 1px solid #374151;
    border-radius: 3px;
    color: #f1f5f9;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
    selection-background-color: #f59e0b;
    selection-color: #000;
}

QLineEdit:focus {
    border: 1px solid #f59e0b;
    background: #0f1117;
}

QLineEdit:disabled {
    background: #1e2330;
    color: #4b5563;
    border-color: #1e2330;
}

QLineEdit[readOnly="true"] {
    background: #151820;
    color: #6b7280;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
QPushButton {
    background: #232830;
    color: #cbd5e1;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
    min-height: 28px;
}

QPushButton:hover {
    background: #2d3340;
    border-color: #f59e0b;
    color: #f8fafc;
}

QPushButton:pressed {
    background: #1a1e24;
    border-color: #d97706;
}

QPushButton:disabled {
    background: #1a1e24;
    color: #374151;
    border-color: #1e2330;
}

QPushButton#calculateBtn {
    background: #065f46;
    color: #6ee7b7;
    border-color: #059669;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 2px;
    min-height: 38px;
}

QPushButton#calculateBtn:hover {
    background: #047857;
    border-color: #10b981;
    color: #a7f3d0;
}

QPushButton#calculateBtn:pressed {
    background: #064e3b;
}

QPushButton#saveBtn {
    background: #1e3a5f;
    color: #93c5fd;
    border-color: #3b82f6;
}

QPushButton#saveBtn:hover {
    background: #1d4ed8;
    color: #dbeafe;
}

QPushButton#accessBtn {
    background: #451a03;
    color: #fbbf24;
    border-color: #d97706;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#accessBtn:hover {
    background: #78350f;
    border-color: #f59e0b;
}

QPushButton#dangerBtn {
    background: #450a0a;
    color: #fca5a5;
    border-color: #ef4444;
}

QPushButton#dangerBtn:hover {
    background: #7f1d1d;
}

/* ── CheckBox ─────────────────────────────────────────────────────── */
QCheckBox {
    color: #94a3b8;
    spacing: 8px;
    font-size: 11px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #374151;
    border-radius: 3px;
    background: #0f1117;
}

QCheckBox::indicator:checked {
    background: #f59e0b;
    border-color: #d97706;
    image: none;
}

QCheckBox::indicator:checked:after {
    color: #000;
}

QCheckBox:disabled {
    color: #374151;
}

QCheckBox::indicator:disabled {
    background: #1e2330;
    border-color: #1e2330;
}

/* ── ComboBox ─────────────────────────────────────────────────────── */
QComboBox {
    background: #0f1117;
    border: 1px solid #374151;
    border-radius: 3px;
    color: #f1f5f9;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 26px;
}

QComboBox:focus {
    border-color: #f59e0b;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background: #0f1117;
    border: 1px solid #374151;
    color: #f1f5f9;
    selection-background-color: #f59e0b;
    selection-color: #000;
}

QComboBox:disabled {
    background: #1e2330;
    color: #4b5563;
}

/* ── ScrollArea ───────────────────────────────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #0f1117;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #374151;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #f59e0b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Status / text areas ─────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {
    background: #0f1117;
    border: 1px solid #2d3340;
    color: #94a3b8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    border-radius: 3px;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #374151;
    border-radius: 3px;
    background: #0f1117;
    height: 12px;
    text-align: center;
    color: #f59e0b;
    font-size: 10px;
    font-weight: 700;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #d97706, stop:1 #f59e0b);
    border-radius: 2px;
}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #2d3340;
    width: 2px;
    height: 2px;
}

/* ── ToolTip ─────────────────────────────────────────────────────── */
QToolTip {
    background: #232830;
    color: #f1f5f9;
    border: 1px solid #f59e0b;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 11px;
}

/* ── Menu ────────────────────────────────────────────────────────── */
QMenuBar {
    background: #141720;
    color: #94a3b8;
    border-bottom: 1px solid #2d3340;
}

QMenuBar::item:selected {
    background: #f59e0b;
    color: #000;
}

QMenu {
    background: #1a1e24;
    border: 1px solid #2d3340;
    color: #d8dce4;
}

QMenu::item:selected {
    background: #f59e0b;
    color: #000;
}

/* ── Dialog ButtonBox ────────────────────────────────────────────── */
QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* ── Status label colours ────────────────────────────────────────── */
QLabel#statusOk    { color: #10b981; font-weight: 800; font-size: 16px; }
QLabel#statusError { color: #ef4444; font-weight: 800; font-size: 16px; }
QLabel#statusWarn  { color: #f59e0b; font-weight: 800; font-size: 16px; }

/* ── Pattern selector ────────────────────────────────────────────── */
#patternFrame {
    border: 2px solid #2d3340;
    border-radius: 6px;
    background: #141720;
    padding: 4px;
}

#patternFrame[selected="true"] {
    border: 2px solid #f59e0b;
    background: #1e2330;
}

/* ── GCode viewer ────────────────────────────────────────────────── */
#gcodeCanvas {
    background: #0a0d12;
    border: 1px solid #2d3340;
    border-radius: 4px;
}

/* ── Stat value labels ───────────────────────────────────────────── */
QLabel#statValue {
    color: #f59e0b;
    font-size: 28px;
    font-weight: 900;
    font-family: "Consolas", monospace;
}

QLabel#statSmall {
    color: #38bdf8;
    font-size: 13px;
    font-weight: 700;
    font-family: "Consolas", monospace;
}
"""
