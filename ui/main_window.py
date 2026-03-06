# -*- coding: utf-8 -*-
"""
Main application window for JaliMaker.
Assembles all tabs, manages calculation pipeline, progress, and GCode saving.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QTabWidget, QProgressBar, QMessageBox, QFileDialog, QFrame,
    QSizePolicy, QPlainTextEdit, QSplitter, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

from core.config_manager import ConfigManager
from core.security_manager import SecurityManager
from core.calculator import Calculator, DrillParams, CalcResults
from core.gcode_generator import GCodeGenerator
from core.version import VERSION, APP_NAME, COMPANY, check_latest_version

from ui.styles import MAIN_STYLESHEET
from ui.pattern_preview import PatternPreviewWidget
from ui.gcode_viewer import GCodeViewerWidget
from ui.setup_tab import SetupTab

logger = logging.getLogger("JaliMaker.MainWindow")

# ── Background worker ─────────────────────────────────────────────────────────

class CalcWorker(QObject):
    """Run calculation in background thread."""
    finished  = Signal(object, object)   # CalcResults, DrillParams
    error     = Signal(str)
    progress  = Signal(int)

    def __init__(self, params: DrillParams):
        super().__init__()
        self._params = params

    def run(self):
        try:
            self.progress.emit(10)
            calc = Calculator()
            self.progress.emit(40)
            results = calc.calculate(self._params)
            self.progress.emit(80)
            gen = GCodeGenerator()
            gcode = gen.generate_all(self._params, results)
            self.progress.emit(100)
            self.finished.emit(results, gcode)
        except Exception as e:
            logger.error(f"CalcWorker error: {e}", exc_info=True)
            self.error.emit(str(e))


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, config: ConfigManager, log: logging.Logger):
        super().__init__()
        self._config   = config
        self._log      = log
        self._security = SecurityManager(config)
        self._calc_results: Optional[CalcResults] = None
        self._gcode_dict: Optional[dict] = None
        self._drill_params: Optional[DrillParams] = None
        self._worker_thread: Optional[QThread] = None

        self.setWindowTitle(f"{APP_NAME} – {COMPANY}")
        self.setMinimumSize(1000, 650)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._build_ui()
        self._load_grill_fields()
        self._connect_signals()
        self._schedule_version_check()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)

        # Jali Maker tab
        self._jali_tab = self._build_jali_tab()
        self._tabs.addTab(self._jali_tab, "  Jali Maker  ")

        # GCode Viewer tab
        self._viewer = GCodeViewerWidget()
        self._tabs.addTab(self._viewer, "  GCode Viewer  ")

        # Setup tab
        self._setup_tab = SetupTab(self._config, self._security)
        self._tabs.addTab(self._setup_tab, "  Setup  ")

        root.addWidget(self._tabs, 1)

        # Status / progress bar
        root.addWidget(self._build_statusbar())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerWidget")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 6, 14, 6)

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        hl.addWidget(title)

        hl.addStretch()

        ver_lbl = QLabel(f"Version {VERSION}  |  {COMPANY}  |  MIT License")
        ver_lbl.setObjectName("versionLabel")
        hl.addWidget(ver_lbl)

        self._update_badge = QLabel("")
        self._update_badge.setObjectName("statusWarn")
        self._update_badge.setVisible(False)
        hl.addWidget(self._update_badge)

        return header

    def _build_statusbar(self) -> QWidget:
        sb = QWidget()
        sb.setFixedHeight(22)
        sb.setStyleSheet("background:#0f1117; border-top:1px solid #2d3340;")
        hl = QHBoxLayout(sb)
        hl.setContentsMargins(8, 2, 8, 2)

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statSmall")
        hl.addWidget(self._status_label)

        hl.addStretch()

        self._progress = QProgressBar()
        self._progress.setFixedWidth(200)
        self._progress.setFixedHeight(10)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        hl.addWidget(self._progress)

        return sb

    # ── Jali Tab ──────────────────────────────────────────────────────────────

    def _build_jali_tab(self) -> QWidget:
        tab = QWidget()
        hl = QHBoxLayout(tab)
        hl.setContentsMargins(6, 6, 6, 6)
        hl.setSpacing(8)

        # Create preview widget FIRST – _build_pattern_selector() triggers
        # _set_pattern() → _refresh_preview(), so _preview must exist already.
        self._preview = PatternPreviewWidget()

        # Left panel (inputs + buttons)
        left = QWidget()
        left.setFixedWidth(440)
        left_vl = QVBoxLayout(left)
        left_vl.setContentsMargins(0, 0, 0, 0)
        left_vl.setSpacing(8)

        left_vl.addWidget(self._build_pattern_selector())
        left_vl.addWidget(self._build_dimensions_group())
        left_vl.addWidget(self._build_action_buttons())
        left_vl.addStretch()

        hl.addWidget(left)

        # Right panel: preview + status
        right = QSplitter(Qt.Vertical)
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right.addWidget(self._preview)

        # Status + stats
        status_widget = self._build_status_panel()
        right.addWidget(status_widget)
        right.setSizes([500, 200])

        hl.addWidget(right, 1)
        return tab

    def _build_pattern_selector(self) -> QGroupBox:
        gb = QGroupBox("Drill Pattern")
        hl = QHBoxLayout(gb)
        hl.setSpacing(16)

        self._pat_btns = []
        patterns = [
            ("Triangular\n(Zig-Zag)",  1),
            ("Rhombus\n(Zig-Zag +1)",  2),
            ("Square\n(Uniform)",       3),
        ]
        for name, num in patterns:
            frame = QFrame()
            frame.setObjectName("patternFrame")
            frame.setFixedSize(90, 70)
            frame.setCursor(Qt.PointingHandCursor)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(4, 4, 4, 4)
            frame_layout.setSpacing(2)

            icon_lbl = QLabel(self._pattern_svg(num))
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setFixedHeight(36)
            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setStyleSheet("font-size:9px; color:#94a3b8;")

            frame_layout.addWidget(icon_lbl)
            frame_layout.addWidget(name_lbl)

            # Click handler
            frame.mousePressEvent = lambda e, n=num: self._set_pattern(n)
            self._pat_btns.append((num, frame))
            hl.addWidget(frame)

        self._current_pattern = 1
        self._set_pattern(1)
        return gb

    def _pattern_svg(self, pattern: int) -> str:
        """Return a tiny Unicode art for each pattern."""
        arts = {
            1: "● ●\n ●\n● ●",   # triangular
            2: "●●●\n ● \n●●●",  # rhombus
            3: "● ●\n● ●\n● ●",  # square
        }
        lbl = QLabel(arts.get(pattern, "?"))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:13px; color:#f59e0b; line-height:1.4;")
        return arts.get(pattern, "?")

    def _set_pattern(self, num: int):
        self._current_pattern = num
        for n, frame in self._pat_btns:
            frame.setProperty("selected", "true" if n == num else "false")
            frame.style().unpolish(frame)
            frame.style().polish(frame)
        self._refresh_preview()

    def _build_dimensions_group(self) -> QGroupBox:
        gb = QGroupBox("Dimensions (mm)")
        grid = QGridLayout(gb)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setVerticalSpacing(6)
        grid.setHorizontalSpacing(8)

        def le(default, tip=""):
            w = QLineEdit(default)
            w.setAlignment(Qt.AlignCenter)
            w.setMinimumHeight(34)
            w.setStyleSheet(
                "font-size:15px; font-weight:700; padding:4px 8px;"
            )
            if tip:
                w.setToolTip(tip)
            return w

        def lbl(text, tip=""):
            l = QLabel(text)
            l.setStyleSheet("font-size:12px;")
            l.setToolTip(tip)
            return l

        # Total size
        grid.addWidget(lbl("Total Size"), 0, 0)
        grid.addWidget(lbl("X:"), 0, 1)
        self.le_size_x = le("160", "Total board width in mm")
        grid.addWidget(self.le_size_x, 0, 2)
        grid.addWidget(lbl("Y:"), 0, 3)
        self.le_size_y = le("505", "Total board height in mm")
        grid.addWidget(self.le_size_y, 0, 4)

        # Border left/top
        grid.addWidget(lbl("Border (a, b)"), 1, 0)
        grid.addWidget(lbl("a:"), 1, 1)
        self.le_gap_x = le("20", "Left border offset (mm)")
        grid.addWidget(self.le_gap_x, 1, 2)
        grid.addWidget(lbl("b:"), 1, 3)
        self.le_gap_y = le("5", "Top border offset (mm)")
        grid.addWidget(self.le_gap_y, 1, 4)

        # Border right/bottom
        grid.addWidget(lbl("Border (c, d)"), 2, 0)
        grid.addWidget(lbl("c:"), 2, 1)
        self.le_gap_c = le("20", "Right border offset (mm)")
        grid.addWidget(self.le_gap_c, 2, 2)
        grid.addWidget(lbl("d:"), 2, 3)
        self.le_gap_d = le("5", "Bottom border offset (mm)")
        grid.addWidget(self.le_gap_d, 2, 4)

        # Holes X / Lines Y
        grid.addWidget(lbl("Holes in X"), 3, 0)
        self.le_holes_x = le("16", "Number of holes per row")
        self.le_holes_x.setToolTip("Holes along X axis")
        grid.addWidget(self.le_holes_x, 3, 2)
        grid.addWidget(lbl("Lines in Y"), 3, 3)
        self.le_holes_y = le("100", "Number of lines/rows")
        grid.addWidget(self.le_holes_y, 3, 4)

        # Pin position
        grid.addWidget(lbl("Pin Position"), 4, 0)
        grid.addWidget(lbl("X:"), 4, 1)
        self.le_pin_x = le("10", "Dowel pin X offset (mm)")
        grid.addWidget(self.le_pin_x, 4, 2)
        grid.addWidget(lbl("Y:"), 4, 3)
        self.le_pin_y = le("15", "Dowel pin Y offset (mm)")
        grid.addWidget(self.le_pin_y, 4, 4)

        # Depths
        grid.addWidget(lbl("Drill Depth (mm)"), 5, 0)
        self.le_depth = le("12", "Drill depth (mm)")
        grid.addWidget(self.le_depth, 5, 2)
        grid.addWidget(lbl("Pin Depth (mm)"), 5, 3)
        self.le_pin_depth = le("7", "Dowel pin depth (mm)")
        grid.addWidget(self.le_pin_depth, 5, 4)

        # Chamfer depth
        grid.addWidget(lbl("Chamfer Depth (mm)"), 6, 0)
        self.le_ch_depth = le("0.8", "Bottom-side chamfer depth (mm)")
        grid.addWidget(self.le_ch_depth, 6, 2)

        # Peg drilling
        self.chk_peg = QCheckBox("Peg Drilling")
        self.chk_peg.setToolTip("Enable peck drilling for deep holes")
        grid.addWidget(self.chk_peg, 7, 0)
        grid.addWidget(lbl("Peg Depth:"), 7, 1)
        self.le_peg_depth = le("2.5", "Peck step depth (mm)")
        grid.addWidget(self.le_peg_depth, 7, 2)
        grid.addWidget(lbl("Retract:"), 7, 3)
        self.le_peg_retract = le("3", "Peck retract height (mm)")
        grid.addWidget(self.le_peg_retract, 7, 4)

        self._dim_fields = [
            self.le_size_x, self.le_size_y, self.le_gap_x, self.le_gap_y,
            self.le_gap_c, self.le_gap_d, self.le_holes_x, self.le_holes_y,
            self.le_pin_x, self.le_pin_y, self.le_depth, self.le_pin_depth,
            self.le_ch_depth, self.le_peg_depth, self.le_peg_retract,
        ]
        return gb

    def _build_action_buttons(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        self._btn_calc = QPushButton("⚙  CALCULATE")
        self._btn_calc.setObjectName("calculateBtn")
        vl.addWidget(self._btn_calc)

        row = QHBoxLayout()
        self._btn_save = QPushButton("💾  Save GCode")
        self._btn_save.setObjectName("saveBtn")
        self._btn_save.setEnabled(False)
        row.addWidget(self._btn_save)

        self._btn_exit = QPushButton("✕  Exit")
        self._btn_exit.setObjectName("dangerBtn")
        row.addWidget(self._btn_exit)
        vl.addLayout(row)

        return w

    def _build_status_panel(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(4)

        # Status row
        status_row = QHBoxLayout()
        self._status_icon = QLabel("—")
        self._status_icon.setObjectName("statValue")
        self._status_icon.setFixedWidth(80)
        status_row.addWidget(self._status_icon)

        # Stats grid
        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(16)
        stats_grid.setVerticalSpacing(2)

        def stat(label):
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#64748b; font-size:10px;")
            val = QLabel("—")
            val.setObjectName("statSmall")
            return lbl, val

        self._lbl_total_holes_v = QLabel("0")
        self._lbl_total_holes_v.setObjectName("statValue")

        l1, self._stat_spacing_x  = stat("Spacing X")
        l2, self._stat_spacing_y  = stat("Spacing Y")
        l3, self._stat_work_x     = stat("Working X")
        l4, self._stat_work_y     = stat("Working Y")
        l5, self._stat_shift_x    = stat("Ref Shift X")
        l6, self._stat_shift_y    = stat("Ref Shift Y")

        for i, (l, v) in enumerate([(l1, self._stat_spacing_x),(l2, self._stat_spacing_y),
                                    (l3, self._stat_work_x),(l4, self._stat_work_y),
                                    (l5, self._stat_shift_x),(l6, self._stat_shift_y)]):
            stats_grid.addWidget(l, i // 2, (i % 2) * 2)
            stats_grid.addWidget(v, i // 2, (i % 2) * 2 + 1)

        status_row.addLayout(stats_grid)

        total_col = QVBoxLayout()
        total_col.addWidget(QLabel("Total Holes"))
        total_col.addWidget(self._lbl_total_holes_v)
        status_row.addLayout(total_col)

        vl.addLayout(status_row)

        # Calculation log
        self._calc_log = QPlainTextEdit()
        self._calc_log.setReadOnly(True)
        self._calc_log.setMaximumHeight(90)
        self._calc_log.setPlaceholderText("Calculation details will appear here...")
        vl.addWidget(self._calc_log)

        return w

    # ── Signal connections ────────────────────────────────────────────────────

    def _connect_signals(self):
        self._btn_calc.clicked.connect(self._on_calculate)
        self._btn_save.clicked.connect(self._on_save_gcode)
        self._btn_exit.clicked.connect(self.close)
        self._preview.hole_hovered.connect(self._on_hole_hovered)
        self._setup_tab.settings_saved.connect(self._load_grill_fields)

        # Live preview refresh on input change
        for field in self._dim_fields:
            field.textChanged.connect(self._refresh_preview)
        self.chk_peg.toggled.connect(self._on_peg_toggled)

        # Tab change – ask password for Setup
        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx: int):
        # Setup tab is index 2 – auth is handled internally by SetupTab
        pass

    # ── Field loading ─────────────────────────────────────────────────────────

    def _load_grill_fields(self):
        c = self._config
        self.le_size_x.setText(c.get("GRILL", "total_size_x"))
        self.le_size_y.setText(c.get("GRILL", "total_size_y"))
        self.le_gap_x.setText(c.get("GRILL", "border_x"))
        self.le_gap_y.setText(c.get("GRILL", "border_y"))
        self.le_gap_c.setText(c.get("GRILL", "border_c", c.get("GRILL", "border_x")))
        self.le_gap_d.setText(c.get("GRILL", "border_d", c.get("GRILL", "border_y")))
        self.le_holes_x.setText(c.get("GRILL", "holes_x"))
        self.le_holes_y.setText(c.get("GRILL", "holes_y"))
        self.le_pin_x.setText(c.get("GRILL", "pin_x"))
        self.le_pin_y.setText(c.get("GRILL", "pin_y"))
        self.le_depth.setText(c.get("GRILL", "depth"))
        self.le_pin_depth.setText(c.get("GRILL", "pin_depth"))
        self.le_ch_depth.setText(c.get("GRILL", "ch_depth"))
        self.le_peg_depth.setText(c.get("GRILL", "peg_depth"))
        self.le_peg_retract.setText(c.get("GRILL", "peg_retract"))
        self.chk_peg.setChecked(c.get_bool("GRILL", "peg_drilling"))
        pattern = c.get_int("GRILL", "pattern", 1)
        self._set_pattern(pattern)
        self._refresh_preview()

    # ── Preview ───────────────────────────────────────────────────────────────

    def _refresh_preview(self):
        # Guard: dimension widgets may not exist yet during UI construction
        if not hasattr(self, "_preview") or not hasattr(self, "le_size_x"):
            return
        try:
            self._preview.update_preview(
                total_x = float(self.le_size_x.text() or "160"),
                total_y = float(self.le_size_y.text() or "505"),
                gap_x   = float(self.le_gap_x.text() or "20"),
                gap_y   = float(self.le_gap_y.text() or "5"),
                gap_c   = float(self.le_gap_c.text() or "20"),
                gap_d   = float(self.le_gap_d.text() or "5"),
                holes_x = int(self.le_holes_x.text() or "16"),
                holes_y = int(self.le_holes_y.text() or "100"),
                pattern = self._current_pattern,
                pin_x   = float(self.le_pin_x.text() or "10"),
                pin_y   = float(self.le_pin_y.text() or "15"),
                drill_dia = float(self._config.get("MACHINE", "drill_dia", "2.0")),
            )
        except ValueError:
            pass  # user mid-typing

    def _on_hole_hovered(self, x: float, y: float, idx: int):
        self._status_label.setText(f"Hole #{idx + 1}  X={x:.4f}  Y={y:.4f}")

    # ── Peg drilling toggle ───────────────────────────────────────────────────

    def _on_peg_toggled(self, checked: bool):
        self.le_peg_depth.setEnabled(checked)
        self.le_peg_retract.setEnabled(checked)

    # ── Calculation ───────────────────────────────────────────────────────────

    def _on_calculate(self):
        if self._worker_thread and self._worker_thread.isRunning():
            return

        try:
            params = self._build_params()
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "Input Error", f"Check your inputs:\n{e}")
            return

        logger.info(f"Starting calculation: pattern={params.pattern} "
                    f"holes={params.holes_x}×{params.holes_y}")

        self._btn_calc.setEnabled(False)
        self._btn_save.setEnabled(False)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._status_label.setText("Calculating...")

        self._worker = CalcWorker(params)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_calc_finished)
        self._worker.error.connect(self._on_calc_error)
        self._worker_thread.start()

    def _on_calc_finished(self, results: CalcResults, gcode: dict):
        self._worker_thread.quit()
        self._worker_thread.wait()

        self._calc_results = results
        self._gcode_dict   = gcode
        self._drill_params = self._build_params()

        # Update stats
        self._lbl_total_holes_v.setText(str(results.total_holes))
        self._stat_spacing_x.setText(f"{results.hole_spacing_x:.4f} mm")
        self._stat_spacing_y.setText(f"{results.hole_spacing_y:.4f} mm")
        self._stat_work_x.setText(f"{results.x_working_size:.2f} mm")
        self._stat_work_y.setText(f"{results.y_working_size:.2f} mm")
        self._stat_shift_x.setText(f"{results.ref_shift_x:.4f} mm")
        self._stat_shift_y.setText(f"{results.ref_shift_y:.4f} mm")

        # Calc log
        log_lines = [
            f"Pattern: {['Triangular','Rhombus','Square'][self._drill_params.pattern - 1]}",
            f"Holes X: {self._drill_params.holes_x}   Lines Y: {self._drill_params.holes_y}",
            f"Spacing X: {results.hole_spacing_x:.4f} mm   Y: {results.hole_spacing_y:.4f} mm",
            f"Working area: {results.x_working_size:.2f} × {results.y_working_size:.2f} mm",
            f"Ref shift: X={results.ref_shift_x:.4f}  Y={results.ref_shift_y:.4f}",
            f"Top holes: {len(results.top_coords)}   Bottom: {len(results.bot_coords)}",
        ]
        if results.warnings:
            log_lines.append("⚠ WARNINGS:")
            log_lines.extend(f"  {w}" for w in results.warnings)

        self._calc_log.setPlainText("\n".join(log_lines))

        # Update preview with real coords (cap for perf)
        self._preview.update_preview(
            total_x = self._drill_params.total_size_x,
            total_y = self._drill_params.total_size_y,
            gap_x   = self._drill_params.gap_x,
            gap_y   = self._drill_params.gap_y,
            gap_c   = self._drill_params.gap_c,
            gap_d   = self._drill_params.gap_d,
            holes_x = self._drill_params.holes_x,
            holes_y = self._drill_params.holes_y,
            pattern = self._drill_params.pattern,
            pin_x   = self._drill_params.dowel_x,
            pin_y   = self._drill_params.dowel_y,
            drill_dia = self._drill_params.drill_dia,
            hole_coords = results.top_coords,
            pin_coords  = results.pin_coords,
        )

        # Load GCode viewer
        self._viewer.load_results(results, self._drill_params)

        # Save grill fields to config
        self._save_grill_to_config()

        self._status_icon.setText("OK")
        self._status_icon.setObjectName("statusOk")
        self._status_icon.style().unpolish(self._status_icon)
        self._status_icon.style().polish(self._status_icon)

        self._btn_calc.setEnabled(True)
        self._btn_calc.setStyleSheet("background:#065f46; color:#6ee7b7;")
        self._btn_save.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText(f"Done – {results.total_holes} holes calculated")

        if results.warnings:
            QMessageBox.warning(self, "Calculation Warnings",
                                "\n".join(results.warnings))

    def _on_calc_error(self, msg: str):
        if self._worker_thread:
            self._worker_thread.quit()
        self._status_icon.setText("ERR")
        self._status_icon.setObjectName("statusError")
        self._status_icon.style().unpolish(self._status_icon)
        self._status_icon.style().polish(self._status_icon)
        self._btn_calc.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText("Calculation failed")
        QMessageBox.critical(self, "Calculation Error", msg)

    # ── Build DrillParams from UI ─────────────────────────────────────────────

    def _build_params(self) -> DrillParams:
        def f(text, default=0.0):
            try:
                return float(text.strip())
            except ValueError:
                raise ValueError(f"Invalid number: '{text}'")

        def i(text, default=0):
            try:
                return int(text.strip())
            except ValueError:
                raise ValueError(f"Invalid integer: '{text}'")

        mo = self._setup_tab.get_machine_options()
        mp = self._setup_tab.get_machine_params()
        fp = self._setup_tab.get_fixture_params()
        pan = self._setup_tab.get_panelization()

        return DrillParams(
            total_size_x  = f(self.le_size_x.text()),
            total_size_y  = f(self.le_size_y.text()),
            gap_x         = f(self.le_gap_x.text()),
            gap_y         = f(self.le_gap_y.text()),
            gap_c         = f(self.le_gap_c.text()),
            gap_d         = f(self.le_gap_d.text()),
            holes_x       = i(self.le_holes_x.text()),
            holes_y       = i(self.le_holes_y.text()),
            dowel_x       = f(self.le_pin_x.text()),
            dowel_y       = f(self.le_pin_y.text()),
            depth         = f(self.le_depth.text()),
            pin_depth     = f(self.le_pin_depth.text()),
            ch_depth      = f(self.le_ch_depth.text()),
            peg_depth     = f(self.le_peg_depth.text()),
            peg_retract   = f(self.le_peg_retract.text()),
            peg_drilling  = self.chk_peg.isChecked(),
            pattern       = self._current_pattern,
            flip_axis     = fp["flip_axis"],
            flip_tolerance_x = fp["flip_tolerance_x"],
            flip_tolerance_y = fp["flip_tolerance_y"],
            fixture_pinning  = mo["fixture_pinning"],
            fixture_cd_x     = fp["fixture_cd_x"],
            fixture_cd_y     = fp["fixture_cd_y"],
            fixture_pin_x    = fp["fixture_pin_x"],
            fixture_pin_y    = fp["fixture_pin_y"],
            retract          = mp["retract"],
            initial_z        = mp["z_initial"],
            feed_rate        = mp["feed_rate"],
            spindle_delay    = mp["spindle_delay"],
            dwell            = mp["dwell"],
            drill_dia        = mp["drill_dia"],
            routing_tool_dia = mp["routing_tool_dia"],
            header           = mp["preamble"],
            footer           = mp["postamble"],
            parking          = mo["parking"],
            buzzer           = mo["buzzer"],
            enable_dwell_top    = mo["enable_dwell_top"],
            enable_dwell_bottom = mo["enable_dwell_bot"],
            enable_chamfer   = mo["enable_chamfer"],
            enable_pin_gcode = mo["enable_pin_gcode"],
            enable_border    = mo["enable_border"],
            merge_border_drill = mo["merge_border_drill"],
            combine_pin_drill  = mo["combine_pin_drill"],
            border_cutting     = fp["border_cutting"],
            optimization       = mp["optimization"],
            panelization       = pan["enabled"],
            panel_rows         = pan["rows"],
            panel_cols         = pan["cols"],
            panel_offset_x     = pan["offset_x"],
            panel_offset_y     = pan["offset_y"],
        )

    # ── Save GCode ────────────────────────────────────────────────────────────

    def _on_save_gcode(self):
        if not self._gcode_dict or not self._calc_results:
            QMessageBox.warning(self, "No GCode", "Please run Calculate first.")
            return

        # ── Step 1: ask for base file name ────────────────────────────────────
        from PySide6.QtWidgets import QInputDialog
        base_name, ok = QInputDialog.getText(
            self,
            "Save GCode – File Name",
            "Enter base file name (without extension):"
            "Files will be saved as  <name>_TOP.ngc  /  <name>_BOTTOM.ngc  /  <name>_PINNING.ngc",
            text="jali",
        )
        if not ok or not base_name.strip():
            return
        base_name = base_name.strip()

        # ── Step 2: pick output folder ────────────────────────────────────────
        out_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Folder",
            self._config.get("APP", "last_gcode_dir", str(Path.home())),
        )
        if not out_dir:
            return

        self._config.set("APP", "last_gcode_dir", out_dir)
        self._config.save()

        # ── Step 3: save with user-supplied base name ─────────────────────────
        gen = GCodeGenerator()
        saved = gen.save_all(self._gcode_dict, Path(out_dir), base_name=base_name)

        msg = "Saved GCode files:\n" + "\n".join(f"• {p.name}" for p in saved)
        QMessageBox.information(self, "GCode Saved", msg)
        self._status_label.setText(f"GCode saved → {out_dir}")
        logger.info(f"GCode saved to {out_dir} base='{base_name}': {[str(p) for p in saved]}")

    # ── Config helpers ────────────────────────────────────────────────────────

    def _save_grill_to_config(self):
        c = self._config
        c.set("GRILL", "total_size_x", self.le_size_x.text())
        c.set("GRILL", "total_size_y", self.le_size_y.text())
        c.set("GRILL", "border_x",     self.le_gap_x.text())
        c.set("GRILL", "border_y",     self.le_gap_y.text())
        c.set("GRILL", "border_c",     self.le_gap_c.text())
        c.set("GRILL", "border_d",     self.le_gap_d.text())
        c.set("GRILL", "holes_x",      self.le_holes_x.text())
        c.set("GRILL", "holes_y",      self.le_holes_y.text())
        c.set("GRILL", "pin_x",        self.le_pin_x.text())
        c.set("GRILL", "pin_y",        self.le_pin_y.text())
        c.set("GRILL", "depth",        self.le_depth.text())
        c.set("GRILL", "pin_depth",    self.le_pin_depth.text())
        c.set("GRILL", "ch_depth",     self.le_ch_depth.text())
        c.set("GRILL", "peg_depth",    self.le_peg_depth.text())
        c.set("GRILL", "peg_retract",  self.le_peg_retract.text())
        c.set("GRILL", "peg_drilling", self.chk_peg.isChecked())
        c.set("GRILL", "pattern",      self._current_pattern)
        c.save()

    # ── Version check ─────────────────────────────────────────────────────────

    def _schedule_version_check(self):
        QTimer.singleShot(3000, self._check_version)

    def _check_version(self):
        info = check_latest_version()
        if info and info.get("update_available"):
            self._update_badge.setText(f"  ⬆ Update available: v{info['latest']}")
            self._update_badge.setVisible(True)
            self._update_badge.setToolTip(info.get("url", ""))

    # ── Close event ───────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_grill_to_config()
        logger.info("Application closing – config saved")
        super().closeEvent(event)
