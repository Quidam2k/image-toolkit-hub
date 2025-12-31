"""
WD14 Tagger - Anime/AI Art Image Tagging using WaifuDiffusion ONNX Model

This module uses the WD14 SwinV2 v3 model to generate descriptive tags for images.
The model is optimized for anime and AI-generated art, with a vocabulary of 10,862 tags.

Key features:
- ONNX Runtime with DirectML GPU acceleration (AMD + NVIDIA compatible)
- CPU fallback if DirectML unavailable
- Fast inference (~1-2 seconds per image on GPU)
- Production-ready model with proven accuracy
- Tags written to .txt files only (never modifies image metadata)
- Result caching: saves tag results alongside images for fast re-processing

Author: Claude Code Implementation
Version: 1.1 - Added result caching
"""

import os
import cv2
import json
import numpy as np
import pandas as pd
import logging
import hashlib
from pathlib import Path
from PIL import Image
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Try to import onnxruntime
try:
    import onnxruntime as ort
except ImportError:
    raise ImportError(
        "onnxruntime not installed. Install with:\n"
        "  pip install onnxruntime-directml  # For GPU (DirectML)\n"
        "  pip install onnxruntime           # For CPU only"
    )


def get_providers():
    """Get available ONNX Runtime execution providers (GPU or CPU)."""
    providers = []

    # Check for DirectML (GPU acceleration on Windows for AMD/NVIDIA)
    if 'DmlExecutionProvider' in ort.get_available_providers():
        providers.append('DmlExecutionProvider')
        logging.info("DirectML GPU acceleration available")
    else:
        logging.warning(
            "DirectML not available - will use CPU (SLOW!).\n"
            "Install with: pip install onnxruntime-directml"
        )

    # Always add CPU as fallback
    providers.append('CPUExecutionProvider')

    return providers


def make_square(img, target_size):
    """
    Pad image to square with white borders.

    Args:
        img: OpenCV image (numpy array)
        target_size: Minimum target size

    Returns:
        Square padded image
    """
    old_size = img.shape[:2]  # (height, width)
    desired_size = max(old_size)
    desired_size = max(desired_size, target_size)

    delta_w = desired_size - old_size[1]
    delta_h = desired_size - old_size[0]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)

    # White padding
    color = [255, 255, 255]
    new_im = cv2.copyMakeBorder(
        img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return new_im


def smart_resize(img, size):
    """
    Resize image intelligently based on current size.

    Args:
        img: OpenCV image (assumes already square from make_square)
        size: Target size

    Returns:
        Resized image
    """
    if img.shape[0] > size:
        # Downscale with INTER_AREA (best for shrinking)
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    elif img.shape[0] < size:
        # Upscale with INTER_CUBIC (best for enlarging)
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)
    # else: already correct size, no resize needed

    return img


