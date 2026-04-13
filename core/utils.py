import os

SUPPORTED_EXTENSIONS = (".png", ".bmp", ".jpg", ".jpeg", ".webp", ".tiff", ".tif")


def format_size(bytes_val: int) -> str:
    """Format byte count as human-readable string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"


def get_file_size(path: str) -> int:
    return os.path.getsize(path)


def get_output_path(input_path: str, output_dir: str, target_ext: str = None) -> str:
    """Return output file path: <output_dir>/<name>_compressed.<ext>

    target_ext: override extension (e.g. '.jpg' when converting BMP→JPEG).
                If None, keep the original extension.
    """
    basename = os.path.basename(input_path)
    name, ext = os.path.splitext(basename)
    out_ext = target_ext if target_ext else ext
    return os.path.join(output_dir, f"{name}_compressed{out_ext}")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
