#!/usr/bin/env python3
"""Converts resources/icon.svg to resources/app.icns using cairosvg + iconutil."""
import os
import subprocess
import cairosvg

ICONSET = "/tmp/PDFReader.iconset"
SVG = os.path.join(os.path.dirname(__file__), "resources/icon.svg")
OUT = os.path.join(os.path.dirname(__file__), "resources/app.icns")

SIZES = [16, 32, 64, 128, 256, 512]

os.makedirs(ICONSET, exist_ok=True)

for s in SIZES:
    for scale, suffix in [(1, ""), (2, "@2x")]:
        px = s * scale
        name = f"icon_{s}x{s}{suffix}.png"
        cairosvg.svg2png(url=SVG, write_to=os.path.join(ICONSET, name),
                         output_width=px, output_height=px)
        print(f"  {name}")

subprocess.run(["iconutil", "-c", "icns", ICONSET, "-o", OUT], check=True)
print(f"Ikona: {OUT}")
