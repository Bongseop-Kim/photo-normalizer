from pathlib import Path

import cv2
import numpy as np
import pytest


def make_product_image(
    dest_dir,
    filename: str = "test.jpg",
    canvas_w: int = 800,
    canvas_h: int = 1000,
    rect_w: int = 400,
    rect_h: int = 700,
    angle: float = 0.0,
    bg_brightness: int = 245,
    product_color: int = 80,
) -> str:
    """Create a white-background test image with a centered rotated rectangle."""
    img = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * bg_brightness
    center = (canvas_w // 2, canvas_h // 2)
    box = cv2.boxPoints(((center[0], center[1]), (rect_w, rect_h), angle))
    cv2.fillPoly(img, [np.intp(box)], (product_color,) * 3)
    path = Path(dest_dir) / filename
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def straight_product(tmp_path):
    return make_product_image(tmp_path, angle=0.0)
