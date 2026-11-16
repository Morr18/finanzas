#!/usr/bin/env python3
"""Genera los iconos de la app móvil (Android e iOS).

Requiere Pillow: ``python3 -m pip install pillow``.
Uso: ``python3 tool/generate_icons.py`` desde la carpeta ``mobile``.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SS = 4  # supersampling para bordes suaves
START = (79, 70, 229)   # #4F46E5
END = (124, 58, 237)    # #7C3AED


def gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(
                round(START[i] + (END[i] - START[i]) * t) for i in range(3)
            )
    return img


def draw_mark(draw: ImageDraw.ImageDraw, size: int, scale: float = 1.0) -> None:
    unit = size * scale
    bar_width = unit * 0.125
    gap = unit * 0.055
    bottom = size / 2 + unit * 0.21
    heights = (0.20, 0.31, 0.42)
    total = 3 * bar_width + 2 * gap
    left = size / 2 - total / 2
    for index, height in enumerate(heights):
        x = left + index * (bar_width + gap)
        top = bottom - unit * height
        draw.rounded_rectangle(
            (x, top, x + bar_width, bottom),
            radius=bar_width / 2,
            fill=(255, 255, 255, 235 if index < 2 else 255),
        )


def icon(size: int, rounded: bool) -> Image.Image:
    big = size * SS
    img = gradient(big)
    draw = ImageDraw.Draw(img, "RGBA")
    draw_mark(draw, big, scale=0.92)
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, big - 1, big - 1), radius=big * 0.22, fill=255
        )
        out = Image.new("RGB", (big, big), (255, 255, 255))
        out.paste(img, (0, 0), mask)
        img = out
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    android = ROOT / "android/app/src/main/res"
    for folder, size in (
        ("mipmap-mdpi", 48),
        ("mipmap-hdpi", 72),
        ("mipmap-xhdpi", 96),
        ("mipmap-xxhdpi", 144),
        ("mipmap-xxxhdpi", 192),
    ):
        target = android / folder / "ic_launcher.png"
        icon(size, rounded=True).save(target)
        print("android", target.relative_to(ROOT))

    assets = ROOT / "ios/Runner/Assets.xcassets/AppIcon.appiconset"
    manifest = json.loads((assets / "Contents.json").read_text())
    for entry in manifest["images"]:
        filename = entry.get("filename")
        if not filename:
            continue
        points = float(entry["size"].split("x")[0])
        scale = int(entry["scale"].rstrip("x"))
        size = round(points * scale)
        icon(size, rounded=False).save(assets / filename)
    print("ios", len(manifest["images"]), "iconos")

    # Icono adaptativo de Android (API 26+).
    anydpi = android / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    (anydpi / "ic_launcher.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background" />\n'
        '    <foreground android:drawable="@drawable/ic_launcher_foreground" />\n'
        "</adaptive-icon>\n"
    )
    values = android / "values"
    (values / "ic_launcher_background.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        '    <color name="ic_launcher_background">#4F46E5</color>\n'
        "</resources>\n"
    )
    drawable = android / "drawable"
    (drawable / "ic_launcher_foreground.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="108dp" android:height="108dp"\n'
        '    android:viewportWidth="108" android:viewportHeight="108">\n'
        '    <path android:fillColor="#FFFFFF"\n'
        '        android:pathData="M31,54 h9 a4.5,4.5 0 0 1 4.5,4.5 v13 a4.5,4.5 0 0 1 -4.5,4.5'
        ' h-9 a4.5,4.5 0 0 1 -4.5,-4.5 v-13 a4.5,4.5 0 0 1 4.5,-4.5 z" />\n'
        '    <path android:fillColor="#FFFFFF"\n'
        '        android:pathData="M47.25,44 h9 a4.5,4.5 0 0 1 4.5,4.5 v23 a4.5,4.5 0 0 1 -4.5,4.5'
        ' h-9 a4.5,4.5 0 0 1 -4.5,-4.5 v-23 a4.5,4.5 0 0 1 4.5,-4.5 z" />\n'
        '    <path android:fillColor="#FFFFFF"\n'
        '        android:pathData="M63.5,34 h9 a4.5,4.5 0 0 1 4.5,4.5 v33 a4.5,4.5 0 0 1 -4.5,4.5'
        ' h-9 a4.5,4.5 0 0 1 -4.5,-4.5 v-33 a4.5,4.5 0 0 1 4.5,-4.5 z" />\n'
        "</vector>\n"
    )
    print("android icono adaptativo")


if __name__ == "__main__":
    main()
