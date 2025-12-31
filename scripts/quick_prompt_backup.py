"""
Quick Prompt Backup Tool

Focus on backing up prompts from PNG files and checking if any JPEGs
still have prompts (indicating they weren't processed by tag embedder yet).

This is for immediate data preservation.
"""

import os
import json
import time
from datetime import datetime
from PIL import Image
from metadata_parser import MetadataParser

def quick_backup(folder_path):
    """Quick backup of prompts from a specific folder."""

    backup_folder = os.path.join(folder_path, 'prompt_backup_emergency')
    os.makedirs(backup_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        'png_prompts_saved': 0,
        'jpeg_prompts_found': 0,
        'jpeg_no_prompts': 0,
        'errors': 0
    }

    parser = MetadataParser()

    # Get all images recursively from this folder and subfolders
    image_files = []
    if os.path.exists(folder_path):
        for root, dirs, files in os.walk(folder_path):
            # Skip backup folders
            if 'prompt_backup' in root or 'backups' in root:
                continue
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(root, file))

    print(f"Processing {len(image_files)} images in {folder_path}")

    for image_path in image_files:
        try:
            file_ext = os.path.splitext(image_path)[1].lower()
            basename = os.path.basename(image_path)

            metadata = parser.extract_metadata(image_path)

            if file_ext == '.png':
                # PNG files - check for parameters
                if metadata and 'parameters' in metadata:
                    # Save backup
                    backup_file = os.path.join(backup_folder, f"{basename}.prompt.json")

                    prompt_data = {
                        'file': image_path,
                        'type': 'png',
                        'extracted_at': timestamp,
                        'parameters': metadata.get('parameters'),
                        'positive_prompt': metadata.get('positive_prompt'),
                        'negative_prompt': metadata.get('negative_prompt'),
                        'tags': metadata.get('tags'),
                        'full_metadata': metadata
                    }

                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(prompt_data, f, indent=2, ensure_ascii=False)

                    results['png_prompts_saved'] += 1
                    print(f"[OK] Saved PNG prompt: {basename}")

            elif file_ext in ['.jpg', '.jpeg']:
                # JPEG files - check if they still have prompts
                has_prompt = False

                if metadata:
                    # Check common prompt indicators
                    for key, value in metadata.items():
                        if isinstance(value, str) and any(indicator in value.lower() for indicator in ['steps:', 'sampler:', 'cfg scale:']):
                            has_prompt = True

                            # Save backup - this JPEG still has a prompt!
                            backup_file = os.path.join(backup_folder, f"{basename}.prompt.json")

                            prompt_data = {
                                'file': image_path,
                                'type': 'jpeg',
                                'extracted_at': timestamp,
                                'prompt_field': key,
                                'prompt_content': value,
                                'full_metadata': metadata,
                                'warning': 'This JPEG still has prompt data - process carefully!'
                            }

                            with open(backup_file, 'w', encoding='utf-8') as f:
                                json.dump(prompt_data, f, indent=2, ensure_ascii=False)

                            results['jpeg_prompts_found'] += 1
                            print(f"[WARNING] FOUND JPEG with prompt: {basename} (field: {key})")
                            break

                if not has_prompt:
                    results['jpeg_no_prompts'] += 1

        except Exception as e:
            results['errors'] += 1
            print(f"ERROR processing {basename}: {e}")

    # Save summary
    summary_file = os.path.join(backup_folder, f"backup_summary_{timestamp}.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Quick Prompt Backup - {timestamp}\n")
        f.write("="*40 + "\n\n")
        f.write(f"Folder: {folder_path}\n")
        f.write(f"PNG prompts saved: {results['png_prompts_saved']}\n")
        f.write(f"JPEG prompts found: {results['jpeg_prompts_found']}\n")
        f.write(f"JPEG without prompts: {results['jpeg_no_prompts']}\n")
        f.write(f"Errors: {results['errors']}\n")

        if results['jpeg_prompts_found'] > 0:
            f.write(f"\n[WARNING] {results['jpeg_prompts_found']} JPEG files still have prompts!\n")
            f.write("These should be processed with the FIXED tag embedder to preserve prompts.\n")

    return results

if __name__ == "__main__":
    # Quick backup of auto_sorted folder
    folders_to_check = [r'H:\Development\image_grid_sorter\auto_sorted']

    for folder in folders_to_check:
        if os.path.exists(folder):
            print(f"\n=== Processing {folder} ===")
            results = quick_backup(folder)

            print(f"\nResults for {folder}:")
            print(f"  PNG prompts saved: {results['png_prompts_saved']}")
            print(f"  JPEG prompts found: {results['jpeg_prompts_found']}")
            print(f"  JPEG without prompts: {results['jpeg_no_prompts']}")
            print(f"  Errors: {results['errors']}")

            if results['jpeg_prompts_found'] > 0:
                print(f"  [WARNING] {results['jpeg_prompts_found']} JPEGs still have prompts - handle carefully!")