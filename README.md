# Ornament Designer (Ornamenter)

A desktop application for designing and generating ornamental patterns. Built with Python 3 and PyQt5. No GPU, no network, no external services — everything runs locally.

---

## Table of Contents

1. [What it does](#1-what-it-does)
2. [Requirements](#2-requirements)
3. [Installation](#3-installation)
4. [Quick start](#4-quick-start)
5. [Modules](#5-modules)
6. [File formats](#6-file-formats)
7. [Project layout](#7-project-layout)
8. [Templates](#8-templates)
9. [Extending the app](#9-extending-the-app)
10. [Testing](#10-testing)
11. [Troubleshooting](#11-troubleshooting)
12. [License](#12-license)
13. [Credits & acknowledgements](#13-credits--acknowledgements)

---

## 1. What it does

Ornament Designer turns a hand-drawn fragment into a full repeating ornament.

You draw a **segment** — a small set of straight and curved lines between a fixed grid of ten points. You then hand that segment to a **template**, which copies and transforms it (translate / rotate / scale / mirror / invert / recolor) according to a small JSON file. The result is a full ornament — a frieze, a mandala, a grid, a spiral galaxy — that you can export to SVG, PNG, JPG, or PDF.

The three modules mirror the three stages of that workflow:

- **Drawer** — draw and style a single segment.
- **Ornamenter** — pick a template, tune its parameters, generate the ornament.
- **Exporter** — save the result.

Every part of the pipeline is data-driven. Segments, templates, and library entries are plain JSON. Nothing is hard-coded that couldn't be a file.

---

## 2. Requirements

- **Python** 3.8 or newer (3.10+ recommended)
- **PyQt5** 5.15 or newer
- No other third-party packages

Everything else — file I/O, geometry, color math, raster and vector export — comes from the standard library and PyQt5.

---

## 3. Installation

### 3.1 From source (recommended)

```bash
# 1. Clone or unpack the project
git clone https://github.com/<your-username>/ornament-designer.git
cd ornament-designer

# 2. (Optional but recommended) create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install the only dependency
pip install PyQt5

# 4. Run
python main.py
```

### 3.2 As a frozen app (optional)

Just download from the Releases.

---

## 4. Quick start

1. Launch the app. You land on the **Drawer** tab.
2. Click one point, then another, to draw a line between them. The two radio buttons at the top of the toolbar switch between **Straight** and **Arc**.
3. Select a line (click it). The right-hand panel lets you change its **width**, **color**, **dash pattern**, **caps**, **joins**, and **opacity**. It also lets you switch the line between straight and arc, edit its **bend**, attach a **gradient**, or change its **z-order**.
4. When the segment looks right, switch to the **Ornamenter** tab. Pick a template on the left. Tune its parameters. Click **Generate**.
5. Switch to the **Exporter** tab. Pick a format, a size, and a background. Click **Export**.

A segment can be saved to a `.json` file, exported as a standalone SVG or PNG, copied to the clipboard, or dropped into the on-disk **library** — all from the Drawer panel.

---

## 5. Modules

### 5.1 Drawer

The interactive editor.

- **Canvas** — 800×600 by default. Ten fixed points: five on the left at `X = 200`, five on the right at `X = 600`. Y coordinates are `100, 200, 300, 400, 500`.
- **Toolbar** — mode selector (straight / arc) and a "Clear" action.
- **Property panel** — type, bend, gradient, z-order, delete.
- **Styler panel** — width, opacity, color + alpha, dash presets, line caps, joins.
- **Segment I/O panel** — load/save JSON, export SVG/PNG, copy/paste JSON, library save/load/delete.

Drawing a line is two clicks: first click selects the start point (it highlights), second click on a different point creates the line. Clicking the same point twice cancels.

Selecting a line highlights it in blue and populates the Styler and property panels. Clicking empty space deselects.

### 5.2 Ornamenter

The generator.

- **Template list** on the left, populated from `templates/*.json` at startup.
- **Parameter panel** — one widget per parameter declared in the template's `params` object, plus the four `color_shift` fields.
- **Preview canvas** — auto-scales the ornament to fit.
- **Generate** button — applies the template. **→ Export** button — sends the result to the Exporter tab.

Parameters are live: change a spinbox, click Generate, see the result. The template list requires an app restart if you add new `.json` files.

### 5.3 Exporter

The output stage.

- **Formats** — SVG, PNG, JPG, PDF.
- **Size** — width and height in pixels (raster) or points (vector).
- **Background** — transparent or a picker color.
- **JPG quality** — 1..100.
- **Overwrite guard** — if the file already exists, you're asked before it's replaced.

The same rendering path (`draw_line` → `QPen` → `QPainter`) is used for on-screen display and for all four export formats, so what you see is what you get. `QSvgGenerator` and `QPdfWriter` correctly translate `QPen.setDashPattern` and `painter.setOpacity` into their respective vector representations — no special-casing is needed per format.

---

## 6. File formats

### 6.1 Segment JSON

A segment file is a dictionary with two keys: `lines` and `base_points`. Every line entry carries both geometry and style.

```json
{
  "lines": [
    {
      "type": "straight",
      "start": [200, 100],
      "end": [600, 500],
      "color": [255, 0, 0, 255],
      "width": 2,
      "z": 0,
      "dash_pattern": [],
      "dash_offset": 0,
      "cap_style": "round",
      "join_style": "round",
      "opacity": 1.0
    },
    {
      "type": "arc",
      "start": [200, 200],
      "end": [600, 400],
      "bend": 50,
      "color": [0, 0, 255, 200],
      "width": 3,
      "z": 1,
      "dash_pattern": [10, 5],
      "dash_offset": 0,
      "cap_style": "square",
      "join_style": "bevel",
      "opacity": 0.8,
      "gradient": {
        "type": "linear",
        "x1": 0, "y1": 0, "x2": 1, "y2": 1,
        "stops": [[0.0, [255, 0, 0, 255]], [1.0, [0, 0, 255, 255]]]
      }
    }
  ],
  "base_points": [[200, 100], [200, 200], "..."]
}
```

Fields added after the initial release — `dash_pattern`, `dash_offset`, `cap_style`, `join_style`, `opacity` — are all optional. Files written before those fields existed still load, with sensible defaults (`[]`, `0.0`, `"round"`, `"round"`, `1.0`).

Style values:

- `cap_style` — `"flat"` | `"round"` | `"square"`. Internally stored as Qt names; exported to SVG as `butt` / `round` / `square`.
- `join_style` — `"miter"` | `"round"` | `"bevel"`.
- `dash_pattern` — list of dash/gap lengths. An empty list means solid.
- `opacity` — 0.0 to 1.0, multiplied with the color's alpha channel.

### 6.2 Template JSON

See the dedicated [Template Authoring Guide](TEMPLATES.md) for the full schema, all parameters of each type, worked examples, and common pitfalls. Quick summary:

```json
{
  "name": "Radial Flower",
  "type": "radial",
  "params": {
    "count": 12,
    "center_x": 400, "center_y": 300,
    "angle_step": 30,
    "radius_step": 0
  },
  "color_shift": {
    "enabled": true,
    "hue_shift_per_step": 30
  }
}
```

Three types are supported out of the box: `linear`, `radial`, `grid`.

---

## 7. Project layout

```
ornament-designer/
├── main.py
├── README.md
├── TEMPLATES.md
├── LICENSE
├── ornament/
│   ├── __init__.py
│   ├── core.py            # data model: Point, Line, ArcLine, Segment, Ornament, Matrix, Gradient
│   ├── render.py          # QPainter-based renderer shared by preview and export
│   ├── drawer.py          # Drawer module + canvas
│   ├── styler.py          # StylerWidget (line style panel)
│   ├── segment_io.py      # Segment import/export/clipboard/library
│   ├── ornamenter.py      # Ornamenter module
│   ├── exporter.py        # Exporter module
│   └── app.py             # MainWindow with tabs
├── templates/             # JSON templates, scanned at startup
│   ├── linear_wave.json
│   ├── radial_flower.json
│   └── ...
└── library/               # auto-created; named segments
    └── my_segment.json
```

### Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `core.py` | Pure data. No Qt. All geometry, serialization, and template application live here. |
| `render.py` | Maps `Line` objects to `QPainter` calls. The only place that knows about Qt drawing primitives. |
| `drawer.py` | The Drawer tab. Owns the canvas and the property panel. |
| `styler.py` | Reusable style panel. Binds to a `Line` by reference. |
| `segment_io.py` | Standalone I/O for a single segment. |
| `ornamenter.py` | The Ornamenter tab. Reads templates, applies them. |
| `exporter.py` | The Exporter tab. Rasterizes to PNG/JPG or writes SVG/PDF. |
| `app.py` | Wires the three tabs together, handles the menu bar. |

`core.py` deliberately has no Qt imports. It can be used from a script, a test, or a future command-line tool without dragging in PyQt.

---

## 8. Templates

The `templates/` folder ships with 17 ready-made templates:

**Linear:** `linear_wave`, `linear_frieze`, `linear_rainbow`, `linear_spiral`, `linear_shrinking`, `linear_zigzag`.

**Radial:** `radial_flower`, `radial_mandala`, `radial_sunburst`, `radial_spiral_galaxy`, `radial_snowflake`, `radial_concentric`.

**Grid:** `grid_basic`, `grid_checkerboard`, `grid_diagonal`, `grid_op_art`, `grid_wallpaper`.

To add your own, drop a `.json` into `templates/` and restart the app. The dropdown picks it up by its `"name"` field.

The full authoring reference — schema, per-type parameters, transform composition, color-shift semantics, validation table, cheat sheet — lives in **[TEMPLATES.md](TEMPLATES.md)**.

---

## 9. Extending the app

### Add a new template type

1. Add a branch in `apply_template()` in `core.py`.
2. The dropdown and parameter panel will pick it up automatically — `OrnamenterWidget` builds widgets from whatever `params` object your template declares.

### Add a new line style attribute

1. Add the field in `Line.__init__` with a default.
2. Extend `_style_dict()` in `core.py` so it round-trips.
3. Extend `line_from_dict()` to read it (with a default for backward compatibility).
4. If it affects rendering, teach `render.draw_line()` about it — that's the only place Qt needs updating.
5. If the field is user-editable, add a control in `styler.py`.

Nothing else changes. Export and preview share the same rendering path.

### Add a new export format

Add a branch to `export_object()` in `exporter.py`. The function takes an `Ornament` or a `Segment` and writes to a path. As long as `render_to_painter()` receives a `QPainter`, every format Qt supports is fair game.

---

## 10. Testing

There's a small set of smoke tests you can run without a display. They cover the data core and the segment I/O helper functions — the parts most likely to regress:

```bash
python - <<'PY'
from ornament.core import (Point, StraightLine, ArcLine, Segment, Ornament,
                           line_from_dict, Matrix, apply_template,
                           CAP_STYLES, JOIN_STYLES, SVG_CAP, SVG_JOIN)

# Matrix identity
assert Matrix.identity().a == 1.0

# SVG cap mapping: flat → butt
ln = StraightLine(Point(0, 0), Point(10, 10))
ln.cap_style = "flat"
assert 'stroke-linecap="butt"' in ln.get_svg()

# Round-trip
ln.dash_pattern = [10.0, 5.0]
ln.opacity = 0.5
back = line_from_dict(ln.to_dict())
assert back.dash_pattern == [10.0, 5.0]
assert back.opacity == 0.5

# Old JSON still loads
old = {"type": "straight", "start": [0, 0], "end": [1, 1],
       "color": [0, 0, 0, 255], "width": 2, "z": 0}
b = line_from_dict(old)
assert b.cap_style == "round" and b.opacity == 1.0

# Templates generate for all three types
s = Segment()
s.add_line(StraightLine(Point(0, 0), Point(100, 100)))
s.add_line(ArcLine(Point(100, 100), Point(200, 0), bend=40))
for t in ("linear", "radial", "grid"):
    tpl = {"name": t, "type": t,
           "params": {"count": 3, "cols": 2, "rows": 2,
                      "step_x": 50, "step_y": 50,
                      "center_x": 100, "center_y": 100,
                      "angle_step": 45},
           "color_shift": {"enabled": True, "hue_shift_per_step": 30}}
    orn = apply_template(s, tpl)
    assert len(orn.segments) >= 1

print("core OK")
PY
```

And a separate one for `segment_io.py`:

```bash
python - <<'PY'
import tempfile
from ornament.core import Point, StraightLine, ArcLine, Segment
from ornament.segment_io import (SegmentLibrary, segment_to_svg,
                                 segment_bounds, segment_to_clipboard_json,
                                 segment_from_clipboard_json, sanitize_name)

s = Segment()
s.add_line(StraightLine(Point(0, 0), Point(100, 100)))
s.add_line(ArcLine(Point(100, 100), Point(200, 0), bend=40))

svg = segment_to_svg(s, padding=10)
assert svg.startswith("<?xml") and "<svg " in svg

back = segment_from_clipboard_json(segment_to_clipboard_json(s))
assert back.to_dict() == s.to_dict()

with tempfile.TemporaryDirectory() as d:
    lib = SegmentLibrary(d)
    lib.save(s, "My Segment!")
    assert lib.list_names() == [sanitize_name("My Segment!")]
    assert lib.load("My Segment!").to_dict() == s.to_dict()

print("segment_io OK")
PY
```

For a fuller test suite, `pytest` works fine — just add `tests/` next to `ornament/` and `pytest tests/`.

---

## 11. Troubleshooting

**"ModuleNotFoundError: No module named 'ornament.app'"**
The `ornament/` package folder must sit next to `main.py`, and the folder name is case-sensitive on Linux/macOS. See the layout in [§8](#8-project-layout).

**"AttributeError: 'OrnamenterWidget' object has no attribute 'params_layout'"**
This was a startup-order bug in `_rebuild_params`. The current `ornamenter.py` creates `params_layout` before connecting the signal that triggers the rebuild. Update to the latest version.

**Dashed lines render as solid in the SVG export**
Check the dash pattern in the Styler. Empty list = solid. If the pattern is set and still solid, it's likely a browser caching an old SVG — reload with a hard refresh.

**The color picker shows no alpha slider**
Qt's `QColorDialog` only shows alpha when created with `ShowAlphaChannel`. The current Styler passes that flag. If you forked and removed it, alpha editing will be hidden.

**The template I added doesn't appear**
Templates are scanned once at startup. Close and relaunch. Also check for a typo in `"name"` — if two files declare the same name, only one wins.

**Generate does nothing**
The segment in the Drawer is empty. Add at least one line first.

**An ornament draws on top of itself**
`step_x`, `step_y`, and `radius_step` are all zero — all copies land at the same spot. Give the template at least one non-zero displacement.

---

## 12. License

This project is released under the **MIT License**. That's the most permissive option short of public domain, and it fits a small PyQt application with no vendored code.

**Why MIT:**

- **Trivial to comply with.** Keep the copyright notice and license text; that's it.
- **Compatible with everything.** MIT code can be used inside GPL, Apache-2.0, BSD, and proprietary projects.
- **No patent grant.** If your jurisdiction needs an explicit patent grant, use **Apache-2.0** instead — otherwise identical in spirit, slightly more formal.
- **No copyleft.** If you want to force derivative works to remain open, use **GPL-3.0** instead.

If you forked this project and are choosing a license now, replace the text below with your own name and year.

```
MIT License

Copyright (c) 2024 <your name>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


---

THIS PROGRAMM IS NOT USED COMMERCIALLY NOW AND NOT WILL BE USED COMMERCIALLY IN THE FUTURE!

---

## 13. Credits & acknowledgements

### Author

Built as a personal project for exploring generative ornament design. Fork freely.

### Special thanks

- **DeepSeek** — the architecture, the data model, the template engine, the Styler panel, the segment I/O module, and this README were shaped through a long back-and-forth with **DeepSeek's coding assistant**. DeepSeek helped reason through the affine transform composition, caught the `flat → butt` SVG mapping bug, cleaned up the `_loading` guard patterns, and iterated on the template schema until it stabilized. The project would have taken significantly longer without that collaboration. Also translation all comments to English was performed by DeepSeek.
- **The PyQt5 maintainers** and the **Qt Project** — for a GUI toolkit that's powerful enough to draw ornaments, expose a color picker with alpha, and serialize vector output to four formats, all from one Python-friendly API.
- **Riverbank Computing** — for maintaining PyQt5 as a first-class binding.
- **The Python standard library** — `colorsys` for HSL math, `json` for the entire serialization layer, `math` for the Bezier and arc geometry. None of this needed a third-party dependency.

### Open source projects this app depends on

| Project | License | Role |
|---------|---------|------|
| [PyQt5](https://riverbankcomputing.com/software/pyqt/) | GPL-3.0 / commercial | GUI toolkit |
| [Qt 5](https://www.qt.io/) | LGPL-3.0 / commercial | Underlying C++ toolkit |
| [Python](https://www.python.org/) | PSF License | Language runtime |

No other runtime dependencies. The `templates/` JSON files and the `library/` folder are data, not code, and are not covered by any license claim from the app — they're yours to keep, modify, or ship.

### Contributing

Bug reports, template packs, and pull requests are welcome. When opening an issue, please include:

1. Your OS and Python version.
2. The exact steps to reproduce.
3. Any traceback in full — not paraphrased.
4. If it's a template issue, attach the `.json` file.

When opening a pull request, please keep the style of the codebase:

- All UI text and code comments in English.
- `core.py` stays Qt-free — if you need Qt, the change belongs in `render.py` or one of the tab modules.
- New `Line` fields must round-trip through `to_dict()` / `line_from_dict()` with backward-compatible defaults.
- Every PR should at least pass the smoke tests in [§10](#10-testing).

---

*Happy ornamenting.*