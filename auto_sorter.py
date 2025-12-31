"""
AutoSorter Module for Image Grid Sorter

This module provides comprehensive image sorting functionality based on metadata content,
including support for multi-tag sorting and re-sorting of existing collections.

Key Features:
- Multi-tag sorting with configurable strategies (single, multi, smart_combination, all_combinations)
- Progress tracking with pause/resume/cancel capabilities
- Comprehensive error handling and categorization
- Re-sorting of existing auto-sorted images with updated rules
- File movement tracking for undo operations
- Detailed statistics and reporting

Author: Claude Code Implementation
Version: 2.1 (Added re-sort functionality)
"""

import os
import shutil
import threading
import logging
import time
from pathlib import Path
from metadata_parser import MetadataParser
from undo_manager import UndoManager
from visual_classifier import (
    VisualClassifier, VisualClassification,
    ShotType, PersonCount, NSFWRating, LoRASortingProfile
)


# Companion file extensions to move/copy alongside images
COMPANION_EXTENSIONS = ['.txt', '.json', '.yaml', '.yml']

class AutoSorter:
    """
    Automatically sort images based on metadata content using configurable term matching.
    
    This class handles both initial sorting and re-sorting operations with support for
    multiple destination strategies, progress tracking, and comprehensive error handling.
    
    Attributes:
        config_manager: Configuration management instance
        metadata_parser: Metadata extraction and parsing instance
        progress_callback: Optional callback for progress updates
        cancelled: Flag indicating if current operation was cancelled
        paused: Flag indicating if current operation is paused
        logger: Logging instance for operation tracking
    """
    
    def __init__(self, config_manager, progress_callback=None):
        self.config_manager = config_manager
        self.metadata_parser = MetadataParser()
        self.progress_callback = progress_callback
        self.cancelled = False
        self.paused = False
        self._pause_event = threading.Event()  # For efficient pause waiting
        self._pause_event.set()  # Not paused initially
        self.logger = logging.getLogger(__name__)
        self.undo_manager = UndoManager(max_history=50)

    def check_disk_space(self, image_files, destination_folder=None):
        """
        Check if there's enough disk space for the operation.

        Args:
            image_files: List of image files to process
            destination_folder: Destination folder (uses auto_sorted if None)

        Returns:
            (success, error_message) tuple
        """
        if not destination_folder:
            destination_folder = self.config_manager.sorted_folders.get('auto_sorted')

        if not destination_folder or not os.path.exists(destination_folder):
            return True, None  # Can't check, assume OK

        try:
            # Calculate total size of files
            total_size = 0
            for image_file in image_files:
                if os.path.exists(image_file):
                    total_size += os.path.getsize(image_file)

            # Get free space
            free_space = shutil.disk_usage(destination_folder).free

            # Apply safety margin (10% extra)
            required_space = total_size * 1.1

            if required_space > free_space:
                free_gb = free_space / (1024 ** 3)
                required_gb = required_space / (1024 ** 3)
                error_msg = (
                    f"Insufficient disk space: need {required_gb:.2f} GB, "
                    f"only {free_gb:.2f} GB available"
                )
                return False, error_msg

            return True, None

        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return True, None  # Log error but allow operation
    
    def sort_by_metadata(self, image_files, terms=None):
        """
        Sort a list of images based on configured metadata terms.

        This is the main sorting method that processes images according to the current
        multi-tag mode and term configurations. Supports progress callbacks and
        comprehensive error tracking.

        Args:
            image_files (list): List of image file paths to sort
            terms (list, optional): Override terms to use. If None, uses configured terms.

        Returns:
            dict: Detailed results including:
                - processed: Number of images processed
                - sorted: Number of images successfully sorted
                - errors: List of error messages
                - term_counts: Dictionary of matches per term
                - unmatched: Number of unmatched images
                - unmatched_files: List of unmatched file paths
                - file_movements: List of all file operations for undo
                - timestamp: When operation started
                - error_categories: Categorized error counts
        """
        # Reset operation state for new sort
        self.cancelled = False
        self.paused = False
        self._pause_event.set()  # Not paused initially

        if terms is None:
            terms = self.config_manager.get_auto_sort_terms()

        if not terms:
            self.logger.warning("No auto-sort terms configured")
            return {'processed': 0, 'sorted': 0, 'errors': []}

        # Check disk space before starting
        success, error_msg = self.check_disk_space(image_files)
        if not success:
            self.logger.error(f"Disk space check failed: {error_msg}")
            return {
                'processed': 0,
                'sorted': 0,
                'errors': [error_msg]
            }
        
        results = {
            'processed': 0,
            'sorted': 0,
            'errors': [],
            'term_counts': {},
            'unmatched': 0,
            'unmatched_files': [],  # Track files that were unmatched
            'file_movements': [],  # Track all file movements for undo
            'timestamp': time.time(),  # When auto-sort started
            'error_categories': {
                'no_metadata': 0,
                'file_access': 0,
                'destination_error': 0,
                'unknown': 0
            }
        }
        
        total_images = len(image_files)
        
        for i, image_file in enumerate(image_files):
            if self.cancelled:
                break

            # Wait if paused (uses efficient Event.wait instead of polling)
            self._pause_event.wait()
            
            try:
                result = self.process_image(image_file, terms)
                results['processed'] += 1
                
                if result['sorted']:
                    # Handle multi-tag results
                    sorted_count = result.get('sorted_count', 1)
                    results['sorted'] += sorted_count
                    
                    # Update term counts for all destinations
                    if result.get('destinations'):
                        for dest in result['destinations']:
                            folder_name = dest.get('folder_name', '')
                            if folder_name:
                                results['term_counts'][folder_name] = results['term_counts'].get(folder_name, 0) + 1
                    else:
                        # Backward compatibility - single term
                        term = result.get('term', '')
                        if term:
                            results['term_counts'][term] = results['term_counts'].get(term, 0) + 1
                    
                    # Track file movements for undo (handle multiple movements)
                    if result.get('movements'):
                        results['file_movements'].extend(result['movements'])
                    elif result.get('movement'):
                        results['file_movements'].append(result['movement'])
                else:
                    results['unmatched'] += 1
                
                # Track unmatched files separately (not errors)
                if result.get('unmatched'):
                    results['unmatched_files'].append({
                        'file': image_file,
                        'debug_info': result.get('debug_info', '')
                    })
                
                if result.get('error'):
                    # Track processing errors separately
                    error_category = result.get('error_category', 'unknown')
                    results['error_categories'][error_category] += 1
                    
                    error_entry = {
                        'file': image_file,
                        'error': result['error'],
                        'category': error_category
                    }
                    
                    if result.get('debug_info'):
                        error_entry['debug'] = result['debug_info']
                    
                    results['errors'].append(error_entry)
                    print(f"AUTO-SORT ERROR [{error_category}]: {os.path.basename(image_file)} - {result['error']}")
                    if result.get('debug_info'):
                        print(f"  DEBUG: {result['debug_info']}")
                
                # Update progress
                if self.progress_callback:
                    self.progress_callback(i + 1, total_images, os.path.basename(image_file))
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {image_file}: {e}"
                self.logger.error(error_msg)
                print(f"AUTO-SORT ERROR: {error_msg}")  # Console output for debugging
                results['errors'].append({
                    'file': image_file,
                    'error': str(e)
                })
                
                # Update progress even on error
                results['processed'] += 1
                if self.progress_callback:
                    self.progress_callback(i + 1, total_images, f"ERROR: {os.path.basename(image_file)}",
                                         processed=results['processed'], sorted=results['sorted'],
                                         errors=len(results['errors']))

        # Record operation for undo capability
        if results.get('file_movements'):
            operation_name = f"Auto-Sort: {results['sorted']} images ({results['processed']} processed)"
            self.undo_manager.record_operation(
                results['file_movements'],
                operation_name,
                metadata={'term_counts': results.get('term_counts', {})}
            )

        return results
    
    def process_image(self, image_path, terms):
        """Process a single image for auto-sorting."""
        result = {
            'sorted': False,
            'term': None,
            'destination': None,
            'error': None
        }
        
        try:
            # Extract metadata
            metadata = self.metadata_parser.extract_metadata(image_path)
            
            if not metadata:
                result['error'] = "No metadata found"
                result['error_category'] = 'no_metadata'
                
                # Debug: check if file exists and basic info
                if os.path.exists(image_path):
                    file_size = os.path.getsize(image_path)
                    file_ext = os.path.splitext(image_path)[1].lower()
                    result['debug_info'] = f"File exists, size: {file_size}, ext: {file_ext}"
                    
                    # Check if companion tag file exists
                    tag_file = image_path + '.txt'
                    if os.path.exists(tag_file):
                        try:
                            with open(tag_file, 'r', encoding='utf-8') as f:
                                tag_content = f.read().strip()
                            result['debug_info'] += f", tag file: {len(tag_content)} chars"
                        except Exception as e:
                            result['debug_info'] += f", tag file error: {e}"
                    else:
                        result['debug_info'] += ", no tag file"
                else:
                    result['debug_info'] = "File does not exist"
                    
                return result
            
            # Find matching terms
            matches = self.metadata_parser.search_terms_in_metadata(metadata, terms)
            
            if not matches:
                # Handle no matches according to configuration
                settings = self.config_manager.get_auto_sort_settings()
                if settings.get('handle_no_matches') == 'move_to_unmatched':
                    result = self.sort_to_unmatched(image_path)
                else:
                    # Not an error - just unmatched (left in place)
                    result['sorted'] = False
                    result['unmatched'] = True
                    
                    # Debug: show what metadata was found for troubleshooting
                    debug_fields = []
                    for key, value in metadata.items():
                        if isinstance(value, str) and len(value) > 0:
                            preview = value[:100] + "..." if len(value) > 100 else value
                            debug_fields.append(f"{key}: {preview}")
                    result['debug_info'] = f"Metadata found: {', '.join(debug_fields[:3])}"
                    
                return result
            
            # Handle multiple matches with new multi-tag logic
            result = self.sort_with_multi_tag_logic(image_path, matches)
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error processing {image_path}: {e}")
        
        return result
    
    def sort_with_multi_tag_logic(self, image_path, matching_terms):
        """Sort image using new multi-tag logic with companion file support."""
        # Get destination strategy from config manager
        destination_info = self.config_manager.get_multi_tag_destinations(matching_terms)
        destinations = destination_info['destinations']
        strategy = destination_info['strategy']

        if not destinations:
            return {
                'sorted': False,
                'error': "No valid destinations found",
                'unmatched': True
            }

        # Check copy vs move preference
        settings = self.config_manager.get_auto_sort_settings()
        use_copy_mode = settings.get('copy_instead_of_move', False)

        # Pre-create all destination folders (optimization)
        all_dest_paths = set(d['path'] for d in destinations if d.get('path'))
        for dest_path in all_dest_paths:
            try:
                os.makedirs(dest_path, exist_ok=True)
            except Exception as e:
                self.logger.warning(f"Could not pre-create {dest_path}: {e}")

        # Track all movements for undo
        all_movements = []
        sorted_count = 0
        first_destination = None  # Track where the file ends up first (for subsequent copies)
        errors = []

        for i, dest_info in enumerate(destinations):
            dest_path = dest_info['path']
            if not dest_path:
                continue

            try:
                # Generate destination filename
                filename = os.path.basename(image_path)
                full_dest_path = os.path.join(dest_path, filename)

                # Handle file naming conflicts
                full_dest_path = self.handle_naming_conflict(full_dest_path)

                # Determine operation based on settings and position
                if use_copy_mode:
                    # Copy mode: always copy from original source
                    self.copy_with_companions(image_path, full_dest_path)
                    operation = 'copy'
                    source_path = image_path
                elif i == 0:
                    # Move mode, first destination: move the original
                    self.move_with_companions(image_path, full_dest_path)
                    operation = 'move'
                    source_path = image_path
                    first_destination = full_dest_path
                else:
                    # Move mode, subsequent destinations: copy from first destination
                    copy_source = first_destination if first_destination else image_path
                    if os.path.exists(copy_source):
                        self.copy_with_companions(copy_source, full_dest_path)
                        operation = 'copy'
                        source_path = copy_source
                    else:
                        errors.append(f"Source file not found for destination {dest_info['folder_name']}")
                        continue

                # Track movement for undo
                movement_record = {
                    'operation': operation,
                    'source': source_path,
                    'destination': full_dest_path,
                    'term': dest_info.get('folder_name', ''),
                    'terms': [t['term'] for t in dest_info['terms']],
                    'dest_type': dest_info['type'],
                    'timestamp': time.time()
                }
                all_movements.append(movement_record)

                sorted_count += 1

            except Exception as e:
                error_msg = f"Error sorting to {dest_info['folder_name']}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Prepare result
        result = {
            'sorted': sorted_count > 0,
            'destinations': destinations,
            'sorted_count': sorted_count,
            'strategy': strategy,
            'movements': all_movements
        }

        if sorted_count > 0:
            # For backward compatibility, set 'term' to the primary destination
            primary_dest = destinations[0]
            result['term'] = primary_dest.get('folder_name', '')
            result['destination'] = primary_dest['path']

            # Set 'movement' for backward compatibility (first movement)
            if all_movements:
                result['movement'] = all_movements[0]

        if errors:
            result['errors'] = errors
            if sorted_count == 0:
                result['error'] = "; ".join(errors)

        return result
    
    def sort_to_term(self, image_path, term_config, track_movement=True):
        """Sort an image to a specific term folder."""
        result = {
            'sorted': False,
            'term': term_config['term'],
            'destination': None,
            'error': None,
            'movement': None
        }
        
        try:
            # Get destination folder
            dest_folder = self.config_manager.get_term_folder_path(term_config['term'])
            
            if not dest_folder:
                result['error'] = f"No folder configured for term: {term_config['term']}"
                return result
            
            # Ensure destination folder exists
            os.makedirs(dest_folder, exist_ok=True)
            
            # Generate destination filename
            filename = os.path.basename(image_path)
            dest_path = os.path.join(dest_folder, filename)
            
            # Handle file naming conflicts
            dest_path = self.handle_naming_conflict(dest_path)
            
            # Move or copy the file (with companion files)
            settings = self.config_manager.get_auto_sort_settings()
            operation = 'copy' if settings.get('copy_instead_of_move', False) else 'move'

            if operation == 'copy':
                self.copy_with_companions(image_path, dest_path)
            else:
                self.move_with_companions(image_path, dest_path)
            
            # Track movement for undo functionality
            if track_movement:
                movement_record = {
                    'operation': operation,
                    'source': image_path,
                    'destination': dest_path,
                    'term': term_config['term'],
                    'timestamp': time.time()
                }
                result['movement'] = movement_record
            
            result['sorted'] = True
            result['destination'] = dest_path
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error sorting {image_path} to term {term_config['term']}: {e}")
        
        return result
    
    def sort_to_unmatched(self, image_path):
        """Sort an image that doesn't match any terms to the unmatched folder."""
        result = {
            'sorted': False,
            'term': 'unmatched',
            'destination': None,
            'error': None
        }
        
        try:
            # Get unmatched folder (use top-level unmatched folder, not auto_sorted/unmatched)
            unmatched_folder = self.config_manager.sorted_folders.get('unmatched')
            if not unmatched_folder:
                result['error'] = "Unmatched folder not configured"
                return result
            
            os.makedirs(unmatched_folder, exist_ok=True)
            
            # Generate destination filename
            filename = os.path.basename(image_path)
            dest_path = os.path.join(unmatched_folder, filename)
            
            # Handle file naming conflicts
            dest_path = self.handle_naming_conflict(dest_path)
            
            # Move or copy the file (with companion files)
            settings = self.config_manager.get_auto_sort_settings()
            if settings.get('copy_instead_of_move', False):
                self.copy_with_companions(image_path, dest_path)
            else:
                self.move_with_companions(image_path, dest_path)

            result['sorted'] = True
            result['destination'] = dest_path

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error sorting {image_path} to unmatched: {e}")
        
        return result
    
    
    def handle_naming_conflict(self, dest_path):
        """Handle file naming conflicts by adding numeric suffix."""
        if not os.path.exists(dest_path):
            return dest_path

        base, ext = os.path.splitext(dest_path)
        counter = 1

        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{ext}"
            counter += 1

        return dest_path

    def get_companion_files(self, image_path):
        """
        Find all companion files for an image (e.g., .txt tag files).

        Args:
            image_path: Path to the image file

        Returns:
            List of paths to companion files that exist
        """
        companions = []
        for ext in COMPANION_EXTENSIONS:
            companion_path = image_path + ext
            if os.path.exists(companion_path):
                companions.append(companion_path)
        return companions

    def move_with_companions(self, source_path, dest_path):
        """
        Move an image and all its companion files to the destination.

        Args:
            source_path: Source image path
            dest_path: Destination image path

        Returns:
            List of (source, dest) tuples for all files moved
        """
        moved_files = []

        # Move the main image
        shutil.move(source_path, dest_path)
        moved_files.append((source_path, dest_path))

        # Move companion files
        for companion_src in self.get_companion_files(source_path):
            ext = os.path.splitext(companion_src)[1]
            companion_dest = dest_path + ext
            if os.path.exists(companion_src):
                shutil.move(companion_src, companion_dest)
                moved_files.append((companion_src, companion_dest))

        return moved_files

    def copy_with_companions(self, source_path, dest_path):
        """
        Copy an image and all its companion files to the destination.

        Args:
            source_path: Source image path
            dest_path: Destination image path

        Returns:
            List of (source, dest) tuples for all files copied
        """
        copied_files = []

        # Copy the main image
        shutil.copy2(source_path, dest_path)
        copied_files.append((source_path, dest_path))

        # Copy companion files
        for companion_src in self.get_companion_files(source_path):
            ext = os.path.splitext(companion_src)[1]
            companion_dest = dest_path + ext
            if os.path.exists(companion_src):
                shutil.copy2(companion_src, companion_dest)
                copied_files.append((companion_src, companion_dest))

        return copied_files
    
    def cancel_operation(self):
        """Cancel the current sorting operation."""
        self.cancelled = True
        # Also release pause to allow cancellation to take effect
        self._pause_event.set()

    def pause_operation(self):
        """Pause the current sorting operation."""
        self.paused = True
        self._pause_event.clear()  # Block the wait()

    def resume_operation(self):
        """Resume a paused sorting operation."""
        self.paused = False
        self._pause_event.set()  # Release the wait()
    
    def is_cancelled(self):
        """Check if the operation was cancelled."""
        return self.cancelled
    
    def is_paused(self):
        """Check if the operation is paused."""
        return self.paused
    
    def reset_state(self):
        """Reset the sorter state for a new operation."""
        self.cancelled = False
        self.paused = False
    
    def re_sort_auto_sorted_images(self, progress_callback=None):
        """
        Re-evaluate and re-sort existing auto-sorted images using current term rules.
        
        This method scans all existing auto-sorted folders, re-evaluates each image
        against the current term configuration, and moves/copies images to appropriate
        destinations based on updated rules. Useful when adding new terms or changing
        multi-tag modes.
        
        Args:
            progress_callback (callable, optional): Function to call with progress updates.
                Receives dict with keys: progress, current_file, processed, total, moved
                
        Returns:
            dict: Re-sort operation results including:
                - processed: Number of images processed
                - moved: Number of images moved/copied to new locations
                - errors: List of error messages encountered
                - file_movements: List of all file operations performed
                - timestamp: When operation started
        """
        if progress_callback:
            self.progress_callback = progress_callback
        
        # Collect all existing auto-sorted images
        image_data = self.collect_auto_sorted_images()
        
        if not image_data:
            return {
                'processed': 0,
                'moved': 0,
                'errors': [],
                'message': 'No auto-sorted images found to re-sort'
            }
        
        results = {
            'processed': 0,
            'moved': 0,
            'errors': [],
            'file_movements': [],
            'timestamp': time.time()
        }
        
        total_images = len(image_data)
        current_terms = self.config_manager.get_auto_sort_terms()
        
        for i, image_info in enumerate(image_data):
            if self.cancelled:
                break
            
            # Wait if paused
            while self.paused and not self.cancelled:
                time.sleep(0.1)
            
            if self.progress_callback:
                progress = (i / total_images) * 100
                self.progress_callback({
                    'progress': progress,
                    'current_file': image_info['filename'],
                    'processed': i,
                    'total': total_images,
                    'moved': results['moved']
                })
            
            try:
                moved = self.re_evaluate_image_placement(image_info, current_terms, results)
                if moved:
                    results['moved'] += 1
                results['processed'] += 1
                
            except Exception as e:
                error_msg = f"Error re-sorting {image_info['filename']}: {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return results
    
    def collect_auto_sorted_images(self):
        """
        Scan all auto-sorted subdirectories and collect image information.
        
        Recursively walks through the auto_sorted base directory to find all image files
        and collect metadata about their current locations for re-sorting evaluation.
        
        Returns:
            list: List of dicts with keys:
                - filename: Base filename of the image
                - full_path: Complete path to the image file
                - current_folder: Relative folder name from auto_sorted base
                - current_folder_full: Complete path to current folder
        """
        auto_sorted_base = self.config_manager.sorted_folders.get('auto_sorted')
        if not auto_sorted_base or not os.path.exists(auto_sorted_base):
            return []
        
        image_data = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        
        # Scan all subdirectories in auto_sorted
        for root, dirs, files in os.walk(auto_sorted_base):
            for filename in files:
                # Check if it's an image file
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    full_path = os.path.join(root, filename)
                    # Get the relative folder name (from auto_sorted base)
                    rel_folder = os.path.relpath(root, auto_sorted_base)
                    
                    image_data.append({
                        'filename': filename,
                        'full_path': full_path,
                        'current_folder': rel_folder,
                        'current_folder_full': root
                    })
        
        return image_data
    
    def re_evaluate_image_placement(self, image_info, current_terms, results):
        """Determine if image needs to be moved to different/additional folders."""
        image_path = image_info['full_path']
        
        # Get metadata for this image
        metadata = self.metadata_parser.extract_metadata(image_path)
        if not metadata:
            return False
        
        # Find matching terms using current configuration
        matching_terms = []
        for term in current_terms:
            if not term.get('enabled', True):
                continue
            
            if self.metadata_parser.term_matches_metadata(term, metadata):
                matching_terms.append(term)
        
        # Get where this image should be placed with current rules
        destination_info = self.config_manager.get_multi_tag_destinations(matching_terms)
        new_destinations = destination_info['destinations']
        
        if not new_destinations:
            # Should go to unmatched if no matches
            unmatched_path = self.config_manager.sorted_folders.get('unmatched')
            if unmatched_path and image_info['current_folder'] != 'unmatched':
                self.move_image_to_new_location(image_info, unmatched_path, results)
                return True
            return False
        
        # Check if current location is still valid
        current_should_exist = False
        new_paths_needed = []
        
        for dest_info in new_destinations:
            dest_path = dest_info['path']
            if dest_path:
                new_paths_needed.append(dest_path)
                # Check if current location matches one of the new destinations
                if image_info['current_folder_full'] == dest_path:
                    current_should_exist = True
        
        # If image is in a location it should no longer be in, or if new locations are needed
        moved = False
        if not current_should_exist or len(new_paths_needed) > 1:
            moved = self.handle_re_sort_movement(image_info, new_paths_needed, results)
        
        return moved
    
    def handle_re_sort_movement(self, image_info, new_destinations, results):
        """Move/copy image to new destinations as needed."""
        image_path = image_info['full_path']
        filename = image_info['filename']
        moved = False
        
        # Move to the first destination, copy to additional ones
        for i, dest_path in enumerate(new_destinations):
            try:
                os.makedirs(dest_path, exist_ok=True)
                dest_file_path = os.path.join(dest_path, filename)
                dest_file_path = self.handle_naming_conflict(dest_file_path)
                
                if i == 0:
                    # Move to first destination
                    if image_info['current_folder_full'] != dest_path:
                        shutil.move(image_path, dest_file_path)
                        operation = 'move'
                        moved = True
                        # Update the path for subsequent operations
                        image_path = dest_file_path
                else:
                    # Copy to additional destinations
                    if not os.path.exists(dest_file_path):
                        shutil.copy2(image_path, dest_file_path)
                        operation = 'copy'
                        moved = True
                
                # Track the movement
                results['file_movements'].append({
                    'operation': operation,
                    'source': image_info['full_path'] if i == 0 else image_path,
                    'destination': dest_file_path,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                error_msg = f"Error moving {filename} to {dest_path}: {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return moved
    
    def move_image_to_new_location(self, image_info, dest_base_path, results):
        """Move image to a new location (like unmatched)."""
        try:
            os.makedirs(dest_base_path, exist_ok=True)
            dest_file_path = os.path.join(dest_base_path, image_info['filename'])
            dest_file_path = self.handle_naming_conflict(dest_file_path)
            
            shutil.move(image_info['full_path'], dest_file_path)
            
            results['file_movements'].append({
                'operation': 'move',
                'source': image_info['full_path'],
                'destination': dest_file_path,
                'timestamp': time.time()
            })
            
        except Exception as e:
            error_msg = f"Error moving {image_info['filename']}: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
    
    def collect_unmatched_from_source(self, source_folders, progress_callback=None):
        """
        Scan source folders and collect unmatched images to the unmatched folder.
        
        This method identifies images in source folders that haven't been auto-sorted
        and don't match any current terms, then moves/copies them to the unmatched folder.
        
        Args:
            source_folders (list): List of source folder paths to scan
            progress_callback (callable, optional): Function to call with progress updates
            
        Returns:
            dict: Collection results including:
                - scanned: Number of images scanned
                - collected: Number of images moved to unmatched folder
                - errors: List of error messages
                - already_sorted: Number of images already in destination folders
                - matched_terms: Number of images that match current terms
        """
        if progress_callback:
            self.progress_callback = progress_callback
        
        results = {
            'scanned': 0,
            'collected': 0,
            'errors': [],
            'already_sorted': 0,
            'matched_terms': 0,
            'file_movements': [],
            'timestamp': time.time()
        }
        
        # Get all destination folders to exclude from scanning
        destination_folders = set(self.config_manager.sorted_folders.values())
        
        # Get current terms for matching
        current_terms = self.config_manager.get_auto_sort_terms()
        enabled_terms = [t for t in current_terms if t.get('enabled', True)]
        
        # Collect all images from source folders
        include_subfolders = self.config_manager.config.get('include_subfolders', True)
        all_source_images = []
        for source_folder in source_folders:
            if not os.path.exists(source_folder):
                continue
                
            if include_subfolders:
                # Recursively scan subdirectories
                for root, dirs, files in os.walk(source_folder):
                    # Skip destination folders
                    if any(dest_folder in root for dest_folder in destination_folders):
                        continue
                        
                    for filename in files:
                        _, ext = os.path.splitext(filename.lower())
                        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
                            full_path = os.path.join(root, filename)
                            all_source_images.append(full_path)
            else:
                # Only scan the root folder
                try:
                    files = os.listdir(source_folder)
                    for filename in files:
                        file_path = os.path.join(source_folder, filename)
                        if os.path.isfile(file_path):
                            _, ext = os.path.splitext(filename.lower())
                            if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
                                all_source_images.append(file_path)
                except OSError:
                    continue
        
        total_images = len(all_source_images)
        if total_images == 0:
            return results
        
        for i, image_path in enumerate(all_source_images):
            if self.cancelled:
                break
                
            # Wait if paused
            while self.paused and not self.cancelled:
                time.sleep(0.1)
            
            if self.progress_callback:
                progress = (i / total_images) * 100
                self.progress_callback({
                    'progress': progress,
                    'current_file': os.path.basename(image_path),
                    'scanned': i,
                    'total': total_images,
                    'collected': results['collected']
                })
            
            try:
                results['scanned'] += 1
                
                # Check if image is already in a destination folder
                if self.is_in_destination_folder(image_path):
                    results['already_sorted'] += 1
                    continue
                
                # Get metadata and check against current terms
                metadata = self.metadata_parser.extract_metadata(image_path)
                if not metadata:
                    # No metadata, collect as unmatched
                    if self.move_to_unmatched_folder(image_path, results):
                        results['collected'] += 1
                    continue
                
                # Check if matches any current terms
                matches = self.metadata_parser.search_terms_in_metadata(metadata, enabled_terms)
                if matches:
                    results['matched_terms'] += 1
                    continue
                
                # No matches, collect as unmatched
                if self.move_to_unmatched_folder(image_path, results):
                    results['collected'] += 1
                    
            except Exception as e:
                error_msg = f"Error processing {os.path.basename(image_path)}: {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return results
    
    def is_in_destination_folder(self, image_path):
        """Check if an image is already in one of the destination folders."""
        destination_folders = self.config_manager.sorted_folders.values()
        for dest_folder in destination_folders:
            if dest_folder and os.path.commonpath([image_path, dest_folder]) == dest_folder:
                return True
        return False
    
    def move_to_unmatched_folder(self, image_path, results):
        """Move an image to the unmatched folder and track the operation."""
        try:
            unmatched_folder = self.config_manager.sorted_folders.get('unmatched')
            if not unmatched_folder:
                return False

            os.makedirs(unmatched_folder, exist_ok=True)
            filename = os.path.basename(image_path)
            dest_path = os.path.join(unmatched_folder, filename)
            dest_path = self.handle_naming_conflict(dest_path)

            # Respect copy vs move preference
            settings = self.config_manager.get_auto_sort_settings()
            if settings.get('copy_instead_of_move', False):
                shutil.copy2(image_path, dest_path)
                operation = 'copy'
            else:
                shutil.move(image_path, dest_path)
                operation = 'move'

            # Track the movement
            results['file_movements'].append({
                'operation': operation,
                'source': image_path,
                'destination': dest_path,
                'timestamp': time.time()
            })

            return True

        except Exception as e:
            error_msg = f"Error moving {os.path.basename(image_path)} to unmatched: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
            return False

    # ========== Visual Classification Sorting Methods ==========

    def sort_by_visual_classification(self, image_files, sort_by='shot_type',
                                      use_yolo=False, progress_callback=None):
        """
        Sort images based on visual classification (shot type, person count, NSFW rating).

        This method uses the WD14 tagger to classify images and sorts them into
        folders based on visual properties rather than metadata terms.

        Args:
            image_files (list): List of image file paths to sort
            sort_by (str): Classification to sort by - 'shot_type', 'person_count', 'nsfw_rating'
            use_yolo (bool): Whether to use YOLO for more accurate person detection
            progress_callback (callable, optional): Function for progress updates

        Returns:
            dict: Results including processed, sorted, errors, classification_counts
        """
        self.cancelled = False
        self.paused = False
        self._pause_event.set()

        if progress_callback:
            self.progress_callback = progress_callback

        # Initialize visual classifier
        try:
            classifier = VisualClassifier(use_yolo=use_yolo)
            if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
                return {
                    'processed': 0,
                    'sorted': 0,
                    'errors': ['WD14 tagger not loaded. Check model files.']
                }
        except Exception as e:
            return {
                'processed': 0,
                'sorted': 0,
                'errors': [f'Failed to initialize visual classifier: {e}']
            }

        results = {
            'processed': 0,
            'sorted': 0,
            'errors': [],
            'classification_counts': {},
            'file_movements': [],
            'timestamp': time.time()
        }

        # Get base destination folder
        auto_sorted_base = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
        visual_sort_base = os.path.join(auto_sorted_base, f'visual_{sort_by}')

        total_images = len(image_files)
        settings = self.config_manager.get_auto_sort_settings()
        use_copy_mode = settings.get('copy_instead_of_move', False)

        for i, image_file in enumerate(image_files):
            if self.cancelled:
                break

            self._pause_event.wait()

            try:
                # Classify the image
                classification = classifier.classify_image(image_file)
                results['processed'] += 1

                # Get folder name based on sort_by parameter
                folder_name = classifier.get_sorting_folder(classification, sort_by)

                if folder_name == 'unknown':
                    # Track as unclassified but not an error
                    results['classification_counts']['unknown'] = \
                        results['classification_counts'].get('unknown', 0) + 1
                    continue

                # Create destination folder
                dest_folder = os.path.join(visual_sort_base, folder_name)
                os.makedirs(dest_folder, exist_ok=True)

                # Generate destination path
                filename = os.path.basename(image_file)
                dest_path = os.path.join(dest_folder, filename)
                dest_path = self.handle_naming_conflict(dest_path)

                # Move or copy
                if use_copy_mode:
                    self.copy_with_companions(image_file, dest_path)
                    operation = 'copy'
                else:
                    self.move_with_companions(image_file, dest_path)
                    operation = 'move'

                results['sorted'] += 1
                results['classification_counts'][folder_name] = \
                    results['classification_counts'].get(folder_name, 0) + 1

                # Track movement
                results['file_movements'].append({
                    'operation': operation,
                    'source': image_file,
                    'destination': dest_path,
                    'classification': folder_name,
                    'timestamp': time.time()
                })

                # Update progress
                if self.progress_callback:
                    self.progress_callback(
                        i + 1, total_images, os.path.basename(image_file),
                        processed=results['processed'],
                        sorted=results['sorted'],
                        errors=len(results['errors'])
                    )

            except Exception as e:
                error_msg = f"Error classifying {os.path.basename(image_file)}: {e}"
                results['errors'].append({'file': image_file, 'error': str(e)})
                self.logger.error(error_msg)

        return results

    def sort_by_lora_profile(self, image_files, profile, use_yolo=False,
                             progress_callback=None):
        """
        Sort images that match a specific LoRA profile.

        This filters images to only those that match the profile's criteria
        (shot type, person count, NSFW rating, required/excluded tags).

        Args:
            image_files (list): List of image file paths to sort
            profile (LoRASortingProfile): The LoRA profile to match against
            use_yolo (bool): Whether to use YOLO for person detection
            progress_callback (callable, optional): Function for progress updates

        Returns:
            dict: Results including matched, not_matched, errors
        """
        self.cancelled = False
        self.paused = False
        self._pause_event.set()

        if progress_callback:
            self.progress_callback = progress_callback

        # Initialize visual classifier
        try:
            classifier = VisualClassifier(use_yolo=use_yolo)
            if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
                return {
                    'processed': 0,
                    'matched': 0,
                    'errors': ['WD14 tagger not loaded.']
                }
        except Exception as e:
            return {
                'processed': 0,
                'matched': 0,
                'errors': [f'Failed to initialize visual classifier: {e}']
            }

        results = {
            'processed': 0,
            'matched': 0,
            'not_matched': 0,
            'errors': [],
            'file_movements': [],
            'timestamp': time.time()
        }

        # Get destination folder for this profile
        auto_sorted_base = self.config_manager.sorted_folders.get('auto_sorted', 'auto_sorted')
        profile_folder = os.path.join(auto_sorted_base, 'lora_profiles', profile.name)
        os.makedirs(profile_folder, exist_ok=True)

        total_images = len(image_files)
        settings = self.config_manager.get_auto_sort_settings()
        use_copy_mode = settings.get('copy_instead_of_move', False)

        for i, image_file in enumerate(image_files):
            if self.cancelled:
                break

            self._pause_event.wait()

            try:
                # Classify the image
                classification = classifier.classify_image(image_file)
                results['processed'] += 1

                # Check if it matches the profile
                if profile.matches(classification):
                    # Generate destination path
                    filename = os.path.basename(image_file)
                    dest_path = os.path.join(profile_folder, filename)
                    dest_path = self.handle_naming_conflict(dest_path)

                    # Move or copy
                    if use_copy_mode:
                        self.copy_with_companions(image_file, dest_path)
                        operation = 'copy'
                    else:
                        self.move_with_companions(image_file, dest_path)
                        operation = 'move'

                    results['matched'] += 1

                    # Track movement
                    results['file_movements'].append({
                        'operation': operation,
                        'source': image_file,
                        'destination': dest_path,
                        'profile': profile.name,
                        'classification': classification.to_dict(),
                        'timestamp': time.time()
                    })
                else:
                    results['not_matched'] += 1

                # Update progress
                if self.progress_callback:
                    self.progress_callback(
                        i + 1, total_images, os.path.basename(image_file),
                        processed=results['processed'],
                        matched=results['matched'],
                        errors=len(results['errors'])
                    )

            except Exception as e:
                error_msg = f"Error processing {os.path.basename(image_file)}: {e}"
                results['errors'].append({'file': image_file, 'error': str(e)})
                self.logger.error(error_msg)

        return results

    def classify_images_batch(self, image_files, use_yolo=False, progress_callback=None):
        """
        Classify a batch of images without sorting them.

        Useful for previewing classifications before committing to a sort operation.

        Args:
            image_files (list): List of image file paths
            use_yolo (bool): Whether to use YOLO for person detection
            progress_callback (callable, optional): Function for progress updates

        Returns:
            dict: Classification results and statistics
        """
        self.cancelled = False
        self.paused = False
        self._pause_event.set()

        if progress_callback:
            self.progress_callback = progress_callback

        try:
            classifier = VisualClassifier(use_yolo=use_yolo)
            if not classifier.wd14_tagger or not classifier.wd14_tagger.loaded:
                return {
                    'processed': 0,
                    'errors': ['WD14 tagger not loaded.'],
                    'classifications': []
                }
        except Exception as e:
            return {
                'processed': 0,
                'errors': [f'Failed to initialize visual classifier: {e}'],
                'classifications': []
            }

        results = {
            'processed': 0,
            'classifications': [],
            'shot_type_counts': {},
            'person_count_counts': {},
            'nsfw_rating_counts': {},
            'errors': []
        }

        total_images = len(image_files)

        for i, image_file in enumerate(image_files):
            if self.cancelled:
                break

            self._pause_event.wait()

            try:
                classification = classifier.classify_image(image_file)
                results['processed'] += 1

                # Store classification
                results['classifications'].append(classification.to_dict())

                # Update counts
                shot = classification.shot_type.value
                person = classification.person_count.value
                rating = classification.nsfw_rating.value

                results['shot_type_counts'][shot] = \
                    results['shot_type_counts'].get(shot, 0) + 1
                results['person_count_counts'][person] = \
                    results['person_count_counts'].get(person, 0) + 1
                results['nsfw_rating_counts'][rating] = \
                    results['nsfw_rating_counts'].get(rating, 0) + 1

                # Update progress
                if self.progress_callback:
                    self.progress_callback(
                        i + 1, total_images, os.path.basename(image_file),
                        processed=results['processed']
                    )

            except Exception as e:
                results['errors'].append({'file': image_file, 'error': str(e)})
                self.logger.error(f"Error classifying {image_file}: {e}")

        return results