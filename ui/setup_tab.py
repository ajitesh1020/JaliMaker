# -*- coding: utf-8 -*-
"""Setup tab widget – machine, fixture and panelization settings."""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QScrollArea, QMessageBox, QInputDialog, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.config_manager import ConfigManager
from core.security_manager import SecurityManager

logger = logging.getLogger("JaliMaker.SetupTab")


class SetupTab(QWidget):
    """Password-protected setup tab for machine and fixture parameters."""

    settings_saved = Signal()

    def __init__(self, config: ConfigManager, security: SecurityManager, parent=None):
        super().__init__(parent)
        self._config   = config
        self._security = security
        self._locked   = True
        self._build_ui()
        self._load_from_config()
        self._apply_lock(True)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        # Lock banner
        self._lock_bar = QWidget()
        lock_row = QHBoxLayout(self._lock_bar)
        lock_row.setContentsMargins(8, 4, 8, 4)
        self._lock_icon = QLabel("🔒  Setup is locked")
        self._lock_icon.setObjectName("statusWarn")
        lock_row.addWidget(self._lock_icon)
        lock_row.addStretch()

        self._btn_unlock = QPushButton("Unlock Setup")
        self._btn_unlock.setObjectName("accessBtn")
        self._btn_unlock.clicked.connect(self._on_unlock)
        lock_row.addWidget(self._btn_unlock)

        self._btn_change_pw = QPushButton("Change Password")
        self._btn_change_pw.setObjectName("dangerBtn")
        self._btn_change_pw.setVisible(False)
        self._btn_change_pw.clicked.connect(self._on_change_password)
        lock_row.addWidget(self._btn_change_pw)

        outer.addWidget(self._lock_bar)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(4, 4, 4, 4)

        # Sections
        content_layout.addWidget(self._build_machine_options())
        content_layout.addWidget(self._build_machine_params())
        content_layout.addWidget(self._build_fixture_params())
        content_layout.addWidget(self._build_panelization())
        content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # Save button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_save = QPushButton("💾  Save All Settings")
        self._btn_save.setObjectName("saveBtn")
        self._btn_save.setFixedWidth(200)
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        outer.addLayout(btn_row)

    def _row(self, parent_layout, label_txt: str, widget, tooltip: str = "") -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label_txt)
        lbl.setFixedWidth(190)
        if tooltip:
            lbl.setToolTip(tooltip)
        row.addWidget(lbl)
        row.addWidget(widget)
        parent_layout.addLayout(row)
        return widget

    def _le(self, placeholder: str = "") -> QLineEdit:
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        w.setFixedWidth(160)
        return w

    # ── Machine options ───────────────────────────────────────────────────────

    def _build_machine_options(self) -> QGroupBox:
        gb = QGroupBox("Machine Options")
        grid = QGridLayout(gb)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)

        def cb(text, tooltip=""):
            c = QCheckBox(text)
            if tooltip:
                c.setToolTip(tooltip)
            return c

        self.chk_parking     = cb("Enable Parking",              "Park spindle at job end")
        self.chk_buzzer      = cb("Enable Buzzer",               "Sound alert on completion")
        self.chk_combine_pin = cb("Combine Pinning + Drilling",  "Merge pin & drill in one file")
        self.chk_border      = cb("Border Engrave",              "Enable border cutting")
        self.chk_border_merge= cb("Merge Border + Drilling",     "Combine border and drilling")
        self.chk_chamfer     = cb("Generate Chamfer GCode",      "Generate bottom-side chamfer")
        self.chk_pin_gcode   = cb("Generate Separate Pin GCode", "Produce standalone pin file")
        self.chk_dwell_top   = cb("Dwell at Depth (Top)",        "Pause at bottom of top holes")
        self.chk_dwell_bot   = cb("Dwell at Depth (Bottom)",     "Pause at bottom of chamfer holes")
        self.chk_fixture_pin = cb("Fixture Reference Pinning",   "Use fixture coordinates for pins")

        opts = [
            self.chk_parking, self.chk_buzzer, self.chk_combine_pin,
            self.chk_border, self.chk_border_merge, self.chk_chamfer,
            self.chk_pin_gcode, self.chk_dwell_top, self.chk_dwell_bot,
            self.chk_fixture_pin,
        ]
        for i, o in enumerate(opts):
            grid.addWidget(o, i // 2, i % 2)

        self._machine_option_widgets = opts
        return gb

    # ── Machine parameters ────────────────────────────────────────────────────

    def _build_machine_params(self) -> QGroupBox:
        gb = QGroupBox("Machine Parameters")
        layout = QVBoxLayout(gb)
        layout.setSpacing(6)

        self.le_preamble   = QLineEdit()
        self.le_postamble  = QLineEdit()
        self.le_retract    = self._le("mm")
        self.le_z_initial  = self._le("mm")
        self.le_feed_rate  = self._le("mm/min")
        self.le_spindle_d  = self._le("s")
        self.le_dwell_d    = self._le("s")
        self.le_drill_dia  = self._le("mm")
        self.le_route_dia  = self._le("mm")

        fields = [
            ("Preamble GCode",      self.le_preamble,  "GCode header block"),
            ("Postamble GCode",     self.le_postamble, "GCode footer block"),
            ("Retract Height (mm)", self.le_retract,   "Z height between holes"),
            ("Z Safe Initial (mm)", self.le_z_initial, "Initial Z safe height"),
            ("Feed Rate (mm/min)",  self.le_feed_rate, "Drilling feed rate"),
            ("Spindle Delay (s)",   self.le_spindle_d, "Spindle warm-up delay"),
            ("Dwell at Depth (s)",  self.le_dwell_d,   "Pause time at hole bottom"),
            ("Drill Diameter (mm)", self.le_drill_dia, "Main drill tool diameter"),
            ("Routing Tool (mm)",   self.le_route_dia, "Border routing tool diameter"),
        ]
        for label, widget, tip in fields:
            self._row(layout, label, widget, tip)

        # Optimisation
        row = QHBoxLayout()
        lbl = QLabel("Path Optimisation")
        lbl.setFixedWidth(190)
        self.cmb_optim = QComboBox()
        self.cmb_optim.addItems([
            "Auto (Boustrophedon)", "Top → Bottom", "Bottom → Top",
            "Left → Right", "Right → Left"
        ])
        self.cmb_optim.setFixedWidth(160)
        row.addWidget(lbl)
        row.addWidget(self.cmb_optim)
        row.addStretch()
        layout.addLayout(row)

        self._machine_param_widgets = [
            self.le_preamble, self.le_postamble, self.le_retract, self.le_z_initial,
            self.le_feed_rate, self.le_spindle_d, self.le_dwell_d, self.le_drill_dia,
            self.le_route_dia, self.cmb_optim,
        ]
        return gb

    # ── Fixture parameters ────────────────────────────────────────────────────

    def _build_fixture_params(self) -> QGroupBox:
        gb = QGroupBox("Fixture Parameters")
        layout = QVBoxLayout(gb)
        layout.setSpacing(6)

        self.le_fix_cd_x  = self._le("mm")
        self.le_fix_cd_y  = self._le("mm")
        self.le_fix_x     = self._le("mm")
        self.le_fix_y     = self._le("mm")
        self.le_flip_tol_x= self._le("mm")
        self.le_flip_tol_y= self._le("mm")

        fields = [
            ("Fixture Pin CD X (mm)",    self.le_fix_cd_x,   "Fixture pin centre distance X"),
            ("Fixture Pin CD Y (mm)",    self.le_fix_cd_y,   "Fixture pin centre distance Y"),
            ("First Pin X (mm)",         self.le_fix_x,      "First fixture pin X position"),
            ("First Pin Y (mm)",         self.le_fix_y,      "First fixture pin Y position"),
            ("Flip Tolerance X (mm)",    self.le_flip_tol_x, "X tolerance for flip reference"),
            ("Flip Tolerance Y (mm)",    self.le_flip_tol_y, "Y tolerance for flip reference"),
        ]
        for label, widget, tip in fields:
            self._row(layout, label, widget, tip)

        # Flip axis
        row = QHBoxLayout()
        lbl = QLabel("Flip Axis")
        lbl.setFixedWidth(190)
        lbl.setToolTip("Board flip method for bottom-side GCode")
        self.cmb_flip_axis = QComboBox()
        self.cmb_flip_axis.addItems([
            "X-axis flip (mirror along Y)",
            "Y-axis flip (mirror along X)",
            "Centre flip (mirror both axes)",
        ])
        self.cmb_flip_axis.setFixedWidth(240)
        row.addWidget(lbl)
        row.addWidget(self.cmb_flip_axis)
        row.addStretch()
        layout.addLayout(row)

        # Border cutting
        row2 = QHBoxLayout()
        lbl2 = QLabel("Border Cutting")
        lbl2.setFixedWidth(190)
        self.cmb_border_cut = QComboBox()
        self.cmb_border_cut.addItems(["Inside Cut", "Outside Cut", "On Contour"])
        self.cmb_border_cut.setFixedWidth(160)
        row2.addWidget(lbl2)
        row2.addWidget(self.cmb_border_cut)
        row2.addStretch()
        layout.addLayout(row2)

        self._fixture_widgets = [
            self.le_fix_cd_x, self.le_fix_cd_y, self.le_fix_x, self.le_fix_y,
            self.le_flip_tol_x, self.le_flip_tol_y, self.cmb_flip_axis, self.cmb_border_cut,
        ]
        return gb

    # ── Panelization ──────────────────────────────────────────────────────────

    def _build_panelization(self) -> QGroupBox:
        gb = QGroupBox("Panelization (Array Copy)")
        layout = QVBoxLayout(gb)
        layout.setSpacing(6)

        self.chk_panel = QCheckBox("Enable Panelization")
        layout.addWidget(self.chk_panel)

        self.le_panel_rows   = self._le("rows")
        self.le_panel_cols   = self._le("cols")
        self.le_panel_off_x  = self._le("mm")
        self.le_panel_off_y  = self._le("mm")

        fields = [
            ("Rows",      self.le_panel_rows,  "Number of rows"),
            ("Columns",   self.le_panel_cols,  "Number of columns"),
            ("Offset X",  self.le_panel_off_x, "X spacing between panels (mm)"),
            ("Offset Y",  self.le_panel_off_y, "Y spacing between panels (mm)"),
        ]
        for label, widget, tip in fields:
            self._row(layout, label, widget, tip)

        self._panel_widgets = [
            self.le_panel_rows, self.le_panel_cols,
            self.le_panel_off_x, self.le_panel_off_y,
        ]
        return gb

    # ── Lock / unlock ─────────────────────────────────────────────────────────

    def _apply_lock(self, locked: bool):
        self._locked = locked
        all_widgets = (
            self._machine_option_widgets +
            self._machine_param_widgets  +
            self._fixture_widgets        +
            self._panel_widgets          +
            [self.chk_panel, self._btn_save, self.cmb_flip_axis, self.cmb_border_cut]
        )
        for w in all_widgets:
            w.setEnabled(not locked)

        if locked:
            self._lock_icon.setText("🔒  Setup is locked  –  click Unlock to edit")
            self._lock_icon.setObjectName("statusWarn")
            self._btn_change_pw.setVisible(False)
        else:
            self._lock_icon.setText("🔓  Setup unlocked  –  edit freely, then Save")
            self._lock_icon.setObjectName("statusOk")
            self._btn_change_pw.setVisible(True)
        # Force style refresh
        self._lock_icon.style().unpolish(self._lock_icon)
        self._lock_icon.style().polish(self._lock_icon)

    def _on_unlock(self):
        if self._security.dev_mode:
            logger.info("Dev mode: bypass password")
            self._apply_lock(False)
            return

        if not self._security.has_password():
            self._security.initialise_default_password()
            QMessageBox.information(
                self, "Default Password Set",
                "No password was set.\n"
                f"Default password is: indus1234\n\n"
                "Please change it via 'Change Password' after unlocking."
            )

        pw, ok = QInputDialog.getText(
            self, "Setup Password", "Enter password:", QLineEdit.Password
        )
        if ok and self._security.verify(pw):
            self._apply_lock(False)
        elif ok:
            QMessageBox.warning(self, "Access Denied", "Incorrect password.")

    def _on_change_password(self):
        new_pw, ok1 = QInputDialog.getText(
            self, "New Password", "Enter new password:", QLineEdit.Password
        )
        if not ok1 or not new_pw.strip():
            return
        conf_pw, ok2 = QInputDialog.getText(
            self, "Confirm Password", "Confirm new password:", QLineEdit.Password
        )
        if ok2 and new_pw == conf_pw:
            self._security.set_password(new_pw)
            QMessageBox.information(self, "Password Changed", "Password updated successfully.")
        else:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")

    # ── Config I/O ────────────────────────────────────────────────────────────

    def _load_from_config(self):
        c = self._config
        # Options
        self.chk_parking.setChecked(c.get_bool("MACHINE", "parking"))
        self.chk_buzzer.setChecked(c.get_bool("MACHINE", "buzzer"))
        self.chk_combine_pin.setChecked(c.get_bool("MACHINE", "pinning_with_drilling"))
        self.chk_border.setChecked(c.get_bool("MACHINE", "border_engrave"))
        self.chk_border_merge.setChecked(c.get_bool("MACHINE", "border_with_drilling"))
        self.chk_chamfer.setChecked(c.get_bool("MACHINE", "chamfer_gcode"))
        self.chk_pin_gcode.setChecked(c.get_bool("MACHINE", "pin_gcode"))
        self.chk_dwell_top.setChecked(c.get_bool("MACHINE", "dwell_top"))
        self.chk_dwell_bot.setChecked(c.get_bool("MACHINE", "dwell_bottom"))
        self.chk_fixture_pin.setChecked(c.get_bool("FIXTURE", "fixture_pinning"))
        # Machine params
        self.le_preamble.setText(c.get("MACHINE", "preamble"))
        self.le_postamble.setText(c.get("MACHINE", "postamble"))
        self.le_retract.setText(c.get("MACHINE", "retract"))
        self.le_z_initial.setText(c.get("MACHINE", "z_initial"))
        self.le_feed_rate.setText(c.get("MACHINE", "feed_rate"))
        self.le_spindle_d.setText(c.get("MACHINE", "spindle_delay"))
        self.le_dwell_d.setText(c.get("MACHINE", "dwell_depth"))
        self.le_drill_dia.setText(c.get("MACHINE", "drill_dia"))
        self.le_route_dia.setText(c.get("MACHINE", "routing_tool_dia"))
        optim_map = {"auto": 0, "top_bottom": 1, "bottom_top": 2, "left_right": 3, "right_left": 4}
        self.cmb_optim.setCurrentIndex(optim_map.get(c.get("MACHINE", "optimization", "auto"), 0))
        # Fixture
        self.le_fix_cd_x.setText(c.get("FIXTURE", "fixture_cd_x"))
        self.le_fix_cd_y.setText(c.get("FIXTURE", "fixture_cd_y"))
        self.le_fix_x.setText(c.get("FIXTURE", "fixture_x"))
        self.le_fix_y.setText(c.get("FIXTURE", "fixture_y"))
        self.le_flip_tol_x.setText(c.get("FIXTURE", "flip_tolerance_x"))
        self.le_flip_tol_y.setText(c.get("FIXTURE", "flip_tolerance_y"))
        self.cmb_flip_axis.setCurrentIndex(c.get_int("FIXTURE", "flip_axis"))
        self.cmb_border_cut.setCurrentIndex(c.get_int("FIXTURE", "border_cutting"))
        # Panelization
        self.chk_panel.setChecked(c.get_bool("PANELIZATION", "enabled"))
        self.le_panel_rows.setText(c.get("PANELIZATION", "rows", "2"))
        self.le_panel_cols.setText(c.get("PANELIZATION", "columns", "2"))
        self.le_panel_off_x.setText(c.get("PANELIZATION", "offset_x", "10"))
        self.le_panel_off_y.setText(c.get("PANELIZATION", "offset_y", "10"))

    def _on_save(self):
        optim_vals = ["auto", "top_bottom", "bottom_top", "left_right", "right_left"]
        c = self._config
        # Machine options
        c.set("MACHINE", "parking",              self.chk_parking.isChecked())
        c.set("MACHINE", "buzzer",               self.chk_buzzer.isChecked())
        c.set("MACHINE", "pinning_with_drilling",self.chk_combine_pin.isChecked())
        c.set("MACHINE", "border_engrave",       self.chk_border.isChecked())
        c.set("MACHINE", "border_with_drilling", self.chk_border_merge.isChecked())
        c.set("MACHINE", "chamfer_gcode",        self.chk_chamfer.isChecked())
        c.set("MACHINE", "pin_gcode",            self.chk_pin_gcode.isChecked())
        c.set("MACHINE", "dwell_top",            self.chk_dwell_top.isChecked())
        c.set("MACHINE", "dwell_bottom",         self.chk_dwell_bot.isChecked())
        # Machine params
        c.set("MACHINE", "preamble",         self.le_preamble.text())
        c.set("MACHINE", "postamble",        self.le_postamble.text())
        c.set("MACHINE", "retract",          self.le_retract.text())
        c.set("MACHINE", "z_initial",        self.le_z_initial.text())
        c.set("MACHINE", "feed_rate",        self.le_feed_rate.text())
        c.set("MACHINE", "spindle_delay",    self.le_spindle_d.text())
        c.set("MACHINE", "dwell_depth",      self.le_dwell_d.text())
        c.set("MACHINE", "drill_dia",        self.le_drill_dia.text())
        c.set("MACHINE", "routing_tool_dia", self.le_route_dia.text())
        c.set("MACHINE", "optimization",     optim_vals[self.cmb_optim.currentIndex()])
        # Fixture
        c.set("FIXTURE", "fixture_pinning",  self.chk_fixture_pin.isChecked())
        c.set("FIXTURE", "fixture_cd_x",     self.le_fix_cd_x.text())
        c.set("FIXTURE", "fixture_cd_y",     self.le_fix_cd_y.text())
        c.set("FIXTURE", "fixture_x",        self.le_fix_x.text())
        c.set("FIXTURE", "fixture_y",        self.le_fix_y.text())
        c.set("FIXTURE", "flip_tolerance_x", self.le_flip_tol_x.text())
        c.set("FIXTURE", "flip_tolerance_y", self.le_flip_tol_y.text())
        c.set("FIXTURE", "flip_axis",        self.cmb_flip_axis.currentIndex())
        c.set("FIXTURE", "border_cutting",   self.cmb_border_cut.currentIndex())
        # Panelization
        c.set("PANELIZATION", "enabled",  self.chk_panel.isChecked())
        c.set("PANELIZATION", "rows",     self.le_panel_rows.text())
        c.set("PANELIZATION", "columns",  self.le_panel_cols.text())
        c.set("PANELIZATION", "offset_x", self.le_panel_off_x.text())
        c.set("PANELIZATION", "offset_y", self.le_panel_off_y.text())
        c.save()
        logger.info("Setup settings saved")
        self.settings_saved.emit()
        QMessageBox.information(self, "Saved", "All settings saved to grill_config.ini")

    # ── Public getters (called by main window) ────────────────────────────────

    def get_machine_options(self) -> dict:
        return {
            "parking":           self.chk_parking.isChecked(),
            "buzzer":            self.chk_buzzer.isChecked(),
            "combine_pin_drill": self.chk_combine_pin.isChecked(),
            "enable_border":     self.chk_border.isChecked(),
            "merge_border_drill":self.chk_border_merge.isChecked(),
            "enable_chamfer":    self.chk_chamfer.isChecked(),
            "enable_pin_gcode":  self.chk_pin_gcode.isChecked(),
            "enable_dwell_top":  self.chk_dwell_top.isChecked(),
            "enable_dwell_bot":  self.chk_dwell_bot.isChecked(),
            "fixture_pinning":   self.chk_fixture_pin.isChecked(),
        }

    def get_machine_params(self) -> dict:
        optim_vals = ["auto", "top_bottom", "bottom_top", "left_right", "right_left"]
        return {
            "preamble":       self.le_preamble.text(),
            "postamble":      self.le_postamble.text(),
            "retract":        float(self.le_retract.text() or "5"),
            "z_initial":      float(self.le_z_initial.text() or "20"),
            "feed_rate":      float(self.le_feed_rate.text() or "4000"),
            "spindle_delay":  float(self.le_spindle_d.text() or "2"),
            "dwell":          float(self.le_dwell_d.text() or "0.2"),
            "drill_dia":      float(self.le_drill_dia.text() or "2.0"),
            "routing_tool_dia": float(self.le_route_dia.text() or "1.0"),
            "optimization":   optim_vals[self.cmb_optim.currentIndex()],
        }

    def get_fixture_params(self) -> dict:
        return {
            "fixture_cd_x":    float(self.le_fix_cd_x.text() or "140"),
            "fixture_cd_y":    float(self.le_fix_cd_y.text() or "460"),
            "fixture_pin_x":   float(self.le_fix_x.text() or "1"),
            "fixture_pin_y":   float(self.le_fix_y.text() or "10"),
            "flip_tolerance_x":float(self.le_flip_tol_x.text() or "2"),
            "flip_tolerance_y":float(self.le_flip_tol_y.text() or "2"),
            "flip_axis":       self.cmb_flip_axis.currentIndex(),
            "border_cutting":  self.cmb_border_cut.currentIndex(),
        }

    def get_panelization(self) -> dict:
        return {
            "enabled":    self.chk_panel.isChecked(),
            "rows":       int(self.le_panel_rows.text() or "1"),
            "cols":       int(self.le_panel_cols.text() or "1"),
            "offset_x":  float(self.le_panel_off_x.text() or "0"),
            "offset_y":  float(self.le_panel_off_y.text() or "0"),
        }
