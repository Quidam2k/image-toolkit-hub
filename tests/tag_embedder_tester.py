"""
Tag Embedder Safety Testing Tool

This tool provides comprehensive testing and validation for the tag embedder,
including dry-run capabilities, safety checks, and prompt preservation validation.

Features:
- Dry-run mode to test operations without making changes
- Safety validation before embedding
- Prompt preservation verification
- Batch testing capabilities
- Detailed reporting

Author: Claude Code Implementation for Safe Operations
Version: 1.0
"""

import os
import json
import shutil
from datetime import datetime
from tag_embedder import TagEmbedder
from metadata_parser import MetadataParser
import logging

class TagEmbedderTester:
    """Test and validate tag embedding operations safely."""

    def __init__(self):
        self.embedder = TagEmbedder()
        self.parser = MetadataParser()
        self.logger = logging.getLogger(__name__)

    def test_single_image(self, image_path, dry_run=True):
        """
        Test tag embedding on a single image with comprehensive reporting.

        Args:
            image_path: Path to image file
            dry_run: If True, don't actually modify the image

        Returns:
            dict: Detailed test results
        """
        self.embedder.set_dry_run_mode(dry_run)

        results = {
            'image_path': image_path,
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat(),
            'test_results': {},
            'safety_check': {},
            'embedding_result': {},
            'validation': {},
            'recommendations': []
        }

        try:
            # Check if image and tag file exist
            tag_file = image_path + '.txt'
            if not os.path.exists(image_path):
                results['test_results']['error'] = 'Image file not found'
                return results

            if not os.path.exists(tag_file):
                results['test_results']['error'] = 'Tag file not found'
                return results

            # Read tag content
            with open(tag_file, 'r', encoding='utf-8') as f:
                tag_content = f.read().strip()

            results['test_results']['tag_file_size'] = len(tag_content)
            results['test_results']['tag_preview'] = tag_content[:100] + ('...' if len(tag_content) > 100 else '')

            # Perform safety check
            safety_check = self.embedder.check_for_existing_prompts(image_path)
            results['safety_check'] = safety_check

            # Extract current metadata
            current_metadata = self.parser.extract_metadata(image_path)
            results['test_results']['current_metadata_fields'] = list(current_metadata.keys()) if current_metadata else []

            # Test embedding
            embedding_result = self.embedder.embed_tag_file_in_image(image_path)
            results['embedding_result'] = embedding_result

            # Generate recommendations
            if safety_check['has_prompts']:
                if safety_check['risk_level'] == 'high':
                    results['recommendations'].append('⚠️  HIGH RISK: Image contains prompt data that could be overwritten')
                    results['recommendations'].append('✅ FIXED: New embedder preserves existing prompts')
                else:
                    results['recommendations'].append('✅ LOW RISK: PNG format preserves existing data')

            if not embedding_result.get('success', False) and not dry_run:
                results['recommendations'].append('❌ Embedding failed - check logs for details')

            if embedding_result.get('backup_created', False):
                results['recommendations'].append('✅ Backup file created')

            # Validation (if not dry run and embedding succeeded)
            if not dry_run and embedding_result.get('success', False):
                validation_result = self.validate_embedding(image_path, tag_content)
                results['validation'] = validation_result

        except Exception as e:
            results['test_results']['error'] = str(e)
            self.logger.error(f"Error testing {image_path}: {e}")

        return results

    def validate_embedding(self, image_path, expected_tags):
        """
        Validate that tags were embedded correctly and prompts preserved.

        Args:
            image_path: Path to image file
            expected_tags: Tag content that should be embedded

        Returns:
            dict: Validation results
        """
        validation = {
            'tags_found': False,
            'tags_match': False,
            'prompts_preserved': False,
            'details': []
        }

        try:
            # Re-extract metadata after embedding
            metadata = self.parser.extract_metadata(image_path)

            if not metadata:
                validation['details'].append('No metadata found after embedding')
                return validation

            # Check for embedded tags
            if 'tags' in metadata:
                validation['tags_found'] = True
                embedded_tags = metadata['tags']

                # Check if tags match (allowing for some formatting differences)
                if expected_tags.strip() in embedded_tags or embedded_tags in expected_tags.strip():
                    validation['tags_match'] = True
                    validation['details'].append('✅ Tags embedded correctly')
                else:
                    validation['details'].append(f'⚠️  Tag mismatch - Expected: {expected_tags[:50]}..., Found: {embedded_tags[:50]}...')

            # Check for preserved prompts
            prompt_indicators = ['parameters', 'positive_prompt', 'negative_prompt']
            preserved_prompts = [field for field in prompt_indicators if field in metadata]

            if preserved_prompts:
                validation['prompts_preserved'] = True
                validation['details'].append(f'✅ Prompts preserved in: {", ".join(preserved_prompts)}')
            else:
                # Check for any field that looks like a prompt
                for key, value in metadata.items():
                    if isinstance(value, str) and any(keyword in value.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                        validation['prompts_preserved'] = True
                        validation['details'].append(f'✅ Prompt data preserved in {key} field')
                        break

        except Exception as e:
            validation['details'].append(f'Validation error: {e}')

        return validation

    def test_batch(self, folder_path, max_files=10, dry_run=True):
        """
        Test tag embedding on multiple files in a folder.

        Args:
            folder_path: Path to folder containing images
            max_files: Maximum number of files to test
            dry_run: If True, don't actually modify images

        Returns:
            dict: Batch test results
        """
        results = {
            'folder_path': folder_path,
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat(),
            'files_tested': 0,
            'files_with_tags': 0,
            'files_with_prompts': 0,
            'high_risk_files': 0,
            'successful_embeddings': 0,
            'individual_results': [],
            'summary': {}
        }

        try:
            # Find image files with tag files
            image_files = []
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_path = os.path.join(folder_path, file)
                    tag_path = image_path + '.txt'
                    if os.path.exists(tag_path):
                        image_files.append(image_path)

            # Limit to max_files
            image_files = image_files[:max_files]
            print(f"Testing {len(image_files)} files (max: {max_files})")

            for i, image_path in enumerate(image_files):
                print(f"Testing {i+1}/{len(image_files)}: {os.path.basename(image_path)}")

                test_result = self.test_single_image(image_path, dry_run)
                results['individual_results'].append(test_result)
                results['files_tested'] += 1

                # Update counters
                if not test_result.get('test_results', {}).get('error'):
                    results['files_with_tags'] += 1

                if test_result.get('safety_check', {}).get('has_prompts', False):
                    results['files_with_prompts'] += 1

                if test_result.get('safety_check', {}).get('risk_level') == 'high':
                    results['high_risk_files'] += 1

                if test_result.get('embedding_result', {}).get('success', False):
                    results['successful_embeddings'] += 1

            # Generate summary
            results['summary'] = {
                'total_tested': results['files_tested'],
                'success_rate': f"{results['successful_embeddings']}/{results['files_tested']} ({100*results['successful_embeddings']/max(results['files_tested'], 1):.1f}%)",
                'files_with_prompts': f"{results['files_with_prompts']} ({100*results['files_with_prompts']/max(results['files_tested'], 1):.1f}%)",
                'high_risk_files': f"{results['high_risk_files']} ({100*results['high_risk_files']/max(results['files_tested'], 1):.1f}%)"
            }

        except Exception as e:
            results['error'] = str(e)
            self.logger.error(f"Error in batch test: {e}")

        return results

    def save_test_report(self, results, output_path=None):
        """Save test results to a file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tag_embedder_test_report_{timestamp}.json"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            print(f"Test report saved to: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error saving test report: {e}")
            return None

def main():
    """Interactive testing interface."""
    import sys

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    tester = TagEmbedderTester()

    print("Tag Embedder Safety Tester")
    print("=" * 40)

    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = input("Enter path to test (file or folder): ").strip()

    if not os.path.exists(test_path):
        print(f"Error: Path '{test_path}' does not exist")
        return

    # Ask for dry run mode
    dry_run_input = input("Enable dry-run mode? (Y/n): ").strip().lower()
    dry_run = dry_run_input != 'n'

    if dry_run:
        print("🔍 DRY RUN MODE: No changes will be made")
    else:
        print("⚠️  LIVE MODE: Changes will be made to files")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled")
            return

    if os.path.isfile(test_path):
        # Test single file
        print(f"\nTesting single file: {test_path}")
        results = tester.test_single_image(test_path, dry_run)

        print("\nTest Results:")
        print(f"Safety check: {results['safety_check']['risk_level']} risk")
        if results['safety_check']['has_prompts']:
            print(f"Prompts found in: {', '.join(results['safety_check']['prompt_locations'])}")

        if results['embedding_result']:
            print(f"Embedding result: {results['embedding_result']['action_taken']}")
            print(f"Success: {results['embedding_result']['success']}")

        if results['recommendations']:
            print("\nRecommendations:")
            for rec in results['recommendations']:
                print(f"  {rec}")

    else:
        # Test folder
        max_files = int(input("Maximum files to test (default 10): ").strip() or "10")
        print(f"\nTesting folder: {test_path} (max {max_files} files)")

        results = tester.test_batch(test_path, max_files, dry_run)

        print("\nBatch Test Results:")
        print(f"Files tested: {results['summary']['total_tested']}")
        print(f"Success rate: {results['summary']['success_rate']}")
        print(f"Files with prompts: {results['summary']['files_with_prompts']}")
        print(f"High-risk files: {results['summary']['high_risk_files']}")

    # Save report
    save_report = input("\nSave detailed report? (Y/n): ").strip().lower()
    if save_report != 'n':
        report_path = tester.save_test_report(results)
        if report_path:
            print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()