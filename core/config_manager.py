# -*- coding: utf-8 -*-
"""
Configuration manager – reads/writes grill_config.ini.
Creates with defaults if missing.
"""

import logging
from configparser import ConfigParser
from pathlib import Path
from typing import Any

logger = logging.getLogger("JaliMaker.Config")

CONFIG_PATH = Path(__file__).parent.parent / "grill_config.ini"


# ─── Default values ──────────────────────────────────────────────────────────
DEFAULTS: dict[str, dict[str, str]] = {
    "SECURITY": {
        "dev_mode": "false",
        "password_hash": "",
    },
    "GRILL": {
        "total_size_x": "160",
        "total_size_y": "505",
        "border_x": "20",
        "border_y": "5",
        "border_c": "20",
        "border_d": "5",
        "holes_x": "16",
        "holes_y": "100",
        "pin_x": "10",
        "pin_y": "15",
        "depth": "12",
        "pin_depth": "7",
        "ch_depth": "0.8",
        "pattern": "1",
        "peg_depth": "2.5",
        "peg_retract": "3",
        "peg_drilling": "false",
    },
    "MACHINE": {
        "parking": "true",
        "buzzer": "true",
        "pinning_with_drilling": "false",
        "border_engrave": "false",
        "border_with_drilling": "false",
        "chamfer_gcode": "false",
        "pin_gcode": "false",
        "dwell_top": "false",
        "dwell_bottom": "false",
        "preamble": "G17 G21 G90 G64 P0.01  M3 S40000",
        "postamble": "M5 M9 M2",
        "retract": "5",
        "z_initial": "20",
        "feed_rate": "4000",
        "spindle_delay": "2",
        "dwell_depth": "0.2",
        "drill_dia": "2.0",
        "routing_tool_dia": "1.0",
        "optimization": "auto",          # auto / top_bottom / bottom_top / left_right / right_left
    },
    "FIXTURE": {
        "fixture_pinning": "true",
        "fixture_cd_x": "140",
        "fixture_cd_y": "460",
        "fixture_x": "1",
        "fixture_y": "10",
        "flip_tolerance_x": "2",
        "flip_tolerance_y": "2",
        "flip_axis": "0",                # 0=X-flip, 1=Y-flip, 2=Center
        "border_cutting": "1",           # 0=Inside, 1=Outside, 2=On contour
    },
    "PANELIZATION": {
        "enabled": "false",
        "rows": "2",
        "columns": "2",
        "offset_x": "10",
        "offset_y": "10",
    },
    "APP": {
        "last_gcode_dir": "",
        "window_maximized": "true",
        "log_enabled": "true",
    },
}


class ConfigManager:
    """Thread-safe wrapper around ConfigParser with typed accessors."""

    def __init__(self, path: Path = CONFIG_PATH):
        self._path = path
        self._config = ConfigParser()
        self._load_or_create()

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self._config.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        try:
            return self._config.getint(section, key, fallback=fallback)
        except Exception:
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        try:
            return self._config.getfloat(section, key, fallback=fallback)
        except Exception:
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        try:
            return self._config.getboolean(section, key, fallback=fallback)
        except Exception:
            return fallback

    def set(self, section: str, key: str, value: Any) -> None:
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, str(value).lower() if isinstance(value, bool) else str(value))

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            self._config.write(fh)
        logger.info(f"Configuration saved → {self._path}")

    def get_section(self, section: str) -> dict:
        if self._config.has_section(section):
            return dict(self._config[section])
        return {}

    def set_section(self, section: str, data: dict) -> None:
        if not self._config.has_section(section):
            self._config.add_section(section)
        for k, v in data.items():
            self._config.set(section, k, str(v).lower() if isinstance(v, bool) else str(v))

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load_or_create(self) -> None:
        if self._path.exists():
            self._config.read(self._path, encoding="utf-8")
            self._inject_missing_defaults()
            logger.info(f"Config loaded from {self._path}")
        else:
            self._write_defaults()
            logger.warning(f"Config not found – created defaults at {self._path}")

    def _inject_missing_defaults(self) -> None:
        """Add any keys present in DEFAULTS but absent in file (backwards compat)."""
        changed = False
        for section, kv in DEFAULTS.items():
            if not self._config.has_section(section):
                self._config.add_section(section)
                changed = True
            for key, val in kv.items():
                if not self._config.has_option(section, key):
                    self._config.set(section, key, val)
                    changed = True
        if changed:
            self.save()

    def _write_defaults(self) -> None:
        for section, kv in DEFAULTS.items():
            self._config.add_section(section)
            for key, val in kv.items():
                self._config.set(section, key, val)
        self.save()
