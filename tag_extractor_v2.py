"""
Tag Extractor V2 - Clean Tag Extraction with Technical Metadata Filtering

Improvements over V1:
- Properly parses prompt structure (stops at "Negative prompt:")
- Filters out LoRA references (<lora:...>)
- Filters out technical parameters (Steps, Sampler, CFG, Seed, etc.)
- Only extracts content-descriptive tags
- Better handling of prompt formats

Author: Claude Code Implementation
Version: 2.0
"""

import os
import re
from metadata_parser import MetadataParser
from tag_generator import DescriptiveTagGenerator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TagExtractorV2:
    """Extract and deduplicate tags with technical metadata filtering."""

    # Technical parameters to skip (case-insensitive)
    TECHNICAL_PARAMS = {
        'steps', 'sampler', 'cfg scale', 'seed', 'size', 'model hash', 'model',
        'denoising strength', 'clip skip', 'ensd', 'hires upscale', 'hires steps',
        'hires upscaler', 'hires cfg scale', 'version', 'schedule type',
        'schedule max sigma', 'schedule min sigma', 'schedule rho', 'sgm noise multiplier',
        'discard penultimate sigma', 'template', 'negative template', 'lora hashes',
        'ti hashes', 'embed', 'embedding', 'hypernet', 'hypernet hash',
        'face restoration', 'postprocessing', 'addnet enabled', 'addnet module',
        'guidance scale', 'num inference steps', 'width', 'height', 'scale'
    }

    # LoRA reference patterns
    LORA_PATTERN = re.compile(r'<lora:[^>]+>')

    # Weight/strength patterns (e.g., ":0.8", ":1.2")
    WEIGHT_PATTERN = re.compile(r':\s*-?\d+\.?\d*\s*(?:>|$)')

    # Technical parameter line pattern (e.g., "Steps: 25")
    PARAM_LINE_PATTERN = re.compile(r'^([^:]+):\s*(.+)$')

    def __init__(self):
        """Initialize tag extractor with dependencies."""
        self.logger = logging.getLogger(__name__)
        self.parser = MetadataParser()
        self.tag_generator = DescriptiveTagGenerator()

    def extract_tags_from_image(self, image_path):
        """
        Extract tags from an image using all available sources.

        Args:
            image_path: Path to image file

        Returns:
            dict with deduplicated tags and source information
        """
        result = {
            'image': os.path.basename(image_path),
            'status': 'success',
            'tags': [],
            'sources': {
                'clip': [],
                'prompt': [],
                'both': []
            },
            'deduplication': {
                'total_before': 0,
                'total_after': 0,
                'removed_duplicates': []
            }
        }

        try:
            # Extract CLIP tags
            clip_tags = self._extract_clip_tags(image_path)

            # Extract prompt tags (clean, filtered)
            prompt_tags = self._extract_prompt_tags(image_path)

            # Deduplicate and combine
            final_tags, dedup_info = self._deduplicate_tags(clip_tags, prompt_tags)

            result['tags'] = final_tags
            result['sources'] = dedup_info['sources']
            result['deduplication'] = {
                'total_before': dedup_info['total_before'],
                'total_after': len(final_tags),
                'removed_duplicates': dedup_info['duplicates_removed']
            }

            return result

        except Exception as e:
            self.logger.error(f"Error extracting tags from {image_path}: {e}")
            return {
                'image': os.path.basename(image_path),
                'status': 'error',
                'error': str(e)
            }

    def _extract_clip_tags(self, image_path):
        """
        Extract tags by analyzing image with CLIP.

        Args:
            image_path: Path to image file

        Returns:
            list of CLIP-generated tags
        """
        try:
            result = self.tag_generator.generate_tags_for_image(image_path)

            if result['status'] == 'success':
                return result['tags']
            else:
                self.logger.debug(f"CLIP analysis failed for {image_path}: {result.get('error')}")
                return []

        except Exception as e:
            self.logger.debug(f"Error in CLIP extraction: {e}")
            return []

    def _extract_prompt_tags(self, image_path):
        """
        Extract CLEAN tags by parsing the image's prompt.

        Only extracts content tags from positive prompt, skipping:
        - Negative prompts
        - Technical parameters (Steps, Sampler, etc.)
        - LoRA references
        - Weights and modifiers

        Args:
            image_path: Path to image file

        Returns:
            list of clean content tags
        """
        try:
            metadata = self.parser.extract_metadata(image_path)

            if not metadata:
                return []

            found_tags = set()

            # Extract from positive prompt
            if 'positive_prompt' in metadata and metadata['positive_prompt']:
                prompt = metadata['positive_prompt']
                tags = self._parse_positive_prompt(prompt)
                found_tags.update(tags)

            # Extract from parameters field (for SD format that puts prompt in parameters)
            if 'parameters' in metadata and metadata['parameters']:
                params_str = str(metadata['parameters'])
                tags = self._parse_positive_prompt(params_str)
                found_tags.update(tags)

            return list(found_tags)

        except Exception as e:
            self.logger.debug(f"Error in prompt extraction: {e}")
            return []

    def _parse_positive_prompt(self, prompt_text):
        """
        Parse positive prompt and extract only content tags.

        Stops at "Negative prompt:" and filters out technical metadata.

        Args:
            prompt_text: Full prompt text

        Returns:
            set of clean content tags
        """
        if not prompt_text:
            return set()

        # Stop at "Negative prompt:" (case-insensitive)
        negative_idx = prompt_text.lower().find('negative prompt:')
        if negative_idx != -1:
            prompt_text = prompt_text[:negative_idx]

        # Remove LoRA references
        prompt_text = self.LORA_PATTERN.sub('', prompt_text)

        # Split by comma
        tokens = [t.strip() for t in prompt_text.split(',')]

        clean_tags = set()

        for token in tokens:
            if not token:
                continue

            # Skip if this is a technical parameter line
            if self._is_technical_param(token):
                continue

            # Remove weight/strength modifiers
            token = self.WEIGHT_PATTERN.sub('', token)

            # Clean up the token
            token = token.strip()

            # Skip empty, too short, or containing only special chars
            if not token or len(token) < 2:
                continue

            # Skip tokens that are mostly numbers
            if self._is_mostly_numbers(token):
                continue

            # Skip tokens with technical keywords
            if self._contains_technical_keywords(token):
                continue

            clean_tags.add(token)

        return clean_tags

    def _is_technical_param(self, text):
        """Check if text is a technical parameter line."""
        # Check for "Key: Value" pattern
        match = self.PARAM_LINE_PATTERN.match(text)
        if match:
            key = match.group(1).strip().lower()
            if key in self.TECHNICAL_PARAMS:
                return True

        return False

    def _is_mostly_numbers(self, text):
        """Check if text is mostly numeric (e.g., "1570573183")."""
        if not text:
            return False

        digit_count = sum(c.isdigit() for c in text)
        return digit_count / len(text) > 0.7

    def _contains_technical_keywords(self, text):
        """Check if text contains technical keywords."""
        text_lower = text.lower()

        # Check against technical params
        for param in self.TECHNICAL_PARAMS:
            if param in text_lower:
                return True

        # Check for bracket patterns typical of technical syntax
        if re.search(r'[\[\]\{\}]', text):
            return True

        return False

    def _deduplicate_tags(self, clip_tags, prompt_tags):
        """
        Deduplicate tags from multiple sources.

        Logic:
        1. Find tags in both sources (keep once, note source)
        2. Find tags only in CLIP
        3. Find tags only in prompt
        4. Combine all unique tags
        5. Maintain source tracking

        Args:
            clip_tags: List of CLIP-generated tags
            prompt_tags: List of tags found in prompt

        Returns:
            (deduplicated_tag_list, deduplication_info_dict)
        """
        clip_set = set(clip_tags)
        prompt_set = set(prompt_tags)

        # Find duplicates
        both = clip_set & prompt_set
        only_clip = clip_set - prompt_set
        only_prompt = prompt_set - clip_set

        # Build deduplicated list (order: both, clip-only, prompt-only)
        deduplicated = list(both) + list(only_clip) + list(only_prompt)

        dedup_info = {
            'total_before': len(clip_tags) + len(prompt_tags),
            'sources': {
                'clip': list(only_clip),
                'prompt': list(only_prompt),
                'both': list(both)
            },
            'duplicates_removed': list(both)  # These were redundant
        }

        return deduplicated, dedup_info

    def extract_tags_from_folder(self, folder_path, recursive=False, progress_callback=None):
        """
        Extract tags from all images in a folder.

        Args:
            folder_path: Path to folder containing images
            recursive: If True, process subfolders
            progress_callback: Optional callback for progress updates (current, total, message)

        Returns:
            dict with extraction results
        """
        results = {
            'folder': folder_path,
            'total_images': 0,
            'successful': 0,
            'failed': 0,
            'images': [],
            'all_tags': {},  # Tag frequency across all images
            'source_stats': {
                'from_clip': 0,
                'from_prompt': 0,
                'from_both': 0
            }
        }

        # Find all image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
        image_files = []

        if recursive:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        image_files.append(os.path.join(root, file))
        else:
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        image_files.append(os.path.join(folder_path, file))

        results['total_images'] = len(image_files)
        self.logger.info(f"Extracting tags from {len(image_files)} images...")

        for i, image_path in enumerate(image_files):
            try:
                tag_result = self.extract_tags_from_image(image_path)

                if tag_result['status'] == 'success':
                    results['successful'] += 1
                    results['images'].append(tag_result)

                    # Add to frequency count
                    for tag in tag_result['tags']:
                        results['all_tags'][tag] = results['all_tags'].get(tag, 0) + 1

                    # Track source distribution
                    sources = tag_result['sources']
                    results['source_stats']['from_clip'] += len(sources['clip'])
                    results['source_stats']['from_prompt'] += len(sources['prompt'])
                    results['source_stats']['from_both'] += len(sources['both'])

                else:
                    results['failed'] += 1

                # Progress callback
                if progress_callback:
                    progress_callback(
                        i + 1,
                        len(image_files),
                        f"Processing: {os.path.basename(image_path)}"
                    )

            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"Exception processing {image_path}: {e}")

        # Sort tags by frequency
        results['all_tags'] = dict(sorted(
            results['all_tags'].items(),
            key=lambda x: x[1],
            reverse=True
        ))

        return results


def main():
    """Test improved tag extraction."""
    print("="*70)
    print("Tag Extractor V2 - Clean tag extraction with metadata filtering")
    print("="*70)

    try:
        extractor = TagExtractorV2()
        print("Tag extractor V2 initialized successfully")

        # Test with a sample prompt
        test_prompts = [
            "1girl, blonde hair, blue eyes, fantasy background\nNegative prompt: ugly, bad anatomy\nSteps: 25, Sampler: DPM++ 2M, CFG scale: 7, Seed: 12345",
            "<lora:LoraName:0.8> beautiful woman, red dress, city street",
            "masterpiece, best quality, cowgirl position, explicit content"
        ]

        print("\nTesting prompt parsing:")
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\nTest {i}:")
            print(f"  Input: {prompt[:100]}...")
            tags = extractor._parse_positive_prompt(prompt)
            print(f"  Clean tags: {sorted(tags)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
