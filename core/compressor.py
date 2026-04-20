"""
Image compression engine.

Supports: JPEG, PNG, WebP, BMP, TIFF, HEIC/HEIF
Output formats: original, jpeg, webp

Compression strategies:
  JPEG  – Pillow JPEG with quality tuning + chroma subsampling + EXIF strip
  PNG   – Pillow quantize (lossy palette) + oxipng lossless optimizer
  WebP  – Pillow WebP lossy (method=6)
  BMP   – always converted (BMP is uncompressed)
  TIFF  – LZW lossless re-encode
  HEIC  – decoded via pillow-heif, re-saved as target format
"""

import io
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

# oxipng — fast Rust-based lossless PNG optimizer
try:
    import oxipng as _oxipng
    _OXIPNG_SUPPORT = True
except ImportError:
    _OXIPNG_SUPPORT = False

# ---------------------------------------------------------------------------
# Compression profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "extreme": {
        "jpeg_quality":    40,    # aggressive but still recognisable
        "webp_quality":    35,
        "webp_method":     6,     # slowest / best WebP encoder
        "png_compress":    9,
        "png_quantize":    True,
        "png_colors":      128,   # extreme: 128-colour palette
        "subsampling":     2,     # 4:2:0 chroma (smaller, barely visible)
        "strip_exif":      True,
        "oxipng_level":    6,
    },
    "recommended": {
        "jpeg_quality":    68,
        "webp_quality":    72,
        "webp_method":     6,
        "png_compress":    9,
        "png_quantize":    True,  # ← now ON (non-alpha only)
        "png_colors":      256,
        "subsampling":     2,
        "strip_exif":      True,  # strip EXIF — big win on phone photos
        "oxipng_level":    4,
    },
    "low": {
        "jpeg_quality":    82,
        "webp_quality":    82,
        "webp_method":     4,
        "png_compress":    6,
        "png_quantize":    False,
        "png_colors":      256,
        "subsampling":     0,     # 4:4:4 chroma (better quality)
        "strip_exif":      False, # keep EXIF in low-compression mode
        "oxipng_level":    2,
    },
}

# Extension → internal format name
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
    was_skipped=True  → compressed file was not smaller; original was copied.
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
        # "original" — BMP and HEIC always convert to JPEG (no meaningful re-save otherwise)
        target_fmt = "jpeg" if src_fmt in ("bmp", "heic") else src_fmt

    # ── Load ──────────────────────────────────────────────────────────────
    img, exif_bytes = _load_image(input_path)

    # Bake EXIF orientation into pixels so we can safely strip metadata
    img = ImageOps.exif_transpose(img)

    # ── Resize (optional) ─────────────────────────────────────────────────
    if max_dim:
        img = _apply_resize(img, max_dim)

    # ── Auto-grayscale detection ──────────────────────────────────────────
    # If the image is colour but actually all grey values, shrink to L mode.
    # JPEG L-mode files are ~2× smaller than RGB for the same content.
    if target_fmt == "jpeg" and img.mode == "RGB":
        if _is_grayscale(img):
            img = img.convert("L")

    # ── Mode normalisation ────────────────────────────────────────────────
    img = _normalize_mode(img, target_fmt)

    # ── Save ──────────────────────────────────────────────────────────────
    exif_to_embed = b"" if profile["strip_exif"] else exif_bytes
    _save_image(img, output_path, target_fmt, profile, exif_to_embed)

    if progress_callback:
        progress_callback(1, 1)

    # ── Skip if compression made things larger ────────────────────────────
    out_size = os.path.getsize(output_path)
    if out_size >= in_size:
        shutil.copy2(input_path, output_path)
        return in_size, in_size, True

    return in_size, out_size, False


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_image(path: str):
    """Open image and extract raw EXIF bytes."""
    img = Image.open(path)
    img.load()
    exif_bytes = img.info.get("exif", b"")
    return img, exif_bytes


def _apply_resize(img: Image.Image, max_dim: int) -> Image.Image:
    """Resize so neither dimension exceeds max_dim (preserves aspect ratio)."""
    if max(img.width, img.height) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return img


