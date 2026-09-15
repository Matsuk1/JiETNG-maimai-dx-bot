from io import BytesIO
from PIL import Image, JpegImagePlugin
from modules.images.upload import _encode_jpeg


def test_jpeg_preserves_color_resolution_size_and_source():
    with Image.new('RGBA', (64, 32), (255, 0, 0, 255)) as image:
        data = _encode_jpeg(image)
        assert image.getpixel((0, 0)) == (255, 0, 0, 255)
        with Image.open(BytesIO(data)) as encoded:
            assert encoded.size == image.size
            assert JpegImagePlugin.get_sampling(encoded) == 0
            assert encoded.info.get('progressive')


def test_transparent_background_is_white():
    with Image.new('RGBA', (16, 16), (0, 0, 0, 0)) as image:
        with Image.open(BytesIO(_encode_jpeg(image))) as encoded:
            assert encoded.convert('RGB').getpixel((8, 8)) == (255, 255, 255)
