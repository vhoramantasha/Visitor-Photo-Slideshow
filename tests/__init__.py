import io
from PIL import Image

def create_test_image(format="JPEG", size=(200, 200), color=(100, 150, 200)):
    """Generate in-memory valid image buffer for test suites."""
    buf = io.BytesIO()
    mode = "RGB" if format.upper() in ("JPEG", "JPG") else "RGBA"
    img = Image.new(mode, size, color=color)
    img.save(buf, format="JPEG" if format.upper() in ("JPEG", "JPG") else format.upper())
    buf.seek(0)
    return buf
