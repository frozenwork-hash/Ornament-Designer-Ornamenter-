"""Ornament Designer data core."""
from __future__ import annotations
import math, json, os, colorsys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

RGBA = Tuple[int, int, int, int]

# === Single source of truth for style names ===
# render.py must support mapping for exactly these values
# (see assertions in render._CAP_MAP / _JOIN_MAP).
CAP_STYLES = ("flat", "round", "square")
JOIN_STYLES = ("miter", "round", "bevel")

# Mapping of internal names (Qt terminology) to SVG values.
# Qt calls the flat cap "flat", SVG calls it "butt".
SVG_CAP = {"flat": "butt", "round": "round", "square": "square"}
# join matches between Qt and SVG 1:1 — kept as a dict for uniformity.
SVG_JOIN = {"miter": "miter", "round": "round", "bevel": "bevel"}

# Line style attributes (added earlier):
#   dash_pattern: List[float] — dash/gap lengths in canvas units ([] = solid)
#   dash_offset: float        — dash phase offset
#   cap_style: str            — "flat" | "round" | "square"  (exported to SVG as butt/round/square)
#   join_style: str           — "miter" | "round" | "bevel"
#   opacity: float            — overall opacity (0..1), multiplied by the color's alpha
#
# Example JSON serialization of a line:
# {
#   "type": "straight",
#   "start": [0, 0], "end": [100, 100],
#   "color": [255, 0, 0, 255], "width": 2, "z": 0,
#   "dash_pattern": [10, 5], "dash_offset": 0,
#   "cap_style": "round", "join_style": "round", "opacity": 1.0
# }


# ==================== Matrix (affine 2×3) ====================

@dataclass
class Matrix:
    a: float = 1.0; b: float = 0.0
    c: float = 0.0; d: float = 1.0
    e: float = 0.0; f: float = 0.0

    @staticmethod
    def identity() -> "Matrix":
        return Matrix()

    @staticmethod
    def translate(tx, ty) -> "Matrix":
        return Matrix(1, 0, 0, 1, tx, ty)

    @staticmethod
    def scale(sx, sy=None) -> "Matrix":
        sy = sx if sy is None else sy
        return Matrix(sx, 0, 0, sy, 0, 0)

    @staticmethod
    def rotate(deg) -> "Matrix":
        r = math.radians(deg); c, s = math.cos(r), math.sin(r)
        return Matrix(c, s, -s, c, 0, 0)

    @staticmethod
    def rotate_about(deg, cx, cy) -> "Matrix":
        return (Matrix.translate(cx, cy)
                @ Matrix.rotate(deg)
                @ Matrix.translate(-cx, -cy))

    def apply(self, x, y):
        return (self.a * x + self.c * y + self.e,
                self.b * x + self.d * y + self.f)

    def __matmul__(self, o: "Matrix") -> "Matrix":
        # self @ o  ==  first o, then self
        return Matrix(
            self.a * o.a + self.c * o.b, self.b * o.a + self.d * o.b,
            self.a * o.c + self.c * o.d, self.b * o.c + self.d * o.d,
            self.a * o.e + self.c * o.f + self.e,
            self.b * o.e + self.d * o.f + self.f)


# ==================== Point ====================

@dataclass
class Point:
    x: float
    y: float

    def transformed(self, m: Matrix) -> "Point":
        x, y = m.apply(self.x, self.y)
        return Point(x, y)

    def to_list(self):
        return [self.x, self.y]

    @classmethod
    def from_list(cls, l):
        return cls(float(l[0]), float(l[1]))


# ==================== Gradient ====================

