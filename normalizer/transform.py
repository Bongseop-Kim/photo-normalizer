from __future__ import annotations

import math
import subprocess
from pathlib import Path

from normalizer.models import ImageRecord

IMAGE_MAGICK_TIMEOUT = 30


def compute_crop_rect(
    bbox: tuple[int, int, int, int],
    canvas_width: int,
    canvas_height: int,
    target_ratio: float,
    image_width: int,
    image_height: int,
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
    if image_width <= 0 or image_height <= 0:
        raise ValueError(
            "image_width and image_height must be > 0, "
            f"got image_width={image_width}, image_height={image_height}"
        )
    if not math.isfinite(target_ratio) or not (0 < target_ratio <= 1.0):
        raise ValueError(
            f"target_ratio must be > 0 and <= 1.0, got target_ratio={target_ratio!r}"
        )
    subject_cx = x + width // 2
    subject_cy = y + height // 2
    scale_x = (canvas_width * target_ratio) / width
    scale_y = (canvas_height * target_ratio) / height
    scale = min(scale_x, scale_y)
    size_w = round(canvas_width / scale)
    size_h = round(canvas_height / scale)
    crop_x = max(0, min(subject_cx - size_w // 2, image_width - size_w))
    crop_y = max(0, min(subject_cy - size_h // 2, image_height - size_h))
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


def _get_image_size(image_path: Path) -> tuple[int, int]:
    cmd = [
        "magick",
        "identify",
        "-format",
        "%w %h",
        str(image_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=IMAGE_MAGICK_TIMEOUT,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        raise RuntimeError(
            f"Failed to read image size for {image_path}: {stderr.strip() if stderr else exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Timed out reading image size for {image_path} after {exc.timeout}s") from exc

    output = result.stdout.decode(errors="replace").strip()
    try:
        width_text, height_text = output.split()
        return int(width_text), int(height_text)
    except ValueError as exc:
        raise RuntimeError(f"Unexpected image size output for {image_path}: {output!r}") from exc


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
    image_width, image_height = _get_image_size(record.work_path)
    crop_x, crop_y, size_w, size_h, scale = compute_crop_rect(
        bbox,
        canvas_w,
        canvas_h,
        record.config.target_ratio,
        image_width,
        image_height,
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

    if abs(scale - 1.0) < 0.005 and image_bg > 0:
        return record

    def run_brightness_contrast() -> None:
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

    output_path = record.work_path.with_stem(f"{record.work_path.stem}_bright")
    if record.config.brightness_method == "level" and reference_bg <= 0:
        record.warnings.append("reference_bg <= 0; skipping brightness level adjustment")
        return record

    if not record.config.dry_run:
        if record.config.brightness_method == "level":
            white_pct = max(0.0, (image_bg / reference_bg) * 100.0)
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
            run_brightness_contrast()
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
