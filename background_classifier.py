"""
Background Classifier for T-Shirt/POD Image Selection

Identifies images with simple, removable backgrounds suitable for:
- T-shirt printing
- Print-on-demand products
- Sticker/decal production
- Any use requiring background removal

Uses WD14 tagger to detect background tags and classifies them as:
- SUITABLE: simple_background, white_background, transparent_background, solid colors
- NOT SUITABLE: blurry_background, photo_background, pattern backgrounds

Author: Claude Code Implementation
Version: 1.0
"""

import os
import logging
import shutil
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Persistent cache for background tags (survives between sessions)
CACHE_FILE = Path(__file__).parent / "data" / "background_tag_cache.json"


class BackgroundTagCache:
    """Persistent cache for WD14 background tag results."""

    def __init__(self):
        self.cache = {}
        self._load()

    def _load(self):
        """Load cache from disk."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded background cache: {len(self.cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}

    def _save(self):
        """Save cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_key(self, image_path: str) -> str:
        """Get cache key from file path and modification time."""
        try:
            mtime = os.path.getmtime(image_path)
            return f"{image_path}|{mtime}"
        except:
            return image_path

    def get(self, image_path: str) -> Optional[Dict]:
        """Get cached background tags for image."""
        key = self._get_key(image_path)
        return self.cache.get(key)

    def set(self, image_path: str, background_tags: List[str], tag_scores: Dict[str, float]):
        """Cache background tags for image."""
        key = self._get_key(image_path)
        self.cache[key] = {
            'tags': background_tags,
            'scores': tag_scores
        }

    def save(self):
        """Persist cache to disk."""
        self._save()


# Global cache instance
_cache = None

def get_cache() -> BackgroundTagCache:
    """Get or create the global cache."""
    global _cache
    if _cache is None:
        _cache = BackgroundTagCache()
    return _cache


class BackgroundType(Enum):
    """Classification of background types."""
    SIMPLE = "simple"              # Plain solid backgrounds
    TRANSPARENT = "transparent"    # Explicit transparent background
    SOLID_COLOR = "solid_color"    # Solid color backgrounds (white, black, grey, etc.)
    GRADIENT = "gradient"          # Gradient backgrounds (borderline)
    PATTERN = "pattern"            # Patterned backgrounds (not suitable)
    COMPLEX = "complex"            # Complex/photo backgrounds (not suitable)
    UNKNOWN = "unknown"            # No background tag detected


@dataclass
class BackgroundClassification:
    """Result of background classification for an image."""
    image_path: str
    background_type: BackgroundType
    is_suitable: bool
    detected_tags: List[str]
    confidence: float
    reason: str

    def to_dict(self) -> Dict:
        return {
            'image_path': self.image_path,
            'background_type': self.background_type.value,
            'is_suitable': self.is_suitable,
            'detected_tags': self.detected_tags,
            'confidence': self.confidence,
            'reason': self.reason
        }