@dataclass
class Gradient:
    type: str = "linear"          # "linear" | "radial"
    x1: float = 0.0; y1: float = 0.0
    x2: float = 1.0; y2: float = 1.0
    stops: List[Tuple[float, RGBA]] = field(default_factory=list)

    def to_dict(self):
        return {"type": self.type, "x1": self.x1, "y1": self.y1,
                "x2": self.x2, "y2": self.y2,
                "stops": [[s[0], list(s[1])] for s in self.stops]}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("type", "linear"),
                   d.get("x1", 0.0), d.get("y1", 0.0),
                   d.get("x2", 1.0), d.get("y2", 1.0),
                   [(float(s[0]), tuple(s[1])) for s in d.get("stops", [])])

    def svg_def(self, gid: str) -> str:
        if self.type == "linear":
            head = (f'<linearGradient id="{gid}" x1="{self.x1}" y1="{self.y1}" '
                    f'x2="{self.x2}" y2="{self.y2}">')
            tail = '</linearGradient>'
        else:
            head = (f'<radialGradient id="{gid}" cx="{self.x1}" cy="{self.y1}" '
                    f'r="{self.x2}">')
            tail = '</radialGradient>'
        stops = "".join(
            f'<stop offset="{off:.3f}" stop-color="rgb({r},{g},{b})" '
            f'stop-opacity="{a/255:.3f}"/>'
            for off, (r, g, b, a) in self.stops)
        return head + stops + tail


# ==================== Lines ====================

class Line:
    type_name = "line"

    def __init__(self, start: Point, end: Point,
                 color: RGBA = (0, 0, 0, 255),
                 width: float = 2.0, z_index: int = 0,
                 gradient: Optional[Gradient] = None,
                 dash_pattern: Optional[List[float]] = None,
                 dash_offset: float = 0.0,
                 cap_style: str = "round",
                 join_style: str = "round",
                 opacity: float = 1.0):
        self.start_point = start
        self.end_point = end
        self.stroke_color = tuple(color)
        self.stroke_width = float(width)
        self.z_index = int(z_index)
        self.gradient = gradient
        self.dash_pattern = list(dash_pattern) if dash_pattern else []
        self.dash_offset = float(dash_offset)
        self.cap_style = cap_style if cap_style in CAP_STYLES else "round"
        self.join_style = join_style if join_style in JOIN_STYLES else "round"
        self.opacity = max(0.0, min(1.0, float(opacity)))

    def clone(self) -> "Line": raise NotImplementedError
    def to_dict(self) -> Dict[str, Any]: raise NotImplementedError
    def get_svg(self, gid: Optional[str] = None) -> str: raise NotImplementedError

    def apply_transform(self, m: Matrix) -> "Line":
        c = self.clone()
        c.start_point = self.start_point.transformed(m)
        c.end_point = self.end_point.transformed(m)
        return c

    def _style_dict(self) -> Dict[str, Any]:
        """Common style fields for to_dict()."""
        return {
            "dash_pattern": list(self.dash_pattern),
            "dash_offset": self.dash_offset,
            "cap_style": self.cap_style,
            "join_style": self.join_style,
            "opacity": self.opacity,
        }

    def _stroke_attrs(self, gid: Optional[str] = None) -> str:
        """SVG stroke attributes as a single string.

        Internal names ('flat') are converted to valid SVG names ('butt')
        so that manual serialization (Segment.get_svg / Ornament.get_svg)
        produces valid SVG.
        """
        parts = []
        if gid:
            parts.append(f'stroke="url(#{gid})"')
        else:
            r, g, b, a = self.stroke_color
            parts.append(f'stroke="rgb({r},{g},{b})"')
            # effective opacity = color alpha × line opacity
            eff = max(0, min(255, int(round(a * self.opacity))))
            parts.append(f'stroke-opacity="{eff/255:.3f}"')
        parts.append(f'stroke-width="{self.stroke_width}"')
        if self.dash_pattern:
            arr = ",".join(str(x) for x in self.dash_pattern)
            parts.append(f'stroke-dasharray="{arr}"')
            if self.dash_offset:
                parts.append(f'stroke-dashoffset="{self.dash_offset}"')
        # ← critical fix: SVG doesn't know "flat", it needs "butt"
        svg_cap = SVG_CAP.get(self.cap_style, "round")
        svg_join = SVG_JOIN.get(self.join_style, "round")
        parts.append(f'stroke-linecap="{svg_cap}"')
        parts.append(f'stroke-linejoin="{svg_join}"')
        if gid and self.opacity < 1.0:
            parts.append(f'stroke-opacity="{self.opacity:.3f}"')
        return " ".join(parts)


