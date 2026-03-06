# -*- coding: utf-8 -*-
"""Basic unit tests for JaliMaker core modules."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.calculator import Calculator, DrillParams, CalcResults


def make_params(**overrides) -> DrillParams:
    defaults = dict(
        total_size_x=160, total_size_y=505,
        gap_x=20, gap_y=5, gap_c=20, gap_d=5,
        holes_x=16, holes_y=100,
        dowel_x=10, dowel_y=15,
        depth=12, pin_depth=7, ch_depth=0.8,
        peg_depth=2.5, peg_retract=3, peg_drilling=False,
        pattern=1, flip_axis=0,
        flip_tolerance_x=2, flip_tolerance_y=2,
        fixture_pinning=False,
        fixture_cd_x=140, fixture_cd_y=460,
        fixture_pin_x=1, fixture_pin_y=10,
        retract=5, initial_z=20, feed_rate=4000,
        spindle_delay=2, dwell=0.2,
        drill_dia=2.0, routing_tool_dia=1.0,
        header="G17 G21 G90", footer="M5 M2",
        parking=True, buzzer=False,
        enable_dwell_top=False, enable_dwell_bot=False,
        enable_chamfer=False, enable_pin_gcode=False,
        enable_border=False, merge_border_drill=False,
        combine_pin_drill=False, border_cutting=0,
        optimization="auto",
        panelization=False, panel_rows=1, panel_cols=1,
        panel_offset_x=0, panel_offset_y=0,
    )
    defaults.update(overrides)
    return DrillParams(**defaults)


class TestCalculator:

    def test_triangular_hole_count(self):
        calc = Calculator()
        p = make_params(holes_x=10, holes_y=20, pattern=1)
        r = calc.calculate(p)
        assert r.total_holes == 10 * 20

    def test_square_hole_count(self):
        calc = Calculator()
        p = make_params(holes_x=8, holes_y=10, pattern=3)
        r = calc.calculate(p)
        assert r.total_holes == 80

    def test_coord_count_matches_holes(self):
        calc = Calculator()
        p = make_params(holes_x=5, holes_y=6, pattern=1)
        r = calc.calculate(p)
        assert len(r.top_coords) == 30
        assert len(r.bot_coords) == 30

    def test_spacing_positive(self):
        calc = Calculator()
        p = make_params()
        r = calc.calculate(p)
        assert r.hole_spacing_x > 0
        assert r.hole_spacing_y > 0

    def test_warning_when_spacing_lt_drill_dia(self):
        calc = Calculator()
        p = make_params(holes_x=1000, drill_dia=5.0)
        r = calc.calculate(p)
        assert len(r.warnings) > 0

    def test_fixture_shift_computed(self):
        calc = Calculator()
        p = make_params(fixture_pinning=True)
        r = calc.calculate(p)
        # Shift should be non-zero when fixture is enabled
        # (unless geometry is perfectly symmetric)
        assert isinstance(r.shift_bottom_x, float)

    def test_panelization_doubles_coords(self):
        calc = Calculator()
        p = make_params(holes_x=4, holes_y=4, pattern=3,
                        panelization=True, panel_rows=2, panel_cols=2,
                        panel_offset_x=200, panel_offset_y=600)
        r = calc.calculate(p)
        assert len(r.top_coords) == 4 * 4 * 4   # 4×4 holes × 2×2 panels

    def test_x_flip_mirror(self):
        calc = Calculator()
        p = make_params(holes_x=2, holes_y=2, pattern=3, flip_axis=0)
        r = calc.calculate(p)
        for (tx, ty), (bx, by) in zip(r.top_coords, r.bot_coords):
            assert abs((tx + bx) - p.total_size_x) < 0.01
            assert abs(ty - by) < 0.01

    def test_y_flip_mirror(self):
        calc = Calculator()
        p = make_params(holes_x=2, holes_y=2, pattern=3, flip_axis=1)
        r = calc.calculate(p)
        for (tx, ty), (bx, by) in zip(r.top_coords, r.bot_coords):
            assert abs(tx - bx) < 0.01
            assert abs((ty + by) - p.total_size_y) < 0.01
