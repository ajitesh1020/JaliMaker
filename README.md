# JaliMaker – CNC Grill / Jali GCode Generator

> **By Ajitesh Kannojia** | MIT License | LinuxCNC compatible

---

## Overview

JaliMaker is an industrial-grade Python application for generating LinuxCNC-compatible G-code to drill decorative grill/jali patterns on CNC routers. It supports:

- **Three drill patterns**: Triangular (zig-zag), Rhombus (zig-zag +1 per even row), Square (uniform grid)
- **Two-sided drilling** with precise fixture pinning for board flipping (horizontal & vertical)
- **Chamfer / bottom-side G-code** generation
- **Panelisation** (array-copy multiple boards in one job)
- **Live dynamic board preview** – no static images, everything updates as you type
- **Interactive G-code viewer** with zoom, pan, hole selection and coordinate display
- **Password-protected Setup tab** with dev-mode bypass via INI
- **Path optimisation**: Auto boustrophedon, top↔bottom, left↔right
- **GitHub version checking** at startup

---

## Screenshots

*(Screenshots to be added)*

---


## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v3.3.2 (latest)
- Feat: Save GCode now asks for a base filename via QInputDialog
- Feat: output files named <name>_TOP.ngc / _BOTTOM.ngc / _PINNING.ngc / _BORDER.ngc"

### v3.3.1 
- Fixed startup crash: `AttributeError: _preview` / `le_size_x` — widget construction order
- Fixed `DeprecationWarning` for `AA_UseHighDpiPixmaps` (Qt6 removed it)
- Dimension input boxes enlarged (height 34 px, font 15 px bold) for easier entry
- Pattern preview: added zoom/pan (scroll=zoom, MMB=pan, RMB=fit), auto-fit on resize
- Pattern preview: fixed missing holes at board bottom edge (subsampling bug)
- Pattern preview: fixed unreadable `b`/`d` gap annotations — replaced rotated text with upright horizontal labels at fixed corner positions
- GCode viewer: fixed Top Only / Bottom Only filter buttons (were not filtering)
- GCode viewer: active filter button highlighted; status label shows current mode

### v3.3.0
- Initial modular rewrite with full feature set

---
## Installation

### Prerequisites

- Python 3.10+
- LinuxCNC (for running generated G-code)

### Quick Start

```bash
git clone https://github.com/ajitesh1020/JaliMaker.git
cd jaliMaker
pip install -r requirements.txt
python main.py
```

### Install as package

```bash
pip install .
jalimaker
```

---

## Project Structure

```
jaliMaker/
├── main.py                  # Entry point
├── grill_config.ini         # Auto-created config (do not delete)
├── requirements.txt
├── setup.py
├── core/
│   ├── calculator.py        # Pattern maths & path optimisation
│   ├── config_manager.py    # INI read/write with defaults
│   ├── gcode_generator.py   # LinuxCNC G-code builder
│   ├── logger.py            # Logging setup
│   ├── security_manager.py  # SHA-256 password auth
│   └── version.py           # Version + GitHub update check
├── ui/
│   ├── main_window.py       # Main QMainWindow
│   ├── setup_tab.py         # Password-protected setup
│   ├── pattern_preview.py   # Live board/hole preview widget
│   ├── gcode_viewer.py      # Interactive G-code plotter
│   └── styles.py            # Dark industrial QSS theme
├── logs/                    # Auto-created log files
└── gcode_output/            # Default output directory
```

---

## Configuration

`grill_config.ini` is created automatically if missing. Key sections:

| Section | Description |
|---------|-------------|
| `[SECURITY]` | `dev_mode`, `password_hash` |
| `[GRILL]` | Board dimensions, hole counts, depths |
| `[MACHINE]` | Feed rate, spindle, G-code preamble/postamble |
| `[FIXTURE]` | Pin positions, flip axis, tolerances |
| `[PANELIZATION]` | Array-copy settings |
| `[APP]` | Last directory, window state |

### Developer Mode

Set `dev_mode = true` in `[SECURITY]` to bypass the Setup tab password prompt. Do **not** enable in production.

---

## G-code Output Files

| File | Contents |
|------|----------|
| `jali_top.ngc` | Top-side drilling |
| `jali_bottom.ngc` | Bottom-side chamfer |
| `jali_pin.ngc` | Dowel pin drilling |
| `jali_border.ngc` | Border routing |

---

## Flip Logic

| Setting | Flip behaviour |
|---------|---------------|
| X-axis flip | Board flipped horizontally (mirror Y axis) |
| Y-axis flip | Board flipped vertically (mirror X axis) |
| Centre flip | Both axes mirrored |

---

## Logging

Logs are written to `logs/jalimaker_YYYYMMDD.log`. Enable `dev_mode` in INI for DEBUG-level console output.

---

## License

```
MIT License
Copyright (c) 2025 Indus Robotics

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Contributing

Pull requests welcome. Please open an issue first for major changes.

---

## Changelog

### v3.3.0
- Complete modular rewrite
- Dynamic live board preview (replaces static images)
- Interactive G-code viewer with zoom/pan/selection
- Background calculation thread with progress bar
- Y-axis flip added (was X-axis only before)
- Path optimisation: Auto / Top-Bottom / Bottom-Top / Left-Right / Right-Left
- Panelisation moved to Setup tab (checkbox enable)
- Password-protected Setup with dev-mode bypass
- GitHub version update checking
- Dark industrial UI theme
- Comprehensive structured logging
