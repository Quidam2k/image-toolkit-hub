"""
Tag Extractor - Extract and Deduplicate Tags from Multiple Sources

Extracts tags from both CLIP analysis and image prompts, deduplicates them,
and tracks which sources contributed each tag.

This enables building a comprehensive tag frequency database.

Author: Claude Code Implementation
Version: 1.0
"""

import os
from metadata_parser import MetadataParser
from tag_generator import DescriptiveTagGenerator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TagExtractor:
    """Extract and deduplicate tags from CLIP analysis and prompts."""

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
                'both': []  # Tags found in both sources
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

            # Extract prompt tags
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
        Extract tags by parsing the image's prompt.

        Extracts comma-separated tags from:
        - positive_prompt
        - negative_prompt (when relevant)
        - parameters field

        Args:
            image_path: Path to image file

        Returns:
            list of tags found in prompt
        """
        try:
            metadata = self.parser.extract_metadata(image_path)

            if not metadata:
                return []

            found_tags = set()

            # Check positive prompt - extract comma-separated tags
            if 'positive_prompt' in metadata and metadata['positive_prompt']:
                prompt = metadata['positive_prompt']
                # Split by comma and clean up whitespace
                tokens = [t.strip() for t in prompt.split(',')]
                found_tags.update([t for t in tokens if t])

            # Check parameters field (Stable Diffusion format)
            if 'parameters' in metadata and metadata['parameters']:
                params_str = str(metadata['parameters'])
                # Extract comma-separated values
                tokens = [t.strip() for t in params_str.split(',')]
                found_tags.update([t for t in tokens if t])

            return list(found_tags)

        except Exception as e:
            self.logger.debug(f"Error in prompt extraction: {e}")
            return []

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
            progress_callback: Optional callback for progress updates

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
        print(f"Extracting tags from {len(image_files)} images...")

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

                    print(f"[{i+1}/{len(image_files)}] {os.path.basename(image_path)}: "
                          f"{len(tag_result['tags'])} tags "
                          f"(CLIP: {len(sources['clip'])}, "
                          f"Prompt: {len(sources['prompt'])}, "
                          f"Both: {len(sources['both'])})")
                else:
                    results['failed'] += 1
                    print(f"[{i+1}/{len(image_files)}] {os.path.basename(image_path)}: ERROR")

                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, len(image_files))

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
    """Test tag extraction."""
    print("="*70)
    print("Tag Extractor - Extract tags from CLIP and prompts")
    print("="*70)

    try:
        extractor = TagExtractor()
        print("Tag extractor initialized successfully")

        # Example usage:
        # result = extractor.extract_tags_from_folder('./auto_sorted/cowgirl', recursive=False)
        # print(f"Extracted from {result['successful']} images")
        # print(f"Total unique tags: {len(result['all_tags'])}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