class StraightLine(Line):
    type_name = "straight"

    def clone(self):
        return StraightLine(
            self.start_point, self.end_point,
            self.stroke_color, self.stroke_width, self.z_index,
            Gradient.from_dict(self.gradient.to_dict()) if self.gradient else None,
            list(self.dash_pattern), self.dash_offset,
            self.cap_style, self.join_style, self.opacity)

    def to_dict(self):
        d = {"type": "straight",
             "start": self.start_point.to_list(),
             "end": self.end_point.to_list(),
             "color": list(self.stroke_color),
             "width": self.stroke_width,
             "z": self.z_index}
        if self.gradient:
            d["gradient"] = self.gradient.to_dict()
        d.update(self._style_dict())
        return d

    def get_svg(self, gid=None):
        attrs = self._stroke_attrs(gid)
        return (f'<line x1="{self.start_point.x}" y1="{self.start_point.y}" '
                f'x2="{self.end_point.x}" y2="{self.end_point.y}" '
                f'{attrs} fill="none"/>')


class ArcLine(Line):
    """Quadratic Bezier curve with a bend parameter."""
    type_name = "arc"

    def __init__(self, start, end,
                 color=(0, 0, 0, 255), width=2.0, z_index=0,
                 gradient=None, bend: float = 0.0,
                 dash_pattern=None, dash_offset=0.0,
                 cap_style="round", join_style="round", opacity=1.0):
        super().__init__(start, end, color, width, z_index, gradient,
                         dash_pattern, dash_offset, cap_style, join_style, opacity)
        self.bend = float(bend)

    def control_point(self) -> Point:
        mx = (self.start_point.x + self.end_point.x) / 2
        my = (self.start_point.y + self.end_point.y) / 2
        dx = self.end_point.x - self.start_point.x
        dy = self.end_point.y - self.start_point.y
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        return Point(mx + nx * self.bend, my + ny * self.bend)

    def apply_transform(self, m):
        c = self.clone()
        c.start_point = self.start_point.transformed(m)
        c.end_point = self.end_point.transformed(m)
        ctrl_t = self.control_point().transformed(m)
        mx = (c.start_point.x + c.end_point.x) / 2
        my = (c.start_point.y + c.end_point.y) / 2
        dx = c.end_point.x - c.start_point.x
        dy = c.end_point.y - c.start_point.y
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        c.bend = (ctrl_t.x - mx) * nx + (ctrl_t.y - my) * ny
        return c

    def clone(self):
        return ArcLine(
            self.start_point, self.end_point,
            self.stroke_color, self.stroke_width, self.z_index,
            Gradient.from_dict(self.gradient.to_dict()) if self.gradient else None,
            self.bend,
            list(self.dash_pattern), self.dash_offset,
            self.cap_style, self.join_style, self.opacity)

    def to_dict(self):
        d = {"type": "arc",
             "start": self.start_point.to_list(),
             "end": self.end_point.to_list(),
             "bend": self.bend,
             "color": list(self.stroke_color),
             "width": self.stroke_width,
             "z": self.z_index}
        if self.gradient:
            d["gradient"] = self.gradient.to_dict()
        d.update(self._style_dict())
        return d

    def get_svg(self, gid=None):
        attrs = self._stroke_attrs(gid)
        c = self.control_point()
        return (f'<path d="M {self.start_point.x} {self.start_point.y} '
                f'Q {c.x} {c.y} {self.end_point.x} {self.end_point.y}" '
                f'{attrs} fill="none"/>')


def line_from_dict(d: Dict[str, Any]) -> Optional[Line]:
    t = d.get("type", "straight")
    sp = Point.from_list(d["start"]); ep = Point.from_list(d["end"])
    color = tuple(d.get("color", [0, 0, 0, 255]))
    width = d.get("width", 2.0)
    z = d.get("z", 0)
    grad = Gradient.from_dict(d["gradient"]) if d.get("gradient") else None

    # new fields are optional; defaults keep compatibility with old JSON
    op = d.get("opacity")
    common = dict(
        dash_pattern=list(d.get("dash_pattern", []) or []),
        dash_offset=float(d.get("dash_offset", 0.0) or 0.0),
        cap_style=d.get("cap_style") or "round",
        join_style=d.get("join_style") or "round",
        opacity=float(1.0 if op is None else op),
    )
    if t == "straight":
        return StraightLine(sp, ep, color, width, z, grad, **common)
    if t == "arc":
        return ArcLine(sp, ep, color, width, z, grad,
                       bend=d.get("bend", 0.0), **common)
    return None


# ==================== Segment ====================

