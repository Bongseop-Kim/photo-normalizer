from __future__ import annotations

import subprocess
from pathlib import Path

from normalizer.models import ImageRecord


def detect_icc_profile(image_path: Path) -> str:
    result = subprocess.run(
        ["magick", "identify", "-verbose", str(image_path)],
        capture_output=True,
        check=True,
        text=True,
    )
    lines = result.stdout.splitlines()
    for line in lines:
        if "icc:description:" in line.lower():
            return line.split(":", 2)[-1].strip() or "unknown-icc"
    for line in lines:
        lower_line = line.lower()
        if "profile-icc" in lower_line or ("profile" in lower_line and "icc" in lower_line):
            return line.strip().split(":")[-1].strip() or "unknown-icc"
    for line in lines:
        if "Colorspace:" in line:
            return line.split(":")[-1].strip()
    return "none"


def _is_srgb(profile: str) -> bool:
    return "srgb" in profile.lower() or profile == "none"


def step0_color_normalize(record: ImageRecord) -> ImageRecord:
    profile = detect_icc_profile(record.work_path)
    record.measurements["original_profile"] = profile

    if not record.config.srgb_convert or _is_srgb(profile):
        record.measurements["profile_converted"] = False
        return record

    if record.config.dry_run:
        record.measurements["profile_converted"] = False
        return record

    output_path = record.work_path.with_stem(f"{record.work_path.stem}_srgb")
    subprocess.run(
        ["magick", str(record.work_path), "-profile", record.config.icc_profile, str(output_path)],
        check=True,
        capture_output=True,
    )
    record.work_path = output_path
    record.measurements["profile_converted"] = True
    return record