class WD14Tagger:
    """WaifuDiffusion 1.4 tagger for anime/AI art image analysis."""

    # Cache file extension - stored alongside images
    CACHE_EXTENSION = '.wd14cache.json'
    CACHE_VERSION = '1.1'  # Increment when model or processing changes

    def __init__(self,
                 model_path='models/wd14/model.onnx',
                 tags_path='models/wd14/selected_tags.csv',
                 threshold=0.35,
                 use_cache=True):
        """
        Initialize WD14 tagger.

        Args:
            model_path: Path to ONNX model file
            tags_path: Path to tags CSV file
            threshold: Minimum confidence threshold for tags (0.0-1.0)
            use_cache: Whether to use file-based caching (default True)
        """
        self.logger = logging.getLogger(__name__)
        self.model_path = Path(model_path)
        self.tags_path = Path(tags_path)
        self.threshold = threshold
        self.use_cache = use_cache
        self.model = None
        self.tags_df = None
        self.tag_names = []
        self.loaded = False
        self.cache_hits = 0
        self.cache_misses = 0

        # Load model and tags
        self._load_model()
        self._load_tags()

    def _get_cache_path(self, image_path: str) -> Path:
        """Get cache file path for an image (stored alongside the image)."""
        return Path(str(image_path) + self.CACHE_EXTENSION)

    def _get_file_hash(self, image_path: str) -> str:
        """Get a quick hash of file size + mtime for cache validation."""
        try:
            stat = os.stat(image_path)
            # Use size + mtime as a quick fingerprint (faster than hashing file contents)
            return f"{stat.st_size}_{stat.st_mtime}"
        except OSError:
            return ""

    def _load_cache(self, image_path: str) -> Optional[Dict]:
        """
        Load cached results for an image if valid.

        Args:
            image_path: Path to the image file

        Returns:
            Cached tag_confidences dict, or None if cache invalid/missing
        """
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(image_path)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Validate cache version
            if cache_data.get('cache_version') != self.CACHE_VERSION:
                self.logger.debug(f"Cache version mismatch for {image_path}")
                return None

            # Validate file hasn't changed (quick check via size+mtime)
            if cache_data.get('file_hash') != self._get_file_hash(image_path):
                self.logger.debug(f"File changed, cache invalid for {image_path}")
                return None

            self.cache_hits += 1
            return cache_data.get('tag_confidences', {})

        except (json.JSONDecodeError, KeyError, OSError) as e:
            self.logger.debug(f"Cache read error for {image_path}: {e}")
            return None

    def _save_cache(self, image_path: str, tag_confidences: Dict[str, float]) -> bool:
        """
        Save tag results to cache file alongside the image.

        Args:
            image_path: Path to the image file
            tag_confidences: Dict mapping tag names to confidence scores

        Returns:
            True if cache saved successfully
        """
        if not self.use_cache:
            return False

        cache_path = self._get_cache_path(image_path)

        try:
            cache_data = {
                'cache_version': self.CACHE_VERSION,
                'file_hash': self._get_file_hash(image_path),
                'cached_at': datetime.now().isoformat(),
                'model_path': str(self.model_path),
                'tag_confidences': tag_confidences
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)

            return True

        except OSError as e:
            self.logger.warning(f"Failed to save cache for {image_path}: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'total': total,
            'hit_rate_percent': round(hit_rate, 1)
        }

    def clear_cache_stats(self):
        """Reset cache statistics."""
        self.cache_hits = 0
        self.cache_misses = 0

    def _load_model(self):
        """Load ONNX model with available providers."""
        if not self.model_path.exists():
            self.logger.error(f"Model file not found: {self.model_path}")
            self.logger.info("Please copy model from B:\\ai_art\\Tagger\\Models\\wd14\\wd-swinv2-tagger-v3\\")
            self.loaded = False
            return

        try:
            print(f"Loading WD14 model from {self.model_path}...")
            providers = get_providers()
            print(f"Using providers: {providers}")

            self.model = ort.InferenceSession(
                str(self.model_path),
                providers=providers
            )

            self.loaded = True
            print("WD14 model loaded successfully!")
            self.logger.info(f"Model loaded: {self.model_path}")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.loaded = False

    def _load_tags(self):
        """Load tag vocabulary from CSV."""
        if not self.tags_path.exists():
            self.logger.error(f"Tags file not found: {self.tags_path}")
            self.loaded = False
            return

        try:
            self.tags_df = pd.read_csv(self.tags_path)
            self.tag_names = self.tags_df['name'].tolist()

            print(f"Loaded {len(self.tag_names)} tags from vocabulary")
            self.logger.info(f"Tags loaded: {len(self.tag_names)} total")

        except Exception as e:
            self.logger.error(f"Failed to load tags: {e}")
            self.loaded = False

    def preprocess_image(self, image_path):
        """
        Preprocess image for WD14 model inference.

        Args:
            image_path: Path to image file

        Returns:
            Preprocessed numpy array ready for model input
        """
        # Get model input size
        _, height, _, _ = self.model.get_inputs()[0].shape

        # Load image with PIL
        image = Image.open(image_path)

        # Alpha to white background
        image = image.convert('RGBA')
        new_image = Image.new('RGBA', image.size, 'WHITE')
        new_image.paste(image, mask=image)
        image = new_image.convert('RGB')

        # Convert to numpy (OpenCV format)
        image = np.asarray(image)

        # PIL RGB to OpenCV BGR
        image = image[:, :, ::-1]

        # Make square and resize to model input size
        image = make_square(image, height)
        image = smart_resize(image, height)

        # Normalize to float32 and add batch dimension
        image = image.astype(np.float32)
        image = np.expand_dims(image, 0)

        return image

    def interrogate(self, image_path, skip_cache=False):
        """
        Run WD14 model inference on image (with caching).

        Args:
            image_path: Path to image file
            skip_cache: If True, bypass cache and force re-inference

        Returns:
            Dict mapping tag names to confidence scores
        """
        # Try to load from cache first
        if not skip_cache:
            cached = self._load_cache(image_path)
            if cached is not None:
                return cached

        # Cache miss - need to run inference
        self.cache_misses += 1

        if not self.loaded or self.model is None:
            self.logger.warning("Model not loaded, cannot interrogate")
            return {}

        try:
            # Preprocess image
            image = self.preprocess_image(image_path)

            # Run inference
            input_name = self.model.get_inputs()[0].name
            label_name = self.model.get_outputs()[0].name
            confidences = self.model.run([label_name], {input_name: image})[0]

            # Combine tags with confidences
            tag_confidences = {}
            for tag_name, confidence in zip(self.tag_names, confidences[0]):
                tag_confidences[tag_name] = float(confidence)

            # Save to cache for next time
            self._save_cache(image_path, tag_confidences)

            return tag_confidences

        except Exception as e:
            self.logger.error(f"Inference failed for {image_path}: {e}")
            return {}

    def get_tags(self, image_path, threshold=None):
        """
        Get filtered tags above confidence threshold.

        Args:
            image_path: Path to image file
            threshold: Confidence threshold (uses self.threshold if None)

        Returns:
            List of (tag, confidence) tuples sorted by confidence descending
        """
        if threshold is None:
            threshold = self.threshold

        # Get all tag confidences
        tag_confidences = self.interrogate(image_path)

        if not tag_confidences:
            return []

        # Filter by threshold and sort by confidence
        filtered_tags = [
            (tag, conf)
            for tag, conf in tag_confidences.items()
            if conf >= threshold
        ]

        filtered_tags.sort(key=lambda x: x[1], reverse=True)

        return filtered_tags

    def generate_tags_for_image(self, image_path, threshold=None):
        """
        Generate tags for a single image.

        Args:
            image_path: Path to image file
            threshold: Confidence threshold (uses self.threshold if None)

        Returns:
            Dict with status, tags, and metadata
        """
        if not os.path.exists(image_path):
            return {
                'status': 'error',
                'error': f'Image not found: {image_path}',
                'image': os.path.basename(image_path)
            }

        try:
            # Get tags with confidences
            tag_results = self.get_tags(image_path, threshold)

            # Separate ratings from general tags
            ratings = [(tag, conf) for tag, conf in tag_results if tag.startswith('rating:')]
            general_tags = [(tag, conf) for tag, conf in tag_results if not tag.startswith('rating:')]

            return {
                'status': 'success',
                'image': os.path.basename(image_path),
                'tags': [tag for tag, conf in general_tags],
                'confidences': {tag: conf for tag, conf in general_tags},
                'ratings': {tag: conf for tag, conf in ratings},
                'tag_count': len(general_tags),
                'threshold': threshold or self.threshold
            }

        except Exception as e:
            self.logger.error(f"Error generating tags for {image_path}: {e}")
            return {
                'status': 'error',
                'image': os.path.basename(image_path),
                'error': str(e)
            }

    def save_tags_to_file(self, image_path, tags):
        """
        Save tags to companion .txt file.

        CRITICAL: Only writes to .txt file, never modifies the image itself.

        Args:
            image_path: Path to image file
            tags: List of tags or comma-separated string

        Returns:
            Dict with save status
        """
        tag_file = image_path + '.txt'

        try:
            # Ensure tags is a string
            tag_content = ', '.join(tags) if isinstance(tags, list) else str(tags)

            # Write to .txt file only
            with open(tag_file, 'w', encoding='utf-8') as f:
                f.write(tag_content)

            return {
                'status': 'success',
                'tag_file': tag_file,
                'tag_count': len(tag_content.split(', ')) if tag_content else 0
            }

        except Exception as e:
            self.logger.error(f"Error saving tags to {tag_file}: {e}")
            return {
                'status': 'error',
                'tag_file': tag_file,
                'error': str(e)
            }


def main():
    """Test the WD14 tagger."""
    print("="*60)
    print("WD14 Tagger - WaifuDiffusion SwinV2 v3")
    print("="*60)
    print("Anime/AI art image tagging with ONNX DirectML acceleration")
    print("Tags are saved to .txt files only - images are NEVER modified")
    print("="*60)

    try:
        tagger = WD14Tagger()

        if not tagger.loaded:
            print("\nERROR: Model not loaded. Please check model files exist:")
            print(f"  Model: {tagger.model_path}")
            print(f"  Tags:  {tagger.tags_path}")
            return 1

        print("\nModel loaded successfully!")
        print(f"Ready to tag images with {len(tagger.tag_names)} tag vocabulary")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
