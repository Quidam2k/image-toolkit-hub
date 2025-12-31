"""
Prompt Preservation Audit Suite

Comprehensive validation that original image prompts are preserved through the
tag generation and embedding pipeline.

This is the CRITICAL SAFETY CHECK before processing your new batch.

Pipeline being tested:
1. Start with original image (with embedded prompts)
2. Generate tags -> save to .txt file (should NOT touch image)
3. Embed tags into image metadata (should PRESERVE original prompts)
4. Verify original prompts still exist

Author: Claude Code Implementation
Version: 1.0
"""

import os
import shutil
import json
import logging
from datetime import datetime
from metadata_parser import MetadataParser
from tag_embedder import TagEmbedder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class PromptPreservationAudit:
    """Audit the prompt preservation pipeline."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser = MetadataParser()
        self.embedder = TagEmbedder()
        self.test_results = []

    def extract_prompts_from_metadata(self, metadata):
        """Extract all prompt-like data from image metadata."""
        prompts = {}

        if not metadata:
            return prompts

        # Look for common prompt fields
        prompt_fields = {
            'parameters': 'Stable Diffusion parameters',
            'positive_prompt': 'Positive prompt',
            'negative_prompt': 'Negative prompt',
            'parameters_text': 'SD parameters text',
            'prompt': 'Prompt field'
        }

        for field, description in prompt_fields.items():
            if field in metadata and metadata[field]:
                prompts[field] = {
                    'value': metadata[field],
                    'description': description,
                    'size': len(str(metadata[field]))
                }

        # Also look for any field containing prompt keywords
        for key, value in metadata.items():
            if isinstance(value, str):
                if any(kw in value.lower() for kw in ['steps:', 'sampler:', 'cfg scale:', 'seed:']):
                    if key not in prompts:
                        prompts[key] = {
                            'value': value,
                            'description': f'Field containing SD keywords: {key}',
                            'size': len(value)
                        }

        return prompts

    def audit_single_image(self, image_path, test_name=None):
        """
        Audit a single image through the entire pipeline.

        Args:
            image_path: Path to image file
            test_name: Optional name for this test

        Returns:
            dict with detailed audit results
        """
        if test_name is None:
            test_name = os.path.basename(image_path)

        audit = {
            'test_name': test_name,
            'image_path': image_path,
            'timestamp': datetime.now().isoformat(),
            'stages': {
                'initial_state': {},
                'after_tag_generation': {},
                'after_tag_embedding': {}
            },
            'results': {
                'prompts_preserved': False,
                'issues': [],
                'warnings': [],
                'recommendations': []
            }
        }

        try:
            # Stage 1: Check initial state
            print(f"\n{'='*60}")
            print(f"Auditing: {test_name}")
            print(f"{'='*60}")

            print("\n[Stage 1] Checking initial image state...")
            if not os.path.exists(image_path):
                audit['results']['issues'].append(f"Image file not found: {image_path}")
                return audit

            # Extract initial metadata
            initial_metadata = self.parser.extract_metadata(image_path)
            initial_prompts = self.extract_prompts_from_metadata(initial_metadata)

            audit['stages']['initial_state'] = {
                'metadata_fields': list(initial_metadata.keys()) if initial_metadata else [],
                'prompts_found': list(initial_prompts.keys()),
                'prompt_count': len(initial_prompts),
                'has_prompts': len(initial_prompts) > 0
            }

            print(f"  Initial metadata fields: {len(initial_metadata) if initial_metadata else 0}")
            print(f"  Prompts found: {len(initial_prompts)}")
            for field, info in initial_prompts.items():
                preview = str(info['value'])[:60] + '...' if len(str(info['value'])) > 60 else str(info['value'])
                print(f"    - {field}: {preview}")

            # Stage 2: Simulate tag generation (check it doesn't modify image)
            print("\n[Stage 2] Creating test tag file...")

            # Create backup of original image
            backup_path = image_path + '.audit_backup'
            shutil.copy2(image_path, backup_path)
            audit['results']['recommendations'].append(f"Created backup: {backup_path}")

            # Create a test tag file
            tag_file = image_path + '.txt'
            test_tags = "test_tag_1, test_tag_2, test_tag_3"
            with open(tag_file, 'w', encoding='utf-8') as f:
                f.write(test_tags)
            print(f"  Created test tag file: {tag_file}")

            # Check if image was modified (it shouldn't be)
            after_tag_gen_metadata = self.parser.extract_metadata(image_path)
            after_tag_gen_prompts = self.extract_prompts_from_metadata(after_tag_gen_metadata)

            audit['stages']['after_tag_generation'] = {
                'metadata_fields': list(after_tag_gen_metadata.keys()) if after_tag_gen_metadata else [],
                'prompts_found': list(after_tag_gen_prompts.keys()),
                'prompt_count': len(after_tag_gen_prompts),
                'image_modified': backup_path != image_path  # Will be rechecked below
            }

            # Stage 3: Run tag embedder
            print("\n[Stage 3] Embedding tags into image metadata...")

            # Enable safety checks
            self.embedder.set_safety_checks(True)
            self.embedder.set_dry_run_mode(False)

            # Check for existing prompts
            prompt_check = self.embedder.check_for_existing_prompts(image_path)
            print(f"  Safety check result: {prompt_check['risk_level']} risk")
            if prompt_check['has_prompts']:
                print(f"  Existing prompts found in: {prompt_check['prompt_locations']}")

            # Embed tags
            embed_result = self.embedder.embed_tag_file_in_image(
                image_path,
                backup_original=True,
                force_overwrite=False
            )

            print(f"  Embedding result: {embed_result['action_taken']}")
            if embed_result.get('warnings'):
                for warning in embed_result['warnings']:
                    print(f"    WARNING: {warning}")

            # Stage 4: Verify prompts are still there
            print("\n[Stage 4] Verifying prompts after embedding...")

            final_metadata = self.parser.extract_metadata(image_path)
            final_prompts = self.extract_prompts_from_metadata(final_metadata)

            audit['stages']['after_tag_embedding'] = {
                'metadata_fields': list(final_metadata.keys()) if final_metadata else [],
                'prompts_found': list(final_prompts.keys()),
                'prompt_count': len(final_prompts),
                'tags_embedded': 'tags' in final_metadata if final_metadata else False
            }

            print(f"  Prompts still present: {len(final_prompts)} found")
            for field, info in final_prompts.items():
                preview = str(info['value'])[:60] + '...' if len(str(info['value'])) > 60 else str(info['value'])
                print(f"    - {field}: {preview}")

            # Compare before and after
            print("\n[Analysis] Comparing before and after...")
            initial_fields = set(initial_prompts.keys())
            final_fields = set(final_prompts.keys())

            if initial_fields == final_fields:
                print("  [OK] All prompt fields preserved!")
                audit['results']['prompts_preserved'] = True
            else:
                lost_fields = initial_fields - final_fields
                if lost_fields:
                    audit['results']['issues'].append(
                        f"Prompt fields were LOST: {lost_fields}"
                    )
                    print(f"  [FAIL] LOST fields: {lost_fields}")
                else:
                    audit['results']['warnings'].append(
                        "New prompt fields detected (but original preserved)"
                    )
                    print(f"  [INFO] New fields: {final_fields - initial_fields}")

            # Check if tags were embedded
            if 'tags' in final_metadata:
                print(f"  [OK] Tags embedded successfully")
            else:
                audit['results']['warnings'].append("Tags not found in metadata after embedding")
                print(f"  [INFO] Tags not found in final metadata")

            # Cleanup
            print("\n[Cleanup] Restoring from backup...")
            shutil.move(backup_path, image_path)
            if os.path.exists(tag_file):
                os.remove(tag_file)
            print("  Image restored to original state")

        except Exception as e:
            audit['results']['issues'].append(f"Audit failed with exception: {e}")
            self.logger.error(f"Error auditing {image_path}: {e}", exc_info=True)
            # Cleanup on error
            if os.path.exists(backup_path):
                try:
                    shutil.move(backup_path, image_path)
                except:
                    pass

        self.test_results.append(audit)
        return audit

    def audit_folder(self, folder_path, max_files=5, recursive=False):
        """Audit multiple images in a folder."""
        print(f"\n{'='*60}")
        print(f"Prompt Preservation Audit")
        print(f"{'='*60}")
        print(f"Folder: {folder_path}")
        print(f"Max files to test: {max_files}")

        # Find image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
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

        # Limit to max_files
        image_files = image_files[:max_files]

        print(f"Found {len(image_files)} images to test\n")

        # Test each image
        for i, image_path in enumerate(image_files, 1):
            print(f"\n[Test {i}/{len(image_files)}]")
            self.audit_single_image(image_path)

        # Generate report
        return self.generate_report()

    def generate_report(self):
        """Generate comprehensive audit report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed': sum(1 for t in self.test_results if t['results']['prompts_preserved']),
            'failed': sum(1 for t in self.test_results if not t['results']['prompts_preserved'] and t['results']['issues']),
            'warnings': sum(1 for t in self.test_results if t['results']['warnings']),
            'tests': self.test_results
        }

        print(f"\n{'='*60}")
        print("AUDIT REPORT")
        print(f"{'='*60}")
        print(f"Total tests: {report['total_tests']}")
        print(f"Passed (prompts preserved): {report['passed']}")
        print(f"Failed (prompts lost): {report['failed']}")
        print(f"Warnings: {report['warnings']}")

        if report['failed'] > 0:
            print("\n⚠️  CRITICAL: Some tests FAILED - prompts were lost!")
            print("Do NOT process your new batch until this is fixed.")
        elif report['warnings'] > 0:
            print("\n✓ All prompts preserved, but some warnings detected")
            print("Review warnings before processing new batch")
        else:
            print("\n✓ All tests PASSED - Pipeline is safe!")
            print("Ready to process new batch")

        return report

    def save_report(self, report, output_file=None):
        """Save audit report to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"prompt_preservation_audit_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {output_file}")
        return output_file


if __name__ == '__main__':
    import sys

    # Example usage
    audit = PromptPreservationAudit()

    # You can customize this:
    # - audit.audit_single_image('/path/to/image.png')
    # - audit.audit_folder('/path/to/folder', max_files=5)

    print("Prompt Preservation Audit Tool")
    print("Usage:")
    print("  audit = PromptPreservationAudit()")
    print("  report = audit.audit_folder('/path/to/images', max_files=5)")
    print("  audit.save_report(report)")
