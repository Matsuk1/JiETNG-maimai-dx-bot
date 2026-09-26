from io import BytesIO

from PIL import Image

from modules.images import cache


def _png_bytes(color=(10, 20, 30, 255)):
    with Image.new("RGBA", (16, 12), color) as image, BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return buffer.getvalue()


def test_downloaded_cover_is_cached_as_webp(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "COVERS_DIR", str(tmp_path))
    downloaded = Image.open(BytesIO(_png_bytes())).convert("RGBA")
    monkeypatch.setattr(cache, "_download_rgba", lambda *args, **kwargs: (downloaded.copy(), b"png"))

    image = cache.get_cover_image("https://example.test/cover.png", "cover.png")
    image.close()

    target = tmp_path / "cover.webp"
    assert target.is_file()
    assert not (tmp_path / "cover.png").exists()
    with Image.open(target) as stored:
        assert stored.format == "WEBP"
        assert stored.size == (16, 12)
    downloaded.close()


def test_legacy_cover_is_read_and_migrated_to_webp(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "COVERS_DIR", str(tmp_path))
    legacy = tmp_path / "legacy.png"
    legacy.write_bytes(_png_bytes())

    image = cache.get_cover_image(None, "legacy.png")
    assert image.size == (16, 12)
    image.close()

    with Image.open(tmp_path / "legacy.webp") as stored:
        assert stored.format == "WEBP"
