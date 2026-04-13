import pytest

from normalizer.transform import compute_brightness_scale, compute_crop_rect


def test_crop_rect_size():
    _, _, size, _, _ = compute_crop_rect(
        bbox=(200, 150, 400, 700),
        canvas_size=1000,
        target_ratio=0.80,
    )
    assert abs(size - 875) < 2


def test_crop_rect_centered_on_subject():
    bbox = (200, 150, 400, 700)
    cx, cy, size, _, _ = compute_crop_rect(
        bbox=bbox,
        canvas_size=1000,
        target_ratio=0.80,
    )
    subject_cx = bbox[0] + bbox[2] // 2
    subject_cy = bbox[1] + bbox[3] // 2
    crop_cx = cx + size // 2
    crop_cy = cy + size // 2
    assert abs(crop_cx - subject_cx) < 2
    assert abs(crop_cy - subject_cy) < 2


def test_brightness_scale():
    scale = compute_brightness_scale(image_bg=238.0, reference_bg=245.0)
    assert abs(scale - (245.0 / 238.0)) < 0.001


def test_brightness_scale_equal_returns_one():
    assert compute_brightness_scale(245.0, 245.0) == pytest.approx(1.0)


def test_brightness_scale_zero_denominator():
    assert compute_brightness_scale(0.0, 245.0) == 1.0
