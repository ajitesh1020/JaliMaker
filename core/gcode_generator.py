# -*- coding: utf-8 -*-
"""
GCode generation module.
Converts CalcResults + DrillParams into LinuxCNC-compatible GCode strings.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from core.calculator import DrillParams, CalcResults
from core.version import VERSION, APP_NAME, COMPANY

logger = logging.getLogger("JaliMaker.GCode")


class GCodeGenerator:
    """Generates all GCode files from calculation results."""

    PATTERN_NAMES = {1: "Triangular", 2: "Rhombus", 3: "Square"}

    def generate_all(self, p: DrillParams, r: CalcResults) -> dict:
        """
        Generate all GCode files according to settings.
        Returns dict: {'top': [...], 'bottom': [...], 'pin': [...], 'border': [...]}
        """
        output = {"top": [], "bottom": [], "pin": [], "border": []}

        logger.info("Generating GCode files")

        # ── Top / combined ────────────────────────────────────────────────────
        if p.combine_pin_drill:
            output["top"] = self._gen_top(r, p, label="TOP + PINNING", include_pins=True)
        elif p.merge_border_drill and p.enable_border:
            output["top"] = self._gen_border_and_drill(r, p)
        else:
            output["top"] = self._gen_top(r, p, label="TOP")

        # ── Bottom (chamfer) ──────────────────────────────────────────────────
        if p.enable_chamfer and r.bot_coords:  # enable_chamfer
            output["bottom"] = self._gen_bottom(r, p)

        # ── Separate pin GCode ────────────────────────────────────────────────
        if p.enable_pin_gcode and not p.combine_pin_drill:
            output["pin"] = self._gen_pin(r, p)

        # ── Border GCode ──────────────────────────────────────────────────────
        if p.enable_border and not p.merge_border_drill:
            output["border"] = self._gen_border(r, p)

        logger.info(f"GCode lines: top={len(output['top'])}  "
                    f"bottom={len(output['bottom'])}  "
                    f"pin={len(output['pin'])}  "
                    f"border={len(output['border'])}")
        return output

    # ── File I/O ──────────────────────────────────────────────────────────────

    def save_all(self, gcode_dict: dict, out_dir: Path, base_name: str = "jali") -> List[Path]:
        """Write non-empty GCode lists to .ngc files; return saved paths."""
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        suffixes = {"top": "top", "bottom": "bottom", "pin": "pin", "border": "border"}
        for key, lines in gcode_dict.items():
            if lines:
                path = out_dir / f"{base_name}_{suffixes[key]}.ngc"
                path.write_text("\n".join(lines), encoding="utf-8")
                saved.append(path)
                logger.info(f"Saved {key} GCode → {path}  ({len(lines)} lines)")
        return saved

    # ── Private generators ────────────────────────────────────────────────────

    def _header(self, p: DrillParams, label: str, total_holes: int) -> List[str]:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"({APP_NAME} v{VERSION} | {COMPANY})",
            f"(Generated: {ts})",
            f"(File: {label})",
            f"(Pattern: {self.PATTERN_NAMES.get(p.pattern, '?')})",
            f"(Total holes: {total_holes})",
            f"(Drill dia: {p.drill_dia:.2f} mm  Feed: {p.feed_rate} mm/min)",
            f"(Depth: {p.depth:.2f} mm  Retract: {p.retract:.2f} mm)",
            "",
            p.header,
            f"G4 P{p.spindle_delay:.1f}    (spindle warm-up delay)",
            f"G0 Z{p.initial_z:.3f}",
        ]
        return lines

    def _footer(self, p: DrillParams) -> List[str]:
        lines = []
        if p.parking:
            lines += ["G0 X0 Y0    (park position)"]
        if p.buzzer:
            lines += ["M300 S440 P500    (buzzer)"]
        lines += [p.footer, ""]
        return lines

    def _drill_move(
        self,
        x: float,
        y: float,
        depth: float,
        retract: float,
        feed: float,
        dwell: float | None,
        peg: bool,
        peg_depth: float,
        peg_retract: float,
        index: int,
    ) -> List[str]:
        """Return GCode lines for a single drilling move."""
        lines = [f"(Hole {index + 1}: X={x:.4f} Y={y:.4f})"]
        lines.append(f"G0 X{x:.4f} Y{y:.4f}")
        lines.append(f"G0 Z{retract:.3f}")

        if peg:
            # Peck drilling: multiple incremental passes
            z = 0.0
            pass_num = 1
            while z < depth:
                z = min(z + peg_depth, depth)
                lines.append(f"G1 Z-{z:.3f} F{feed}")
                if dwell is not None:
                    lines.append(f"G4 P{dwell:.2f}")
                lines.append(f"G0 Z{peg_retract:.3f}")
                pass_num += 1
        else:
            lines.append(f"G1 Z-{depth:.3f} F{feed}")
            if dwell is not None:
                lines.append(f"G4 P{dwell:.2f}")
            lines.append(f"G0 Z{retract:.3f}")

        return lines

    def _gen_top(
        self,
        r: CalcResults,
        p: DrillParams,
        label: str = "TOP",
        include_pins: bool = False,
    ) -> List[str]:
        lines = self._header(p, label, r.total_holes)
        dwell = float(p.dwell) if p.enable_dwell_top else None

        if include_pins:
            lines.append("( === Dowel pin drilling === )")
            lines += self._pin_moves(r.pin_coords, p)
            lines.append("( === Main drilling === )")

        for i, (x, y) in enumerate(r.top_coords):
            lines += self._drill_move(
                x, y, p.depth, p.retract, p.feed_rate,
                dwell, p.peg_drilling, p.peg_depth, p.peg_retract, i
            )
        lines += self._footer(p)
        return lines

    def _gen_bottom(self, r: CalcResults, p: DrillParams) -> List[str]:
        lines = self._header(p, "BOTTOM (chamfer)", r.total_holes)
        dwell = float(p.dwell) if p.enable_dwell_bottom else None

        for i, (x, y) in enumerate(r.bot_coords):
            lines.append(f"(Chamfer hole {i + 1}: X={x:.4f} Y={y:.4f})")
            lines.append(f"G0 X{x:.4f} Y{y:.4f}")
            lines.append(f"G0 Z{p.retract:.3f}")
            lines.append(f"G1 Z-{p.ch_depth:.3f} F{p.feed_rate}")
            if dwell:
                lines.append(f"G4 P{dwell:.2f}")
            lines.append(f"G0 Z{p.retract:.3f}")

        lines += self._footer(p)
        return lines

    def _gen_pin(self, r: CalcResults, p: DrillParams) -> List[str]:
        lines = self._header(p, "PINNING", len(r.pin_coords))
        lines += self._pin_moves(r.pin_coords, p)
        lines += self._footer(p)
        return lines

    def _pin_moves(self, pins: List[Tuple[float, float]], p: DrillParams) -> List[str]:
        lines = []
        for i, (x, y) in enumerate(pins):
            lines.append(f"(Pin {i + 1}: X={x:.4f} Y={y:.4f})")
            lines.append(f"G0 X{x:.4f} Y{y:.4f}")
            lines.append(f"G0 Z{p.retract:.3f}")
            lines.append(f"G1 Z-{p.pin_depth:.3f} F{p.feed_rate}")
            lines.append(f"G0 Z{p.retract:.3f}")
        return lines

    def _gen_border(self, r: CalcResults, p: DrillParams) -> List[str]:
        lines = self._header(p, "BORDER", 0)
        lines += self._border_moves(p)
        lines += self._footer(p)
        return lines

    def _gen_border_and_drill(self, r: CalcResults, p: DrillParams) -> List[str]:
        lines = self._header(p, "TOP + BORDER", r.total_holes)
        lines.append("( === Border cut === )")
        lines += self._border_moves(p)
        lines.append(f"G0 Z{p.initial_z:.3f}")
        lines.append("( === Drilling === )")
        dwell = float(p.dwell) if p.enable_dwell_top else None
        for i, (x, y) in enumerate(r.top_coords):
            lines += self._drill_move(
                x, y, p.depth, p.retract, p.feed_rate,
                dwell, p.peg_drilling, p.peg_depth, p.peg_retract, i
            )
        lines += self._footer(p)
        return lines

    def _border_moves(self, p: DrillParams) -> List[str]:
        r_dia = p.routing_tool_dia / 2
        if p.border_cutting == 0:
            off = -r_dia
        elif p.border_cutting == 1:
            off = r_dia
        else:
            off = 0.0

        x0 = round(p.gap_x + off, 4)
        y0 = round(p.gap_y + off, 4)
        x1 = round(p.total_size_x - p.gap_c + off, 4)
        y1 = round(p.total_size_y - p.gap_d + off, 4)

        return [
            f"G0 X{x0:.4f} Y{y0:.4f}",
            f"G1 Z-{p.depth:.3f} F{p.feed_rate}",
            f"G1 X{x1:.4f} Y{y0:.4f}",
            f"G1 X{x1:.4f} Y{y1:.4f}",
            f"G1 X{x0:.4f} Y{y1:.4f}",
            f"G1 X{x0:.4f} Y{y0:.4f}",
            f"G0 Z{p.retract:.3f}",
        ]
