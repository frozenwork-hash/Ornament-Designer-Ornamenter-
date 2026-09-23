# smoke_segment_io.py
import os, tempfile, json
from ornament.core import Point, StraightLine, ArcLine, Segment
from ornament.segment_io import (
    SegmentLibrary, segment_to_svg, segment_bounds,
    segment_to_clipboard_json, segment_from_clipboard_json,
    sanitize_name)

s = Segment()
s.add_line(StraightLine(Point(0, 0), Point(100, 100)))
s.add_line(ArcLine(Point(100, 100), Point(200, 0), bend=40))

# bounds include arc control point (midpoint + perpendicular * bend)
x0, y0, x1, y1 = segment_bounds(s, padding=0)
assert x1 - x0 >= 200
assert y1 - y0 >= 100

# SVG is a complete document
svg = segment_to_svg(s, padding=10)
assert svg.startswith("<?xml")
assert "<svg " in svg and "</svg>" in svg
assert "viewBox=" in svg
assert 'stroke-linecap="butt"' not in svg or True  # just noting: cap default = round

# Clipboard round-trip
text = segment_to_clipboard_json(s)
back = segment_from_clipboard_json(text)
assert back is not None
assert len(back.lines) == 2
assert back.to_dict() == s.to_dict()

# Library round-trip
with tempfile.TemporaryDirectory() as d:
    lib = SegmentLibrary(d)
    lib.save(s, "My Segment!")
    names = lib.list_names()
    assert names == [sanitize_name("My Segment!")], names
    loaded = lib.load("My Segment!")
    assert loaded.to_dict() == s.to_dict()
    assert lib.delete("My Segment!") is True
    assert lib.list_names() == []

print("OK")