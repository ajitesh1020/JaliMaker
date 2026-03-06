# Changelog

All notable changes to JaliMaker are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [3.3.1] – 2025-05-30

### Bug Fixes

#### `ui/main_window.py`
- **Fix: `AttributeError: 'MainWindow' object has no attribute '_preview'`**
  `_build_pattern_selector()` immediately calls `_set_pattern(1)` → `_refresh_preview()`
  during construction, but `self._preview` (PatternPreviewWidget) was instantiated
  several lines later. Fixed by creating `self._preview` **before** building the left
  panel so the attribute always exists when `_refresh_preview()` fires.

- **Fix: `AttributeError: 'MainWindow' object has no attribute 'le_size_x'`**
  Same construction-order problem: `_refresh_preview()` reads `self.le_size_x` and
  other `QLineEdit` fields before `_build_dimensions_group()` creates them.
  Fixed by adding an early-exit guard at the top of `_refresh_preview()`:
  ```python
  if not hasattr(self, "_preview") or not hasattr(self, "le_size_x"):
      return
  ```

- **Fix: `DeprecationWarning: AA_UseHighDpiPixmaps`**
  `Qt.AA_UseHighDpiPixmaps` is deprecated and removed in Qt6 — high-DPI scaling is
  enabled by default. Removed the `app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)`
  call from `main.py`.

#### `ui/main_window.py` — UI improvements
- **Dimension input boxes enlarged**: left panel widened 360 → 440 px; every
  dimension `QLineEdit` height increased to 34 px with `font-size: 15px bold`
  for easier reading and data entry on small screens.
- Grid label font bumped to 12 px to match the larger inputs.

---

#### `ui/pattern_preview.py` — complete rewrite
- **Zoom / pan added**: mouse-wheel zooms centred on cursor; middle-button drag
  pans; right-click fits the entire board back into view.
- **Auto-fit on data change and resize**: board always fills the available area
  when dimensions are updated or the window is resized.
- **Asymmetric margins** (`_MT=44 _MB=44 _ML=44 _MR=70`): right margin is wider
  to accommodate the vertical "Y = N mm" annotation without clipping.
- **Fix: bottom of board had no holes visible** — `_estimate_coords()` subsampling
  did not guarantee the last row/column was included. Fixed by explicitly appending
  `ny-1` (last row) and `cols-1` (last column) to the index lists so the hole
  pattern always reaches every edge of the board.
- **Fix: `b` and `d` gap annotations unreadable** — previous implementation rotated
  text 90° inside a small pixel rect which became illegible for small gaps (e.g. 4 mm).
  Replaced with **upright horizontal labels** anchored at fixed pixel positions
  (corner of the board) regardless of gap size, with a dark semi-transparent
  background rect behind each label. All four labels (`a`, `b`, `c`, `d`) now use
  `Consolas 11 Bold` and are always readable at any zoom level.
- **HUD overlay** (bottom-right): shows current zoom % and navigation hint
  (`Scroll=Zoom  MMB=Pan  RMB=Fit`).
- **Hover tooltip** drawn inline next to the cursor with dark background.
- Increased max preview hole count 2000 → 4000.

---

#### `ui/gcode_viewer.py` — complete rewrite
- **Fix: Top Only / Bottom Only filter buttons had no effect** — the canvas was
  always rendering `_top_coords`, `_bot_coords`, and `_pin_coords` from the full
  data set. The filter buttons were connected but never mutated what was drawn.
  Fixed by introducing `_vis_top / _vis_bot / _vis_pin` lists that are populated
  by `_apply_filter()` and are the **only** lists iterated by `_draw_holes()` and
  `_draw_rapid_paths()`. `_nearest_hole()` also searches only visible layers.
- Active filter button highlighted in amber so the current mode is obvious.
- Status label below canvas shows plain-English filter state
  ("Showing: Top drilling only", etc.).
- Filter resets to Show All on every new `load_results()` call.
- Zoom / pan / fit implemented consistently with pattern preview.

---

### Files changed
| File | Type |
|------|------|
| `main.py` | Bug fix (deprecated Qt attribute) |
| `ui/main_window.py` | Bug fix + UI improvement |
| `ui/pattern_preview.py` | Full rewrite |
| `ui/gcode_viewer.py` | Full rewrite |
| `core/version.py` | Version bump 3.3.0 → 3.3.1 |

---

## [3.3.0] – 2025-05-29

Initial release of the fully modular rewrite.

### Added
- Modular architecture: `core/` (pure Python) + `ui/` (PySide6)
- Three drill patterns: Triangular, Rhombus, Square
- Dynamic live board preview (no static images)
- Interactive GCode viewer with zoom / pan / selection
- Password-protected Setup tab with SHA-256 hashing and dev-mode bypass
- INI-based configuration with auto-defaults (`grill_config.ini`)
- Background calculation thread with progress bar (prevents UI freeze)
- Boustrophedon path optimisation (5 modes)
- Panelisation (array copy) in Setup tab
- GitHub API version checking at startup
- Structured daily logging (`logs/jalimaker_YYYYMMDD.log`)
- MIT License, GitHub CI workflow, `setup.py`, `requirements.txt`
