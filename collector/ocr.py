"""قراءة النص من الصور بقارئ ويندوز المدمج (Windows OCR) — مجاني وبدون إنترنت.

يشتغل على ويندوز 10/11 بس. إذا ما متوفر، الصور تنترك والبرنامج يكمل عادي.
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile

_engine = None
_available = None


def available() -> bool:
    global _available
    if _available is None:
        try:
            import winrt.windows.media.ocr  # noqa: F401
            _available = os.name == "nt"
        except Exception:
            _available = False
    return _available


def _get_engine():
    global _engine
    if _engine is None:
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.globalization import Language
        # أسماء الأجهزة والأرقام بالبوسترات إنكليزية، فنستعمل الإنكليزي أول
        _engine = OcrEngine.try_create_from_language(Language("en-US")) or OcrEngine.try_create_from_user_profile_languages()
    return _engine


def _prepare(image_bytes: bytes) -> str:
    """نكبّر الصور الصغيرة حتى الأرقام تنقرا أوضح، ونحفظها PNG مؤقت."""
    from PIL import Image
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = im.size
    if w < 80 or h < 80:
        raise ValueError("small")
    scale = 2 if max(w, h) < 1400 else 1
    if scale > 1:
        im = im.resize((w * scale, h * scale), Image.LANCZOS)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    im.save(path)
    return path


async def _ocr_file(path: str) -> list[str]:
    from winrt.windows.storage import StorageFile, FileAccessMode
    from winrt.windows.graphics.imaging import BitmapDecoder
    f = await StorageFile.get_file_from_path_async(path)
    stream = await f.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await _get_engine().recognize_async(bitmap)
    return [line.text for line in result.lines]


def image_to_text(image_bytes: bytes) -> str:
    if not available():
        return ""
    try:
        path = _prepare(image_bytes)
    except Exception:
        return ""
    try:
        return "\n".join(asyncio.run(_ocr_file(path)))
    except Exception:
        return ""
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
