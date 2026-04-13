from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def detect_subject(
    image_path: Path,
    adaptive: bool = False,
    morphology_enabled: bool = False,
    morphology_kernel_size: int = 3,
    corner_sample_size: int = 100,
) -> tuple[tuple[int, int, int, int], float, float] | None:
    img = cv2.imread(str(image_path))
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    total_pixels = height * width

    if adaptive:
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=51,
            C=10,
        )
    else:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    if morphology_enabled:
        kernel_size = max(1, int(morphology_kernel_size))
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (kernel_size, kernel_size),
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    areas = [(c, cv2.contourArea(c)) for c in contours]
    largest, area = max(areas, key=lambda x: x[1])
    if area < 100 or area / total_pixels > 0.90:
        return None

    bbox = cv2.boundingRect(largest)

    min_rect = cv2.minAreaRect(largest)
    rect_w, rect_h = min_rect[1]
    raw_angle = float(min_rect[2])
    angle = raw_angle + 90.0 if rect_w > rect_h else raw_angle

    sample_size = max(1, min(int(corner_sample_size), height // 4, width // 4))
    corners = [
        gray[0:sample_size, 0:sample_size],
        gray[0:sample_size, width - sample_size : width],
        gray[height - sample_size : height, 0:sample_size],
        gray[height - sample_size : height, width - sample_size : width],
    ]
    brightness_mean = float(np.mean([corner.mean() for corner in corners]))

    return bbox, angle, brightness_mean
