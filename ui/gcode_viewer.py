# -*- coding: utf-8 -*-
"""
Interactive GCode viewer widget.
  - Colour-coded drill layers: Top / Bottom / Pin
  - Dashed rapid-move paths per layer
  - Top Only / Bottom Only / Show All filter buttons (actually work)
  - Zoom (scroll), Pan (MMB), Fit (RMB), hole selection + coordinate display
"""

import math
import logging
from typing import List, Tuple, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QWheelEvent, QMouseEvent
)

logger = logging.getLogger("JaliMaker.GCodeViewer")

# ── Palette ───────────────────────────────────────────────────────────────────
COL_BG        = QColor("#0a0d12")
COL_GRID      = QColor("#1a1e24")
COL_BOARD_BG  = QColor("#1c1410")
COL_BOARD_ED  = QColor("#6b5040")
COL_AXIS_LBL  = QColor("#64748b")
COL_TOP_HOLE  = QColor("#22d3ee")
COL_BOT_HOLE  = QColor("#f87171")
COL_PIN_HOLE  = QColor("#818cf8")
COL_RAPID     = QColor("#f59e0b")
COL_HOVER     = QColor("#fbbf24")
COL_SELECT    = QColor("#ffffff")
COL_TEXT      = QColor("#cbd5e1")

# Filter modes
SHOW_ALL = "all"
SHOW_TOP = "top"
SHOW_BOT = "bot"


