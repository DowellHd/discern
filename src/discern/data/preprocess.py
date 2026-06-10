"""Image preprocessing pipeline: deskew, denoise, normalize."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def deskew(image: Image.Image) -> Image.Image:
    """Detect and correct image skew via contour-based angle estimation."""
    gray = np.array(image.convert("L"))
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 5:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return image
    h, w = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        np.array(image),
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return Image.fromarray(rotated)


def denoise(image: Image.Image) -> Image.Image:
    """Apply fast non-local means denoising."""
    arr = np.array(image)
    if arr.ndim == 2 or (arr.ndim == 3 and arr.shape[2] == 1):
        denoised = cv2.fastNlMeansDenoising(arr, h=10)
    else:
        denoised = cv2.fastNlMeansDenoisingColored(arr, h=6, hColor=6)
    return Image.fromarray(denoised)


def normalize(image: Image.Image) -> Image.Image:
    """Convert to grayscale and apply CLAHE contrast normalization."""
    gray = np.array(image.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return Image.fromarray(enhanced)


def preprocess(image: Image.Image) -> Image.Image:
    """Full pipeline: deskew → denoise → normalize."""
    return normalize(denoise(deskew(image)))
