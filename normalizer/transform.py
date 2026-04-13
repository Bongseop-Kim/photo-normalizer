from __future__ import annotations

import subprocess
from pathlib import Path

from normalizer.models import ImageRecord


def compute_crop_rect(
    bbox: tuple[int, int, int, int],
    canvas_size: int,
    target_ratio: float,
) -> tuple[int, int, int, int, float]:
    x, y, width, height = bbox
    subject_cx = x + width // 2
    subject_cy = y + height // 2
    target_pixels = canvas_size * target_ratio
    scale = target_pixels / max(width, height)
    size = int(round(canvas_size / scale))
    crop_x = subject_cx - size // 2
    crop_y = subject_cy - size // 2
    return crop_x, crop_y, size, size, scale


def compute_brightness_scale(image_bg: float, reference_bg: float) -> float:
    if image_bg == 0:
        return 1.0
    return reference_bg / image_bg


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def step2_rotate(record: ImageRecord, reference_angle: float) -> ImageRecord:
    original_angle = record.measurements.get("original_angle", 0.0)
    delta = reference_angle - original_angle
    record.measurements["angle_delta"] = round(delta, 2)
    record.measurements["angle_corrected"] = False

    if not record.config.angle_enabled or abs(delta) <= record.config.angle_tolerance:
        return record

    output_path = record.work_path.with_stem(f"{record.work_path.stem}_rot")
    if not record.config.dry_run:
        _run(["magick", str(record.work_path), "-rotate", str(delta), str(output_path)])
        record.work_path = output_path
    record.measurements["angle_corrected"] = True
    return record


def step3_crop_resize(record: ImageRecord, bbox: tuple[int, int, int, int]) -> ImageRecord:
    canvas = record.config.canvas_width
    crop_x, crop_y, size, _, scale = compute_crop_rect(bbox, canvas, record.config.target_ratio)

    record.measurements["crop_applied"] = [crop_x, crop_y, size, size]
    record.measurements["resize_scale"] = round(scale, 4)

    if scale > record.config.max_upscale:
        record.warnings.append(
            f"resize_scale {scale:.2f} exceeds max_upscale {record.config.max_upscale}"
        )

    output_path = record.work_path.with_stem(f"{record.work_path.stem}_crop")
    if not record.config.dry_run:
        _run(
            [
                "magick",
                str(record.work_path),
                "-crop",
                f"{size}x{size}+{crop_x}+{crop_y}",
                "+repage",
                "-resize",
                f"{canvas}x{canvas}!",
                str(output_path),
            ]
        )
        record.work_path = output_path
    return record


def step4_brightness(record: ImageRecord, reference_bg: float) -> ImageRecord:
    image_bg = record.measurements.get("original_brightness_mean", reference_bg)
    scale = compute_brightness_scale(image_bg, reference_bg)
    record.measurements["brightness_delta"] = round(reference_bg - image_bg, 2)

    if abs(scale - 1.0) < 0.005:
        return record

    output_path = record.work_path.with_stem(f"{record.work_path.stem}_bright")
    if not record.config.dry_run:
        if record.config.brightness_method == "level":
            white_pct = max(0.0, min(100.0, (reference_bg / 255.0) * 100.0))
            _run(
                [
                    "magick",
                    str(record.work_path),
                    "-level",
                    f"0%,{white_pct:.2f}%",
                    str(output_path),
                ]
            )
        else:
            brightness_delta = int((reference_bg - image_bg) / 255.0 * 100)
            _run(
                [
                    "magick",
                    str(record.work_path),
                    "-brightness-contrast",
                    f"{brightness_delta},0",
                    str(output_path),
                ]
            )
        record.work_path = output_path
    return record


def step5_finalize(record: ImageRecord, output_path: Path) -> ImageRecord:
    if record.config.dry_run:
        return record

    canvas_width = record.config.canvas_width
    canvas_height = record.config.canvas_height
    args = [
        "magick",
        str(record.work_path),
        "-background",
        record.config.background,
        "-gravity",
        "center",
        "-extent",
        f"{canvas_width}x{canvas_height}",
    ]
    if record.config.strip_exif:
        args.append("-strip")
    if record.config.preserve_icc:
        args.extend(["-profile", record.config.icc_profile])
    args.append(str(output_path))
    _run(args)
    return record