class GCodeCanvas(QWidget):
    """The actual drawing canvas."""

    hole_selected = Signal(str, float, float, int)   # type, x, y, index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)

        # Raw data (full sets)
        self._all_top:  List[Tuple[float, float]] = []
        self._all_bot:  List[Tuple[float, float]] = []
        self._all_pin:  List[Tuple[float, float]] = []
        self._board_x: float = 160.0
        self._board_y: float = 505.0
        self._drill_dia: float = 2.0

        # Currently visible (filtered) sets
        self._vis_top: List[Tuple[float, float]] = []
        self._vis_bot: List[Tuple[float, float]] = []
        self._vis_pin: List[Tuple[float, float]] = []

        self._filter: str = SHOW_ALL

        # View state
        self._scale:  float = 1.0
        self._offset: QPointF = QPointF(60, 60)
        self._last_mouse: Optional[QPointF] = None
        self._panning: bool = False
        self._hovered_info: Optional[tuple] = None
        self._selected_info: Optional[tuple] = None
        self._fit_pending: bool = True

    # ── Public API ────────────────────────────────────────────────────────────

    def load_data(
        self,
        top_coords:  List[Tuple[float, float]],
        bot_coords:  List[Tuple[float, float]],
        pin_coords:  List[Tuple[float, float]],
        board_x: float,
        board_y: float,
        drill_dia: float,
    ) -> None:
        self._all_top  = top_coords
        self._all_bot  = bot_coords
        self._all_pin  = pin_coords
        self._board_x  = board_x
        self._board_y  = board_y
        self._drill_dia = drill_dia
        self._apply_filter()
        self._fit_pending = True
        self.update()

    def set_filter(self, mode: str) -> None:
        """Set visibility filter: 'all', 'top', 'bot'."""
        self._filter = mode
        self._apply_filter()
        self.update()

    def fit_to_view(self) -> None:
        margin = 60
        vw = max(self.width()  - 2 * margin, 10)
        vh = max(self.height() - 2 * margin, 10)
        self._scale = min(vw / max(self._board_x, 1), vh / max(self._board_y, 1))
        bw = self._board_x * self._scale
        bh = self._board_y * self._scale
        self._offset = QPointF(margin + (vw - bw) / 2, margin + (vh - bh) / 2)
        self._fit_pending = False
        self.update()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _apply_filter(self):
        if self._filter == SHOW_TOP:
            self._vis_top = self._all_top
            self._vis_bot = []
            self._vis_pin = self._all_pin   # pins always shown (they're structural)
        elif self._filter == SHOW_BOT:
            self._vis_top = []
            self._vis_bot = self._all_bot
            self._vis_pin = self._all_pin
        else:  # SHOW_ALL
            self._vis_top = self._all_top
            self._vis_bot = self._all_bot
            self._vis_pin = self._all_pin
        logger.debug(f"Filter={self._filter}  top={len(self._vis_top)}  "
                     f"bot={len(self._vis_bot)}  pin={len(self._vis_pin)}")

    def _w2s(self, wx: float, wy: float) -> QPointF:
        return QPointF(self._offset.x() + wx * self._scale,
                       self._offset.y() + wy * self._scale)

    def _s2w(self, sx: float, sy: float) -> Tuple[float, float]:
        return ((sx - self._offset.x()) / self._scale,
                (sy - self._offset.y()) / self._scale)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _evt):
        if self._fit_pending:
            self.fit_to_view()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), COL_BG)

        self._draw_grid(p)
        self._draw_board(p)

        # Rapid-move paths for visible layers
        self._draw_rapid_paths(p, self._vis_top, COL_TOP_HOLE)
        self._draw_rapid_paths(p, self._vis_bot, COL_BOT_HOLE)

        # Holes for visible layers
        r_px = max(self._drill_dia * self._scale / 2, 2.5)
        self._draw_holes(p, self._vis_top, COL_TOP_HOLE, r_px, "T")
        self._draw_holes(p, self._vis_bot, COL_BOT_HOLE, r_px, "B")
        self._draw_holes(p, self._vis_pin, COL_PIN_HOLE, r_px * 1.5, "P")

        self._draw_legend(p)
        if self._hovered_info:
            self._draw_hover_info(p, *self._hovered_info)
        p.end()

    def _draw_grid(self, p: QPainter):
        step_mm = self._nice_step()
        step_px = step_mm * self._scale
        if step_px < 8:
            return
        p.setPen(QPen(COL_GRID, 0.5))
        x = self._offset.x() % step_px
        while x < self.width():
            p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            x += step_px
        y = self._offset.y() % step_px
        while y < self.height():
            p.drawLine(QPointF(0, y), QPointF(self.width(), y))
            y += step_px
        # Axis mm labels
        p.setPen(QPen(COL_AXIS_LBL))
        p.setFont(QFont("Consolas", 7))
        mm = 0.0
        while mm <= self._board_x + step_mm:
            sp = self._w2s(mm, 0)
            if 0 < sp.x() < self.width():
                p.drawText(QRectF(sp.x() - 14, self.height() - 14, 28, 12),
                           Qt.AlignCenter, f"{mm:.0f}")
            mm += step_mm

    def _nice_step(self) -> float:
        target = 50
        raw = target / max(self._scale, 0.001)
        mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
        for f in (1, 2, 5, 10):
            if mag * f * self._scale >= target:
                return mag * f
        return mag * 10

    def _draw_board(self, p: QPainter):
        tl = self._w2s(0, 0)
        br = self._w2s(self._board_x, self._board_y)
        p.fillRect(QRectF(tl, br), COL_BOARD_BG)
        p.setPen(QPen(COL_BOARD_ED, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(tl, br))
        # Origin
        o = self._w2s(0, 0)
        p.setPen(QPen(QColor("#374151"), 1))
        p.drawLine(QPointF(o.x() - 6, o.y()), QPointF(o.x() + 6, o.y()))
        p.drawLine(QPointF(o.x(), o.y() - 6), QPointF(o.x(), o.y() + 6))
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(COL_AXIS_LBL))
        p.drawText(QRectF(o.x() + 2, o.y() + 2, 30, 12), Qt.AlignLeft, "X0Y0")

    def _draw_rapid_paths(self, p: QPainter, coords, color: QColor):
        if len(coords) < 2:
            return
        pen = QPen(color, 0.6, Qt.DashLine)
        pen.setDashPattern([4, 4])
        p.setPen(pen)
        for i in range(len(coords) - 1):
            a = self._w2s(*coords[i])
            b = self._w2s(*coords[i + 1])
            p.drawLine(a, b)

    def _draw_holes(self, p: QPainter, coords, color: QColor, r_px: float, kind: str):
        shown = min(len(coords), 5000)
        for i in range(shown):
            x, y = coords[i]
            sp = self._w2s(x, y)
            hr = QRectF(sp.x() - r_px, sp.y() - r_px, 2 * r_px, 2 * r_px)
            is_hov = self._hovered_info and self._hovered_info[:2] == (kind, i)
            is_sel = self._selected_info and self._selected_info[:2] == (kind, i)
            if is_sel:
                p.setPen(QPen(COL_SELECT, 2.0))
                p.setBrush(QBrush(COL_SELECT.darker(200)))
                p.drawEllipse(hr.adjusted(-2, -2, 2, 2))
            elif is_hov:
                p.setPen(QPen(COL_HOVER, 1.5))
                p.setBrush(QBrush(COL_HOVER.darker(300)))
            else:
                p.setPen(QPen(color.darker(150), 0.5))
                p.setBrush(QBrush(color.darker(400)))
            p.drawEllipse(hr)

    def _draw_legend(self, p: QPainter):
        items = [
            (COL_TOP_HOLE, f"Top drills ({len(self._vis_top)})"),
            (COL_BOT_HOLE, f"Bottom/chamfer ({len(self._vis_bot)})"),
            (COL_PIN_HOLE, f"Pin holes ({len(self._vis_pin)})"),
            (COL_RAPID,    "Rapid moves"),
        ]
        x, y = 10, 10
        p.setFont(QFont("Consolas", 9))
        for color, text in items:
            p.setPen(QPen(color, 1.5))
            p.setBrush(QBrush(color.darker(400)))
            p.drawEllipse(QRectF(x, y + 2, 10, 10))
            p.setPen(QPen(COL_TEXT))
            p.drawText(QRectF(x + 14, y, 180, 14), Qt.AlignVCenter | Qt.AlignLeft, text)
            y += 18

    def _draw_hover_info(self, p: QPainter, kind, idx, wx, wy):
        sp = self._w2s(wx, wy)
        p.setPen(QPen(COL_HOVER, 0.8, Qt.DotLine))
        p.drawLine(QPointF(0, sp.y()), QPointF(self.width(), sp.y()))
        p.drawLine(QPointF(sp.x(), 0), QPointF(sp.x(), self.height()))
        text = f"[{kind}#{idx + 1}]  X={wx:.4f}  Y={wy:.4f}"
        p.setFont(QFont("Consolas", 9))
        tw = p.fontMetrics().horizontalAdvance(text) + 12
        bx_ = min(sp.x() + 10, self.width() - tw - 4)
        by_ = max(sp.y() - 24, 4)
        p.fillRect(QRectF(bx_, by_, tw, 16), QColor("#141720"))
        p.setPen(QPen(COL_HOVER))
        p.drawText(QRectF(bx_ + 4, by_, tw, 16), Qt.AlignVCenter, text)

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        mp = event.position()
        self._offset = QPointF(
            mp.x() - (mp.x() - self._offset.x()) * factor,
            mp.y() - (mp.y() - self._offset.y()) * factor,
        )
        self._scale = max(0.2, min(self._scale * factor, 200.0))
        self._fit_pending = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier
        ):
            self._panning = True
            self._last_mouse = event.position()
        elif event.button() == Qt.LeftButton:
            info = self._nearest_hole(event.position().x(), event.position().y())
            self._selected_info = info
            if info:
                kind, idx, wx, wy = info
                self.hole_selected.emit(kind, wx, wy, idx)
            self.update()
        elif event.button() == Qt.RightButton:
            self.fit_to_view()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self._panning and self._last_mouse:
            delta = pos - self._last_mouse
            self._offset += delta
            self._last_mouse = pos
            self._fit_pending = False
            self.update()
        else:
            info = self._nearest_hole(pos.x(), pos.y())
            self._hovered_info = info
            self.update()

    def mouseReleaseEvent(self, _evt):
        self._panning = False
        self._last_mouse = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_pending = True

    def _nearest_hole(self, sx, sy) -> Optional[tuple]:
        threshold = max(self._drill_dia * self._scale / 2 + 6, 8)
        best, best_d = None, threshold
        # Only search visible layers
        for kind, coords in [("T", self._vis_top), ("B", self._vis_bot), ("P", self._vis_pin)]:
            for idx, (wx, wy) in enumerate(coords[:5000]):
                sp = self._w2s(wx, wy)
                d = math.hypot(sx - sp.x(), sy - sp.y())
                if d < best_d:
                    best_d, best = d, (kind, idx, wx, wy)
        return best


