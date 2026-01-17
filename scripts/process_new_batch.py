"""
PHASE 2: Process New Batch

Comprehensive script for processing a new batch of images:
1. Generate CLIP tags for all images
2. Extract descriptive tags from prompts (deduplicated)
3. Embed tags into image metadata (preserving original prompts)
4. Verify prompt preservation on sample
5. Add to frequency database for analysis

This is the critical step before re-sorting the entire collection.
All operations are safe: prompts are preserved, tags go to .txt files first.
"""

import os
import sys
import json
from datetime import datetime
from tag_generator import DescriptiveTagGenerator
from tag_extractor_v2 import TagExtractorV2 as TagExtractor
from tag_embedder import TagEmbedder
from prompt_preservation_audit import PromptPreservationAudit
from tag_frequency_database import TagFrequencyDatabase


class NewBatchProcessor:
    """Process a new batch of images through complete pipeline."""

    def __init__(self, batch_folder, output_dir='./processed_batches'):
        """
        Initialize batch processor.

        Args:
            batch_folder: Path to folder with new images
            output_dir: Where to store processing logs and reports
        """
        self.batch_folder = batch_folder
        self.output_dir = output_dir
        self.logger_file = os.path.join(output_dir, f"batch_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Initialize components
        self.tag_generator = DescriptiveTagGenerator()
        self.tag_extractor = TagExtractor()
        self.tag_embedder = TagEmbedder()
        self.audit = PromptPreservationAudit()
        self.frequency_db = TagFrequencyDatabase()

        self.log_file = open(self.logger_file, 'w', encoding='utf-8')

    def log(self, message):
        """Log message to both console and file."""
        print(message)
        self.log_file.write(message + '\n')
        self.log_file.flush()

    def find_images(self):
        """Find all images in batch folder."""
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
        images = []

        for root, dirs, files in os.walk(self.batch_folder):
            for file in files:
                if os.path.splitext(file)[1].lower() in image_extensions:
                    images.append(os.path.join(root, file))

        return images

    def process_phase_2a_generate_tags(self, images, progress_callback=None):
        """
        Phase 2.1: Generate CLIP tags for all images.

        Returns: dict with generation statistics
        """
        self.log("\n" + "="*70)
        self.log("PHASE 2.1: GENERATING CLIP TAGS")
        self.log("="*70)

        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'total_tags_generated': 0
        }

        for i, image_path in enumerate(images):
            try:
                tag_result = self.tag_generator.generate_tags_for_image(image_path)

                results['processed'] += 1

                if tag_result['status'] == 'success':
                    results['success'] += 1
                    results['total_tags_generated'] += tag_result['tag_count']

                    if (i + 1) % 100 == 0:
                        self.log(f"  [{i+1}/{len(images)}] Progress: {results['success']} successful")
                else:
                    results['failed'] += 1

                if progress_callback:
                    progress_callback(i + 1, len(images))

            except Exception as e:
                results['failed'] += 1
                self.log(f"  ERROR processing {image_path}: {e}")

        self.log(f"\nGenerated tags complete:")
        self.log(f"  Processed: {results['processed']}")
        self.log(f"  Successful: {results['success']}")
        self.log(f"  Failed: {results['failed']}")
        self.log(f"  Total tags: {results['total_tags_generated']}")

        return results

    def process_phase_2b_extract_all_tags(self, images):
        """
        Phase 2.2: Extract tags from prompts + CLIP (deduplicated).

        Returns: dict with extraction statistics
        """
        self.log("\n" + "="*70)
        self.log("PHASE 2.2: EXTRACTING AND DEDUPLICATING TAGS")
        self.log("="*70)

        results = {
            'processed': 0,
            'extracted': 0,
            'from_clip': 0,
            'from_prompt': 0,
            'deduplicated': 0
        }

        for i, image_path in enumerate(images):
            try:
                extract_result = self.tag_extractor.extract_tags_from_image(image_path)

                if extract_result['status'] == 'success':
                    results['processed'] += 1
                    results['extracted'] += len(extract_result['tags'])

                    sources = extract_result['sources']
                    results['from_clip'] += len(sources['clip'])
                    results['from_prompt'] += len(sources['prompt'])
                    results['deduplicated'] += len(sources['both'])

                    if (i + 1) % 500 == 0:
                        self.log(f"  [{i+1}/{len(images)}] Extracted: {results['extracted']} tags, "
                                f"Dedup: {results['deduplicated']}")

            except Exception as e:
                self.log(f"  ERROR extracting from {image_path}: {e}")

        self.log(f"\nExtraction complete:")
        self.log(f"  Images processed: {results['processed']}")
        self.log(f"  Total tags: {results['extracted']}")
        self.log(f"  From CLIP only: {results['from_clip']}")
        self.log(f"  From prompt only: {results['from_prompt']}")
        self.log(f"  Deduplicated (both sources): {results['deduplicated']}")

        return results

    def process_phase_2c_embed_tags(self, images):
        """
        Phase 2.3: Embed tags into image metadata.

        Returns: dict with embedding statistics
        """
        self.log("\n" + "="*70)
        self.log("PHASE 2.3: EMBEDDING TAGS INTO METADATA")
        self.log("="*70)

        self.tag_embedder.set_safety_checks(True)
        self.tag_embedder.set_dry_run_mode(False)

        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'backups_created': 0,
            'prompts_preserved': 0,
            'high_risk': 0
        }

        for i, image_path in enumerate(images):
            try:
                # Check for existing prompts
                prompt_check = self.tag_embedder.check_for_existing_prompts(image_path)

                if prompt_check.get('has_prompts'):
                    results['prompts_preserved'] += 1
                    if prompt_check.get('risk_level') == 'high':
                        results['high_risk'] += 1

                # Embed tags
                embed_result = self.tag_embedder.embed_tag_file_in_image(
                    image_path,
                    backup_original=True,
                    force_overwrite=False
                )

                results['processed'] += 1

                if embed_result.get('success'):
                    results['success'] += 1

                if embed_result.get('backup_created'):
                    results['backups_created'] += 1

                if (i + 1) % 500 == 0:
                    self.log(f"  [{i+1}/{len(images)}] Embedded: {results['success']} success")

            except Exception as e:
                results['failed'] += 1
                self.log(f"  ERROR embedding {image_path}: {e}")

        self.log(f"\nEmbedding complete:")
        self.log(f"  Processed: {results['processed']}")
        self.log(f"  Successful: {results['success']}")
        self.log(f"  Failed: {results['failed']}")
        self.log(f"  Backups created: {results['backups_created']}")
        self.log(f"  Images with existing prompts: {results['prompts_preserved']}")
        self.log(f"  High-risk embeddings: {results['high_risk']}")

        return results

    def process_phase_2d_verify_preservation(self, images, sample_size=10):
        """
        Phase 2.4: Verify prompt preservation on sample.

        Returns: dict with verification results
        """
        self.log("\n" + "="*70)
        self.log(f"PHASE 2.4: VERIFYING PROMPT PRESERVATION (sample: {sample_size} images)")
        self.log("="*70)

        # Select random sample
        import random
        sample = random.sample(images, min(sample_size, len(images)))

        results = {
            'tested': 0,
            'preserved': 0,
            'issues': []
        }

        for image_path in sample:
            audit_result = self.audit.audit_single_image(image_path, os.path.basename(image_path))

            results['tested'] += 1

            if audit_result['results']['prompts_preserved']:
                results['preserved'] += 1
            elif audit_result['results']['issues']:
                results['issues'].extend(audit_result['results']['issues'])

        self.log(f"\nVerification complete:")
        self.log(f"  Tested: {results['tested']} images")
        self.log(f"  Preserved: {results['preserved']}")

        if results['issues']:
            self.log(f"  ISSUES FOUND: {len(results['issues'])}")
            for issue in results['issues'][:5]:
                self.log(f"    - {issue}")

        return results

    def process_complete_batch(self):
        """
        Execute complete Phase 2 pipeline.

        Returns: Overall summary
        """
        self.log("="*70)
        self.log("PHASE 2: PROCESS NEW BATCH")
        self.log("="*70)
        self.log(f"Batch folder: {self.batch_folder}")
        self.log(f"Started: {datetime.now().isoformat()}")

        # Find images
        self.log("\nScanning for images...")
        images = self.find_images()
        self.log(f"Found {len(images)} images to process")

        if not images:
            self.log("ERROR: No images found in batch folder")
            return None

        # Execute phases
        results = {
            'phase_2a': self.process_phase_2a_generate_tags(images),
            'phase_2b': self.process_phase_2b_extract_all_tags(images),
            'phase_2c': self.process_phase_2c_embed_tags(images),
            'phase_2d': self.process_phase_2d_verify_preservation(images, sample_size=10)
        }

        self.log("\n" + "="*70)
        self.log("PHASE 2 COMPLETE")
        self.log("="*70)
        self.log(f"Completed: {datetime.now().isoformat()}")
        self.log(f"Log file: {self.logger_file}")

        # Save results
        results_file = os.path.join(self.output_dir, f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        self.log(f"Results saved to: {results_file}")

        self.log_file.close()

        return results


def main():
    """Main entry point."""
    batch_folder = r"H:\Development\image_grid_sorter\sorted_txt2img-images\1"

    print("\n" + "="*70)
    print("PHASE 2: PROCESS NEW BATCH")
    print("="*70)
    print(f"Batch folder: {batch_folder}")
    print("="*70)

    try:
        processor = NewBatchProcessor(batch_folder)
        results = processor.process_complete_batch()

        if results:
            print("\n[SUCCESS] Batch processing complete")
            print(f"Check log file for details: {processor.logger_file}")
        else:
            print("\n[FAILED] Batch processing failed")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
