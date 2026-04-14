from pathlib import Path

import cv2
import numpy as np
import pytest

from normalizer.detect import detect_subject
from tests.conftest import make_product_image


def test_detect_returns_tuple(straight_product):
    result = detect_subject(Path(straight_product))
    assert result is not None
    bbox, angle, brightness = result
    assert len(bbox) == 4
    assert isinstance(angle, float)
    assert isinstance(brightness, float)


def test_detect_bbox_size_close_to_rect(straight_product):
    result = detect_subject(Path(straight_product))
    assert result is not None
    bbox, _, _ = result
    x, y, w, h = bbox
    assert x >= 0 and y >= 0
    assert abs(w - 400) < 20
    assert abs(h - 700) < 20


def test_detect_angle_near_zero(straight_product):
    result = detect_subject(Path(straight_product))
    assert result is not None
    _, angle, _ = result
    assert abs(angle) < 3.0


def test_detect_brightness_close_to_background(straight_product):
    result = detect_subject(Path(straight_product))
    assert result is not None
    _, _, brightness = result
    assert 230 < brightness < 256


def test_detect_none_on_solid_white(tmp_path):
    img = np.ones((800, 800, 3), dtype=np.uint8) * 255
    path = tmp_path / "white.jpg"
    cv2.imwrite(str(path), img)
    assert detect_subject(path) is None


def test_detect_tilted_product(tmp_path):
    path = make_product_image(tmp_path, angle=5.0, filename="tilted.jpg")
    result = detect_subject(Path(path))
    assert result is not None
    bbox, _, _ = result
    assert bbox[2] > 0 and bbox[3] > 0


def test_detect_small_image_uses_non_empty_corner_samples(tmp_path):
    path = make_product_image(
        tmp_path,
        filename="tiny.jpg",
        canvas_w=200,
        canvas_h=3,
        rect_w=60,
        rect_h=2,
        bg_brightness=240,
        product_color=0,
    )
    result = detect_subject(Path(path), corner_sample_size=100)
    assert result is not None
    _, _, brightness = result
    assert not np.isnan(brightness)


def test_detect_sanitizes_non_positive_morphology_kernel(straight_product):
    result = detect_subject(
        Path(straight_product),
        morphology_enabled=True,
        morphology_kernel_size=0,
    )
    assert result is not None
