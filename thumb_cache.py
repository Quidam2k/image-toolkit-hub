"""Persistent thumbnail and image dimension cache."""

import hashlib
import logging
import os
import sqlite3
import threading
import time

from PIL import Image


logger = logging.getLogger(__name__)

_DEFAULT_MAX_BYTES = 2 * 1024 ** 3
_ACCESS_INTERVAL = 3600
_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
_BILINEAR = getattr(Image, "Resampling", Image).BILINEAR


class ThumbCache:
    """Cache image dimensions and rendered thumbnails."""

    def __init__(self, cache_dir=None):
        self._lock = threading.RLock()
        self._conn = None
        self.enabled = False

        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data",
                "thumb_cache",
            )
        self.cache_dir = os.path.abspath(os.fspath(cache_dir))
        self.db_path = os.path.join(self.cache_dir, "index.db")

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False,
            )
            self._conn = conn
            with self._lock:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS dims ("
                    "path TEXT PRIMARY KEY, "
                    "mtime REAL, "
                    "size INTEGER, "
                    "width INTEGER, "
                    "height INTEGER)"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS thumbs ("
                    "key TEXT PRIMARY KEY, "
                    "path TEXT, "
                    "bytes INTEGER, "
                    "last_access REAL)"
                )
                conn.commit()
            self.enabled = True
        except Exception:
            logger.warning("Failed to initialize thumbnail cache", exc_info=True)
            with self._lock:
                if self._conn is not None:
                    try:
                        self._conn.close()
                    except Exception:
                        logger.debug("Failed to close cache database", exc_info=True)
                self._conn = None

    @staticmethod
    def _normalized_path(path):
        return os.path.normcase(os.path.abspath(os.fspath(path)))

    def _key_for(self, path, row_height, stat_result):
        normpath = self._normalized_path(path)
        value = (
            f"{normpath}|{stat_result.st_mtime}|"
            f"{stat_result.st_size}|{row_height}"
        )
        return hashlib.sha1(
            value.encode("utf-8", "surrogatepass")
        ).hexdigest()

    def _thumb_path(self, key):
        return os.path.join(self.cache_dir, key[:2], key + ".jpg")

    def _delete_thumb_row(self, key):
        if not self.enabled:
            return
        try:
            with self._lock:
                if not self.enabled or self._conn is None:
                    return
                self._conn.execute("DELETE FROM thumbs WHERE key = ?", (key,))
                self._conn.commit()
        except Exception:
            logger.debug("Failed to delete thumbnail row", exc_info=True)

    def _touch_thumb(self, key, path, byte_count, now):
        if not self.enabled:
            return
        try:
            with self._lock:
                if not self.enabled or self._conn is None:
                    return
                row = self._conn.execute(
                    "SELECT last_access FROM thumbs WHERE key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    if byte_count is None:
                        return
                    self._conn.execute(
                        "INSERT OR REPLACE INTO thumbs "
                        "(key, path, bytes, last_access) VALUES (?, ?, ?, ?)",
                        (key, path, byte_count, now),
                    )
                    self._conn.commit()
                elif row[0] is None or row[0] < now - _ACCESS_INTERVAL:
                    self._conn.execute(
                        "UPDATE thumbs SET last_access = ? WHERE key = ?",
                        (now, key),
                    )
                    self._conn.commit()
        except Exception:
            logger.debug("Failed to update thumbnail access time", exc_info=True)

    def get_dims(self, path):
        """Return the original image width and height."""
        stat_result = os.stat(path)
        normpath = self._normalized_path(path)
        mtime = stat_result.st_mtime
        size = stat_result.st_size

        if self.enabled:
            try:
                with self._lock:
                    if self.enabled and self._conn is not None:
                        row = self._conn.execute(
                            "SELECT width, height FROM dims "
                            "WHERE path = ? AND mtime = ? AND size = ?",
                            (normpath, mtime, size),
                        ).fetchone()
                    else:
                        row = None
                if row is not None and row[0] > 0 and row[1] > 0:
                    return int(row[0]), int(row[1])
            except Exception:
                logger.debug("Failed to read cached dimensions", exc_info=True)

        with Image.open(path) as image:
            width, height = image.size

        if self.enabled:
            try:
                with self._lock:
                    if self.enabled and self._conn is not None:
                        self._conn.execute(
                            "INSERT OR REPLACE INTO dims "
                            "(path, mtime, size, width, height) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (normpath, mtime, size, width, height),
                        )
                        self._conn.commit()
            except Exception:
                logger.debug("Failed to cache image dimensions", exc_info=True)

        return width, height

    def load_thumb(self, path, row_height):
        """Load or create a thumbnail."""
        row_height = int(row_height)
        if row_height <= 0:
            raise ValueError("row_height must be positive")

        width, height = self.get_dims(path)
        if width <= 0 or height <= 0:
            raise ValueError("image dimensions must be positive")

        target_width = max(1, int(row_height * width / height))
        target_size = (target_width, row_height)
        stat_result = os.stat(path)
        key = self._key_for(path, row_height, stat_result)
        normpath = self._normalized_path(path)
        final_path = self._thumb_path(key)

        if self.enabled:
            try:
                if os.path.isfile(final_path):
                    with Image.open(final_path) as cached:
                        cached.load()
                        if cached.size != target_size:
                            raise ValueError("cached thumbnail has wrong size")
                        result = cached.convert("RGB")  # detached copy; no file lock kept
                    try:
                        byte_count = os.path.getsize(final_path)
                    except OSError:
                        byte_count = None
                    self._touch_thumb(
                        key, normpath, byte_count, time.time()
                    )
                    return result
            except Exception:
                logger.debug("Cached thumbnail is unreadable", exc_info=True)
                try:
                    os.remove(final_path)
                except FileNotFoundError:
                    pass
                except OSError:
                    logger.debug(
                        "Failed to remove unreadable thumbnail",
                        exc_info=True,
                    )
                self._delete_thumb_row(key)

        pixel_count = width * height
        with Image.open(path) as image:
            has_alpha = (
                image.mode in ("RGBA", "LA")
                or (
                    image.mode == "P"
                    and "transparency" in image.info
                )
            )

            if image.format == "JPEG":
                image.draft("RGB", target_size)

            if pixel_count > 100_000_000:
                image.thumbnail((2000, 2000), _LANCZOS)

            resample = (
                _BILINEAR if pixel_count > 25_000_000 else _LANCZOS
            )
            resized = image.resize(target_size, resample)

            if has_alpha:
                rgba = resized.convert("RGBA")
                background = Image.new(
                    "RGBA", rgba.size, (0, 0, 0, 255)
                )
                background.alpha_composite(rgba)
                result = background.convert("RGB")
            else:
                result = resized.convert("RGB")

        if self.enabled:
            temp_path = (
                f"{final_path}.{os.getpid()}."
                f"{threading.get_ident()}.tmp"
            )
            try:
                os.makedirs(os.path.dirname(final_path), exist_ok=True)
                result.save(temp_path, format="JPEG", quality=85)
                os.replace(temp_path, final_path)
                byte_count = os.path.getsize(final_path)
                now = time.time()
                with self._lock:
                    if self.enabled and self._conn is not None:
                        self._conn.execute(
                            "INSERT OR REPLACE INTO thumbs "
                            "(key, path, bytes, last_access) "
                            "VALUES (?, ?, ?, ?)",
                            (key, normpath, byte_count, now),
                        )
                        self._conn.commit()
            except Exception:
                logger.debug("Failed to save cached thumbnail", exc_info=True)
            finally:
                try:
                    os.remove(temp_path)
                except FileNotFoundError:
                    pass
                except OSError:
                    logger.debug(
                        "Failed to remove temporary thumbnail",
                        exc_info=True,
                    )

        return result

    def has_thumb(self, path, row_height):
        """Return whether a cached thumbnail file exists."""
        if not self.enabled:
            return False
        try:
            row_height = int(row_height)
            if row_height <= 0:
                return False
            stat_result = os.stat(path)
            key = self._key_for(path, row_height, stat_result)
            return os.path.isfile(self._thumb_path(key))
        except Exception:
            return False

    def prune(self, max_bytes=_DEFAULT_MAX_BYTES):
        """Remove old thumbnails when the cache is oversized."""
        if not self.enabled:
            return 0

        try:
            max_bytes = max(0, int(max_bytes))
            with self._lock:
                if not self.enabled or self._conn is None:
                    return 0
                rows = self._conn.execute(
                    "SELECT key, bytes FROM thumbs "
                    "ORDER BY last_access ASC"
                ).fetchall()

            missing_keys = []
            existing = []
            total = 0

            for key, byte_count in rows:
                byte_count = max(0, int(byte_count or 0))
                file_path = self._thumb_path(key)
                if os.path.isfile(file_path):
                    existing.append((key, byte_count, file_path))
                    total += byte_count
                else:
                    missing_keys.append(key)

            removed = 0
            deleted_keys = list(missing_keys)

            if total > max_bytes:
                target = int(max_bytes * 0.9)
                for key, byte_count, file_path in existing:
                    if total <= target:
                        break
                    try:
                        os.remove(file_path)
                        removed += 1
                        total -= byte_count
                        deleted_keys.append(key)
                    except FileNotFoundError:
                        total -= byte_count
                        deleted_keys.append(key)
                    except OSError:
                        logger.debug(
                            "Failed to remove cached thumbnail",
                            exc_info=True,
                        )

            if deleted_keys:
                with self._lock:
                    if self.enabled and self._conn is not None:
                        self._conn.executemany(
                            "DELETE FROM thumbs WHERE key = ?",
                            ((key,) for key in deleted_keys),
                        )
                        self._conn.commit()

            return removed
        except Exception:
            logger.warning("Failed to prune thumbnail cache", exc_info=True)
            return 0

    def prune_async(self, max_bytes=_DEFAULT_MAX_BYTES):
        """Prune the cache in a daemon thread."""
        thread = threading.Thread(
            target=self.prune,
            args=(max_bytes,),
            name="ThumbCachePrune",
            daemon=True,
        )
        thread.start()
        return thread

    def stats(self):
        """Return cache row and byte counts."""
        result = {"thumbs": 0, "bytes": 0, "dims": 0}
        if not self.enabled:
            return result

        try:
            with self._lock:
                if not self.enabled or self._conn is None:
                    return result
                thumb_row = self._conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(bytes), 0) FROM thumbs"
                ).fetchone()
                dims_row = self._conn.execute(
                    "SELECT COUNT(*) FROM dims"
                ).fetchone()
            result["thumbs"] = int(thumb_row[0])
            result["bytes"] = int(thumb_row[1])
            result["dims"] = int(dims_row[0])
        except Exception:
            logger.debug("Failed to read cache statistics", exc_info=True)

        return result

    def close(self):
        """Close the cache database."""
        with self._lock:
            conn = self._conn
            self._conn = None
            self.enabled = False
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    logger.debug(
                        "Failed to close cache database",
                        exc_info=True,
                    )


_cache_instance = None
_cache_lock = threading.Lock()


def get_cache():
    """Return the process-wide thumbnail cache."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ThumbCache()
    return _cache_instance
