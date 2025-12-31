"""
Prompt Recovery Tool for Image Grid Sorter

This tool helps recover and backup prompts from images before any metadata
operations that might overwrite them. Critical for preserving original
generation parameters.

Features:
- Extract prompts from PNG files (safe - have parameters field)
- Extract prompts from unprocessed JPEG files
- Create backup files with original prompts
- Generate recovery reports
- Validate prompt extraction

Author: Claude Code Implementation for Data Recovery
Version: 1.0
"""

import os
import json
import time
from datetime import datetime
from PIL import Image
from metadata_parser import MetadataParser
import logging

class PromptRecovery:
    """Extract and backup prompts from images to prevent data loss."""

    def __init__(self):
        self.metadata_parser = MetadataParser()
        self.logger = logging.getLogger(__name__)

    def extract_all_prompts(self, root_folder, backup_folder=None):
        """
        Extract prompts from all images in a folder tree and save backups.

        Args:
            root_folder: Root directory to search for images
            backup_folder: Where to save prompt backups (default: root_folder/prompt_backups)

        Returns:
            dict: Results including counts and file lists
        """
        if backup_folder is None:
            backup_folder = os.path.join(root_folder, 'prompt_backups')

        # Create backup folder
        os.makedirs(backup_folder, exist_ok=True)

        # Create timestamped subfolder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(backup_folder, f"extraction_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)

        results = {
            'processed': 0,
            'png_with_prompts': 0,
            'jpeg_with_prompts': 0,
            'no_prompts': 0,
            'errors': 0,
            'files_with_prompts': [],
            'files_without_prompts': [],
            'error_files': [],
            'backup_folder': session_folder,
            'timestamp': timestamp
        }

        # Find all image files
        image_extensions = ['.png', '.jpg', '.jpeg']
        image_files = []

        for root, dirs, files in os.walk(root_folder):
            # Skip backup folders to avoid recursion
            if 'prompt_backups' in root or 'backups' in root:
                continue

            for file in files:
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(root, file))

        print(f"Found {len(image_files)} image files to process...")

        # Process each image
        for i, image_path in enumerate(image_files):
            if i % 100 == 0:
                print(f"Processing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")

            try:
                prompt_data = self.extract_prompt_from_image(image_path)
                results['processed'] += 1

                if prompt_data:
                    # Save backup
                    self.save_prompt_backup(image_path, prompt_data, session_folder)

                    # Track by file type
                    file_ext = os.path.splitext(image_path)[1].lower()
                    if file_ext == '.png':
                        results['png_with_prompts'] += 1
                    elif file_ext in ['.jpg', '.jpeg']:
                        results['jpeg_with_prompts'] += 1

                    results['files_with_prompts'].append({
                        'file': image_path,
                        'type': file_ext,
                        'prompt_length': len(prompt_data.get('positive_prompt', '')),
                        'has_negative': bool(prompt_data.get('negative_prompt')),
                        'has_parameters': bool(prompt_data.get('parameters'))
                    })
                else:
                    results['no_prompts'] += 1
                    results['files_without_prompts'].append(image_path)

            except Exception as e:
                results['errors'] += 1
                results['error_files'].append({
                    'file': image_path,
                    'error': str(e)
                })
                print(f"ERROR processing {os.path.basename(image_path)}: {e}")

        # Save summary report
        self.save_extraction_report(results, session_folder)

        return results

    def extract_prompt_from_image(self, image_path):
        """
        Extract prompt data from a single image.

        Returns:
            dict: Prompt data including positive_prompt, negative_prompt, parameters
            None: If no prompt found
        """
        try:
            metadata = self.metadata_parser.extract_metadata(image_path)

            if not metadata:
                return None

            prompt_data = {}

            # Check for Stable Diffusion parameters (most reliable)
            if 'positive_prompt' in metadata:
                prompt_data['positive_prompt'] = metadata['positive_prompt']

            if 'negative_prompt' in metadata:
                prompt_data['negative_prompt'] = metadata['negative_prompt']

            if 'parameters' in metadata and isinstance(metadata['parameters'], dict):
                prompt_data['parameters'] = metadata['parameters']

            # Fallback: look for raw parameters string
            if not prompt_data and 'parameters' in metadata:
                # Raw parameters string - try to parse it
                raw_params = metadata['parameters']
                if isinstance(raw_params, str) and any(keyword in raw_params.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                    parsed = self.metadata_parser.parse_sd_parameters(raw_params)
                    if parsed:
                        prompt_data.update(parsed)

            # Fallback: check other metadata fields for prompt-like content
            if not prompt_data:
                for key, value in metadata.items():
                    if isinstance(value, str) and any(keyword in value.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                        # Found prompt-like content
                        parsed = self.metadata_parser.parse_sd_parameters(value)
                        if parsed:
                            prompt_data.update(parsed)
                            prompt_data['source_field'] = key
                            break

            # Add source metadata
            if prompt_data:
                prompt_data['extraction_source'] = os.path.splitext(image_path)[1].lower()
                prompt_data['extracted_at'] = datetime.now().isoformat()
                prompt_data['original_file'] = image_path

            return prompt_data if prompt_data else None

        except Exception as e:
            self.logger.error(f"Error extracting prompt from {image_path}: {e}")
            raise

    def save_prompt_backup(self, image_path, prompt_data, backup_folder):
        """Save prompt data to backup file."""
        try:
            # Create relative path structure in backup folder
            rel_path = os.path.relpath(image_path)
            backup_path = os.path.join(backup_folder, rel_path + '.prompt.json')

            # Create directory structure
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # Save prompt data
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Error saving prompt backup for {image_path}: {e}")
            raise

    def save_extraction_report(self, results, session_folder):
        """Save extraction report."""
        try:
            report_path = os.path.join(session_folder, 'extraction_report.json')

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            # Also save a human-readable summary
            summary_path = os.path.join(session_folder, 'extraction_summary.txt')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"Prompt Extraction Report - {results['timestamp']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total images processed: {results['processed']}\n")
                f.write(f"PNG files with prompts: {results['png_with_prompts']}\n")
                f.write(f"JPEG files with prompts: {results['jpeg_with_prompts']}\n")
                f.write(f"Files without prompts: {results['no_prompts']}\n")
                f.write(f"Errors: {results['errors']}\n\n")

                if results['files_with_prompts']:
                    f.write("FILES WITH PROMPTS SAVED:\n")
                    f.write("-" * 30 + "\n")
                    for file_info in results['files_with_prompts']:
                        f.write(f"{file_info['file']} ({file_info['type']})\n")
                        f.write(f"  Prompt length: {file_info['prompt_length']} chars\n")
                        f.write(f"  Has negative: {file_info['has_negative']}\n")
                        f.write(f"  Has parameters: {file_info['has_parameters']}\n\n")

                if results['error_files']:
                    f.write("\nERROR FILES:\n")
                    f.write("-" * 15 + "\n")
                    for error_info in results['error_files']:
                        f.write(f"{error_info['file']}: {error_info['error']}\n")

            print(f"Extraction report saved to: {summary_path}")

        except Exception as e:
            self.logger.error(f"Error saving extraction report: {e}")

if __name__ == "__main__":
    import sys

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        root_folder = sys.argv[1]
    else:
        root_folder = input("Enter the root folder to scan for images: ").strip()

    if not os.path.exists(root_folder):
        print(f"Error: Folder '{root_folder}' does not exist")
        sys.exit(1)

    recovery = PromptRecovery()

    print(f"Starting prompt extraction from: {root_folder}")
    print("This will scan all images and create backups of any found prompts...")

    results = recovery.extract_all_prompts(root_folder)

    print("\n" + "=" * 60)
    print("PROMPT EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total images processed: {results['processed']}")
    print(f"PNG files with prompts: {results['png_with_prompts']}")
    print(f"JPEG files with prompts: {results['jpeg_with_prompts']}")
    print(f"Files without prompts: {results['no_prompts']}")
    print(f"Errors: {results['errors']}")
    print(f"Backups saved to: {results['backup_folder']}")

    if results['jpeg_with_prompts'] > 0:
        print(f"\n⚠️  WARNING: Found {results['jpeg_with_prompts']} JPEG files with prompts!")
        print("These may be at risk if tag embedding has not been run yet.")
        print("Consider processing these with the fixed tag embedder ASAP.")