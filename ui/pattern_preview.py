# -*- coding: utf-8 -*-
"""
Dynamic pattern preview widget.
  - Asymmetric margins: extra right for Y label, extra bottom for gap labels
  - Holes always cover full board (first+last row/col always included)
  - Zoom / pan / fit-on-resize
  - Annotation labels drawn as HORIZONTAL text boxes (no rotation) for
    vertical dimensions – avoids the tiny-rotated-text problem entirely
"""

import math
import logging
from typing import List, Optional, Tuple

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QLinearGradient, QWheelEvent
)

logger = logging.getLogger("JaliMaker.Preview")

C_BG_TOP   = QColor("#0d1117")
C_BG_BOT   = QColor("#141720")
C_BOARD_TL = QColor("#c8a882")
C_BOARD_BR = QColor("#b89870")
C_BOARD_ED = QColor("#6b5040")
C_WORK_DASH= QColor("#4b5563")
C_HOLE     = QColor("#f0f0f0")
C_HOLE_ED  = QColor("#1e2330")
C_HOVER    = QColor("#f59e0b")
C_SEL      = QColor("#fbbf24")
C_PIN      = QColor("#3b82f6")
C_PIN_FILL = QColor("#1e3a5f")
C_ANN_MAIN = QColor("#f59e0b")   # X= / Y= total
C_ANN_GAP  = QColor("#f87171")   # a / b gaps
C_ANN_DIM  = QColor("#38bdf8")   # c / d gaps
C_ANN_TXT  = QColor("#cbd5e1")

# Fixed pixel margins around the board drawing area
_MT = 44   # top    – room for X total label
_MB = 44   # bottom – room for a / gap label
_ML = 44   # left   – room for b / gap label
_MR = 70   # right  – room for Y total + d label (widest text)