def _is_grayscale(img: Image.Image) -> bool:
    """Return True if an RGB image contains only grey pixels (R==G==B).

    Samples a 64×64 downscale for speed instead of scanning every pixel.
    """
    try:
        thumb = img.resize((64, 64), Image.BOX)
        r, g, b = thumb.split()
        return r.tobytes() == g.tobytes() == b.tobytes()
    except Exception:
        return False


def _normalize_mode(img: Image.Image, target_fmt: str) -> Image.Image:
    """Convert image to a colour mode compatible with target_fmt."""
    mode = img.mode

    # Flatten exotic modes to RGB first
    if mode in ("CMYK", "YCbCr", "I", "F"):
        img = img.convert("RGB")
        mode = "RGB"
    if mode == "1":
        img = img.convert("L")
        mode = "L"

    if target_fmt == "jpeg":
        if mode in ("RGBA", "LA", "PA"):
            img = _flatten_alpha(img)
        elif mode == "P":
            img = img.convert("RGB")
        # "L" is valid JPEG — keep it

    elif target_fmt == "webp":
        if mode == "P":
            img = img.convert("RGBA")

    elif target_fmt in ("png", "tiff"):
        if mode == "P":
            img = img.convert("RGBA")

    return img


def _flatten_alpha(img: Image.Image) -> Image.Image:
    """Composite alpha image onto a white background → RGB."""
    if img.mode in ("PA", "LA"):
        img = img.convert("RGBA")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        bg.paste(img, mask=img.split()[3])
    else:
        bg.paste(img)
    return bg


def _has_real_alpha(img: Image.Image) -> bool:
    """Return True if the image actually uses non-255 alpha pixels."""
    if img.mode not in ("RGBA", "LA"):
        return False
    try:
        alpha = img.split()[-1]
        return min(alpha.getdata()) < 255
    except Exception:
        return True


def _save_image(
    img: Image.Image,
    output_path: str,
    target_fmt: str,
    profile: dict,
    exif_bytes: bytes,
):
    """Save the image to output_path with the given format and profile."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # ── JPEG ──────────────────────────────────────────────────────────────
    if target_fmt == "jpeg":
        kw = dict(
            format="JPEG",
            quality=profile["jpeg_quality"],
            optimize=True,
            progressive=True,
            subsampling=profile["subsampling"],
        )
        if exif_bytes:
            kw["exif"] = exif_bytes
        img.save(output_path, **kw)

    # ── PNG ───────────────────────────────────────────────────────────────
    elif target_fmt == "png":
        # Lossy palette quantization — only when no meaningful alpha
        if profile["png_quantize"] and img.mode in ("RGB", "L", "RGBA"):
            if img.mode == "RGBA" and _has_real_alpha(img):
                pass  # preserve alpha — skip quantize
            else:
                try:
                    work = img if img.mode != "RGBA" else img.convert("RGB")
                    img = work.quantize(
                        colors=profile["png_colors"],
                        method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.FLOYDSTEINBERG,
                    )
                except Exception:
                    pass

        img.save(output_path, format="PNG",
                 optimize=True,
                 compress_level=profile["png_compress"])

        # Post-process with oxipng for additional lossless gains
        if _OXIPNG_SUPPORT:
            try:
                _oxipng.optimize(output_path, level=profile["oxipng_level"])
            except Exception:
                pass

    # ── WebP ──────────────────────────────────────────────────────────────
    elif target_fmt == "webp":
        kw = dict(
            format="WEBP",
            quality=profile["webp_quality"],
            method=profile["webp_method"],
            lossless=False,
        )
        if exif_bytes:
            kw["exif"] = exif_bytes
        img.save(output_path, **kw)

    # ── TIFF ──────────────────────────────────────────────────────────────
    elif target_fmt == "tiff":
        img.save(output_path, format="TIFF", compression="tiff_lzw")

    # ── Fallback ──────────────────────────────────────────────────────────
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(output_path, format="JPEG",
                 quality=profile["jpeg_quality"],
                 optimize=True, progressive=True)
