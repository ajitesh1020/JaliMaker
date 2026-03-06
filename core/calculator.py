# -*- coding: utf-8 -*-
"""
Core mathematical engine for Jali/Grill pattern calculations.
All geometry and path-optimisation lives here – no Qt imports.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Literal

import numpy as np

logger = logging.getLogger("JaliMaker.Calculator")

ROUND_POS = 4   # position rounding
ROUND_DIM = 2   # dimension rounding

Pattern = Literal[1, 2, 3]   # 1=Triangular, 2=Rhombus, 3=Square
OptMode = Literal["auto", "top_bottom", "bottom_top", "left_right", "right_left"]


@dataclass
class DrillParams:
    """All validated input parameters."""
    total_size_x: float
    total_size_y: float
    gap_x: float           # border left
    gap_y: float           # border top
    gap_c: float           # border right
    gap_d: float           # border bottom
    holes_x: int
    holes_y: int
    dowel_x: float
    dowel_y: float
    depth: float
    pin_depth: float
    ch_depth: float
    peg_depth: float
    peg_retract: float
    peg_drilling: bool
    pattern: Pattern
    flip_axis: int         # 0=X-axis, 1=Y-axis, 2=Center
    flip_tolerance_x: float
    flip_tolerance_y: float
    fixture_pinning: bool
    fixture_cd_x: float
    fixture_cd_y: float
    fixture_pin_x: float
    fixture_pin_y: float
    retract: float
    initial_z: float
    feed_rate: float
    spindle_delay: float
    dwell: float
    drill_dia: float
    routing_tool_dia: float
    header: str
    footer: str
    parking: bool
    buzzer: bool
    enable_dwell_top: bool
    enable_dwell_bottom: bool
    enable_chamfer: bool
    enable_pin_gcode: bool
    enable_border: bool
    merge_border_drill: bool
    combine_pin_drill: bool
    border_cutting: int
    optimization: OptMode = "auto"
    panelization: bool = False
    panel_rows: int = 1
    panel_cols: int = 1
    panel_offset_x: float = 0.0
    panel_offset_y: float = 0.0


@dataclass
class CalcResults:
    """Output of perform_calculations()."""
    total_holes: int = 0
    x_working_size: float = 0.0
    y_working_size: float = 0.0
    hole_spacing_x: float = 0.0
    hole_spacing_y: float = 0.0
    shift_bottom_x: float = 0.0
    shift_bottom_y: float = 0.0
    gap_x_computed: float = 0.0
    gap_y_computed: float = 0.0
    ref_shift_x: float = 0.0
    ref_shift_y: float = 0.0
    top_coords: List[Tuple[float, float]] = field(default_factory=list)
    bot_coords: List[Tuple[float, float]] = field(default_factory=list)
    pin_coords: List[Tuple[float, float]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class Calculator:
    """Stateless calculation engine."""

    # ── Public entry point ────────────────────────────────────────────────────

    def calculate(self, p: DrillParams) -> CalcResults:
        """Run full calculation pipeline and return results."""
        r = CalcResults()
        logger.info("=" * 50)
        logger.info("Starting calculation")
        logger.debug(f"Pattern={p.pattern}  holes_x={p.holes_x}  holes_y={p.holes_y}")
        logger.debug(f"Size X={p.total_size_x}  Y={p.total_size_y}")
        logger.debug(f"Gap a={p.gap_x} b={p.gap_y} c={p.gap_c} d={p.gap_d}")

        # Working area
        r.x_working_size = round(p.total_size_x - p.gap_x - p.gap_c, ROUND_DIM)
        r.y_working_size = round(p.total_size_y - p.gap_y - p.gap_d, ROUND_DIM)

        # Spacing
        r.hole_spacing_x, r.hole_spacing_y, r.total_holes = self._compute_spacing(p, r)

        # Validate spacing vs drill diameter
        self._validate_spacing(p, r)

        # Fixture reference shift
        r.shift_bottom_x, r.shift_bottom_y, r.ref_shift_x, r.ref_shift_y = \
            self._compute_fixture_shift(p)

        # Generate raw coordinates
        raw_top, raw_bot = self._generate_coordinates(p, r)

        # Optimise paths
        r.top_coords = self._optimise(raw_top, p.holes_x, p.optimization)
        r.bot_coords  = self._optimise(raw_bot,  p.holes_x, p.optimization)

        # Pin coordinates (4-corner dowel positions)
        r.pin_coords = self._compute_pin_positions(p)

        # Panelization expansion
        if p.panelization and (p.panel_rows > 1 or p.panel_cols > 1):
            r.top_coords = self._panelize(r.top_coords, p)
            r.bot_coords  = self._panelize(r.bot_coords,  p)

        logger.info(f"Calculation complete: {r.total_holes} holes  "
                    f"spacing X={r.hole_spacing_x:.4f}  Y={r.hole_spacing_y:.4f}")
        return r

    # ── Spacing ───────────────────────────────────────────────────────────────

    def _compute_spacing(self, p: DrillParams, r: CalcResults) -> Tuple[float, float, int]:
        """Return (spacing_x, spacing_y, total_holes)."""
        nx = p.holes_x
        ny = p.holes_y

        if p.pattern == 1:     # Triangular (zig-zag) – offset every other row by half pitch
            pattern_cols = 2 * nx
            total = nx * ny
        elif p.pattern == 2:   # Rhombus – offset + 1 extra hole on even rows
            pattern_cols = 2 * nx + 1
            total = int(nx * ny + ny / 2)
        else:                  # Square – uniform grid
            pattern_cols = nx
            total = nx * ny

        denom_x = (pattern_cols - 1) if pattern_cols > 1 else 1
        denom_y = (ny - 1) if ny > 1 else 1

        spacing_x = round(r.x_working_size / denom_x, ROUND_POS)
        spacing_y = round(r.y_working_size / denom_y, ROUND_POS)

        logger.debug(f"pattern_cols={pattern_cols}  spacing_x={spacing_x}  spacing_y={spacing_y}")
        return spacing_x, spacing_y, total

    # ── Coordinate generation ─────────────────────────────────────────────────

    def _generate_coordinates(
        self, p: DrillParams, r: CalcResults
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """Generate raw (un-optimised) top and bottom coordinates."""
        top_coords: List[Tuple[float, float]] = []
        bot_coords:  List[Tuple[float, float]] = []

        sx = r.hole_spacing_x
        sy = r.hole_spacing_y

        for row in range(p.holes_y):
            cols_in_row = p.holes_x + (1 if p.pattern == 2 and row % 2 == 1 else 0)
            row_offset_x = 0.0

            if p.pattern in (1, 2):
                if row % 2 == 1:        # odd rows shifted half a pitch
                    row_offset_x = sx

            for col in range(cols_in_row):
                if p.pattern in (1, 2):
                    # Interleaved columns: 0, 2, 4 … => physical positions spaced 2*sx
                    x = p.gap_x + sx + col * 2 * sx - row_offset_x
                else:                   # Square – uniform
                    x = p.gap_x + col * sx

                y = p.gap_y + row * sy

                x = round(x, ROUND_POS)
                y = round(y, ROUND_POS)

                top_coords.append((x, y))

                # ── Flip / mirror ─────────────────────────────────────────────
                bx, by = self._mirror(x, y, p, r)
                bot_coords.append((round(bx, ROUND_POS), round(by, ROUND_POS)))

        logger.debug(f"Generated {len(top_coords)} top coords and {len(bot_coords)} bottom coords")
        return top_coords, bot_coords

    def _mirror(
        self, x: float, y: float, p: DrillParams, r: CalcResults
    ) -> Tuple[float, float]:
        """Mirror a coordinate according to flip_axis and fixture shift."""
        sx = r.shift_bottom_x
        sy = r.shift_bottom_y

        if p.flip_axis == 0:        # X-axis flip → mirror Y
            bx = p.total_size_x - x + sx
            by = y + sy
        elif p.flip_axis == 1:      # Y-axis flip → mirror X
            bx = x + sx
            by = p.total_size_y - y + sy
        else:                       # Centre flip → mirror both
            bx = p.total_size_x - x + sx
            by = p.total_size_y - y + sy

        return bx, by

    # ── Path optimisation ─────────────────────────────────────────────────────

    def _optimise(
        self,
        coords: List[Tuple[float, float]],
        holes_per_row: int,
        mode: OptMode,
    ) -> List[Tuple[float, float]]:
        """Re-order coordinates to minimise rapid travel distance."""
        if not coords or holes_per_row < 1:
            return coords

        arr = np.array(coords)
        n_rows = math.floor(len(arr) / holes_per_row)
        remainder = len(arr) - n_rows * holes_per_row

        rows = [arr[i * holes_per_row:(i + 1) * holes_per_row] for i in range(n_rows)]
        if remainder:
            rows.append(arr[n_rows * holes_per_row:])

        result: List[Tuple[float, float]] = []

        # Determine row traversal order
        if mode in ("auto", "top_bottom"):
            row_order = range(len(rows))
        elif mode == "bottom_top":
            row_order = range(len(rows) - 1, -1, -1)
        elif mode == "left_right":
            row_order = range(len(rows))
        elif mode == "right_left":
            row_order = range(len(rows) - 1, -1, -1)
        else:
            row_order = range(len(rows))

        for idx, ri in enumerate(row_order):
            row_pts = rows[ri]
            # Boustrophedon (serpentine): alternate direction each row
            if mode in ("auto", "top_bottom", "bottom_top"):
                reverse = (idx % 2 == 1)
            elif mode == "left_right":
                reverse = False
            else:
                reverse = True

            pts = list(reversed(row_pts)) if reverse else list(row_pts)
            result.extend([(round(float(pt[0]), ROUND_POS), round(float(pt[1]), ROUND_POS)) for pt in pts])

        logger.debug(f"Optimised {len(result)} points  mode={mode}")
        return result

    # ── Fixture shift ─────────────────────────────────────────────────────────

    def _compute_fixture_shift(self, p: DrillParams) -> Tuple[float, float, float, float]:
        """Compute reference shift for bottom-side GCode."""
        if not p.fixture_pinning:
            return 0.0, 0.0, 0.0, 0.0

        xx = (p.total_size_x - p.fixture_cd_x) / 2
        yy = (p.total_size_y - p.fixture_cd_y) / 2

        shift_x = round(p.fixture_pin_x - xx, ROUND_POS)
        shift_y = round(p.flip_tolerance_y, ROUND_POS)

        ref_x = round(-shift_x, ROUND_POS)
        ref_y = round(shift_y, ROUND_POS)

        logger.debug(f"Fixture shift: dx={shift_x}  dy={shift_y}  ref_x={ref_x}  ref_y={ref_y}")
        return shift_x, shift_y, ref_x, ref_y

    # ── Dowel / pin positions ─────────────────────────────────────────────────

    def _compute_pin_positions(self, p: DrillParams) -> List[Tuple[float, float]]:
        """Return 4-corner dowel pin positions."""
        if p.fixture_pinning:
            cx = (p.total_size_x - p.fixture_cd_x) / 2
            cy = (p.total_size_y - p.fixture_cd_y) / 2
            pins = [
                (round(cx, ROUND_POS),                round(cy, ROUND_POS)),
                (round(cx + p.fixture_cd_x, ROUND_POS), round(cy, ROUND_POS)),
                (round(cx, ROUND_POS),                round(cy + p.fixture_cd_y, ROUND_POS)),
                (round(cx + p.fixture_cd_x, ROUND_POS), round(cy + p.fixture_cd_y, ROUND_POS)),
            ]
        else:
            pins = [
                (round(p.dowel_x, ROUND_POS),                         round(p.dowel_y, ROUND_POS)),
                (round(p.total_size_x - p.dowel_x, ROUND_POS),        round(p.dowel_y, ROUND_POS)),
                (round(p.dowel_x, ROUND_POS),                         round(p.total_size_y - p.dowel_y, ROUND_POS)),
                (round(p.total_size_x - p.dowel_x, ROUND_POS),        round(p.total_size_y - p.dowel_y, ROUND_POS)),
            ]
        logger.debug(f"Pin positions: {pins}")
        return pins

    # ── Panelization ──────────────────────────────────────────────────────────

    def _panelize(
        self, coords: List[Tuple[float, float]], p: DrillParams
    ) -> List[Tuple[float, float]]:
        """Expand a single-panel coordinate list into an m×n array."""
        out = []
        for row in range(p.panel_rows):
            for col in range(p.panel_cols):
                dx = col * p.panel_offset_x
                dy = row * p.panel_offset_y
                for x, y in coords:
                    out.append((round(x + dx, ROUND_POS), round(y + dy, ROUND_POS)))
        logger.info(f"Panelized: {len(coords)} → {len(out)} coords  "
                    f"({p.panel_rows}×{p.panel_cols})")
        return out

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_spacing(self, p: DrillParams, r: CalcResults) -> None:
        d = p.drill_dia
        if abs(r.hole_spacing_x) < d:
            msg = (f"X spacing {r.hole_spacing_x:.4f} < drill dia {d:.4f}  "
                   "→ reduce holes_x or increase board width")
            r.warnings.append(msg)
            logger.warning(msg)
        if abs(r.hole_spacing_y) < d:
            msg = (f"Y spacing {r.hole_spacing_y:.4f} < drill dia {d:.4f}  "
                   "→ reduce holes_y or increase board height")
            r.warnings.append(msg)
            logger.warning(msg)