class PatternPreviewWidget(QWidget):
    """
    Fully dynamic board/hole pattern preview.
    Scroll=Zoom  |  MMB-drag=Pan  |  RMB=Fit entire board
    """

    hole_hovered = Signal(float, float, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 380)
        self.setFocusPolicy(Qt.WheelFocus)
        self.setMouseTracking(True)

        self._total_x:   float = 160.0
        self._total_y:   float = 505.0
        self._gap_x:     float = 20.0
        self._gap_y:     float = 5.0
        self._gap_c:     float = 20.0
        self._gap_d:     float = 5.0
        self._holes_x:   int   = 16
        self._holes_y:   int   = 100
        self._pattern:   int   = 1
        self._pin_x:     float = 10.0
        self._pin_y:     float = 15.0
        self._drill_dia: float = 2.0
        self._hole_coords: List[Tuple[float, float]] = []
        self._pin_coords:  List[Tuple[float, float]] = []
        self._hovered_idx: int = -1
        self._selected_idx: int = -1

        self._scale:  float = 1.0
        self._offset: QPointF = QPointF(_ML, _MT)
        self._panning: bool = False
        self._last_mouse: Optional[QPointF] = None
        self._fit_pending: bool = True

    # ── Public API ────────────────────────────────────────────────────────────

    def update_preview(
        self,
        total_x: float, total_y: float,
        gap_x: float,  gap_y: float,
        gap_c: float,  gap_d: float,
        holes_x: int,  holes_y: int,
        pattern: int,
        pin_x: float,  pin_y: float,
        drill_dia: float,
        hole_coords: Optional[List[Tuple[float, float]]] = None,
        pin_coords:  Optional[List[Tuple[float, float]]] = None,
    ) -> None:
        self._total_x   = max(total_x, 1.0)
        self._total_y   = max(total_y, 1.0)
        self._gap_x, self._gap_y = gap_x, gap_y
        self._gap_c, self._gap_d = gap_c, gap_d
        self._holes_x   = max(holes_x, 1)
        self._holes_y   = max(holes_y, 1)
        self._pattern   = pattern
        self._pin_x, self._pin_y = pin_x, pin_y
        self._drill_dia = drill_dia
        self._hole_coords = hole_coords if hole_coords is not None else self._estimate_coords()
        self._pin_coords  = pin_coords  if pin_coords  is not None else self._estimate_pins()
        self._fit_pending = True
        self.update()

    def fit_to_view(self):
        avail_w = max(self.width()  - _ML - _MR, 10)
        avail_h = max(self.height() - _MT - _MB, 10)
        self._scale = min(avail_w / self._total_x, avail_h / self._total_y)
        board_w = self._total_x * self._scale
        board_h = self._total_y * self._scale
        self._offset = QPointF(
            _ML + (avail_w - board_w) / 2,
            _MT + (avail_h - board_h) / 2,
        )
        self._fit_pending = False
        self.update()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _w2s(self, wx: float, wy: float) -> QPointF:
        return QPointF(self._offset.x() + wx * self._scale,
                       self._offset.y() + wy * self._scale)

    def _dim(self, d: float) -> float:
        return d * self._scale

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        if self._fit_pending:
            self.fit_to_view()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        W, H = self.width(), self.height()

        # Background
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0, C_BG_TOP)
        bg.setColorAt(1, C_BG_BOT)
        p.fillRect(0, 0, W, H, bg)

        tl = self._w2s(0, 0)
        br = self._w2s(self._total_x, self._total_y)

        # Board fill + border
        bfill = QLinearGradient(tl.x(), tl.y(), br.x(), br.y())
        bfill.setColorAt(0, C_BOARD_TL)
        bfill.setColorAt(1, C_BOARD_BR)
        p.fillRect(QRectF(tl, br), bfill)
        p.setPen(QPen(C_BOARD_ED, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(tl, br))

        # Working-area dashed outline
        p.setPen(QPen(C_WORK_DASH, 1.0, Qt.DashLine))
        p.drawRect(QRectF(
            self._w2s(self._gap_x,                 self._gap_y),
            self._w2s(self._total_x - self._gap_c, self._total_y - self._gap_d),
        ))

        # Holes
        r_px  = max(self._dim(self._drill_dia / 2), 2.0)
        shown = min(len(self._hole_coords), 4000)
        for idx in range(shown):
            hx, hy = self._hole_coords[idx]
            sp = self._w2s(hx, hy)
            hr = QRectF(sp.x() - r_px, sp.y() - r_px, 2 * r_px, 2 * r_px)
            if idx == self._hovered_idx:
                p.setPen(QPen(C_HOVER, 1.5));   p.setBrush(QBrush(QColor("#78350f")))
            elif idx == self._selected_idx:
                p.setPen(QPen(C_SEL, 2.0));     p.setBrush(QBrush(QColor("#92400e")))
            else:
                p.setPen(QPen(C_HOLE_ED, 0.5)); p.setBrush(QBrush(C_HOLE))
            p.drawEllipse(hr)

        # Pin holes
        r_pin = max(r_px * 1.5, 4.0)
        p.setPen(QPen(C_PIN, 1.5))
        p.setBrush(QBrush(C_PIN_FILL))
        for px_, py_ in self._pin_coords:
            sp = self._w2s(px_, py_)
            p.drawEllipse(sp, r_pin, r_pin)

        self._draw_annotations(p, tl.x(), tl.y(), br.x() - tl.x(), br.y() - tl.y())
        self._draw_hud(p, W, H)
        p.end()

    # ── Annotations ──────────────────────────────────────────────────────────
    #
    # Strategy: ALL labels are drawn as HORIZONTAL text – no rotation.
    # Horizontal arrows get their label above the line.
    # Vertical arrows get their label to the side as upright text.
    # This guarantees every label is the same readable size regardless
    # of how small the gap span is in pixels.

    def _draw_annotations(self, p: QPainter, ox, oy, bw, bh):
        ex = ox + bw   # right edge of board
        ey = oy + bh   # bottom edge of board
        sc = self._scale

        # ── Fonts ─────────────────────────────────────────────────────────────
        F_TOTAL = QFont("Consolas", 12, QFont.Bold)   # X= / Y= totals
        F_GAP   = QFont("Consolas", 11, QFont.Bold)   # a / b / c / d gaps

        # ── Helpers ───────────────────────────────────────────────────────────

        def tick(p, x, y, horiz):
            """Small perpendicular tick mark."""
            if horiz:
                p.drawLine(QPointF(x, y - 5), QPointF(x, y + 5))
            else:
                p.drawLine(QPointF(x - 5, y), QPointF(x + 5, y))

        def h_arrow_label(x1, x2, y, color, label, font, label_y_offset=-20):
            """Horizontal dimension line with label above it."""
            if abs(x2 - x1) < 2:
                return
            p.setPen(QPen(color, 1.3))
            p.drawLine(QPointF(x1, y), QPointF(x2, y))
            tick(p, x1, y, horiz=True)
            tick(p, x2, y, horiz=True)
            mid = (x1 + x2) / 2
            p.setFont(font)
            p.setPen(QPen(color))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(label) + 10
            p.fillRect(QRectF(mid - tw/2, y + label_y_offset - 1, tw, fm.height() + 2),
                       QColor(13, 17, 23, 200))
            p.drawText(QRectF(mid - tw/2, y + label_y_offset, tw, fm.height()),
                       Qt.AlignCenter, label)

        def v_arrow_label(y1, y2, x, color, label, font, label_x_offset=10):
            """
            Vertical dimension line with HORIZONTAL (upright) label beside it.
            label_x_offset > 0  → label drawn to the RIGHT of x
            label_x_offset < 0  → label drawn to the LEFT  of x (need space)
            """
            if abs(y2 - y1) < 2:
                return
            p.setPen(QPen(color, 1.3))
            p.drawLine(QPointF(x, y1), QPointF(x, y2))
            tick(p, x, y1, horiz=False)
            tick(p, x, y2, horiz=False)
            mid = (y1 + y2) / 2
            p.setFont(font)
            p.setPen(QPen(color))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(label) + 10
            th = fm.height() + 2
            lx = x + label_x_offset if label_x_offset > 0 else x + label_x_offset - tw
            ly = mid - th / 2
            p.fillRect(QRectF(lx, ly, tw, th), QColor(13, 17, 23, 200))
            p.drawText(QRectF(lx, ly, tw, th), Qt.AlignCenter, label)

        # ── Total dimensions ──────────────────────────────────────────────────
        # X total – above board, centered
        h_arrow_label(ox, ex, oy - 22, C_ANN_MAIN,
                      f"X = {self._total_x:.0f} mm", F_TOTAL, label_y_offset=-20)

        # Y total – right of board, label to the right
        v_arrow_label(oy, ey, ex + 18, C_ANN_MAIN,
                      f"Y = {self._total_y:.0f} mm", F_TOTAL, label_x_offset=10)

        # ── Gap annotations ───────────────────────────────────────────────────
        # Always draw the gap label at a FIXED position regardless of gap size.
        # The arrow spans the actual gap pixels; the label is at a fixed offset.

        # a = gap_x  (left border) – horizontal, below board
        gap_a_px = self._gap_x * sc
        if gap_a_px >= 1:
            p.setPen(QPen(C_ANN_GAP, 1.3))
            p.drawLine(QPointF(ox, ey + 22), QPointF(ox + gap_a_px, ey + 22))
            tick(p, ox,            ey + 22, horiz=True)
            tick(p, ox + gap_a_px, ey + 22, horiz=True)
        p.setFont(F_GAP)
        p.setPen(QPen(C_ANN_GAP))
        lbl_a = f"a={self._gap_x:.0f}"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(lbl_a) + 10
        # Always place label at left edge + 4 so it is always visible
        lx = ox + 4
        p.fillRect(QRectF(lx, ey + 26, tw, fm.height() + 2), QColor(13, 17, 23, 200))
        p.drawText(QRectF(lx, ey + 26, tw, fm.height()), Qt.AlignLeft, lbl_a)

        # c = gap_c  (right border) – horizontal, below board (right side)
        gap_c_px = self._gap_c * sc
        if gap_c_px >= 1:
            p.setPen(QPen(C_ANN_DIM, 1.3))
            p.drawLine(QPointF(ex - gap_c_px, ey + 22), QPointF(ex, ey + 22))
            tick(p, ex - gap_c_px, ey + 22, horiz=True)
            tick(p, ex,            ey + 22, horiz=True)
        p.setFont(F_GAP)
        p.setPen(QPen(C_ANN_DIM))
        lbl_c = f"c={self._gap_c:.0f}"
        tw_c = fm.horizontalAdvance(lbl_c) + 10
        lx_c = ex - tw_c - 4   # right-aligned near right board edge
        p.fillRect(QRectF(lx_c, ey + 26, tw_c, fm.height() + 2), QColor(13, 17, 23, 200))
        p.drawText(QRectF(lx_c, ey + 26, tw_c, fm.height()), Qt.AlignRight, lbl_c)

        # b = gap_y  (top border) – vertical, left of board
        gap_b_px = self._gap_y * sc
        if gap_b_px >= 1:
            p.setPen(QPen(C_ANN_GAP, 1.3))
            p.drawLine(QPointF(ox - 22, oy), QPointF(ox - 22, oy + gap_b_px))
            tick(p, ox - 22, oy,            horiz=False)
            tick(p, ox - 22, oy + gap_b_px, horiz=False)
        p.setFont(F_GAP)
        p.setPen(QPen(C_ANN_GAP))
        lbl_b = f"b={self._gap_y:.0f}"
        tw_b = fm.horizontalAdvance(lbl_b) + 10
        # Always place at top-left corner, readable upright
        p.fillRect(QRectF(ox - tw_b - 26, oy + 2, tw_b, fm.height() + 2),
                   QColor(13, 17, 23, 200))
        p.drawText(QRectF(ox - tw_b - 26, oy + 2, tw_b, fm.height()),
                   Qt.AlignRight, lbl_b)

        # d = gap_d  (bottom border) – vertical, right of board
        gap_d_px = self._gap_d * sc
        if gap_d_px >= 1:
            p.setPen(QPen(C_ANN_DIM, 1.3))
            p.drawLine(QPointF(ex + 18, ey - gap_d_px), QPointF(ex + 18, ey))
            tick(p, ex + 18, ey - gap_d_px, horiz=False)
            tick(p, ex + 18, ey,            horiz=False)
        p.setFont(F_GAP)
        p.setPen(QPen(C_ANN_DIM))
        lbl_d = f"d={self._gap_d:.0f}"
        tw_d = fm.horizontalAdvance(lbl_d) + 10
        # Always place at bottom-right corner, readable upright
        p.fillRect(QRectF(ex + 22, ey - fm.height() - 4, tw_d, fm.height() + 2),
                   QColor(13, 17, 23, 200))
        p.drawText(QRectF(ex + 22, ey - fm.height() - 4, tw_d, fm.height()),
                   Qt.AlignLeft, lbl_d)

        # ── Info banner inside board (top strip) ──────────────────────────────
        F_INFO = QFont("Consolas", 11, QFont.Bold)
        banner_h = 24
        p.fillRect(QRectF(ox, oy, bw, banner_h), QColor(0, 0, 0, 150))
        p.setFont(F_INFO)
        p.setPen(QPen(C_ANN_TXT))
        pat_name = ["Triangular", "Rhombus", "Square"][self._pattern - 1]
        p.drawText(
            QRectF(ox + 6, oy + 2, bw - 12, banner_h - 2),
            Qt.AlignVCenter | Qt.AlignLeft,
            f"{pat_name}   X: {self._holes_x} holes   Y: {self._holes_y} lines",
        )

        # ── Hover tooltip ─────────────────────────────────────────────────────
        if 0 <= self._hovered_idx < len(self._hole_coords):
            hx, hy = self._hole_coords[self._hovered_idx]
            sp = self._w2s(hx, hy)
            txt = f"  X={hx:.3f}  Y={hy:.3f}  #{self._hovered_idx + 1}"
            p.setFont(QFont("Consolas", 10, QFont.Bold))
            fm2 = p.fontMetrics()
            fw = fm2.horizontalAdvance(txt) + 18
            cx = min(sp.x() + 14, self.width() - fw - 4)
            cy = max(sp.y() - 28, 4)
            p.fillRect(QRectF(cx, cy, fw, 20), QColor("#141720"))
            p.setPen(QPen(C_HOVER))
            p.drawRect(QRectF(cx, cy, fw, 20))
            p.drawText(QRectF(cx + 4, cy, fw - 4, 20), Qt.AlignVCenter, txt)

    def _draw_hud(self, p: QPainter, W: int, H: int):
        hint = f"Scroll=Zoom   MMB=Pan   RMB=Fit    {self._scale * 100:.0f}%"
        p.setFont(QFont("Consolas", 9))
        fm_w = p.fontMetrics().horizontalAdvance(hint) + 16
        p.fillRect(QRectF(W - fm_w - 4, H - 20, fm_w + 4, 18), QColor(0, 0, 0, 170))
        p.setPen(QPen(QColor("#475569")))
        p.drawText(QRectF(W - fm_w - 2, H - 20, fm_w, 18), Qt.AlignVCenter, hint)

    # ── Estimate preview hole coordinates ─────────────────────────────────────

    def _estimate_coords(self) -> List[Tuple[float, float]]:
        """
        Subsample the hole grid for preview speed.
        Always includes first + last row and first + last column so the
        board appears fully populated to its edges.
        """
        coords = []
        nx, ny = self._holes_x, self._holes_y
        wx = self._total_x - self._gap_x - self._gap_c
        wy = self._total_y - self._gap_y - self._gap_d

        denom_x = max(2 * nx - 1, 1) if self._pattern in (1, 2) else max(nx - 1, 1)
        sx = wx / denom_x
        sy = wy / max(ny - 1, 1)

        MAX_ROWS, MAX_COLS = 40, 20

        # Build row index list always including first and last
        if ny <= MAX_ROWS:
            row_indices = list(range(ny))
        else:
            step = max(1, (ny - 2) // (MAX_ROWS - 2))
            row_indices = list(range(0, ny - 1, step))
            if (ny - 1) not in row_indices:
                row_indices.append(ny - 1)

        for row in row_indices:
            offset     = sx if (row % 2 == 1 and self._pattern in (1, 2)) else 0.0
            cols_count = nx + (1 if self._pattern == 2 and row % 2 == 1 else 0)

            if cols_count <= MAX_COLS:
                col_indices = list(range(cols_count))
            else:
                step_c = max(1, (cols_count - 2) // (MAX_COLS - 2))
                col_indices = list(range(0, cols_count - 1, step_c))
                if (cols_count - 1) not in col_indices:
                    col_indices.append(cols_count - 1)

            for col in col_indices:
                if self._pattern in (1, 2):
                    x = self._gap_x + sx + col * 2 * sx - offset
                else:
                    x = self._gap_x + col * sx
                y = self._gap_y + row * sy

                if 0 <= x <= self._total_x and 0 <= y <= self._total_y:
                    coords.append((round(x, 4), round(y, 4)))
        return coords

    def _estimate_pins(self) -> List[Tuple[float, float]]:
        return [
            (self._pin_x,                  self._pin_y),
            (self._total_x - self._pin_x,  self._pin_y),
            (self._pin_x,                  self._total_y - self._pin_y),
            (self._total_x - self._pin_x,  self._total_y - self._pin_y),
        ]

    # ── Mouse events ──────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        mp = event.position()
        self._offset = QPointF(
            mp.x() - (mp.x() - self._offset.x()) * factor,
            mp.y() - (mp.y() - self._offset.y()) * factor,
        )
        self._scale = max(0.05, min(self._scale * factor, 500.0))
        self._fit_pending = False
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._last_mouse = pos
        elif event.button() == Qt.RightButton:
            self.fit_to_view()
        elif event.button() == Qt.LeftButton:
            self._selected_idx = self._find_nearest_hole(pos.x(), pos.y())
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._panning and self._last_mouse:
            self._offset += pos - self._last_mouse
            self._last_mouse = pos
            self._fit_pending = False
            self.update()
        else:
            idx = self._find_nearest_hole(pos.x(), pos.y())
            if idx != self._hovered_idx:
                self._hovered_idx = idx
                if idx >= 0:
                    x, y = self._hole_coords[idx]
                    self.hole_hovered.emit(x, y, idx)
                self.update()

    def mouseReleaseEvent(self, _event):
        self._panning = False
        self._last_mouse = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_pending = True

    def _find_nearest_hole(self, mx: float, my: float) -> int:
        if not self._hole_coords:
            return -1
        threshold = max(self._dim(self._drill_dia / 2) + 5, 7)
        best, best_d = -1, threshold
        for i, (hx, hy) in enumerate(self._hole_coords[:4000]):
            sp = self._w2s(hx, hy)
            d = math.hypot(mx - sp.x(), my - sp.y())
            if d < best_d:
                best_d, best = d, i
        return best
