from __future__ import annotations

import subprocess
from pathlib import Path

from normalizer.models import ImageRecord

IMAGE_MAGICK_TIMEOUT = 30


def compute_crop_rect(
    bbox: tuple[int, int, int, int],
    canvas_width: int,
    canvas_height: int,
    target_ratio: float,
) -> tuple[int, int, int, int, float]:
    x, y, width, height = bbox
    if width <= 0 or height <= 0:
        raise ValueError(
            f"bbox width and height must be > 0, got width={width}, height={height} for bbox={bbox!r}"
        )
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError(
            "canvas_width and canvas_height must be > 0, "
            f"got canvas_width={canvas_width}, canvas_height={canvas_height}"
        )
    subject_cx = x + width // 2
    subject_cy = y + height // 2
    scale_x = (canvas_width * target_ratio) / width
    scale_y = (canvas_height * target_ratio) / height
    scale = min(scale_x, scale_y)
    size_w = int(round(canvas_width / scale))
    size_h = int(round(canvas_height / scale))
    crop_x = subject_cx - size_w // 2
    crop_y = subject_cy - size_h // 2
    return crop_x, crop_y, size_w, size_h, scale


def compute_brightness_scale(image_bg: float, reference_bg: float) -> float:
    if image_bg <= 0:
        return 1.0
    return reference_bg / image_bg


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=IMAGE_MAGICK_TIMEOUT)
    except subprocess.CalledProcessError as exc:
        image_path = cmd[1] if len(cmd) > 1 else "unknown"
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout
        details = []
        if stderr:
            details.append(f"stderr: {stderr.strip()}")
        if stdout:
            details.append(f"stdout: {stdout.strip()}")
        details_text = f" ({'; '.join(details)})" if details else ""
        raise RuntimeError(
            "ImageMagick command failed "
            f"for {image_path} with exit code {exc.returncode}: {' '.join(cmd)}{details_text}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        image_path = cmd[1] if len(cmd) > 1 else "unknown"
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        stdout = exc.output.decode(errors="replace") if isinstance(exc.output, bytes) else exc.output
        details = []
        if stderr:
            details.append(f"stderr: {stderr.strip()}")
        if stdout:
            details.append(f"stdout: {stdout.strip()}")
        details_text = f" ({'; '.join(details)})" if details else ""
        raise RuntimeError(
            "ImageMagick command timed out "
            f"after {exc.timeout}s for {image_path}: {' '.join(cmd)}{details_text}"
        ) from exc


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
    canvas_w = record.config.canvas_width
    canvas_h = record.config.canvas_height
    crop_x, crop_y, size_w, size_h, scale = compute_crop_rect(
        bbox,
        canvas_w,
        canvas_h,
        record.config.target_ratio,
    )

    record.measurements["crop_applied"] = [crop_x, crop_y, size_w, size_h]
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
                f"{size_w}x{size_h}{crop_x:+d}{crop_y:+d}",
                "+repage",
                "-resize",
                f"{canvas_w}x{canvas_h}!",
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
            white_pct = 100.0
            if reference_bg > 0:
                white_pct = max(0.0, (image_bg / reference_bg) * 100.0)
            else:
                white_pct = 0.0
            _run(
                [
                    "magick",
                    str(record.work_path),
                    "-level",
                    f"0%,{white_pct:.2f}%",
                    str(output_path),
                ]
            )
        elif record.config.brightness_method == "brightness-contrast":
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
        else:
            raise ValueError(
                f"Unsupported brightness_method: {record.config.brightness_method!r}. "
                "Expected one of: 'level', 'brightness-contrast'."
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
    elif not record.config.strip_exif:
        args.extend(["+profile", "ICC"])
    args.append(str(output_path))
    _run(args)
    return record
