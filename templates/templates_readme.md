# Ornament Designer — Template Authoring Guide

A single-file reference for writing JSON templates consumed by the **Ornamenter** module.

---

## Table of Contents

1. [Where templates live](#1-where-templates-live)
2. [Minimal template](#2-minimal-template)
3. [Full schema](#3-full-schema)
4. [Type `linear`](#4-type-linear)
5. [Type `radial`](#5-type-radial)
6. [Type `grid`](#6-type-grid)
7. [`color_shift` — per-copy hue drift](#7-color_shift--per-copy-hue-drift)
8. [Authoring tips](#8-authoring-tips)
9. [Validation & common mistakes](#9-validation--common-mistakes)
10. [Schema cheat sheet](#10-schema-cheat-sheet)
11. [Shipped templates](#11-shipped-templates)

---

## 1. Where templates live

Drop `.json` files into the `templates/` folder next to `main.py`:

```
ornament_designer/
├── main.py
├── ornament/
│   └── ...
└── templates/
    ├── linear_wave.json
    ├── radial_flower.json
    └── your_template.json    ← add here
```

On startup, `load_templates()` scans the folder and registers every `.json` file by its `"name"` field. The dropdown in the Ornamenter tab is populated from that scan.

- New files require an app restart (the scan runs once in `OrnamenterWidget.__init__`).
- Edits to existing parameters are live once the template is selected.
- If two files declare the same `"name"`, the last one read (alphabetically) wins.

---

## 2. Minimal template

```json
{
  "name": "My First Template",
  "type": "linear",
  "params": {
    "count": 5,
    "step_x": 200
  }
}
```

Every field except `name` and `type` is optional. Missing `params` keys fall back to defaults defined in `apply_template()`. Missing `color_shift` disables color shifts entirely.

---

## 3. Full schema

```json
{
  "name": "string — display name in the dropdown",
  "type": "linear | radial | grid",

  "params": {
    // ... type-specific — see sections 4–6
  },

  "color_shift": {
    "enabled": true,
    "hue_shift_per_step": 0.0,
    "saturation_shift": 0.0,
    "lightness_shift": 0.0,
    "alpha_shift": 0.0
  }
}
```

### Top-level fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | **yes** | Shown in the template list. Used as the registry key. |
| `type` | string | **yes** | One of `linear`, `radial`, `grid`. Unknown types produce an empty ornament. |
| `params` | object | no | Type-specific parameters (sections 4–6). Defaults apply if missing. |
| `color_shift` | object | no | Per-copy color drift (section 7). Absent or `enabled: false` → copies keep source colors. |

---

## 4. Type `linear`

Copies the segment repeatedly with optional per-step translation, rotation, scale, and alternating mirror / invert.

### Parameters

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `count` | int | `1` | Number of copies (including the original at index 0). |
| `step_x` | float | `0.0` | Horizontal shift added per copy. |
| `step_y` | float | `0.0` | Vertical shift added per copy. |
| `rotation_per_step` | float | `0.0` | Rotation in degrees, applied cumulatively (copy `i` rotates by `rot * i`). |
| `scale_per_step` | float | `1.0` | Multiplicative scale, applied as `scl ** i`. `1.0` = no change. |
| `mirror_alternate` | bool | `false` | Odd-indexed copies are mirrored horizontally about the pivot. |
| `invert_alternate` | bool | `false` | Odd-indexed copies are rotated 180° about the pivot. |
| `pivot_x` | float | segment centroid X | Center for mirror / rotate / scale. |
| `pivot_y` | float | segment centroid Y | Same, for the Y axis. |

### Transform composition for copy `i` (0-based)

```
M = Translate(step_x·i, step_y·i)
  · [Scale about pivot, if scale_per_step != 1]
  · [Rotate about pivot by rotation_per_step·i]
  · [Rotate 180° about pivot, if invert_alternate and i odd]
  · [Mirror about pivot.x, if mirror_alternate and i odd]
```

In words: mirror/invert happen first (in the copy's own coordinates), then rotation, then scale, then translation. This matches the "flip in place, then march" intuition.

### Example — classic frieze

```json
{
  "name": "Frieze",
  "type": "linear",
  "params": {
    "count": 10,
    "step_x": 200,
    "mirror_alternate": true,
    "invert_alternate": true,
    "pivot_x": 400,
    "pivot_y": 300
  }
}
```

### Example — spiral chain

```json
{
  "name": "Spiral Chain",
  "type": "linear",
  "params": {
    "count": 18,
    "step_x": 40,
    "rotation_per_step": 12,
    "scale_per_step": 1.03
  }
}
```

---

## 5. Type `radial`

Rotates the segment around a fixed center, optionally pushing each copy outward along its own radius (spiral).

### Parameters

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `count` | int | `8` | Number of copies around the circle. |
| `center_x` | float | segment centroid X | Rotation center X. For the default 800×600 canvas, `400` is the middle. |
| `center_y` | float | segment centroid Y | Rotation center Y. Use `300` for the default canvas. |
| `angle_step` | float | `360 / count` | Degrees between consecutive copies. |
| `radius_step` | float | `0.0` | Push copy `i` outward by `i · radius_step` along its own angle. |

### Placement of copy `i`

```
M = Translate(cos(θᵢ)·r·i, sin(θᵢ)·r·i)  ·  RotateAbout(angle_step·i, center)
```

where `θᵢ = radians(angle_step · i)` and `r = radius_step`.

- `radius_step = 0` → all copies share the same center (flower, mandala).
- `radius_step > 0` → copies drift outward (spiral, galaxy).

### Example — 16-fold mandala

```json
{
  "name": "Mandala",
  "type": "radial",
  "params": {
    "count": 16,
    "center_x": 400,
    "center_y": 300,
    "angle_step": 22.5
  }
}
```

### Example — spiral galaxy

```json
{
  "name": "Spiral Galaxy",
  "type": "radial",
  "params": {
    "count": 40,
    "center_x": 400,
    "center_y": 300,
    "angle_step": 25,
    "radius_step": 8
  }
}
```

---

## 6. Type `grid`

Tiles the segment in a rectangular grid, with an optional checkerboard mirror.

### Parameters

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `cols` | int | `3` | Columns. |
| `rows` | int | `3` | Rows. |
| `step_x` | float | `100.0` | Horizontal spacing between cells. |
| `step_y` | float | `100.0` | Vertical spacing between cells. |
| `mirror_alternate` | bool | `false` | Cells where `(row + col) % 2 == 1` are mirrored horizontally about the segment centroid. |

### Example — checkerboard

```json
{
  "name": "Checkerboard",
  "type": "grid",
  "params": {
    "cols": 6,
    "rows": 6,
    "step_x": 200,
    "step_y": 200,
    "mirror_alternate": true
  }
}
```

---

## 7. `color_shift` — per-copy hue drift

If `enabled` is `true`, every copy's stroke color (and gradient stops) is shifted before being drawn. Shifts are multiplied by the copy index, so:

- `i = 0` → no shift (the original).
- `i = 1` → one step.
- `i = 2` → two steps.

| Key | Unit | Range | Notes |
|-----|------|-------|-------|
| `enabled` | bool | — | Master switch. Missing/`false` = no color changes. |
| `hue_shift_per_step` | degrees | any | Wraps around 360. `30` with 12 copies covers the full spectrum. |
| `saturation_shift` | percentage points | any | `+10` = 10 pp more saturated per step. Clamped to `[0, 1]`. |
| `lightness_shift` | percentage points | any | `-5` = 5 pp darker per step. Clamped to `[0, 1]`. |
| `alpha_shift` | percentage points | any | `-10` = 10 pp more transparent per step. Clamped to `[0, 255]` on the resulting alpha. |

### Example — rainbow ribbon

```json
{
  "name": "Rainbow Ribbon",
  "type": "linear",
  "params": { "count": 12, "step_x": 180 },
  "color_shift": {
    "enabled": true,
    "hue_shift_per_step": 30
  }
}
```

### Example — fading into distance

```json
{
  "name": "Vanishing Corridor",
  "type": "linear",
  "params": { "count": 14, "scale_per_step": 0.9 },
  "color_shift": {
    "enabled": true,
    "lightness_shift": 2,
    "alpha_shift": -3
  }
}
```

---

## 8. Authoring tips

### Start from an existing template

Copy `linear_wave.json` (or any other), rename the file, change `name` to something unique, then experiment. The dropdown will show both old and new on next launch.

### Test quickly

The Ornamenter reads templates **once at startup**, but you can:

1. Edit a JSON.
2. Close the app.
3. Relaunch.

For a faster loop, keep the app open and edit only the parameter widgets in the Ornamenter panel — they're live. Only the *file list* requires a restart.

### Units are canvas pixels

`step_x`, `step_y`, `radius_step` are in the same units as the Drawer canvas (default: 800×600 coordinate space, points at X=200 and X=600). A `step_x` of `200` lines up with the spacing between the two columns of Drawer points.

### Mirror vs. invert

- **Mirror** flips across a vertical axis (`x → 2·pivot_x − x`). Think "face the other way".
- **Invert** rotates 180°. Think "upside down".

For a *bilateral* frieze (the classic look), enable both — even copies upright, odd copies flipped and inverted.

### Radial centers

For the default 800×600 canvas, always start with:

```json
"center_x": 400,
"center_y": 300
```

This is the canvas midpoint. If you change the canvas size later, adjust all radial templates.

### When to raise `count`

- **Flowers / mandalas:** 6–24 copies is plenty; beyond that, lines blur.
- **Sunbursts:** 24–48 reads as a texture rather than distinct rays.
- **Spirals:** 30–60 with a small `angle_step` (10–25°) and modest `radius_step` (3–10) works well.

### Parametric gotchas

- **`scale_per_step` compounds.** `1.03` after 18 steps is ×1.7; `0.9` after 14 steps is ×0.23. Small values go a long way.
- **`rotation_per_step` also compounds.** `12` with 18 copies rotates the last one by 204°.
- **`grid` has no rotation or scale.** If you need rotated grid cells, apply a linear pass first, then a grid pass on the result — but the current build applies one template per segment.
- **`radial` and `grid` ignore `pivot_*`.** `pivot_*` is a `linear`-only extension.

---

## 9. Validation & common mistakes

| Symptom | Likely cause |
|---------|-------------|
| Template doesn't appear in the dropdown | File isn't in `templates/`, isn't `.json`, or JSON is malformed. Check the console — `load_templates` prints `Template error: <file>` for bad JSON. |
| Dropdown shows a blank name | `"name"` is missing. The filename is used as fallback. |
| "No template selected" warning when generating | The segment is empty (no lines in the Drawer). Add at least one line first. |
| Ornament is empty after Generate | `type` is unknown, or `count`/`cols`/`rows` are `0` or negative. |
| Ornament is drawn but colors don't change | `color_shift.enabled` is missing or `false`, or all shift values are `0`. |
| Everything drawn on top of each other | `step_x`/`step_y`/`radius_step` are all zero — you're stacking N copies at the same position. |
| JSON file loads but template looks stale | The scan runs only at startup. Restart the app after adding new files. |

---

## 10. Schema cheat sheet

```jsonc
{
  "name": "...",                     // required, string
  "type": "linear" | "radial" | "grid",

  "params": {
    // linear
    "count": 6,
    "step_x": 200, "step_y": 0,
    "rotation_per_step": 0,
    "scale_per_step": 1.0,
    "mirror_alternate": false,
    "invert_alternate": false,
    "pivot_x": 400, "pivot_y": 300,

    // radial
    "count": 12,
    "center_x": 400, "center_y": 300,
    "angle_step": 30,
    "radius_step": 0,

    // grid
    "cols": 4, "rows": 3,
    "step_x": 400, "step_y": 300,
    "mirror_alternate": true
  },

  "color_shift": {
    "enabled": true,
    "hue_shift_per_step": 30,
    "saturation_shift": 0,
    "lightness_shift": 0,
    "alpha_shift": 0
  }
}
```

Only the keys matching the chosen `type` are read — extras are silently ignored, so a template can carry parameters for multiple types without harm.

---

## 11. Shipped templates

All 17 templates below are included in the default `templates/` folder.

### Linear

| File | Copies | Distinct feature |
|------|--------|------------------|
| `linear_wave.json` | 6 | Mirrored copies, hue drift |
| `linear_frieze.json` | 10 | Classic bilateral frieze (mirror + invert) |
| `linear_rainbow.json` | 12 | Full 360° hue sweep |
| `linear_spiral.json` | 18 | Rotation + scale-up per step |
| `linear_shrinking.json` | 14 | Scale-down vanishing corridor |
| `linear_zigzag.json` | 8 | Vertical offset + alternating mirror |

### Radial

| File | Copies | Distinct feature |
|------|--------|------------------|
| `radial_flower.json` | 12 | Classic flower |
| `radial_mandala.json` | 16 | 22.5° step, mandala |
| `radial_sunburst.json` | 24 | Dense 15° sunburst |
| `radial_spiral_galaxy.json` | 40 | `radius_step: 8` — galaxy |
| `radial_snowflake.json` | 12 | 6-fold symmetry |
| `radial_concentric.json` | 60 | Slow outward drift |

### Grid

| File | Cells | Distinct feature |
|------|-------|------------------|
| `grid_basic.json` | 4×3 | Original checkerboard |
| `grid_checkerboard.json` | 6×6 | Denser mirror grid |
| `grid_diagonal.json` | 5×5 | Diamond tiling |
| `grid_op_art.json` | 8×8 | Op-art moiré |
| `grid_wallpaper.json` | 7×5 | Uniform, no mirror |

---

*End of guide.*