class BackgroundClassifier:
    """
    Classifier for identifying t-shirt-suitable image backgrounds.

    Uses WD14 tagger to detect background tags and applies lenient filtering
    to find images with removable/simple backgrounds.
    """

    # Tags that indicate SUITABLE backgrounds (solid/simple/removable)
    SUITABLE_TAGS = {
        # Most desirable - simple/plain backgrounds
        'simple_background': (BackgroundType.SIMPLE, 1.0),
        'white_background': (BackgroundType.SOLID_COLOR, 1.0),
        'transparent_background': (BackgroundType.TRANSPARENT, 1.0),

        # Solid color backgrounds - all suitable
        'grey_background': (BackgroundType.SOLID_COLOR, 0.95),
        'black_background': (BackgroundType.SOLID_COLOR, 0.95),
        'blue_background': (BackgroundType.SOLID_COLOR, 0.9),
        'pink_background': (BackgroundType.SOLID_COLOR, 0.9),
        'red_background': (BackgroundType.SOLID_COLOR, 0.9),
        'yellow_background': (BackgroundType.SOLID_COLOR, 0.9),
        'green_background': (BackgroundType.SOLID_COLOR, 0.9),
        'purple_background': (BackgroundType.SOLID_COLOR, 0.9),
        'orange_background': (BackgroundType.SOLID_COLOR, 0.9),
        'brown_background': (BackgroundType.SOLID_COLOR, 0.9),
        'aqua_background': (BackgroundType.SOLID_COLOR, 0.9),
        'light_blue_background': (BackgroundType.SOLID_COLOR, 0.9),
        'light_brown_background': (BackgroundType.SOLID_COLOR, 0.9),
        'dark_background': (BackgroundType.SOLID_COLOR, 0.85),
        'monochrome_background': (BackgroundType.SOLID_COLOR, 0.85),

        # Two-tone can work
        'two-tone_background': (BackgroundType.SOLID_COLOR, 0.8),

        # Gradient - borderline but often workable
        'gradient_background': (BackgroundType.GRADIENT, 0.7),
    }

    # Tags that indicate NOT SUITABLE backgrounds
    UNSUITABLE_TAGS = {
        # Complex/photo backgrounds
        'blurry_background': BackgroundType.COMPLEX,
        'photo_background': BackgroundType.COMPLEX,

        # Patterned backgrounds - hard to remove cleanly
        'floral_background': BackgroundType.PATTERN,
        'starry_background': BackgroundType.PATTERN,
        'polka_dot_background': BackgroundType.PATTERN,
        'striped_background': BackgroundType.PATTERN,
        'checkered_background': BackgroundType.PATTERN,
        'heart_background': BackgroundType.PATTERN,
        'argyle_background': BackgroundType.PATTERN,
        'halftone_background': BackgroundType.PATTERN,
        'patterned_background': BackgroundType.PATTERN,
        'plaid_background': BackgroundType.PATTERN,
        'grid_background': BackgroundType.PATTERN,
        'paw_print_background': BackgroundType.PATTERN,
        'snowflake_background': BackgroundType.PATTERN,
        'flag_background': BackgroundType.PATTERN,
        'honeycomb_background': BackgroundType.PATTERN,
        'dotted_background': BackgroundType.PATTERN,
        'leaf_background': BackgroundType.PATTERN,
        'rainbow_background': BackgroundType.PATTERN,
        'sparkle_background': BackgroundType.PATTERN,
        'sunburst_background': BackgroundType.PATTERN,
        'abstract_background': BackgroundType.PATTERN,
        'text_background': BackgroundType.PATTERN,
        'multicolored_background': BackgroundType.PATTERN,
        '3d_background': BackgroundType.COMPLEX,
        'greyscale_with_colored_background': BackgroundType.PATTERN,
    }

    def __init__(self, wd14_tagger=None, skip_wd14_load=False):
        """
        Initialize the background classifier.

        Args:
            wd14_tagger: Optional pre-loaded WD14Tagger instance
            skip_wd14_load: If True, don't load WD14 (for cache-only mode)
        """
        self.wd14_tagger = wd14_tagger
        self.stats = {'cache_hits': 0, 'wd14_calls': 0, 'no_tags': 0}

        if self.wd14_tagger is None and not skip_wd14_load:
            self._load_wd14()

    def _load_wd14(self):
        """Load WD14 tagger for background detection."""
        try:
            from wd14_tagger import WD14Tagger
            self.wd14_tagger = WD14Tagger()
            if self.wd14_tagger.loaded:
                logger.info("WD14 tagger loaded for background classification")
            else:
                logger.warning("WD14 tagger failed to load")
        except ImportError as e:
            logger.error(f"Failed to import WD14Tagger: {e}")
            self.wd14_tagger = None

    def classify_image(self, image_path: str, threshold: float = 0.35,
                        use_cache: bool = True) -> BackgroundClassification:
        """
        Classify an image's background for t-shirt suitability.

        Args:
            image_path: Path to image file
            threshold: Confidence threshold for WD14 tags
            use_cache: If True, check .txt tag files first (much faster)

        Returns:
            BackgroundClassification with suitability determination
        """
        if not os.path.exists(image_path):
            return BackgroundClassification(
                image_path=image_path,
                background_type=BackgroundType.UNKNOWN,
                is_suitable=False,
                detected_tags=[],
                confidence=0.0,
                reason="File not found"
            )

        background_tags = []
        all_tag_scores = {}
        used_cache = False
        cache = get_cache()

        # FAST PATH: Check persistent background tag cache first
        if use_cache:
            cached = cache.get(image_path)
            if cached:
                used_cache = True
                self.stats['cache_hits'] += 1
                background_tags = cached['tags']
                all_tag_scores = cached['scores']

        # SLOW PATH: Use WD14 if no cache found
        if not used_cache:
            if self.wd14_tagger and self.wd14_tagger.loaded:
                self.stats['wd14_calls'] += 1
                tag_results = self.wd14_tagger.get_tags(image_path, threshold=threshold)
                all_tag_scores = {}

                # Extract only background-related tags
                for tag, conf in tag_results:
                    if 'background' in tag.lower():
                        background_tags.append(tag)
                        all_tag_scores[tag] = float(conf)

                # Cache the result for next time
                cache.set(image_path, background_tags, all_tag_scores)
            else:
                self.stats['no_tags'] += 1

        # Check for unsuitable tags first (they override suitable ones)
        for tag in background_tags:
            if tag in self.UNSUITABLE_TAGS:
                return BackgroundClassification(
                    image_path=image_path,
                    background_type=self.UNSUITABLE_TAGS[tag],
                    is_suitable=False,
                    detected_tags=background_tags,
                    confidence=all_tag_scores.get(tag, 0.5),
                    reason=f"Unsuitable background: {tag}"
                )

        # Check for suitable tags
        best_suitable = None
        best_confidence = 0.0
        best_type = BackgroundType.UNKNOWN

        for tag in background_tags:
            if tag in self.SUITABLE_TAGS:
                bg_type, base_conf = self.SUITABLE_TAGS[tag]
                tag_conf = all_tag_scores.get(tag, 0.5)
                effective_conf = base_conf * tag_conf

                if effective_conf > best_confidence:
                    best_confidence = effective_conf
                    best_suitable = tag
                    best_type = bg_type

        if best_suitable:
            return BackgroundClassification(
                image_path=image_path,
                background_type=best_type,
                is_suitable=True,
                detected_tags=background_tags,
                confidence=best_confidence,
                reason=f"Suitable background: {best_suitable}"
            )

        # No background tags detected - unknown
        return BackgroundClassification(
            image_path=image_path,
            background_type=BackgroundType.UNKNOWN,
            is_suitable=False,
            detected_tags=background_tags,
            confidence=0.0,
            reason="No background tags detected"
        )

    def classify_batch(self, image_paths: List[str],
                       threshold: float = 0.35,
                       progress_callback=None) -> List[BackgroundClassification]:
        """
        Classify multiple images.

        Args:
            image_paths: List of image paths
            threshold: Confidence threshold for WD14 tags
            progress_callback: Optional callback(current, total, filename)

        Returns:
            List of BackgroundClassification results
        """
        results = []
        total = len(image_paths)

        for i, image_path in enumerate(image_paths):
            result = self.classify_image(image_path, threshold)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, os.path.basename(image_path))

        return results

    def find_suitable_images(self, source_folders: List[str],
                             threshold: float = 0.35,
                             progress_callback=None,
                             cancel_check=None) -> Tuple[List[str], List[BackgroundClassification]]:
        """
        Find all images with suitable backgrounds in given folders.

        Args:
            source_folders: List of folder paths to scan
            threshold: WD14 confidence threshold
            progress_callback: Optional callback(current, total, filename, status)
            cancel_check: Optional callable that returns True if operation should cancel

        Returns:
            Tuple of (suitable_image_paths, all_classifications)
        """
        # Gather all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
        all_images = []

        for folder in source_folders:
            folder_path = Path(folder)
            if not folder_path.exists():
                logger.warning(f"Folder not found: {folder}")
                continue

            for file_path in folder_path.rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    all_images.append(str(file_path))

        logger.info(f"Found {len(all_images)} images to classify")

        # Classify all images
        suitable = []
        all_results = []
        total = len(all_images)

        for i, image_path in enumerate(all_images):
            # Check for cancellation
            if cancel_check and cancel_check():
                logger.info("Classification cancelled by user")
                break

            result = self.classify_image(image_path, threshold)
            all_results.append(result)

            if result.is_suitable:
                suitable.append(image_path)

            if progress_callback:
                status = "suitable" if result.is_suitable else "not suitable"
                progress_callback(i + 1, total, os.path.basename(image_path), status)

        # Save cache to disk for next time
        get_cache().save()
        logger.info(f"Cache saved. Stats: {self.stats}")

        return suitable, all_results


