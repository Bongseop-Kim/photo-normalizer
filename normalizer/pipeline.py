from __future__ import annotations

import dataclasses
import shutil
import statistics
from pathlib import Path

from normalizer.color import step0_color_normalize
from normalizer.detect import detect_subject
from normalizer.models import BatchResult, ImageRecord, NormalizerConfig
from normalizer.preview import render_preview
from normalizer.report import write_report
from normalizer.transform import (
    step2_rotate,
    step3_crop_resize,
    step4_brightness,
    step5_finalize,
)

_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def run_pipeline(input_dir: Path, output_dir: Path, config: NormalizerConfig) -> BatchResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / ".tmp"
    temp_dir.mkdir(exist_ok=True)

    images = sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in _SUFFIXES
    )

    records: list[ImageRecord] = []
    for src in images:
        work_path = temp_dir / src.name
        shutil.copy2(src, work_path)
        records.append(
            ImageRecord(
                source_path=src,
                work_path=work_path,
                config=config,
                measurements={},
                warnings=[],
            )
        )

    for record in records:
        if record.error:
            continue
        try:
            step0_color_normalize(record)
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 0 error: {exc}"

    for record in records:
        if record.error:
            continue
        try:
            result = detect_subject(
                record.work_path,
                morphology_enabled=config.morphology_enabled,
                morphology_kernel_size=config.morphology_kernel_size,
                corner_sample_size=config.corner_sample_size,
            )
            if result is None:
                record.error = "STEP 1 error: no subject detected"
                continue
            bbox, angle, brightness = result
            record.measurements.update(
                {
                    "original_bbox": list(bbox),
                    "original_angle": round(angle, 2),
                    "original_brightness_mean": round(brightness, 2),
                }
            )
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 1 error: {exc}"

    good_records = [record for record in records if not record.error]
    angles = [
        record.measurements["original_angle"]
        for record in good_records
        if "original_angle" in record.measurements
    ]
    brightnesses = [
        record.measurements["original_brightness_mean"]
        for record in good_records
        if "original_brightness_mean" in record.measurements
    ]
    reference_angle = statistics.median(angles) if angles else 0.0
    reference_brightness = statistics.median(brightnesses) if brightnesses else 245.0

    for record in records:
        if record.error:
            continue
        try:
            step2_rotate(record, reference_angle=reference_angle)
            if record.measurements.get("angle_corrected"):
                result = detect_subject(record.work_path, corner_sample_size=config.corner_sample_size)
                if result is None:
                    raise RuntimeError(
                        "re-detect failed "
                        f"for {record.source_path} after rotation toward "
                        f"reference_angle={reference_angle:.2f}"
                    )
                record.measurements["corrected_bbox"] = list(result[0])
            else:
                record.measurements["corrected_bbox"] = record.measurements["original_bbox"]
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 2 error: {exc}"

    for record in records:
        if record.error:
            continue
        try:
            step3_crop_resize(record, bbox=tuple(record.measurements["corrected_bbox"]))
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 3 error: {exc}"

    for record in records:
        if record.error:
            continue
        try:
            step4_brightness(record, reference_bg=reference_brightness)
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 4 error: {exc}"

    for record in records:
        if record.error:
            continue
        try:
            step5_finalize(record, output_path=output_dir / record.source_path.name)
        except Exception as exc:  # pragma: no cover - pipeline guard
            record.error = f"STEP 5 error: {exc}"

    shutil.rmtree(temp_dir, ignore_errors=True)

    result = BatchResult(
        config_snapshot=dataclasses.asdict(config),
        reference={
            "brightness_mean": round(reference_brightness, 2),
            "angle": round(reference_angle, 2),
        },
        records=records,
    )
    write_report(result, output_dir / "_report.json")
    if not config.dry_run:
        render_preview(
            result,
            output_path=output_dir / "_preview.html",
            input_dir=input_dir,
            output_dir=output_dir,
        )
    return result
