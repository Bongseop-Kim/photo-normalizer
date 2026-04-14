from pathlib import Path

import pytest

from normalizer.models import BatchResult, ImageRecord, NormalizerConfig


def test_config_defaults():
    config = NormalizerConfig()
    assert config.canvas_width == 1000
    assert config.target_ratio == 0.80
    assert config.angle_tolerance == 2.0
    assert config.dry_run is False


def test_image_record_no_error_by_default(tmp_path):
    src = tmp_path / "red.jpg"
    src.touch()
    record = ImageRecord(
        source_path=src,
        work_path=src,
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )
    assert record.error is None


def test_batch_result(tmp_path):
    src = tmp_path / "a.jpg"
    src.touch()
    record = ImageRecord(
        source_path=src,
        work_path=src,
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )
    batch = BatchResult(config_snapshot={}, reference={}, records=[record])
    assert len(batch.records) == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"target_ratio": 0}, "target_ratio"),
        ({"morphology_enabled": True, "morphology_kernel_size": 0}, "morphology_kernel_size"),
        ({"corner_sample_size": -1}, "corner_sample_size"),
        ({"max_upscale": 0}, "max_upscale"),
        ({"trim_fuzz": "abc"}, "trim_fuzz"),
        ({"brightness_method": "bad"}, "brightness_method"),
        ({"brightness_reference": "bad"}, "brightness_reference"),
        ({"angle_reference": "bad"}, "angle_reference"),
        ({"morphology_operation": "bad"}, "morphology_operation"),
    ],
)
def test_config_validation_rejects_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        NormalizerConfig(**kwargs)
