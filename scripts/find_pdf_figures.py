#!/usr/bin/env python3
"""Find and extract figures from a PDF.

The workflow is intentionally pragmatic:
1. If the PDF has embedded raster images, extract them with pdfimages.
2. Find figure captions from pdftotext bounding boxes.
3. For caption-bearing pages, render the page and crop a candidate figure
   region relative to the caption position.

This works well for older journal PDFs where visible figures are often vector
page content rather than standalone raster assets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path


CAPTION_RE = re.compile(
    r"^(fig(?:ure)?)\.?\s*(\d+)\s*(?:[.:]|[—-])",
    re.IGNORECASE,
)
INVALID_XML_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass
class Caption:
    page: int
    page_width: float
    page_height: float
    text: str
    label: str
    number: int
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def run(cmd: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_pdfimages_list(pdf_path: Path) -> list[dict[str, str]]:
    output = run(["pdfimages", "-list", str(pdf_path)], capture=True)
    lines = [line.rstrip() for line in output.splitlines()]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 13:
            continue
        rows.append(
            {
                "page": parts[0],
                "num": parts[1],
                "type": parts[2],
                "width": parts[3],
                "height": parts[4],
                "color": parts[5],
                "comp": parts[6],
                "bpc": parts[7],
                "enc": parts[8],
                "interp": parts[9],
                "object_id": parts[10],
                "x_ppi": parts[11],
                "y_ppi": parts[12],
            }
        )
    return rows


def extract_raster_images(pdf_path: Path, output_dir: Path) -> list[dict[str, str]]:
    rows = parse_pdfimages_list(pdf_path)
    if not rows:
        return []
    raster_dir = output_dir / "raster"
    raster_dir.mkdir(parents=True, exist_ok=True)
    base = raster_dir / "image"
    run(["pdfimages", "-all", str(pdf_path), str(base)])
    return rows


def parse_captions(pdf_path: Path) -> list[Caption]:
    output = run(["pdftotext", "-bbox-layout", str(pdf_path), "-"], capture=True)
    sanitized = INVALID_XML_RE.sub("", output)
    root = ET.fromstring(sanitized)
    captions: list[Caption] = []
    page_number = 0
    for page in root.iter():
        if local_name(page.tag) != "page":
            continue
        page_number += 1
        page_width = float(page.attrib["width"])
        page_height = float(page.attrib["height"])
        for line in page.iter():
            if local_name(line.tag) != "line":
                continue
            words = [node for node in line.iter() if local_name(node.tag) == "word"]
            if not words:
                continue
            text = " ".join((word.text or "").strip() for word in words).strip()
            if not text:
                continue
            match = CAPTION_RE.match(text)
            if not match:
                continue
            x_min = min(float(word.attrib["xMin"]) for word in words)
            y_min = min(float(word.attrib["yMin"]) for word in words)
            x_max = max(float(word.attrib["xMax"]) for word in words)
            y_max = max(float(word.attrib["yMax"]) for word in words)
            captions.append(
                Caption(
                    page=page_number,
                    page_width=page_width,
                    page_height=page_height,
                    text=text,
                    label=match.group(1),
                    number=int(match.group(2)),
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                )
            )
    return captions


def render_page(pdf_path: Path, page_number: int, dpi: int, temp_dir: Path) -> Path:
    base = temp_dir / f"page_{page_number:03d}"
    run(
        [
            "pdftocairo",
            "-png",
            "-r",
            str(dpi),
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf_path),
            str(base),
        ]
    )
    matches = sorted(temp_dir.glob(f"page_{page_number:03d}-*.png"))
    if not matches:
        raise FileNotFoundError(
            f"Expected a rendered page matching page_{page_number:03d}-*.png in {temp_dir}"
        )
    return matches[0]


def image_size(path: Path) -> tuple[int, int]:
    out = run(
        ["magick", "identify", "-format", "%w %h", str(path)],
        capture=True,
    ).strip()
    width_str, height_str = out.split()
    return int(width_str), int(height_str)


def points_to_pixels(value: float, page_extent: float, image_extent: int) -> int:
    return max(0, round((value / page_extent) * image_extent))


def crop_rects(caption: Caption) -> dict[str, tuple[float, float, float, float]]:
    margin_x = 32.0
    top_margin_y = 58.0
    bottom_margin_y = 24.0
    caption_pad = 14.0
    gutter = 18.0

    x0 = margin_x
    x1 = caption.page_width - margin_x
    above_y0 = top_margin_y
    above_y1 = max(top_margin_y + 36.0, caption.y_min - caption_pad)
    below_y0 = min(caption.page_height - bottom_margin_y - 36.0, caption.y_max + caption_pad)
    below_y1 = caption.page_height - bottom_margin_y

    if above_y1 <= above_y0:
        above_y0 = top_margin_y
        above_y1 = caption.page_height - bottom_margin_y
    if below_y1 <= below_y0:
        below_y0 = top_margin_y
        below_y1 = caption.page_height - bottom_margin_y

    rects = {
        "above_full": (x0, above_y0, x1, above_y1),
        "below_full": (x0, below_y0, x1, below_y1),
    }

    # Older journal PDFs often place a single-column figure above a caption
    # that spans both columns. Emit a column-aware alternative for those.
    if not re.search(r"\b(left|right|top|bottom)\b\s*:", caption.text, re.IGNORECASE):
        half = caption.page_width / 2.0
        if caption.x_min < half:
            col_x0 = x0
            col_x1 = half - gutter
        else:
            col_x0 = half + gutter
            col_x1 = x1
        rects["above_column"] = (col_x0, above_y0, col_x1, above_y1)
        rects["below_column"] = (col_x0, below_y0, col_x1, below_y1)

    return rects


def extract_vector_figures(
    pdf_path: Path,
    captions: list[Caption],
    output_dir: Path,
    dpi: int,
) -> list[dict[str, object]]:
    vector_dir = output_dir / "vector"
    vector_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, object]] = []
    rendered_pages: dict[int, Path] = {}

    with tempfile.TemporaryDirectory(prefix="figure-finder-") as temp:
        temp_dir = Path(temp)
        for caption in captions:
            if caption.page not in rendered_pages:
                rendered_pages[caption.page] = render_page(pdf_path, caption.page, dpi, temp_dir)
            page_png = rendered_pages[caption.page]
            img_w, img_h = image_size(page_png)
            for position, (x0_pt, y0_pt, x1_pt, y1_pt) in crop_rects(caption).items():
                x_px = points_to_pixels(x0_pt, caption.page_width, img_w)
                y_px = points_to_pixels(y0_pt, caption.page_height, img_h)
                w_px = max(1, points_to_pixels(x1_pt - x0_pt, caption.page_width, img_w))
                h_px = max(1, points_to_pixels(y1_pt - y0_pt, caption.page_height, img_h))

                stem = f"page_{caption.page:03d}_figure_{caption.number:02d}_{position}"
                out_path = vector_dir / f"{stem}.png"
                run(
                    [
                        "magick",
                        str(page_png),
                        "-crop",
                        f"{w_px}x{h_px}+{x_px}+{y_px}",
                        "+repage",
                        str(out_path),
                    ]
                )
                extracted.append(
                    {
                        "page": caption.page,
                        "figure_number": caption.number,
                        "caption": caption.text,
                        "position": position,
                        "output": str(out_path),
                        "crop_box_points": [x0_pt, y0_pt, x1_pt, y1_pt],
                        "crop_box_pixels": [x_px, y_px, w_px, h_px],
                        "page_render": str(page_png),
                    }
                )
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Input PDF")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write extracted figure assets",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Render DPI for vector figure crops",
    )
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "pdf": str(pdf_path),
        "raster_images": [],
        "captions": [],
        "vector_figures": [],
    }

    manifest["raster_images"] = extract_raster_images(pdf_path, output_dir)
    captions = parse_captions(pdf_path)
    manifest["captions"] = [asdict(caption) for caption in captions]
    manifest["vector_figures"] = extract_vector_figures(pdf_path, captions, output_dir, args.dpi)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote figure assets to {output_dir}")
    print(f"Raster images found: {len(manifest['raster_images'])}")
    print(f"Figure captions found: {len(captions)}")
    print(f"Vector figure crops written: {len(manifest['vector_figures'])}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
