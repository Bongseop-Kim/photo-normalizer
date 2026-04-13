from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NormalizerConfig:
    canvas_width: int = 1000
    canvas_height: int = 1000
    background: str = "#FFFFFF"
    srgb_convert: bool = True
    icc_profile: str = "assets/profiles/sRGB_IEC61966-2-1.icc"
    strip_exif: bool = True
    preserve_icc: bool = True
    target_ratio: float = 0.80
    max_upscale: float = 1.3
    brightness_method: str = "level"
    brightness_reference: str = "median"
    brightness_target: str = "background"
    corner_sample_size: int = 100
    angle_enabled: bool = True
    angle_reference: str = "median"
    angle_tolerance: float = 2.0
    morphology_enabled: bool = False
    morphology_operation: str = "open"
    morphology_kernel_size: int = 3
    trim_fuzz: str = "10%"
    dry_run: bool = False


@dataclass
class ImageRecord:
    source_path: Path
    work_path: Path
    config: NormalizerConfig
    measurements: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class BatchResult:
    config_snapshot: dict
    reference: dict
    records: list[ImageRecord]
