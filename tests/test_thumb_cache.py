import atexit
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thumb_cache import ThumbCache


_ENV = None


def _save_rgb_noise(path, size, image_format, **save_options):
    image = Image.effect_noise(size, 80).convert("RGB")
    try:
        image.save(path, format=image_format, **save_options)
    finally:
        image.close()


def _create_images(source_dir):
    files = []
    expected = {}

    jpeg_path = os.path.join(source_dir, "noise_square.jpg")
    _save_rgb_noise(jpeg_path, (2000, 2000), "JPEG", quality=90)
    files.append(jpeg_path)
    expected[jpeg_path] = (2000, 2000)

    png_path = os.path.join(source_dir, "noise_landscape.png")
    _save_rgb_noise(png_path, (2448, 1632), "PNG", compress_level=1)
    files.append(png_path)
    expected[png_path] = (2448, 1632)

    rgba_path = os.path.join(source_dir, "transparent_rgba.png")
    size = (900, 600)
    red = Image.effect_noise(size, 70)
    green = Image.effect_noise(size, 85)
    blue = Image.effect_noise(size, 100)
    alpha = Image.new("L", size, 255)
    alpha.paste(0, (0, 0, size[0] // 3, size[1]))
    alpha.paste(128, (size[0] // 3, 0, 2 * size[0] // 3, size[1]))
    rgba = Image.merge("RGBA", (red, green, blue, alpha))
    try:
        rgba.save(rgba_path, format="PNG", compress_level=1)
    finally:
        rgba.close()
        red.close()
        green.close()
        blue.close()
        alpha.close()
    files.append(rgba_path)
    expected[rgba_path] = size

    webp_path = os.path.join(source_dir, "noise.webp")
    _save_rgb_noise(webp_path, (960, 640), "WEBP", quality=85)
    files.append(webp_path)
    expected[webp_path] = (960, 640)

    palette_path = os.path.join(source_dir, "transparent_palette.png")
    noise = Image.effect_noise((720, 480), 90)
    palette = noise.quantize(colors=256)
    try:
        palette.putpixel((0, 0), 0)
        palette.save(
            palette_path,
            format="PNG",
            transparency=0,
            compress_level=1,
        )
    finally:
        palette.close()
        noise.close()
    files.append(palette_path)
    expected[palette_path] = (720, 480)

    return files, expected


class _Environment:
    def __init__(self):
        self.source_temp = None
        self.cache_temp = None
        self.cache = None
        self.closed = False

        try:
            self.source_temp = tempfile.TemporaryDirectory(
                prefix="thumb_cache_sources_"
            )
            self.cache_temp = tempfile.TemporaryDirectory(
                prefix="thumb_cache_data_"
            )
            self.source_dir = self.source_temp.name
            self.cache_dir = self.cache_temp.name
            self.files, self.expected = _create_images(self.source_dir)
            self.cache = ThumbCache(cache_dir=self.cache_dir)
        except Exception:
            self.close()
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True

        if self.cache is not None:
            self.cache.close()
            self.cache = None

        if self.cache_temp is not None:
            self.cache_temp.cleanup()
            self.cache_temp = None

        if self.source_temp is not None:
            self.source_temp.cleanup()
            self.source_temp = None


def _get_environment():
    global _ENV
    if _ENV is None:
        _ENV = _Environment()
    return _ENV


def _close_environment():
    global _ENV
    if _ENV is not None:
        _ENV.close()
        _ENV = None


def _expected_width(dimensions, row_height):
    width, height = dimensions
    return max(1, int(row_height * width / height))


def _validate_thumb(image, dimensions, row_height):
    try:
        image.load()
        expected_size = (_expected_width(dimensions, row_height), row_height)
        assert image.size == expected_size, (
            "expected thumbnail size {}, got {}".format(
                expected_size, image.size
            )
        )
        assert image.mode == "RGB", (
            "expected RGB thumbnail, got {}".format(image.mode)
        )
    finally:
        image.close()


def _all_jpegs(root):
    found = set()
    for directory, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower().endswith(".jpg"):
                found.add(os.path.join(directory, filename))
    return found


def test_dims():
    env = _get_environment()
    assert env.cache.enabled is True

    for path in env.files:
        first = env.cache.get_dims(path)
        second = env.cache.get_dims(path)
        assert first == env.expected[path], (
            "wrong dimensions for {}: {}".format(
                os.path.basename(path), first
            )
        )
        assert second == first

    stats = env.cache.stats()
    assert stats["dims"] == len(env.files), (
        "expected {} dimension entries, got {}".format(
            len(env.files), stats["dims"]
        )
    )


def test_cold_vs_warm():
    env = _get_environment()
    row_height = 160

    started = time.perf_counter()
    for path in env.files:
        image = env.cache.load_thumb(path, row_height)
        _validate_thumb(image, env.expected[path], row_height)
    cold_seconds = time.perf_counter() - started

    started = time.perf_counter()
    for path in env.files:
        image = env.cache.load_thumb(path, row_height)
        _validate_thumb(image, env.expected[path], row_height)
    warm_seconds = time.perf_counter() - started

    print(
        "cold_vs_warm timings: cold={:.6f}s warm={:.6f}s".format(
            cold_seconds, warm_seconds
        )
    )
    assert warm_seconds < cold_seconds, (
        "warm load was not faster than cold load"
    )


def test_mtime_invalidation():
    env = _get_environment()
    path = env.files[0]
    previous_stat = os.stat(path)
    new_dimensions = (1200, 700)

    _save_rgb_noise(path, new_dimensions, "JPEG", quality=90)
    os.utime(
        path,
        (
            previous_stat.st_atime,
            previous_stat.st_mtime + 10.0,
        ),
    )
    env.expected[path] = new_dimensions

    assert env.cache.get_dims(path) == new_dimensions

    row_height = 137
    image = env.cache.load_thumb(path, row_height)
    _validate_thumb(image, new_dimensions, row_height)


def test_row_height_keying():
    env = _get_environment()
    path = env.files[0]

    for row_height in (200, 300):
        image = env.cache.load_thumb(path, row_height)
        _validate_thumb(image, env.expected[path], row_height)
        assert env.cache.has_thumb(path, row_height) is True

    assert env.cache.has_thumb(path, 777) is False


def test_corrupt_thumb():
    env = _get_environment()
    path = env.files[-1]
    row_height = 211

    before = _all_jpegs(env.cache_dir)
    image = env.cache.load_thumb(path, row_height)
    _validate_thumb(image, env.expected[path], row_height)
    after = _all_jpegs(env.cache_dir)

    new_files = after - before
    assert len(new_files) == 1, (
        "expected one new cached JPEG, found {}".format(len(new_files))
    )

    thumb_path = new_files.pop()
    with open(thumb_path, "wb") as handle:
        handle.write(b"not a valid jpeg")

    image = env.cache.load_thumb(path, row_height)
    _validate_thumb(image, env.expected[path], row_height)


def test_prune():
    env = _get_environment()

    for path in env.files:
        for row_height in (91, 113):
            image = env.cache.load_thumb(path, row_height)
            _validate_thumb(image, env.expected[path], row_height)

    before = env.cache.stats()
    assert before["bytes"] > 0

    removed = env.cache.prune(max_bytes=1)
    after = env.cache.stats()

    assert removed > 0, "prune did not remove any files"
    assert after["bytes"] < before["bytes"], (
        "thumbnail byte count did not decrease"
    )

    path = env.files[0]
    row_height = 91
    image = env.cache.load_thumb(path, row_height)
    _validate_thumb(image, env.expected[path], row_height)


def test_concurrency():
    env = _get_environment()
    fresh_cache_dir = os.path.join(env.cache_dir, "concurrent_cache")
    cache = ThumbCache(cache_dir=fresh_cache_dir)
    errors = []
    errors_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker():
        for path in env.files:
            for row_height in (144, 233):
                try:
                    barrier.wait(timeout=60)
                    image = cache.load_thumb(path, row_height)
                    _validate_thumb(
                        image, env.expected[path], row_height
                    )
                except Exception as exc:
                    with errors_lock:
                        errors.append(exc)
                    try:
                        barrier.abort()
                    except Exception:
                        pass
                    return

    try:
        assert cache.enabled is True
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker) for _ in range(2)]
            for future in futures:
                future.result()

        assert not errors, "concurrent loads failed: {!r}".format(errors)
    finally:
        cache.close()


def test_disabled_cache():
    env = _get_environment()
    bad_cache_path = os.path.join(env.cache_dir, "cache_path_is_a_file")
    with open(bad_cache_path, "wb") as handle:
        handle.write(b"this is a file, not a directory")

    cache = ThumbCache(cache_dir=bad_cache_path)
    try:
        assert cache.enabled is False

        path = env.files[0]
        dimensions = env.expected[path]
        assert cache.get_dims(path) == dimensions

        row_height = 123
        image = cache.load_thumb(path, row_height)
        _validate_thumb(image, dimensions, row_height)
    finally:
        cache.close()


def _ascii_message(value):
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def main():
    tests = [
        ("dims", test_dims),
        ("cold_vs_warm", test_cold_vs_warm),
        ("mtime_invalidation", test_mtime_invalidation),
        ("row_height_keying", test_row_height_keying),
        ("corrupt_thumb", test_corrupt_thumb),
        ("prune", test_prune),
        ("concurrency", test_concurrency),
        ("disabled_cache", test_disabled_cache),
    ]
    failures = 0

    try:
        _get_environment()
        for name, function in tests:
            try:
                function()
            except Exception as exc:
                failures += 1
                print(
                    "FAIL {}: {}: {}".format(
                        name,
                        type(exc).__name__,
                        _ascii_message(exc),
                    )
                )
            else:
                print("PASS {}".format(name))
    except Exception as exc:
        failures += 1
        print(
            "FAIL setup: {}: {}".format(
                type(exc).__name__,
                _ascii_message(exc),
            )
        )
    finally:
        try:
            _close_environment()
        except Exception as exc:
            failures += 1
            print(
                "FAIL cleanup: {}: {}".format(
                    type(exc).__name__,
                    _ascii_message(exc),
                )
            )

    return 1 if failures else 0


atexit.register(_close_environment)


if __name__ == "__main__":
    raise SystemExit(main())
