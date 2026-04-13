from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from normalizer.models import NormalizerConfig

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_YAML_MAP: dict[str, list[str]] = {
    "canvas_width": ["canvas", "width"],
    "canvas_height": ["canvas", "height"],
    "background": ["canvas", "background"],
    "srgb_convert": ["color_management", "srgb_convert"],
    "icc_profile": ["color_management", "icc_profile"],
    "strip_exif": ["color_management", "strip_exif"],
    "preserve_icc": ["color_management", "preserve_icc"],
    "target_ratio": ["framing", "target_ratio"],
    "max_upscale": ["framing", "max_upscale"],
    "brightness_method": ["brightness", "method"],
    "brightness_reference": ["brightness", "reference"],
    "brightness_target": ["brightness", "target"],
    "corner_sample_size": ["brightness", "corner_sample_size"],
    "angle_enabled": ["angle", "enabled"],
    "angle_reference": ["angle", "reference"],
    "angle_tolerance": ["angle", "tolerance"],
    "morphology_enabled": ["morphology", "enabled"],
    "morphology_operation": ["morphology", "operation"],
    "morphology_kernel_size": ["morphology", "kernel_size"],
    "trim_fuzz": ["trim", "fuzz"],
}


def _get_nested(data: dict[str, Any], keys: list[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def load_config(
    config_path: Path | None,
    overrides: dict[str, Any] | None = None,
) -> NormalizerConfig:
    raw: dict[str, Any] = {}
    config_dir: Path | None = None
    if config_path and config_path.exists():
        raw = yaml.safe_load(config_path.read_text()) or {}
        config_dir = config_path.resolve().parent

    kwargs: dict[str, Any] = {}
    for field_name, yaml_keys in _YAML_MAP.items():
        value = _get_nested(raw, yaml_keys)
        if value is not None:
            kwargs[field_name] = value

    if overrides:
        for key, value in overrides.items():
            if value is not None:
                kwargs[key] = value

    config = NormalizerConfig(**kwargs)
    icc_path = Path(config.icc_profile)
    if not icc_path.is_absolute():
        base_dir = config_dir or _PROJECT_ROOT
        config.icc_profile = str((base_dir / icc_path).resolve())
    return config


def find_config(input_dir: Path, explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"Config file does not exist: {explicit}")
        return explicit

    candidate = input_dir / "config.yaml"
    if candidate.exists():
        return candidate

    project_default = _PROJECT_ROOT / "config.yaml"
    if project_default.exists():
        return project_default

    return None
