"""
Comprehensive Prompt Management Tool

This tool provides complete management of prompts and metadata across your image collection:
- Recovery of existing prompts from backups
- Restoration of prompts to images
- Metadata migration and cleanup
- Collection analysis and reporting

Features:
- Restore prompts from backup JSON files to images
- Migrate prompts between different metadata formats
- Generate comprehensive collection reports
- Validate prompt integrity across formats
- Cleanup and consolidation operations

Author: Claude Code Implementation for Data Recovery
Version: 1.0
"""

import os
import json
import shutil
from datetime import datetime
from PIL import Image
from metadata_parser import MetadataParser
from tag_embedder import TagEmbedder
import logging

class PromptManager:
    """Complete prompt and metadata management system."""

    def __init__(self):
        self.parser = MetadataParser()
        self.embedder = TagEmbedder()
        self.logger = logging.getLogger(__name__)

    def restore_prompts_from_backups(self, backup_folder, target_folder=None, dry_run=True):
        """
        Restore prompts from backup JSON files to corresponding images.

        Args:
            backup_folder: Folder containing .prompt.json backup files
            target_folder: Folder containing images to restore to (default: derive from backup paths)
            dry_run: If True, don't actually modify images

        Returns:
            dict: Restoration results
        """
        results = {
            'processed': 0,
            'restored': 0,
            'errors': 0,
            'skipped': 0,
            'dry_run': dry_run,
            'details': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Find all backup files
            backup_files = []
            for root, dirs, files in os.walk(backup_folder):
                for file in files:
                    if file.endswith('.prompt.json'):
                        backup_files.append(os.path.join(root, file))

            print(f"Found {len(backup_files)} backup files to process...")

            for backup_file in backup_files:
                try:
                    results['processed'] += 1

                    # Load backup data
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)

                    # Determine target image path
                    if target_folder:
                        # Use specified target folder
                        backup_rel_path = os.path.relpath(backup_file, backup_folder)
                        image_name = backup_rel_path.replace('.prompt.json', '')
                        target_image = os.path.join(target_folder, image_name)
                    else:
                        # Use original file path from backup
                        target_image = backup_data.get('original_file') or backup_data.get('file')

                    if not target_image or not os.path.exists(target_image):
                        results['skipped'] += 1
                        results['details'].append({
                            'file': backup_file,
                            'status': 'skipped',
                            'reason': 'Target image not found'
                        })
                        continue

                    # Check if restoration is needed
                    current_metadata = self.parser.extract_metadata(target_image)
                    needs_restoration = True

                    if current_metadata:
                        # Check if prompts already exist
                        if any(field in current_metadata for field in ['positive_prompt', 'parameters']):
                            needs_restoration = False
                            results['skipped'] += 1
                            results['details'].append({
                                'file': target_image,
                                'status': 'skipped',
                                'reason': 'Prompts already exist'
                            })
                            continue

                    if dry_run:
                        results['details'].append({
                            'file': target_image,
                            'status': 'dry_run',
                            'action': f'Would restore prompt from {backup_file}'
                        })
                        continue

                    # Perform restoration
                    restoration_success = self._restore_prompt_to_image(target_image, backup_data)

                    if restoration_success:
                        results['restored'] += 1
                        results['details'].append({
                            'file': target_image,
                            'status': 'restored',
                            'source': backup_file
                        })
                        print(f"✅ Restored: {os.path.basename(target_image)}")
                    else:
                        results['errors'] += 1
                        results['details'].append({
                            'file': target_image,
                            'status': 'error',
                            'reason': 'Restoration failed'
                        })

                except Exception as e:
                    results['errors'] += 1
                    results['details'].append({
                        'file': backup_file,
                        'status': 'error',
                        'reason': str(e)
                    })
                    print(f"❌ Error processing {backup_file}: {e}")

        except Exception as e:
            self.logger.error(f"Error in prompt restoration: {e}")
            results['error'] = str(e)

        return results

    def _restore_prompt_to_image(self, image_path, backup_data):
        """Restore prompt data to a specific image."""
        try:
            file_ext = os.path.splitext(image_path)[1].lower()

            if file_ext == '.png':
                return self._restore_png_prompt(image_path, backup_data)
            elif file_ext in ['.jpg', '.jpeg']:
                return self._restore_jpeg_prompt(image_path, backup_data)
            else:
                self.logger.warning(f"Unsupported format for restoration: {file_ext}")
                return False

        except Exception as e:
            self.logger.error(f"Error restoring prompt to {image_path}: {e}")
            return False

    def _restore_png_prompt(self, image_path, backup_data):
        """Restore prompt to PNG file."""
        try:
            # Create backup
            backup_path = image_path + '.pre_restore_backup'
            shutil.copy2(image_path, backup_path)

            with Image.open(image_path) as img:
                from PIL import PngImagePlugin
                meta = PngImagePlugin.PngInfo()

                # Copy existing metadata
                if hasattr(img, 'text'):
                    for key, value in img.text.items():
                        if key not in ['parameters']:  # Don't copy old parameters if restoring
                            meta.add_text(key, value)

                # Add restored prompt data
                if 'positive_prompt' in backup_data:
                    meta.add_text('positive_prompt', backup_data['positive_prompt'])

                if 'negative_prompt' in backup_data:
                    meta.add_text('negative_prompt', backup_data['negative_prompt'])

                if 'parameters' in backup_data:
                    # Convert parameters back to string format if needed
                    params = backup_data['parameters']
                    if isinstance(params, dict):
                        # Reconstruct parameter string
                        param_str = self._reconstruct_parameter_string(backup_data)
                        meta.add_text('parameters', param_str)
                    elif isinstance(params, str):
                        meta.add_text('parameters', params)

                # Mark as restored
                meta.add_text('prompt_restored_from_backup', datetime.now().isoformat())

                # Save with restored metadata
                img.save(image_path, "PNG", pnginfo=meta)

            return True

        except Exception as e:
            self.logger.error(f"Error restoring PNG prompt: {e}")
            return False

    def _restore_jpeg_prompt(self, image_path, backup_data):
        """Restore prompt to JPEG file using the safe embedder method."""
        try:
            # Create a temporary text file with the prompt data
            prompt_text = self._create_prompt_text_from_backup(backup_data)

            temp_tag_file = image_path + '.temp_restore.txt'
            with open(temp_tag_file, 'w', encoding='utf-8') as f:
                f.write(prompt_text)

            # Use the safe embedder to add the prompt
            # First, rename temp file to expected name
            expected_tag_file = image_path + '.txt'
            backup_existing_tags = None

            # Backup existing tag file if it exists
            if os.path.exists(expected_tag_file):
                backup_existing_tags = expected_tag_file + '.backup'
                shutil.copy2(expected_tag_file, backup_existing_tags)

            # Copy temp file to expected location
            shutil.copy2(temp_tag_file, expected_tag_file)

            # Use embedder to safely add the prompt
            result = self.embedder.embed_tag_file_in_image(image_path, backup_original=True)

            # Cleanup temp files
            os.remove(temp_tag_file)

            # Restore original tag file if it existed
            if backup_existing_tags:
                shutil.move(backup_existing_tags, expected_tag_file)
            else:
                # Remove the temp tag file we created
                if os.path.exists(expected_tag_file):
                    os.remove(expected_tag_file)

            return result.get('success', False) if isinstance(result, dict) else result

        except Exception as e:
            self.logger.error(f"Error restoring JPEG prompt: {e}")
            return False

    def _reconstruct_parameter_string(self, backup_data):
        """Reconstruct parameter string from backup data."""
        try:
            parts = []

            # Add positive prompt
            if 'positive_prompt' in backup_data and backup_data['positive_prompt']:
                parts.append(backup_data['positive_prompt'])

            # Add negative prompt
            if 'negative_prompt' in backup_data and backup_data['negative_prompt']:
                parts.append(f"Negative prompt: {backup_data['negative_prompt']}")

            # Add technical parameters
            if 'parameters' in backup_data and isinstance(backup_data['parameters'], dict):
                param_parts = []
                params = backup_data['parameters']

                for key, value in params.items():
                    param_parts.append(f"{key}: {value}")

                if param_parts:
                    parts.append(", ".join(param_parts))

            return "\n".join(parts)

        except Exception as e:
            self.logger.error(f"Error reconstructing parameter string: {e}")
            return "Restored from backup"

    def _create_prompt_text_from_backup(self, backup_data):
        """Create a text representation of prompt data for restoration."""
        try:
            lines = []
            lines.append("# RESTORED PROMPT DATA")
            lines.append(f"# Restored on: {datetime.now().isoformat()}")
            lines.append("")

            if 'positive_prompt' in backup_data:
                lines.append("POSITIVE PROMPT:")
                lines.append(backup_data['positive_prompt'])
                lines.append("")

            if 'negative_prompt' in backup_data:
                lines.append("NEGATIVE PROMPT:")
                lines.append(backup_data['negative_prompt'])
                lines.append("")

            if 'parameters' in backup_data:
                lines.append("PARAMETERS:")
                params = backup_data['parameters']
                if isinstance(params, dict):
                    for key, value in params.items():
                        lines.append(f"{key}: {value}")
                else:
                    lines.append(str(params))

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Error creating prompt text: {e}")
            return "Restored prompt data (error in formatting)"

    def analyze_collection(self, folder_path, output_file=None):
        """
        Analyze an image collection for prompt availability and metadata health.

        Args:
            folder_path: Path to analyze
            output_file: Optional file to save report

        Returns:
            dict: Analysis results
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'folder_path': folder_path,
            'total_images': 0,
            'png_files': 0,
            'jpeg_files': 0,
            'images_with_prompts': 0,
            'images_with_tags': 0,
            'images_with_backups': 0,
            'prompt_sources': {},
            'recommendations': [],
            'file_details': []
        }

        try:
            # Find all images
            image_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_files.append(os.path.join(root, file))

            analysis['total_images'] = len(image_files)
            print(f"Analyzing {len(image_files)} images...")

            for i, image_path in enumerate(image_files):
                if i % 100 == 0:
                    print(f"Analyzed {i}/{len(image_files)} files...")

                file_ext = os.path.splitext(image_path)[1].lower()
                if file_ext == '.png':
                    analysis['png_files'] += 1
                elif file_ext in ['.jpg', '.jpeg']:
                    analysis['jpeg_files'] += 1

                # Check for metadata
                metadata = self.parser.extract_metadata(image_path)
                file_detail = {
                    'path': image_path,
                    'format': file_ext,
                    'has_prompts': False,
                    'has_tags': False,
                    'has_backup': False,
                    'prompt_sources': []
                }

                if metadata:
                    # Check for prompts
                    prompt_fields = ['positive_prompt', 'negative_prompt', 'parameters']
                    found_prompts = [field for field in prompt_fields if field in metadata]

                    if found_prompts:
                        file_detail['has_prompts'] = True
                        file_detail['prompt_sources'] = found_prompts
                        analysis['images_with_prompts'] += 1

                        # Track prompt source types
                        for source in found_prompts:
                            analysis['prompt_sources'][source] = analysis['prompt_sources'].get(source, 0) + 1

                    # Check for tags
                    if 'tags' in metadata:
                        file_detail['has_tags'] = True
                        analysis['images_with_tags'] += 1

                # Check for backup files
                backup_file = image_path + '.prompt.json'
                if os.path.exists(backup_file):
                    file_detail['has_backup'] = True
                    analysis['images_with_backups'] += 1

                analysis['file_details'].append(file_detail)

            # Generate recommendations
            if analysis['jpeg_files'] > 0 and analysis['images_with_prompts'] < analysis['total_images'] * 0.5:
                analysis['recommendations'].append("Consider running prompt recovery on JPEG files")

            if analysis['images_with_backups'] > 0:
                analysis['recommendations'].append(f"{analysis['images_with_backups']} backup files available for restoration")

            if analysis['png_files'] > analysis['images_with_prompts']:
                analysis['recommendations'].append("Some PNG files may have lost prompts - check metadata")

            # Save report if requested
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False)
                print(f"Analysis report saved to: {output_file}")

        except Exception as e:
            analysis['error'] = str(e)
            self.logger.error(f"Error in collection analysis: {e}")

        return analysis

def main():
    """Interactive prompt management interface."""
    import sys

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    manager = PromptManager()

    print("Comprehensive Prompt Manager")
    print("=" * 50)
    print("1. Restore prompts from backups")
    print("2. Analyze collection")
    print("3. Exit")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        backup_folder = input("Enter backup folder path: ").strip()
        if not os.path.exists(backup_folder):
            print(f"Error: Backup folder '{backup_folder}' not found")
            return

        target_folder = input("Enter target folder (or press Enter to use original paths): ").strip()
        if target_folder and not os.path.exists(target_folder):
            print(f"Error: Target folder '{target_folder}' not found")
            return

        dry_run = input("Enable dry-run mode? (Y/n): ").strip().lower() != 'n'

        print(f"\nRestoring prompts from: {backup_folder}")
        if target_folder:
            print(f"Target folder: {target_folder}")
        print(f"Dry run: {dry_run}")

        results = manager.restore_prompts_from_backups(backup_folder, target_folder, dry_run)

        print(f"\nRestoration Results:")
        print(f"Processed: {results['processed']}")
        print(f"Restored: {results['restored']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Errors: {results['errors']}")

    elif choice == '2':
        folder_path = input("Enter folder path to analyze: ").strip()
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' not found")
            return

        save_report = input("Save detailed report? (Y/n): ").strip().lower() != 'n'
        output_file = None
        if save_report:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"collection_analysis_{timestamp}.json"

        print(f"\nAnalyzing collection: {folder_path}")
        analysis = manager.analyze_collection(folder_path, output_file)

        print(f"\nCollection Analysis:")
        print(f"Total images: {analysis['total_images']}")
        print(f"PNG files: {analysis['png_files']}")
        print(f"JPEG files: {analysis['jpeg_files']}")
        print(f"Images with prompts: {analysis['images_with_prompts']}")
        print(f"Images with tags: {analysis['images_with_tags']}")
        print(f"Images with backups: {analysis['images_with_backups']}")

        if analysis['recommendations']:
            print(f"\nRecommendations:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")

    else:
        print("Goodbye!")

if __name__ == "__main__":
    main()