# ── Wrapper widget with toolbar ───────────────────────────────────────────────

class GCodeViewerWidget(QWidget):
    """GCode viewer with filter toolbar, canvas, and info bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        tb = QHBoxLayout()
        self._btn_fit  = QPushButton("⊡  Fit View")
        self._btn_all  = QPushButton("◉  Show All")
        self._btn_top  = QPushButton("▲  Top Only")
        self._btn_bot  = QPushButton("▼  Bottom Only")

        for btn in (self._btn_fit, self._btn_all, self._btn_top, self._btn_bot):
            btn.setFixedHeight(28)
            btn.setCheckable(False)
            tb.addWidget(btn)

        tb.addStretch()
        self._info_label = QLabel(
            "Scroll=Zoom  |  MMB=Pan  |  RMB=Fit  |  LMB=Select hole"
        )
        self._info_label.setObjectName("statSmall")
        tb.addWidget(self._info_label)
        layout.addLayout(tb)

        # Canvas
        self._canvas = GCodeCanvas()
        layout.addWidget(self._canvas, 1)

        # Selected hole info
        self._sel_label = QLabel("No hole selected")
        self._sel_label.setObjectName("statSmall")
        layout.addWidget(self._sel_label)

        # Active filter indicator
        self._filter_label = QLabel("Showing: All layers")
        self._filter_label.setObjectName("statSmall")
        layout.addWidget(self._filter_label)

        # Connections
        self._btn_fit.clicked.connect(self._canvas.fit_to_view)
        self._btn_all.clicked.connect(self._show_all)
        self._btn_top.clicked.connect(self._show_top)
        self._btn_bot.clicked.connect(self._show_bot)
        self._canvas.hole_selected.connect(self._on_hole_selected)

        # Style active button
        self._update_btn_styles(SHOW_ALL)

    # ── Filter handlers ───────────────────────────────────────────────────────

    def _show_all(self):
        self._canvas.set_filter(SHOW_ALL)
        self._filter_label.setText("Showing: All layers (Top + Bottom + Pins)")
        self._update_btn_styles(SHOW_ALL)

    def _show_top(self):
        self._canvas.set_filter(SHOW_TOP)
        self._filter_label.setText("Showing: Top drilling only")
        self._update_btn_styles(SHOW_TOP)

    def _show_bot(self):
        self._canvas.set_filter(SHOW_BOT)
        self._filter_label.setText("Showing: Bottom / chamfer only")
        self._update_btn_styles(SHOW_BOT)

    def _update_btn_styles(self, active: str):
        style_active   = "background:#f59e0b; color:#000; font-weight:800;"
        style_inactive = ""
        self._btn_all.setStyleSheet(style_active if active == SHOW_ALL else style_inactive)
        self._btn_top.setStyleSheet(style_active if active == SHOW_TOP else style_inactive)
        self._btn_bot.setStyleSheet(style_active if active == SHOW_BOT else style_inactive)

    # ── Load data ─────────────────────────────────────────────────────────────

    def load_results(self, results, params):
        """Load CalcResults + DrillParams into the viewer."""
        self._canvas.load_data(
            top_coords = results.top_coords,
            bot_coords = results.bot_coords,
            pin_coords = results.pin_coords,
            board_x    = params.total_size_x,
            board_y    = params.total_size_y,
            drill_dia  = params.drill_dia,
        )
        # Reset to Show All on every new load
        self._show_all()

    # ── Selection callback ────────────────────────────────────────────────────

    def _on_hole_selected(self, kind: str, x: float, y: float, idx: int):
        names = {"T": "Top drill", "B": "Bottom/chamfer", "P": "Pin hole"}
        self._sel_label.setText(
            f"Selected: {names.get(kind, kind)} #{idx + 1}   "
            f"X = {x:.4f} mm   Y = {y:.4f} mm"
        )