class Segment:
    def __init__(self, lines=None, base_points=None):
        self.lines: List[Line] = list(lines or [])
        self.base_points: List[Point] = list(base_points or [])
        self._next_z = max((l.z_index for l in self.lines), default=-1) + 1

    def add_line(self, line: Line) -> Line:
        line.z_index = self._next_z
        self._next_z += 1
        self.lines.append(line)
        return line

    def remove_line(self, line: Line):
        if line in self.lines:
            self.lines.remove(line)

    def center(self) -> Tuple[float, float]:
        xs, ys = [], []
        for l in self.lines:
            xs.append(l.start_point.x); ys.append(l.start_point.y)
            xs.append(l.end_point.x);   ys.append(l.end_point.y)
            if isinstance(l, ArcLine):
                c = l.control_point()
                xs.append(c.x); ys.append(c.y)
        if not xs:
            return (0.0, 0.0)
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def get_svg(self, defs: Optional[List[str]] = None,
                gid_prefix: str = "g") -> str:
        if defs is None:
            defs = []
        parts = []
        for i, line in enumerate(sorted(self.lines, key=lambda l: l.z_index)):
            if line.gradient:
                gid = f"{gid_prefix}_{i}"
                defs.append(line.gradient.svg_def(gid))
                parts.append(line.get_svg(gid))
            else:
                parts.append(line.get_svg())
        return "\n".join(parts)

    def apply_transform(self, m: Matrix) -> "Segment":
        new = Segment(base_points=[p.transformed(m) for p in self.base_points])
        for l in self.lines:
            nl = l.apply_transform(m)
            nl.z_index = l.z_index
            new.lines.append(nl)
        new._next_z = self._next_z
        return new

    def clone(self) -> "Segment":
        new = Segment(base_points=[Point(p.x, p.y) for p in self.base_points])
        for l in self.lines:
            new.lines.append(l.clone())
        new._next_z = self._next_z
        return new

    def recolor(self, fn):
        for l in self.lines:
            l.stroke_color = tuple(fn(l.stroke_color))
            if l.gradient:
                l.gradient.stops = [(off, tuple(fn(c)))
                                    for off, c in l.gradient.stops]

    def to_dict(self):
        return {"lines": [l.to_dict() for l in self.lines],
                "base_points": [p.to_list() for p in self.base_points]}

    @classmethod
    def from_dict(cls, d):
        s = cls()
        s.base_points = [Point.from_list(p) for p in d.get("base_points", [])]
        for ld in d.get("lines", []):
            line = line_from_dict(ld)
            if line:
                s.lines.append(line)
        s._next_z = max((l.z_index for l in s.lines), default=-1) + 1
        return s


# ==================== Ornament ====================

class Ornament:
    def __init__(self):
        self.segments: List[Segment] = []

    def add_segment(self, seg: Segment):
        self.segments.append(seg)

    def bounds(self):
        xs, ys = [], []
        for seg in self.segments:
            for l in seg.lines:
                for p in (l.start_point, l.end_point):
                    xs.append(p.x); ys.append(p.y)
                if isinstance(l, ArcLine):
                    c = l.control_point()
                    xs.append(c.x); ys.append(c.y)
        if not xs:
            return (0.0, 0.0, 100.0, 100.0)
        return (min(xs), min(ys), max(xs), max(ys))

    def get_svg(self) -> str:
        x0, y0, x1, y1 = self.bounds()
        w, h = max(1.0, x1 - x0), max(1.0, y1 - y0)
        defs: List[str] = []
        body = "\n".join(seg.get_svg(defs, f"g{i}")
                         for i, seg in enumerate(self.segments))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{w:.2f}" height="{h:.2f}" '
                f'viewBox="{x0} {y0} {w} {h}">\n'
                f'<defs>{"".join(defs)}</defs>\n{body}\n</svg>')


# ==================== Color helper ====================

def shift_rgba(rgba: RGBA, hue_shift=0.0, sat_shift=0.0,
               light_shift=0.0, alpha_shift=0.0) -> RGBA:
    """Shifts: hue in degrees, sat/light/alpha in percentage points."""
    r, g, b, a = rgba
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    h = (h + hue_shift / 360.0) % 1.0
    s = max(0.0, min(1.0, s + sat_shift / 100.0))
    l = max(0.0, min(1.0, l + light_shift / 100.0))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    a2 = max(0, min(255, int(round(a + alpha_shift / 100.0 * 255))))
    return (int(r2 * 255), int(g2 * 255), int(b2 * 255), a2)


