import os
import time
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QBuffer, QIODevice

# Small thread pool for background disk writes
_executor = ThreadPoolExecutor(max_workers=2)


def _ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _unique_path(folder, base_name, ext):
    ts = int(time.time() * 1000)
    name = f"{base_name}_{ts}.{ext}"
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return path
    i = 1
    while True:
        candidate = os.path.join(folder, f"{base_name}_{ts}_{i}.{ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def _write_bytes(path: str, data: bytes):
    try:
        with open(path, "wb") as f:
            f.write(data)
    except Exception:
        # best-effort
        pass


def _qimage_to_bytes(img: QImage, fmt: bytes = b"JPG", quality: int = 85) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.ReadWrite)
    img.save(buf, fmt.decode() if isinstance(fmt, bytes) else fmt, quality)
    data = bytes(buf.data())
    buf.close()
    return data


def save_video_screenshot(entry: dict, pixmap: QPixmap, crop_regions: dict, original_width: int,
                          original_height: int, current_video: str, folder_path: str) -> bool:
    """Fast, non-blocking screenshot save.

    Converts QPixmap/QImage to in-memory bytes on the calling (GUI) thread, then
    dispatches disk writes to a background thread. Returns True immediately on
    scheduling to keep UI responsive for rapid key presses.
    """
    try:
        if pixmap is None or pixmap.isNull():
            return False

        base_folder = folder_path if folder_path else os.getcwd()
        screenshots_dir = os.path.join(base_folder, "Screenshots")
        _ensure_dir(screenshots_dir)

        # Convert to QImage
        img: QImage = pixmap.toImage()

        # Prepare base filename from entry
        display = entry.get("display_name") if isinstance(entry, dict) else current_video
        base_name = os.path.splitext(os.path.basename(display))[0]

        # Convert full image to bytes (fast-ish, avoids blocking on disk)
        full_bytes = _qimage_to_bytes(img, fmt=b"JPG", quality=85)
        full_path = _unique_path(screenshots_dir, base_name + "_frame", "jpg")

        tasks = []
        tasks.append(_executor.submit(_write_bytes, full_path, full_bytes))

        # Handle crop if present
        try:
            region = None
            if isinstance(crop_regions, dict):
                region = crop_regions.get(current_video) or crop_regions.get(entry.get('display_name'))
            if region and original_width and original_height:
                x, y, w, h = region
                img_w = img.width()
                img_h = img.height()
                if img_w and img_h:
                    sx = img_w / float(original_width)
                    sy = img_h / float(original_height)
                    rx = int(round(x * sx))
                    ry = int(round(y * sy))
                    rw = max(1, int(round(w * sx)))
                    rh = max(1, int(round(h * sy)))
                    rx = max(0, min(rx, img_w - 1))
                    ry = max(0, min(ry, img_h - 1))
                    if rx + rw > img_w:
                        rw = img_w - rx
                    if ry + rh > img_h:
                        rh = img_h - ry
                    cropped = img.copy(rx, ry, rw, rh)
                    crop_bytes = _qimage_to_bytes(cropped, fmt=b"JPG", quality=90)
                    crop_path = _unique_path(screenshots_dir, base_name + "_crop", "jpg")
                    tasks.append(_executor.submit(_write_bytes, crop_path, crop_bytes))
        except Exception:
            pass

        # Return True immediately to indicate scheduling succeeded
        return True
    except Exception:
        return False
