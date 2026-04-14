from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar
import re


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

    _BRIGHTNESS_METHODS: ClassVar[frozenset[str]] = frozenset({"level", "brightness-contrast"})
    _BRIGHTNESS_REFERENCES: ClassVar[frozenset[str]] = frozenset({"median"})
    _BRIGHTNESS_TARGETS: ClassVar[frozenset[str]] = frozenset({"background"})
    _ANGLE_REFERENCES: ClassVar[frozenset[str]] = frozenset({"median"})
    _MORPHOLOGY_OPERATIONS: ClassVar[frozenset[str]] = frozenset({"open", "close", "erode", "dilate"})

    def __post_init__(self) -> None:
        if not (0 < self.target_ratio <= 1.0):
            raise ValueError("target_ratio must be > 0 and <= 1.0")
        if self.morphology_enabled and int(self.morphology_kernel_size) < 1:
            raise ValueError("morphology_kernel_size must be >= 1 when morphology_enabled is true")
        if int(self.corner_sample_size) < 0:
            raise ValueError("corner_sample_size must be >= 0")
        if float(self.max_upscale) <= 0:
            raise ValueError("max_upscale must be > 0")
        if not re.fullmatch(r"\d+(?:\.\d+)?%", str(self.trim_fuzz)):
            raise ValueError("trim_fuzz must be a percentage string like '10%'")

        if self.brightness_method not in self._BRIGHTNESS_METHODS:
            raise ValueError(f"brightness_method must be one of {sorted(self._BRIGHTNESS_METHODS)}")
        if self.brightness_reference not in self._BRIGHTNESS_REFERENCES:
            raise ValueError(
                f"brightness_reference must be one of {sorted(self._BRIGHTNESS_REFERENCES)}"
            )
        if self.brightness_target not in self._BRIGHTNESS_TARGETS:
            raise ValueError(f"brightness_target must be one of {sorted(self._BRIGHTNESS_TARGETS)}")
        if self.angle_reference not in self._ANGLE_REFERENCES:
            raise ValueError(f"angle_reference must be one of {sorted(self._ANGLE_REFERENCES)}")
        if self.morphology_operation not in self._MORPHOLOGY_OPERATIONS:
            raise ValueError(
                f"morphology_operation must be one of {sorted(self._MORPHOLOGY_OPERATIONS)}"
            )


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
