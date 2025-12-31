"""
Descriptive Tag Generator using WD14 Model

Generates detailed descriptive tags by analyzing image content using WD14 SwinV2 v3.
These tags combined with the original prompts provide better context for auto-sorting.

CRITICAL: This process ONLY writes tags to .txt files and NEVER modifies image metadata.
The original image metadata (including prompts) remains completely untouched.

Author: Claude Code Implementation
Version: 2.0 - WD14 tagger integration (replaces CLIP)
"""

import os
from PIL import Image
import logging
import json
from datetime import datetime
import re
from wd14_tagger import WD14Tagger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DescriptiveTagGenerator:
    """Generate descriptive tags for images using WD14 model."""

    def __init__(self, model_path='models/wd14/model.onnx',
                 tags_path='models/wd14/selected_tags.csv',
                 threshold=0.35):
        """
        Initialize the tag generator with WD14 model.

        Args:
            model_path: Path to the WD14 ONNX model file
            tags_path: Path to WD14 tags CSV file
            threshold: Minimum confidence threshold for tags
        """
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path
        self.tags_path = tags_path
        self.threshold = threshold
        self.loaded = False

        # Initialize WD14 tagger
        self._load_model()

    def _load_model(self):
        """Load the WD14 model for image analysis."""
        try:
            print(f"Loading WD14 model...")
            self.wd14 = WD14Tagger(
                model_path=self.model_path,
                tags_path=self.tags_path,
                threshold=self.threshold
            )
            self.loaded = self.wd14.loaded

            if self.loaded:
                print(f"WD14 model ready for tag generation!")
                self.logger.info(f"WD14 model loaded successfully")
            else:
                self.logger.warning("WD14 model failed to load")

        except Exception as e:
            self.logger.error(f"Failed to initialize WD14 tagger: {e}")
            self.loaded = False

    def analyze_image_with_wd14(self, image_path):
        """
        Use WD14 to generate tags for the image.

        Args:
            image_path: Path to image file

        Returns:
            list of matched tags with scores
        """
        if not self.loaded or self.wd14 is None:
            return []

        try:
            # Get tags from WD14
            tag_results = self.wd14.get_tags(image_path, threshold=self.threshold)

            # Convert to format expected by generate_tags_for_image
            scored_tags = [
                {
                    'tag': tag,
                    'score': float(confidence),
                    'confidence': f"{float(confidence)*100:.1f}%"
                }
                for tag, confidence in tag_results
            ]

            return scored_tags

        except Exception as e:
            self.logger.warning(f"WD14 analysis failed: {e}")
            return []


    def generate_tags_for_image(self, image_path, prompt_text=None):
        """
        Generate comprehensive tags for an image using WD14.

        Args:
            image_path: Path to image file
            prompt_text: Optional prompt text (not used by WD14, kept for compatibility)

        Returns:
            dict with generated tags and metadata
        """
        if not os.path.exists(image_path):
            return {
                'status': 'error',
                'error': f'Image not found: {image_path}',
                'image': os.path.basename(image_path)
            }

        try:
            # WD14-based analysis
            wd14_tags = self.analyze_image_with_wd14(image_path)
            tag_names = [t['tag'] for t in wd14_tags]

            return {
                'status': 'success',
                'image': os.path.basename(image_path),
                'tags': tag_names,
                'tag_count': len(tag_names),
                'wd14_tags': len(tag_names),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error generating tags for {image_path}: {e}")
            return {
                'status': 'error',
                'image': os.path.basename(image_path),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def save_tags_to_file(self, image_path, tags):
        """
        Save tags to companion .txt file.

        CRITICAL: Only writes to .txt file, never modifies the image itself.

        Args:
            image_path: Path to image file
            tags: List of tags or comma-separated string

        Returns:
            dict with save status
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

    def process_folder(self, folder_path, recursive=True, progress_callback=None):
        """
        Process all images in a folder and generate tags.

        Args:
            folder_path: Path to folder containing images
            recursive: If True, process subfolders
            progress_callback: Optional callback for progress updates

        Returns:
            dict with processing results
        """
        results = {
            'folder': folder_path,
            'started': datetime.now().isoformat(),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': [],
            'files': []
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
            for file in os.listdir(folder_path):
                if os.path.splitext(file)[1].lower() in image_extensions:
                    image_files.append(os.path.join(folder_path, file))

        total = len(image_files)
        print(f"Found {total} images to process")

        for i, image_path in enumerate(image_files):
            try:
                # Generate tags
                tag_result = self.generate_tags_for_image(image_path)

                if tag_result['status'] == 'success':
                    # Save tags to file
                    save_result = self.save_tags_to_file(image_path, tag_result['tags'])

                    results['processed'] += 1
                    if save_result['status'] == 'success':
                        results['success'] += 1
                        results['files'].append({
                            'image': image_path,
                            'tags': tag_result['tags'],
                            'tag_count': tag_result['tag_count']
                        })
                        print(f"[{i+1}/{total}] {os.path.basename(image_path)}: {len(tag_result['tags'])} tags")
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to save tags for {image_path}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{image_path}: {tag_result.get('error')}")

                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, total, os.path.basename(image_path))

            except Exception as e:
                results['failed'] += 1
                error_msg = f"Exception processing {image_path}: {e}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)

        results['completed'] = datetime.now().isoformat()

        return results


def main():
    """Test the tag generator."""
    print("="*60)
    print("Descriptive Tag Generator - WD14 Edition")
    print("="*60)
    print("Uses WD14 SwinV2 v3 to analyze images and generate descriptive tags")
    print("Tags are saved to .txt files only - images are NEVER modified")
    print("="*60)

    try:
        generator = DescriptiveTagGenerator()

        if not generator.loaded:
            print("\nERROR: WD14 model not loaded. Please check model files exist:")
            print(f"  Model: {generator.model_path}")
            print(f"  Tags:  {generator.tags_path}")
            return 1

        print("\nWD14 model loaded successfully!")
        print("Ready to tag images")

        # Example: Generate tags for a single image
        # result = generator.generate_tags_for_image('./test_image.png')
        # print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
