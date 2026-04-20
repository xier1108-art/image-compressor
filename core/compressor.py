"""
Image compression engine.

Supports: JPEG, PNG, WebP, BMP, TIFF, HEIC/HEIF
Output formats: original, jpeg, webp
"""

import os
import shutil

from PIL import Image, ImageOps

# Register HEIC/HEIF opener (pillow-heif)
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    _HEIF_SUPPORT = True
except ImportError:
    _HEIF_SUPPORT = False

# ---------------------------------------------------------------------------
# Compression profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "extreme": {
        "jpeg_quality": 45,
        "webp_quality": 40,
        "webp_method": 6,
        "png_compress": 9,
        "png_quantize": True,
        "subsampling": 2,       # 4:2:0 chroma
    },
    "recommended": {
        "jpeg_quality": 72,
        "webp_quality": 75,
        "webp_method": 6,
        "png_compress": 9,
        "png_quantize": False,
        "subsampling": 2,
    },
    "low": {
        "jpeg_quality": 85,
        "webp_quality": 85,
        "webp_method": 4,
        "png_compress": 6,
        "png_quantize": False,
        "subsampling": 0,       # 4:4:4 chroma (better quality)
    },
}

# Format string → PIL save format name
_FMT_MAP = {
    ".jpg":  "jpeg",
    ".jpeg": "jpeg",
    ".png":  "png",
    ".bmp":  "bmp",
    ".webp": "webp",
    ".tiff": "tiff",
    ".tif":  "tiff",
    ".heic": "heic",
    ".heif": "heic",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compress_image(
    input_path: str,
    output_path: str,
    mode: str = "recommended",
    output_format: str = "jpeg",
    max_dim: int = None,
    progress_callback=None,
) -> tuple:
    """Compress a single image file.

    Returns (input_size_bytes, output_size_bytes, was_skipped).
    was_skipped=True means the compressed file was not smaller, so the
    original bytes were copied verbatim.
    """
    profile = PROFILES.get(mode, PROFILES["recommended"])
    in_size = os.path.getsize(input_path)

    ext = os.path.splitext(input_path)[1].lower()
    src_fmt = _FMT_MAP.get(ext, "jpeg")

    # Determine target format
    if output_format == "webp":
        target_fmt = "webp"
    elif output_format == "jpeg":
        target_fmt = "jpeg"
    else:
        # "original" — keep source format, but BMP/HEIC always converts to jpeg
        target_fmt = "jpeg" if src_fmt in ("bmp", "heic") else src_fmt

    # Load image
    img, exif_bytes = _load_image(input_path)

    # Fix orientation via EXIF before any processing
    img = ImageOps.exif_transpose(img)

    # Optional resize
    if max_dim:
        img = _apply_resize(img, max_dim)

    # Normalize color mode for target format
    img = _normalize_mode(img, target_fmt)

    # Compress to output_path
    _save_image(img, output_path, target_fmt, profile, exif_bytes)

    # Report progress
    if progress_callback:
        progress_callback(1, 1)

    # Check if compression actually helped
    out_size = os.path.getsize(output_path)
    if out_size >= in_size:
        shutil.copy2(input_path, output_path)
        return in_size, in_size, True

    return in_size, out_size, False


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_image(path: str):
    """Open image and extract EXIF bytes (for JPEG re-embedding)."""
    img = Image.open(path)
    img.load()
    exif_bytes = img.info.get("exif", b"")
    return img, exif_bytes


def _apply_resize(img: Image.Image, max_dim: int) -> Image.Image:
    """Resize image so neither dimension exceeds max_dim (preserves aspect ratio)."""
    if max(img.width, img.height) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return img


def _normalize_mode(img: Image.Image, target_fmt: str) -> Image.Image:
    """Convert image to an appropriate color mode for the target format."""
    mode = img.mode

    # Always flatten CMYK / unusual modes to RGB first
    if mode in ("CMYK", "YCbCr", "I", "F"):
        img = img.convert("RGB")
        mode = "RGB"
    if mode == "1":
        img = img.convert("L")
        mode = "L"

    if target_fmt == "jpeg":
        # JPEG does not support alpha — composite onto white
        if mode in ("RGBA", "LA", "PA"):
            img = _flatten_alpha(img)
        elif mode == "P":
            img = img.convert("RGB")
        # L (grayscale) is fine for JPEG
    elif target_fmt == "webp":
        # WebP supports RGBA; convert P palette to RGBA
        if mode == "P":
            img = img.convert("RGBA")
    elif target_fmt == "png":
        # PNG supports everything; convert P to RGBA for full fidelity
        if mode == "P":
            img = img.convert("RGBA")
    elif target_fmt == "tiff":
        if mode == "P":
            img = img.convert("RGBA")

    return img


def _flatten_alpha(img: Image.Image) -> Image.Image:
    """Composite an image with alpha onto a white background → RGB."""
    if img.mode == "PA":
        img = img.convert("RGBA")
    elif img.mode == "LA":
        img = img.convert("RGBA")

    bg = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        bg.paste(img, mask=img.split()[3])
    else:
        bg.paste(img)
    return bg


def _save_image(
    img: Image.Image,
    output_path: str,
    target_fmt: str,
    profile: dict,
    exif_bytes: bytes,
):
    """Save image to output_path using the given format and profile."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if target_fmt == "jpeg":
        save_kwargs = dict(
            format="JPEG",
            quality=profile["jpeg_quality"],
            optimize=True,
            progressive=True,
            subsampling=profile["subsampling"],
        )
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        img.save(output_path, **save_kwargs)

    elif target_fmt == "png":
        if profile["png_quantize"] and img.mode in ("RGB", "L"):
            # Quantize to 256 colors for extreme mode (skip if has alpha)
            try:
                img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            except Exception:
                pass  # Fall back to non-quantized save
        img.save(output_path, format="PNG",
                 optimize=True,
                 compress_level=profile["png_compress"])

    elif target_fmt == "webp":
        save_kwargs = dict(
            format="WEBP",
            quality=profile["webp_quality"],
            method=profile["webp_method"],
            lossless=False,
        )
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        img.save(output_path, **save_kwargs)

    elif target_fmt == "tiff":
        img.save(output_path, format="TIFF", compression="tiff_lzw")

    else:
        # Fallback: save as JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(output_path, format="JPEG",
                 quality=profile["jpeg_quality"],
                 optimize=True, progressive=True)
