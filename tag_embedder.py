import os
import shutil
from PIL import Image, PngImagePlugin, ExifTags
from PIL.ExifTags import TAGS
import logging

# Try to import piexif for advanced JPEG metadata handling
try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

class TagEmbedder:
    """Utility for embedding tag file content into image metadata."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dry_run_mode = False
        self.safety_checks_enabled = True
        
    def set_dry_run_mode(self, enabled=True):
        """Enable or disable dry-run mode for testing."""
        self.dry_run_mode = enabled
        self.logger.info(f"Dry-run mode {'enabled' if enabled else 'disabled'}")

    def set_safety_checks(self, enabled=True):
        """Enable or disable safety checks."""
        self.safety_checks_enabled = enabled
        self.logger.info(f"Safety checks {'enabled' if enabled else 'disabled'}")

    def check_for_existing_prompts(self, image_path):
        """
        Check if an image contains prompt data that could be lost.
        Returns dict with findings.
        """
        findings = {
            'has_prompts': False,
            'prompt_locations': [],
            'risk_level': 'low',
            'warnings': []
        }

        try:
            file_ext = os.path.splitext(image_path)[1].lower()

            if file_ext == '.png':
                with Image.open(image_path) as img:
                    if hasattr(img, 'text') and img.text:
                        # Check for parameters field
                        if 'parameters' in img.text:
                            params = img.text['parameters']
                            if isinstance(params, (str, dict)) and any(keyword in str(params).lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                                findings['has_prompts'] = True
                                findings['prompt_locations'].append('PNG parameters field')
                                findings['risk_level'] = 'low'  # PNG embedding preserves existing data

                        # Check other fields
                        for key, value in img.text.items():
                            if isinstance(value, str) and any(keyword in value.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                                if key not in findings['prompt_locations']:
                                    findings['has_prompts'] = True
                                    findings['prompt_locations'].append(f'PNG {key} field')

            elif file_ext in ['.jpg', '.jpeg']:
                with Image.open(image_path) as img:
                    exif_data = img.getexif()
                    if exif_data:
                        # Check common EXIF fields for prompts
                        for tag_id, value in exif_data.items():
                            if isinstance(value, str) and any(keyword in value.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                                tag_name = f"EXIF tag {tag_id}"
                                findings['has_prompts'] = True
                                findings['prompt_locations'].append(tag_name)
                                findings['risk_level'] = 'high'  # JPEG embedding could overwrite
                                findings['warnings'].append(f"Prompt data found in {tag_name} - embedding tags could overwrite this!")

                # Also check with piexif if available
                if HAS_PIEXIF:
                    try:
                        exif_dict = piexif.load(image_path)
                        # Check UserComment
                        comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment, b'')
                        if comment and any(keyword in str(comment).lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                            findings['has_prompts'] = True
                            findings['prompt_locations'].append('EXIF UserComment')
                            findings['risk_level'] = 'high'
                            findings['warnings'].append("Prompt data found in UserComment - will be preserved by new embedder")

                        # Check ImageDescription
                        desc = exif_dict.get('0th', {}).get(piexif.ImageIFD.ImageDescription, b'')
                        if desc and any(keyword in str(desc).lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                            findings['has_prompts'] = True
                            findings['prompt_locations'].append('EXIF ImageDescription')
                            findings['risk_level'] = 'high'
                            findings['warnings'].append("Prompt data found in ImageDescription - will be preserved by new embedder")
                    except:
                        pass

        except Exception as e:
            findings['warnings'].append(f"Error checking for prompts: {e}")

        return findings

    def embed_tag_file_in_image(self, image_path, backup_original=True, force_overwrite=False):
        """
        Embed companion .txt tag file content into image metadata.

        Args:
            image_path: Path to image file
            backup_original: Create .original backup file
            force_overwrite: Skip safety checks and proceed anyway

        Returns:
            dict with success status and details
        """
        result = {
            'success': False,
            'action_taken': 'none',
            'warnings': [],
            'prompt_check': None,
            'backup_created': False,
            'dry_run': self.dry_run_mode
        }

        tag_file_path = image_path + '.txt'

        if not os.path.exists(tag_file_path):
            result['warnings'].append('No tag file found')
            return result

        try:
            # Read tag file content
            with open(tag_file_path, 'r', encoding='utf-8') as f:
                tag_content = f.read().strip()

            if not tag_content:
                result['warnings'].append('Tag file is empty')
                return result

            # Perform safety checks
            if self.safety_checks_enabled and not force_overwrite:
                prompt_check = self.check_for_existing_prompts(image_path)
                result['prompt_check'] = prompt_check

                if prompt_check['has_prompts']:
                    result['warnings'].extend(prompt_check['warnings'])

                    if prompt_check['risk_level'] == 'high' and not force_overwrite:
                        self.logger.warning(f"High-risk prompt overwrite detected for {image_path}")
                        self.logger.warning(f"Prompts found in: {', '.join(prompt_check['prompt_locations'])}")

                        if self.dry_run_mode:
                            result['action_taken'] = 'blocked_by_safety_check'
                            result['warnings'].append('Would block due to high-risk prompt overwrite (use force_overwrite=True to proceed)')
                            return result
                        else:
                            # In non-dry-run mode, proceed but log warnings (our fixed embedder preserves prompts)
                            result['warnings'].append('Proceeding with prompt preservation enabled')

            # Check if in dry-run mode
            if self.dry_run_mode:
                result['action_taken'] = 'dry_run_simulation'
                result['warnings'].append(f'DRY RUN: Would embed tags from {tag_file_path}')
                return result

            # Check file format
            file_ext = os.path.splitext(image_path)[1].lower()

            # Create backup before proceeding
            if backup_original:
                backup_path = image_path + '.original'
                if not os.path.exists(backup_path):
                    shutil.copy2(image_path, backup_path)
                    result['backup_created'] = True
                    self.logger.info(f"Created backup: {backup_path}")

            # Proceed with embedding
            if file_ext == '.png':
                success = self._embed_png_tags(image_path, tag_content, backup_original)
                result['action_taken'] = 'png_embedding'
            elif file_ext in ['.jpg', '.jpeg']:
                success = self._embed_jpeg_tags(image_path, tag_content, backup_original)
                result['action_taken'] = 'jpeg_embedding'
            else:
                self.logger.warning(f"Unsupported format for tag embedding: {file_ext}")
                result['warnings'].append(f'Unsupported format: {file_ext}')
                return result

            result['success'] = success
            if success:
                self.logger.info(f"Successfully embedded tags for {image_path}")
            else:
                result['warnings'].append('Embedding operation failed')

        except Exception as e:
            self.logger.error(f"Error embedding tags for {image_path}: {e}")
            result['warnings'].append(f'Exception: {e}')

        return result
    
    def _embed_png_tags(self, image_path, tag_content, backup_original):
        """Embed tags in PNG metadata."""
        try:
            # Backup original if requested
            if backup_original:
                backup_path = image_path + '.original'
                if not os.path.exists(backup_path):
                    shutil.copy2(image_path, backup_path)
            
            # Open image and read existing metadata
            with Image.open(image_path) as img:
                # Check if tags are already embedded
                if hasattr(img, 'text') and img.text:
                    existing_tags = img.text.get('tags')
                    embedded_marker = img.text.get('tags_embedded_from_file')
                    
                    if existing_tags or embedded_marker:
                        self.logger.info(f"Tags already embedded in {image_path}, skipping")
                        return True  # Consider this success
                
                # Create new metadata dict
                meta = PngImagePlugin.PngInfo()
                
                # Copy existing metadata
                if hasattr(img, 'text'):
                    for key, value in img.text.items():
                        meta.add_text(key, value)
                
                # Add tag content
                meta.add_text("tags", tag_content)
                meta.add_text("tags_embedded_from_file", os.path.basename(image_path + '.txt'))
                
                # Save with new metadata
                img.save(image_path, "PNG", pnginfo=meta)
                
            self.logger.info(f"Embedded tags from {image_path}.txt into PNG metadata")
            return True
            
        except Exception as e:
            self.logger.error(f"Error embedding PNG tags for {image_path}: {e}")
            return False
    
    def _embed_jpeg_tags(self, image_path, tag_content, backup_original):
        """Embed tags in JPEG metadata using multiple strategies."""
        try:
            # Backup original if requested
            if backup_original:
                backup_path = image_path + '.original'
                if not os.path.exists(backup_path):
                    shutil.copy2(image_path, backup_path)
            
            # Try multiple embedding strategies
            success = False
            
            # Strategy 1: Use piexif if available (most robust)
            if HAS_PIEXIF:
                try:
                    success = self._embed_jpeg_usercomment(image_path, tag_content)
                    if success:
                        self.logger.info(f"Embedded tags in JPEG UserComment: {image_path}")
                        return True
                except Exception as e:
                    self.logger.debug(f"UserComment embedding failed: {e}")
                
                try:
                    success = self._embed_jpeg_description(image_path, tag_content)
                    if success:
                        self.logger.info(f"Embedded tags in JPEG ImageDescription: {image_path}")
                        return True
                except Exception as e:
                    self.logger.debug(f"ImageDescription embedding failed: {e}")
            
            # Strategy 2: Try basic PIL EXIF (limited but no dependencies)
            try:
                success = self._embed_jpeg_basic(image_path, tag_content)
                if success:
                    self.logger.info(f"Embedded tags in JPEG basic metadata: {image_path}")
                    return True
            except Exception as e:
                self.logger.debug(f"Basic embedding failed: {e}")
            
            self.logger.warning(f"All JPEG embedding strategies failed for {image_path}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error embedding JPEG tags for {image_path}: {e}")
            return False
    
    def _embed_jpeg_basic(self, image_path, tag_content):
        """Basic JPEG tag embedding using PIL only."""
        try:
            with Image.open(image_path) as img:
                # Get existing EXIF data
                exif_data = img.getexif()
                
                # Add tags to a custom field (we'll use ImageDescription if empty)
                desc_tag = 270  # ImageDescription tag ID
                
                existing_desc = exif_data.get(desc_tag, "")
                if existing_desc and 'TAGS:' in str(existing_desc):
                    return False  # Already has tags
                
                # Prepare tag data
                tag_data = f"TAGS:{tag_content}"
                if existing_desc:
                    new_desc = f"{existing_desc} | {tag_data}"
                else:
                    new_desc = tag_data
                
                # Size limit check
                if len(new_desc.encode('utf-8')) > 270:
                    # Try just tags without existing description
                    if len(tag_data.encode('utf-8')) <= 270:
                        new_desc = tag_data
                    else:
                        return False  # Too large
                
                # Update EXIF
                exif_data[desc_tag] = new_desc
                
                # Save with updated EXIF
                img.save(image_path, "JPEG", exif=exif_data, quality=95)
                
            return True
            
        except Exception as e:
            self.logger.debug(f"Basic JPEG embedding failed: {e}")
            return False
    
    def _embed_jpeg_usercomment(self, image_path, tag_content):
        """Embed tags in JPEG UserComment field (requires piexif)."""
        if not HAS_PIEXIF:
            return False
            
        try:
            # Load existing EXIF data
            exif_dict = piexif.load(image_path)
            
            # Check if tags already exist in UserComment
            existing_comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment, b'')

            # Decode existing comment to check content
            existing_text = ""
            if existing_comment:
                try:
                    existing_text = existing_comment.decode('utf-8', errors='ignore')
                except:
                    existing_text = str(existing_comment)

            # If tags already exist, skip
            if existing_text and 'TAGS:' in existing_text:
                self.logger.info(f"Tags already embedded in UserComment for {image_path}, skipping")
                return True

            # Check if existing comment contains prompt data (preserve it!)
            if existing_text and any(keyword in existing_text.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:', 'seed:', 'model:']):
                # Preserve existing prompt data by appending tags
                new_comment = f"{existing_text} | TAGS:{tag_content}"
                self.logger.info(f"Preserving existing prompt data in UserComment for {image_path}")
            else:
                # No prompt data detected, safe to add just tags
                new_comment = f"TAGS:{tag_content}"

            # Encode as UTF-8 bytes
            tag_bytes = new_comment.encode('utf-8')

            # Check size limit (64KB for UserComment)
            if len(tag_bytes) > 65000:
                # If too long, try to preserve prompt by truncating tags instead
                if existing_text:
                    # Keep the original prompt, truncate tags
                    max_tag_length = 65000 - len(existing_text.encode('utf-8')) - 10  # Leave space for separator
                    if max_tag_length > 0:
                        truncated_tags = tag_content[:max_tag_length]
                        new_comment = f"{existing_text} | TAGS:{truncated_tags}"
                        tag_bytes = new_comment.encode('utf-8')
                        self.logger.warning(f"Truncated tag data to preserve prompt for {image_path}")
                    else:
                        self.logger.error(f"Cannot fit tags without losing prompt data for {image_path}")
                        return False
                else:
                    # No existing data, just truncate tags
                    tag_bytes = tag_bytes[:65000]
                    self.logger.warning(f"Truncated large tag data for {image_path}")

            # Set UserComment with preserved content
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = tag_bytes
            
            # Convert back to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            with Image.open(image_path) as img:
                img.save(image_path, "JPEG", exif=exif_bytes, quality=95, optimize=True)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"UserComment embedding failed: {e}")
            return False
    
    def _embed_jpeg_description(self, image_path, tag_content):
        """Embed tags in JPEG ImageDescription field (requires piexif)."""
        if not HAS_PIEXIF:
            return False
            
        try:
            # Load existing EXIF data
            exif_dict = piexif.load(image_path)
            
            # Check if ImageDescription already exists
            existing_desc = exif_dict.get('0th', {}).get(piexif.ImageIFD.ImageDescription, b'')
            if existing_desc:
                existing_desc = existing_desc.decode('utf-8', errors='ignore')
                # Only add tags if description doesn't already contain them
                if 'TAGS:' not in existing_desc:
                    new_desc = f"{existing_desc} | TAGS:{tag_content}"
                else:
                    self.logger.info(f"Tags already embedded in ImageDescription for {image_path}, skipping")
                    return True  # Already has tags
            else:
                new_desc = f"TAGS:{tag_content}"
            
            # Encode and check size
            desc_bytes = new_desc.encode('utf-8')
            if len(desc_bytes) > 270:  # TIFF string limit
                return False
            
            # Set ImageDescription
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = desc_bytes
            
            # Convert back to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            with Image.open(image_path) as img:
                img.save(image_path, "JPEG", exif=exif_bytes, quality=95, optimize=True)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"ImageDescription embedding failed: {e}")
            return False
    
    
    def embed_tags_in_folder(self, folder_path, file_extensions=None, progress_callback=None):
        """
        Embed tag files for all images in a folder with progress tracking.
        Returns dict with success/failure counts.
        """
        if file_extensions is None:
            file_extensions = ['.png', '.jpg', '.jpeg']
            
        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'no_tags': 0,
            'skipped': 0
        }
        
        # First pass: count total images
        image_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in file_extensions):
                    image_path = os.path.join(root, file)
                    image_files.append(image_path)
        
        total_images = len(image_files)
        
        # Notify progress callback of total
        if progress_callback:
            progress_callback('total', total_images)
        
        # Process each image
        for i, image_path in enumerate(image_files):
            # Check for cancellation
            if progress_callback and progress_callback('check_cancelled'):
                break
            
            # Check for pause
            while progress_callback and progress_callback('check_paused'):
                import time
                time.sleep(0.1)
                if progress_callback('check_cancelled'):
                    break
            
            tag_file_path = image_path + '.txt'
            results['processed'] += 1
            
            # Update progress
            if progress_callback:
                progress_callback('progress', {
                    'processed': results['processed'],
                    'success': results['success'],
                    'failed': results['failed'],
                    'no_tags': results['no_tags'],
                    'skipped': results['skipped'],
                    'current_file': image_path
                })
            
            if not os.path.exists(tag_file_path):
                results['no_tags'] += 1
                continue
            
            # Check if tags are already embedded
            if self._has_embedded_tags(image_path):
                results['skipped'] += 1
                continue
            
            # Attempt to embed tags
            if self.embed_tag_file_in_image(image_path):
                results['success'] += 1
                self.logger.info(f"Successfully embedded tags for {image_path}")
            else:
                results['failed'] += 1
                self.logger.warning(f"Failed to embed tags for {image_path}")
        
        # Notify completion
        if progress_callback:
            progress_callback('complete', results)
        
        return results
    
    def _has_embedded_tags(self, image_path):
        """Check if an image already has embedded tags."""
        try:
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext == '.png':
                with Image.open(image_path) as img:
                    return 'TAGS:' in str(img.info.get('parameters', ''))
            
            elif file_ext in ['.jpg', '.jpeg']:
                with Image.open(image_path) as img:
                    exif_data = img.getexif()
                    if exif_data:
                        # Check ImageDescription
                        desc = exif_data.get(270, "")  # ImageDescription tag
                        if 'TAGS:' in str(desc):
                            return True
                        
                        # Check UserComment if piexif is available
                        if HAS_PIEXIF:
                            try:
                                exif_dict = piexif.load(image_path)
                                comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment, b'')
                                if b'TAGS:' in comment:
                                    return True
                            except:
                                pass
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking embedded tags for {image_path}: {e}")
            return False
    
    def copy_or_move_with_tags(self, src_path, dest_path, copy_mode=True, include_tags=True):
        """
        Copy or move an image file, optionally including its tag file.
        """
        try:
            # Copy/move the main file
            if copy_mode:
                shutil.copy2(src_path, dest_path)
            else:
                shutil.move(src_path, dest_path)
            
            # Handle tag file if it exists and is requested
            if include_tags:
                src_tag = src_path + '.txt'
                dest_tag = dest_path + '.txt'
                
                if os.path.exists(src_tag):
                    if copy_mode:
                        # For copy mode, default is to NOT copy tag files
                        # (they stay with originals)
                        pass
                    else:
                        # For move mode, default is to move tag files too
                        shutil.move(src_tag, dest_tag)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error copying/moving {src_path}: {e}")
            return False