def copy_suitable_images(suitable_paths: List[str],
                         output_folder: Optional[str] = None,
                         progress_callback=None,
                         cancel_check=None,
                         track_operation: bool = True) -> Dict:
    """
    Copy suitable images to output folder.

    Args:
        suitable_paths: List of image paths to copy
        output_folder: Destination folder (auto-generated if None)
        progress_callback: Optional callback(current, total, filename)
        cancel_check: Optional callable that returns True if operation should cancel
        track_operation: If True, track operation for resume capability

    Returns:
        Dict with copy statistics and output folder path
    """
    # Import tracker if tracking enabled
    tracker = None
    if track_operation:
        try:
            from copy_operation_tracker import get_tracker
            tracker = get_tracker()
        except ImportError:
            logger.warning("Copy operation tracker not available")

    # Generate output folder name if not provided
    if output_folder is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_folder = f"tshirt_ready_{timestamp}"

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    # Start tracking if enabled
    if tracker:
        tracker.start_operation(suitable_paths, str(output_path), "tshirt_copy")

    copied = 0
    failed = []
    total = len(suitable_paths)
    was_cancelled = False

    for i, src_path in enumerate(suitable_paths):
        # Check for cancellation
        if cancel_check and cancel_check():
            logger.info("Copy operation cancelled by user")
            was_cancelled = True
            break

        try:
            src = Path(src_path)
            dst = output_path / src.name

            # Handle duplicate filenames
            if dst.exists():
                stem = src.stem
                suffix = src.suffix
                counter = 1
                while dst.exists():
                    dst = output_path / f"{stem}_{counter}{suffix}"
                    counter += 1

            shutil.copy2(src, dst)
            copied += 1

            # Track progress
            if tracker:
                tracker.mark_copied(src_path)

        except Exception as e:
            logger.error(f"Failed to copy {src_path}: {e}")
            failed.append((src_path, str(e)))

        if progress_callback:
            progress_callback(i + 1, total, os.path.basename(src_path))

    # Complete or leave for resume
    if tracker:
        if was_cancelled:
            # Leave state for potential resume
            logger.info(f"Copy operation interrupted. {copied}/{total} files copied. Can be resumed.")
        else:
            tracker.complete_operation()

    return {
        'output_folder': str(output_path),
        'total_found': total,
        'copied': copied,
        'failed': len(failed),
        'failed_files': failed,
        'was_cancelled': was_cancelled
    }


def main():
    """Test the background classifier."""
    print("=" * 60)
    print("Background Classifier for T-Shirt/POD Images")
    print("=" * 60)
    print("Identifies images with simple, removable backgrounds")
    print("=" * 60)

    try:
        classifier = BackgroundClassifier()

        if classifier.wd14_tagger and classifier.wd14_tagger.loaded:
            print("\nWD14 tagger loaded successfully!")
            print("\nSuitable background tags:")
            for tag in sorted(classifier.SUITABLE_TAGS.keys()):
                bg_type, conf = classifier.SUITABLE_TAGS[tag]
                print(f"  + {tag} ({bg_type.value}, {conf:.0%})")

            print("\nUnsuitable background tags:")
            for tag in sorted(classifier.UNSUITABLE_TAGS.keys()):
                bg_type = classifier.UNSUITABLE_TAGS[tag]
                print(f"  - {tag} ({bg_type.value})")
        else:
            print("\nWD14 tagger not loaded. Check model files.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