# ==================== Templates ====================

def apply_template(segment: Segment, template: Dict[str, Any]) -> Ornament:
    orn = Ornament()
    t = template.get("type", "linear")
    p = template.get("params", {})
    cs = template.get("color_shift", {}) or {}
    cx, cy = segment.center()

    def maybe_shift(seg: Segment, i: int):
        if not cs.get("enabled"):
            return
        h = cs.get("hue_shift_per_step", 0.0) * i
        s = cs.get("saturation_shift", 0.0) * i
        l = cs.get("lightness_shift", 0.0) * i
        a = cs.get("alpha_shift", 0.0) * i
        seg.recolor(lambda c: shift_rgba(c, h, s, l, a))

    if t == "linear":
        n = int(p.get("count", 1))
        sx = p.get("step_x", 0.0); sy = p.get("step_y", 0.0)
        rot = p.get("rotation_per_step", 0.0)
        scl = p.get("scale_per_step", 1.0)
        mir = bool(p.get("mirror_alternate"))
        inv = bool(p.get("invert_alternate"))
        pcx = p.get("pivot_x", cx); pcy = p.get("pivot_y", cy)
        for i in range(n):
            m = Matrix.identity()
            if mir and i % 2 == 1:
                m = (Matrix.translate(pcx, 0)
                     @ Matrix.scale(-1, 1)
                     @ Matrix.translate(-pcx, 0) @ m)
            if inv and i % 2 == 1:
                m = Matrix.rotate_about(180, pcx, pcy) @ m
            if rot:
                m = Matrix.rotate_about(rot * i, pcx, pcy) @ m
            if scl != 1.0:
                s = scl ** i
                m = (Matrix.translate(pcx, pcy)
                     @ Matrix.scale(s, s)
                     @ Matrix.translate(-pcx, -pcy) @ m)
            m = Matrix.translate(sx * i, sy * i) @ m
            seg2 = segment.apply_transform(m)
            maybe_shift(seg2, i)
            orn.add_segment(seg2)

    elif t == "radial":
        n = int(p.get("count", 8))
        ccx = p.get("center_x", cx)
        ccy = p.get("center_y", cy)
        astep = p.get("angle_step", 360.0 / max(1, n))
        rstep = p.get("radius_step", 0.0)
        for i in range(n):
            m = Matrix.rotate_about(astep * i, ccx, ccy)
            if rstep:
                ang = math.radians(astep * i)
                m = Matrix.translate(rstep * i * math.cos(ang),
                                     rstep * i * math.sin(ang)) @ m
            seg2 = segment.apply_transform(m)
            maybe_shift(seg2, i)
            orn.add_segment(seg2)

    elif t == "grid":
        cols = int(p.get("cols", 3))
        rows = int(p.get("rows", 3))
        sx = p.get("step_x", 100.0)
        sy = p.get("step_y", 100.0)
        mir = bool(p.get("mirror_alternate"))
        idx = 0
        for r in range(rows):
            for c in range(cols):
                if mir and (r + c) % 2 == 1:
                    m = (Matrix.translate(c * sx + cx, r * sy)
                         @ Matrix.scale(-1, 1)
                         @ Matrix.translate(-cx, 0))
                else:
                    m = Matrix.translate(c * sx, r * sy)
                seg2 = segment.apply_transform(m)
                maybe_shift(seg2, idx)
                orn.add_segment(seg2)
                idx += 1
    return orn


def load_templates(path: str) -> Dict[str, Dict[str, Any]]:
    out = {}
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            if fn.endswith(".json"):
                with open(os.path.join(path, fn), encoding="utf-8") as f:
                    try:
                        t = json.load(f)
                        out[t.get("name", fn)] = t
                    except Exception as e:
                        print("Template error:", fn, e)
    return out


# ==================== File helpers ====================

def save_segment(segment: Segment, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(segment.to_dict(), f, indent=2, ensure_ascii=False)


def load_segment(path: str) -> Segment:
    with open(path, encoding="utf-8") as f:
        return Segment.from_dict(json.load(f))