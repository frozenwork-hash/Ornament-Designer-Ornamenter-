from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QPainterPath,
                         QLinearGradient, QRadialGradient)
from .core import (Segment, Line, ArcLine, Gradient, Ornament,
                   CAP_STYLES, JOIN_STYLES)

# Mapping of string styles to Qt constants.
# Key names must match core.CAP_STYLES / core.JOIN_STYLES —
# the asserts below will catch a desync at import time.
_CAP_MAP = {
    "flat":   Qt.FlatCap,
    "round":  Qt.RoundCap,
    "square": Qt.SquareCap,
}
_JOIN_MAP = {
    "miter": Qt.MiterJoin,
    "round": Qt.RoundJoin,
    "bevel": Qt.BevelJoin,
}

assert set(_CAP_MAP)  == set(CAP_STYLES),  "render._CAP_MAP desynced from core.CAP_STYLES"
assert set(_JOIN_MAP) == set(JOIN_STYLES), "render._JOIN_MAP desynced from core.JOIN_STYLES"


def line_to_path(line: Line) -> QPainterPath:
    p = QPainterPath()
    p.moveTo(line.start_point.x, line.start_point.y)
    if isinstance(line, ArcLine):
        c = line.control_point()
        p.quadTo(c.x, c.y, line.end_point.x, line.end_point.y)
    else:
        p.lineTo(line.end_point.x, line.end_point.y)
    return p


def _build_qgradient(g: Gradient, rect):
    if g.type == "linear":
        lg = QLinearGradient(
            rect.left() + g.x1 * rect.width(),
            rect.top() + g.y1 * rect.height(),
            rect.left() + g.x2 * rect.width(),
            rect.top() + g.y2 * rect.height())
        for off, c in g.stops:
            lg.setColorAt(off, QColor(*c))
        return lg
    rg = QRadialGradient(
        rect.left() + g.x1 * rect.width(),
        rect.top() + g.y1 * rect.height(),
        max(rect.width(), rect.height()) * max(g.x2, 0.01))
    for off, c in g.stops:
        rg.setColorAt(off, QColor(*c))
    return rg


def draw_line(painter: QPainter, line: Line):
    path = line_to_path(line)
    pen = QPen()

    w = max(0.1, line.stroke_width)
    pen.setWidthF(w)
    pen.setCapStyle(_CAP_MAP.get(line.cap_style, Qt.RoundCap))
    pen.setJoinStyle(_JOIN_MAP.get(line.join_style, Qt.RoundJoin))

    if line.dash_pattern:
        pen.setDashPattern([d / w for d in line.dash_pattern])
        if line.dash_offset:
            pen.setDashOffset(line.dash_offset / w)

    if line.gradient is None:
        pen.setColor(QColor(*line.stroke_color))
    else:
        pen.setBrush(QBrush(_build_qgradient(line.gradient, path.boundingRect())))

    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    prev_op = painter.opacity()
    apply_op = line.opacity < 1.0
    if apply_op:
        painter.setOpacity(prev_op * max(0.0, min(1.0, line.opacity)))
    try:
        painter.drawPath(path)
    finally:
        if apply_op:
            painter.setOpacity(prev_op)


def draw_segment(painter: QPainter, seg: Segment):
    for l in sorted(seg.lines, key=lambda x: x.z_index):
        draw_line(painter, l)


def draw_ornament(painter: QPainter, orn: Ornament):
    for seg in orn.segments:
        draw_segment(painter, seg)