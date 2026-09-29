"""
Configuration Manager for Image Grid Sorter

This module provides comprehensive configuration management including:
- JSON-based configuration with automatic migration from legacy INI files
- Multi-tag auto-sorting with various modes (single_folder, multi_folder, smart_combination, all_combinations)
- Term management with priority, exclusions, and flexible search scopes
- Metadata caching and UI preferences
- Backup and recovery functionality

Key Features:
- Backward compatibility with automatic migration
- Validation and sanitization of all configuration data
- Support for combination folder generation
- Comprehensive logging and error handling

Author: Claude Code Implementation
Version: 2.1 (Added all_combinations mode and re-sort functionality)
"""

import os
import json
import shutil
import glob
import copy
import threading
from datetime import datetime
from configparser import ConfigParser
import logging

class ConfigManager:
    """
    Enhanced configuration manager for the Image Grid Sorter application.
    
    Manages all application settings including:
    - Source and destination folder configurations
    - Auto-sort terms with multi-tag support
    - UI preferences and key bindings
    - Metadata caching settings
    - Legacy configuration migration
    
    Configuration is stored in JSON format with automatic backup and recovery.
    """
    
    CURRENT_VERSION = "3.0"  # Output folder restructuring + category labels
    
    def __init__(self, config_file='imagesorter_config.json', legacy_config_file='config.ini'):
        self.config_file = config_file
        self.legacy_config_file = legacy_config_file
        self.logger = logging.getLogger(__name__)

        # Thread-safe lock for configuration access
        # Use RLock to allow nested locking (same thread can acquire multiple times)
        self._lock = threading.RLock()

        self.default_config = {
            'config_version': self.CURRENT_VERSION,
            'source_folders': [],
            'output_folders': {
                '1': '1',
                '2': '2',
                '3': '3',
                'removed': 'removed',
                'auto_sorted': 'auto_sorted',
                'unmatched': 'unmatched'
            },
            'output_base': 'output',
            'category_labels': {
                '__default__': {
                    '1': {'label': 'keep', 'role': 'keep'},
                    '2': {'label': 'maybe', 'role': 'keep'},
                    '3': {'label': 'trash', 'role': 'trash'},
                    'removed': {'label': 'removed', 'role': 'trash'}
                }
            },
            'num_rows': 5,
            'random_order': False,
            'copy_instead_of_move': False,
            'include_subfolders': True,
            'last_folder': '',
            'active_sources': {},
            'destination_location': 'script_dir',
            'auto_sort_terms': [],
            'auto_sort_settings': {
                'enabled': True,
                'create_subfolders': True,
                'handle_multiple_matches': 'first_match',
                'handle_no_matches': 'move_to_unmatched',  # Changed default to auto-collect unmatched
                'copy_instead_of_move': False,
                'backup_before_sort': False,
                'log_operations': True,
                'max_log_entries': 1000,
                'multi_tag_mode': 'all_combinations',
                'multi_tag_max_folders': 5,
                'create_combination_folders': True,
                'combination_separator': '_',
                'min_tags_for_combination': 2,
                'max_tags_for_combination': 3
            },
            'metadata_cache': {
                'enabled': True,
                'max_entries': 10000,
                'expire_days': 30,
                'cache_file': 'metadata_cache.json'
            },
            'ui_preferences': {
                'show_auto_sort_toolbar': True,
                'show_metadata_status': True,
                'show_progress_details': True,
                'auto_sort_confirmation': True,
                'hide_already_sorted': True,  # Hide images already copied to destination folders
                'sidebar_collapsed': False,  # Hub left nav collapsed to a strip
                'rail_collapsed': False,     # Hub right folder rail collapsed to a strip
                'hover_tip_delay_ms': 1300   # Grid hover prompt: dwell before the tip appears
            },
            'bindings': {
                'left_mouse': '1',
                'right_mouse': 'next',
                'middle_mouse': 'config',
                'mouse_button_4': '2',
                'mouse_button_5': '3',
                'key_1': '1',
                'key_2': '2',
                'key_3': '3',
                'key_space': 'next',
                'key_r': 'reload',
                'key_escape': 'exit'
            },
            'handle_tag_files': True
        }
        
        self.config = self.load_config()
        self.sorted_folders = {}
        self.setup_folders()
    
    def load_config(self):
        """Load configuration with version migration."""
        # First try to load the new JSON config
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Check version and migrate if needed
                config_version = loaded_config.get('config_version', '1.0')
                if config_version != self.CURRENT_VERSION:
                    loaded_config = self.migrate_config(loaded_config, config_version)
                
                # Merge with defaults to ensure all keys exist
                config = self.default_config.copy()
                config.update(loaded_config)
                
                # Migrate existing terms to include new search scope fields
                self._migrate_term_configs(config)
                
                return config
                
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.logger.error(f"Error loading JSON config: {e}")
        
        # Fall back to legacy INI config if it exists
        if os.path.exists(self.legacy_config_file):
            return self.load_legacy_config()
        
        # Return default config
        return self.default_config.copy()
    
    def load_legacy_config(self):
        """Load legacy INI configuration and convert to new format."""
        config = self.default_config.copy()
        
        try:
            legacy_config = ConfigParser()
            legacy_config.read(self.legacy_config_file)
            
            # Convert legacy settings
            if legacy_config.has_section('DEFAULT'):
                default_section = legacy_config['DEFAULT']
                config['last_folder'] = default_section.get('last_folder', '')
                config['num_rows'] = default_section.getint('num_rows', 5)
                config['random_order'] = default_section.getboolean('random_order', False)
                config['copy_instead_of_move'] = default_section.getboolean('copy_instead_of_move', False)
            
            # Convert legacy bindings
            if legacy_config.has_section('BINDINGS'):
                bindings = dict(legacy_config['BINDINGS'])
                # Filter out comments
                config['bindings'] = {k: v for k, v in bindings.items() if not k.startswith('#')}
            
            self.logger.info("Converted legacy INI config to new JSON format")
            
        except Exception as e:
            self.logger.error(f"Error loading legacy config: {e}")
        
        return config
    
    def migrate_config(self, old_config, from_version):
        """Migrate configuration from older versions."""
        if from_version == '1.0':
            # Add new fields with defaults
            old_config.update({
                'auto_sort_terms': [],
                'auto_sort_settings': self.default_config['auto_sort_settings'].copy(),
                'metadata_cache': self.default_config['metadata_cache'].copy(),
                'ui_preferences': self.default_config['ui_preferences'].copy()
            })

            # Add new output folders
            if 'output_folders' not in old_config:
                old_config['output_folders'] = self.default_config['output_folders'].copy()
            else:
                old_config['output_folders'].update({
                    'auto_sorted': 'auto_sorted',
                    'unmatched': 'unmatched'
                })
            from_version = '2.1'

        if from_version == '2.1':
            # Add output_base and category_labels
            old_config['output_base'] = self.default_config['output_base']

            # Build default category labels from existing output_folders
            output_folders = old_config.get('output_folders', self.default_config['output_folders'])
            default_labels = {}
            manual_categories = {'1', '2', '3', 'removed'}
            for cat in manual_categories:
                folder_name = output_folders.get(cat, cat)
                # Assign default roles: 3 and removed are trash, rest are keep
                role = 'trash' if cat in ('3', 'removed') else 'keep'
                default_labels[cat] = {'label': folder_name, 'role': role}

            old_config['category_labels'] = {'__default__': default_labels}

            # Map 'both' destination to 'script_dir'
            if old_config.get('destination_location') == 'both':
                old_config['destination_location'] = 'script_dir'

        old_config['config_version'] = self.CURRENT_VERSION
        self.logger.info(f"Migrated config from version {from_version} to {self.CURRENT_VERSION}")
        return old_config
    
    def _migrate_term_configs(self, config):
        """Migrate existing term configurations to include new fields."""
        if 'auto_sort_terms' not in config:
            return
        
        migrated = False
        for term_config in config['auto_sort_terms']:
            # Add search scope defaults
            if 'search_scope' not in term_config:
                term_config['search_scope'] = 'either'
                migrated = True
            
            if 'include_negative_prompt' not in term_config:
                term_config['include_negative_prompt'] = False
                migrated = True
            
            # Add other new fields with defaults if missing
            if 'allow_multi_copy' not in term_config:
                term_config['allow_multi_copy'] = True
                migrated = True
            
            if 'exclusion_terms' not in term_config:
                term_config['exclusion_terms'] = []
                migrated = True
            
            if 'combination_priority' not in term_config:
                term_config['combination_priority'] = 0
                migrated = True
        
        if migrated:
            self.logger.info("Migrated existing terms to include new search scope fields")
    
    def save_config(self):
        """Save configuration with automatic backup (thread-safe)."""
        with self._lock:
            try:
                # Create backup if config exists
                if os.path.exists(self.config_file):
                    self.backup_config()

                # Add version and timestamp
                self.config['config_version'] = self.CURRENT_VERSION
                self.config['last_saved'] = datetime.now().isoformat()

                # Save configuration
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)

            except Exception as e:
                self.logger.error(f"Error saving config: {e}")
                raise
    
    def backup_config(self):
        """Create a backup of the current configuration."""
        try:
            backup_dir = os.path.join(os.path.dirname(self.config_file), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'config_backup_{timestamp}.json')
            
            shutil.copy2(self.config_file, backup_file)
            
            # Clean old backups (keep last 10)
            backup_files = sorted(glob.glob(os.path.join(backup_dir, 'config_backup_*.json')))
            if len(backup_files) > 10:
                for old_backup in backup_files[:-10]:
                    os.remove(old_backup)
                    
        except Exception as e:
            self.logger.error(f"Error creating config backup: {e}")
    
    def _build_source_folders(self, source_folder, base_dir):
        """Build the sorted_folders dict for a single source under a base directory.

        For script_dir mode, base_dir is the output_base path.
        For source_dirs mode, base_dir is the source folder itself.
        """
        source_name = self.sanitize_folder_name(os.path.basename(source_folder))
        dest_location = self.config.get('destination_location', 'script_dir')

        if dest_location == 'script_dir':
            manual_dir = os.path.join(base_dir, 'manual', source_name)
            auto_dir = os.path.join(base_dir, 'auto', source_name)
        else:
            # source_dirs mode: output goes in the source folder directly
            manual_dir = source_folder
            auto_dir = os.path.join(source_folder, 'auto_sorted')

        # Manual categories use labels as folder names
        folders = {}
        for category in ('1', '2', '3', 'removed'):
            label = self.get_label_for_category(source_folder, category)
            folders[category] = os.path.join(manual_dir, label)

        # Auto-sort and unmatched
        folders['auto_sorted'] = auto_dir
        folders['unmatched'] = os.path.join(auto_dir, 'unmatched')

        return folders

    def setup_folders(self):
        """Create output folders including auto-sort destinations."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        active_sources = self.get_active_source_folders()
        dest_location = self.config.get('destination_location', 'script_dir')

        if not active_sources:
            self.sorted_folders = {}
            self.logger.info("No active source folders configured, no output folders created")
            return

        output_base = os.path.join(script_dir, self.config.get('output_base', 'output'))

        # Build and create folders for each active source
        for source_folder in active_sources:
            if dest_location == 'script_dir':
                source_folders = self._build_source_folders(source_folder, output_base)
            else:
                source_folders = self._build_source_folders(source_folder, source_folder)

            # Primary source populates self.sorted_folders
            if source_folder == active_sources[0]:
                self.sorted_folders = source_folders

            # Create all folders on disk
            for folder in source_folders.values():
                os.makedirs(folder, exist_ok=True)

        # Create auto-sort subfolders
        if self.config['auto_sort_settings'].get('create_subfolders', True):
            self.setup_auto_sort_folders()
    
    def setup_auto_sort_folders(self):
        """Create folders for auto-sort terms."""
        auto_sort_base = self.sorted_folders.get('auto_sorted')
        if not auto_sort_base:
            return
        
        for term_config in self.config['auto_sort_terms']:
            if term_config.get('enabled', True):
                folder_name = term_config.get('folder_name', term_config['term'])
                folder_name = self.sanitize_folder_name(folder_name)
                term_folder = os.path.join(auto_sort_base, folder_name)
                os.makedirs(term_folder, exist_ok=True)
        
        # Create unmatched folder if configured
        if self.config['auto_sort_settings'].get('handle_no_matches') == 'move_to_unmatched':
            unmatched_folder = os.path.join(auto_sort_base, 'unmatched')
            os.makedirs(unmatched_folder, exist_ok=True)
    
    def get_auto_sort_terms(self):
        """Get list of auto-sort terms with their settings (thread-safe)."""
        with self._lock:
            # Return a deep copy to prevent external modification
            return copy.deepcopy(self.config.get('auto_sort_terms', []))
    
    def add_auto_sort_term(self, term, **kwargs):
        """Add a new auto-sort term."""
        # Check if term already exists
        existing_terms = [t['term'] for t in self.config['auto_sort_terms']]
        if term in existing_terms:
            raise ValueError(f"Term '{term}' already exists")
        
        new_term = {
            'term': term,
            'enabled': kwargs.get('enabled', True),
            'priority': kwargs.get('priority', len(self.config['auto_sort_terms']) + 1),
            'match_type': kwargs.get('match_type', 'word_boundary'),
            'case_sensitive': kwargs.get('case_sensitive', False),
            'folder_name': kwargs.get('folder_name', self.sanitize_folder_name(term)),
            'allow_multi_copy': kwargs.get('allow_multi_copy', True),
            'exclusion_terms': kwargs.get('exclusion_terms', []),
            'combination_priority': kwargs.get('combination_priority', 0),
            'search_scope': kwargs.get('search_scope', 'either'),
            'include_negative_prompt': kwargs.get('include_negative_prompt', False)
        }
        
        self.validate_term_config(new_term)
        self.config['auto_sort_terms'].append(new_term)
        self.save_config()
        
        # Create the folder
        self.setup_auto_sort_folders()
    
    def remove_auto_sort_term(self, term):
        """Remove an auto-sort term."""
        self.config['auto_sort_terms'] = [
            t for t in self.config['auto_sort_terms'] 
            if t['term'] != term
        ]
        self.save_config()
    
    def update_term_priority(self, term, new_priority):
        """Update the priority of a term."""
        for term_config in self.config['auto_sort_terms']:
            if term_config['term'] == term:
                term_config['priority'] = new_priority
                break
        
        # Re-sort terms by priority
        self.config['auto_sort_terms'].sort(key=lambda x: x.get('priority', 999))
        self.save_config()
    
    def get_auto_sort_settings(self):
        """Get auto-sort configuration settings (thread-safe)."""
        with self._lock:
            return copy.deepcopy(self.config.get('auto_sort_settings', {}))
    
    def update_auto_sort_settings(self, **kwargs):
        """Update auto-sort settings."""
        if 'auto_sort_settings' not in self.config:
            self.config['auto_sort_settings'] = {}
        
        self.config['auto_sort_settings'].update(kwargs)
        self.save_config()
    
    def get_term_folder_path(self, term):
        """Get the full path for a term's destination folder."""
        auto_sort_base = self.sorted_folders.get('auto_sorted')
        if not auto_sort_base:
            return None
        
        term_config = next(
            (t for t in self.config['auto_sort_terms'] if t['term'] == term),
            None
        )
        
        if term_config:
            folder_name = term_config.get('folder_name', term)
            return os.path.join(auto_sort_base, self.sanitize_folder_name(folder_name))
        
        return None
    
    def validate_term_config(self, term_config):
        """Validate a term configuration object."""
        required_fields = ['term', 'enabled', 'priority']
        
        for field in required_fields:
            if field not in term_config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate term string
        if not isinstance(term_config['term'], str) or not term_config['term'].strip():
            raise ValueError("Term must be a non-empty string")
        
        # Validate priority
        if not isinstance(term_config['priority'], int) or term_config['priority'] < 1:
            raise ValueError("Priority must be a positive integer")
        
        # Validate match type
        valid_match_types = ['word_boundary', 'contains', 'exact', 'regex']
        match_type = term_config.get('match_type', 'word_boundary')
        if match_type not in valid_match_types:
            raise ValueError(f"Invalid match_type: {match_type}")
        
        # Validate search scope
        valid_search_scopes = ['prompt_only', 'tags_only', 'either', 'both']
        search_scope = term_config.get('search_scope', 'either')
        if search_scope not in valid_search_scopes:
            raise ValueError(f"Invalid search_scope: {search_scope}")
        
        # Validate include_negative_prompt is boolean
        include_negative = term_config.get('include_negative_prompt', False)
        if not isinstance(include_negative, bool):
            raise ValueError("include_negative_prompt must be a boolean")
        
        return True
    
    def sanitize_folder_name(self, name):
        """Sanitize a folder name for filesystem compatibility."""
        import re
        # Remove invalid characters and replace with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized
    
    def export_terms(self, filename):
        """Export auto-sort terms to a file."""
        export_data = {
            'version': self.CURRENT_VERSION,
            'export_date': datetime.now().isoformat(),
            'terms': self.config['auto_sort_terms'],
            'settings': self.config['auto_sort_settings']
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def import_terms(self, filename, merge=True):
        """Import auto-sort terms from a file."""
        with open(filename, 'r') as f:
            import_data = json.load(f)
        
        imported_terms = import_data.get('terms', [])
        
        if merge:
            # Merge with existing terms (avoid duplicates)
            existing_terms = {t['term'] for t in self.config['auto_sort_terms']}
            new_terms = [t for t in imported_terms if t['term'] not in existing_terms]
            self.config['auto_sort_terms'].extend(new_terms)
        else:
            # Replace existing terms
            self.config['auto_sort_terms'] = imported_terms
        
        # Optionally import settings
        if 'settings' in import_data:
            import_settings = import_data['settings']
            self.config['auto_sort_settings'].update(import_settings)
        
        self.save_config()
        self.setup_auto_sort_folders()
    
    def get_bindings(self):
        """Get key/mouse bindings."""
        return self.config.get('bindings', {})

    def get_setting(self, key, default=None):
        """Get a setting value, checking nested locations."""
        # Check top-level first
        if key in self.config:
            return self.config[key]
        # Check ui_preferences
        if key in self.config.get('ui_preferences', {}):
            return self.config['ui_preferences'][key]
        # Check auto_sort_settings
        if key in self.config.get('auto_sort_settings', {}):
            return self.config['auto_sort_settings'][key]
        # Return default
        return default if default is not None else self.default_config.get(key)

    def set_setting(self, key, value):
        """Set a setting value in the appropriate location."""
        # Top-level scalar keys take priority (mirrors get_setting which reads top-level first).
        # A key that lives at the top level of the default config should always be written there,
        # even if it also happens to appear in a nested section (e.g. copy_instead_of_move).
        top_level_keys = {k for k, v in self.default_config.items() if not isinstance(v, dict)}
        if key in top_level_keys:
            self.config[key] = value
        # Check if it belongs in ui_preferences
        elif key in self.default_config.get('ui_preferences', {}):
            if 'ui_preferences' not in self.config:
                self.config['ui_preferences'] = {}
            self.config['ui_preferences'][key] = value
        # Check if it belongs in auto_sort_settings
        elif key in self.default_config.get('auto_sort_settings', {}):
            if 'auto_sort_settings' not in self.config:
                self.config['auto_sort_settings'] = {}
            self.config['auto_sort_settings'][key] = value
        # Otherwise set at top level
        else:
            self.config[key] = value

    def get_source_folders(self):
        """Get the list of configured source folders."""
        return self.config.get('source_folders', [])
    
    def get_active_source_folders(self):
        """Get the list of active (enabled) source folders."""
        source_folders = self.get_source_folders()
        active_sources = self.config.get('active_sources', {})
        return [folder for folder in source_folders if active_sources.get(folder, True)]
    
    def get_category_labels(self, source_folder=None):
        """Get category labels for a source folder, falling back to __default__.

        Returns dict mapping category key ('1','2','3','removed') to
        {'label': str, 'role': 'keep'|'trash'}.
        """
        labels = self.config.get('category_labels', self.default_config['category_labels'])
        if source_folder and source_folder in labels:
            return labels[source_folder]
        return labels.get('__default__', self.default_config['category_labels']['__default__'])

    def set_category_labels(self, source_folder, labels_dict):
        """Set category labels for a specific source folder (or '__default__').

        Args:
            source_folder: Source folder path, or '__default__' for the fallback.
            labels_dict: Dict mapping category key to {'label': str, 'role': str}.
        """
        if 'category_labels' not in self.config:
            self.config['category_labels'] = copy.deepcopy(self.default_config['category_labels'])
        self.config['category_labels'][source_folder] = labels_dict
        self.save_config()

    def get_label_for_category(self, source_folder, category):
        """Get the folder name label for a category and source.

        Returns the label string (used as the actual folder name on disk).
        """
        labels = self.get_category_labels(source_folder)
        cat_info = labels.get(category)
        if cat_info:
            return cat_info.get('label', category)
        return category

    def get_role_for_category(self, source_folder, category):
        """Get the role ('keep' or 'trash') for a category and source."""
        labels = self.get_category_labels(source_folder)
        cat_info = labels.get(category)
        if cat_info:
            return cat_info.get('role', 'keep')
        return 'keep'

    def get_trash_folders(self):
        """Get all folders with role='trash' across all sources.

        Returns list of dicts with keys: source, category, label, path, role.
        """
        trash_folders = []
        active_sources = self.get_active_source_folders()

        for source_folder in active_sources:
            labels = self.get_category_labels(source_folder)
            for category, info in labels.items():
                if info.get('role') == 'trash':
                    # Get the actual path for this source+category
                    path = self.get_destination_folder_for_source(source_folder, category)
                    if path and os.path.exists(path):
                        trash_folders.append({
                            'source': source_folder,
                            'category': category,
                            'label': info.get('label', category),
                            'path': path,
                            'role': 'trash'
                        })

        return trash_folders

    def get_destination_folder_for_source(self, source_folder, category):
        """Get the appropriate destination folder for a specific source and category."""
        dest_location = self.config.get('destination_location', 'script_dir')
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_base = os.path.join(script_dir, self.config.get('output_base', 'output'))

        folders = self._build_source_folders(
            source_folder,
            output_base if dest_location == 'script_dir' else source_folder
        )
        return folders.get(category)
    
    def get_multi_tag_mode(self):
        """Get the current multi-tag sorting mode (thread-safe)."""
        with self._lock:
            return self.config.get('auto_sort_settings', {}).get('multi_tag_mode', 'single_folder')
    
    def is_multi_folder_enabled(self):
        """Check if multi-folder copying is enabled."""
        mode = self.get_multi_tag_mode()
        return mode in ['multi_folder', 'smart_combination', 'all_combinations']
    
    def get_combination_folder_name(self, terms):
        """Generate a combination folder name from multiple terms."""
        if not terms:
            return None
        
        settings = self.get_auto_sort_settings()
        separator = settings.get('combination_separator', '_')
        min_tags = settings.get('min_tags_for_combination', 2)
        max_tags = settings.get('max_tags_for_combination', 3)
        
        if len(terms) < min_tags or len(terms) > max_tags:
            return None
        
        # Sort terms by combination_priority, then by priority, then alphabetically
        sorted_terms = sorted(terms, key=lambda t: (
            -t.get('combination_priority', 0),
            t.get('priority', 999),
            t['term']
        ))
        
        folder_names = [t.get('folder_name', t['term']) for t in sorted_terms]
        combination_name = separator.join(folder_names)
        
        return self.sanitize_folder_name(combination_name)
    
    def get_combination_folder_path(self, terms):
        """Get the full path for a combination folder."""
        combination_name = self.get_combination_folder_name(terms)
        if not combination_name:
            return None
        
        auto_sort_base = self.sorted_folders.get('auto_sorted')
        if not auto_sort_base:
            return None
        
        return os.path.join(auto_sort_base, combination_name)
    
    def should_create_combination_folder(self, terms):
        """Determine if a combination folder should be created for the given terms."""
        settings = self.get_auto_sort_settings()
        if not settings.get('create_combination_folders', False):
            return False
        
        mode = self.get_multi_tag_mode()
        if mode not in ['smart_combination', 'all_combinations']:
            return False
        
        min_tags = settings.get('min_tags_for_combination', 2)
        max_tags = settings.get('max_tags_for_combination', 3)
        
        return min_tags <= len(terms) <= max_tags
    
    def filter_terms_by_exclusions(self, matching_terms):
        """Remove terms that are excluded by other higher-priority terms."""
        if not matching_terms:
            return matching_terms
        
        # Sort by priority (lower number = higher priority)
        sorted_terms = sorted(matching_terms, key=lambda x: x.get('priority', 999))
        filtered_terms = []
        
        for term in sorted_terms:
            current_exclusions = term.get('exclusion_terms', [])
            
            # Check if this term should be excluded by any already-included term
            excluded = False
            
            # Check if any already-included term excludes this one
            for included_term in filtered_terms:
                included_exclusions = included_term.get('exclusion_terms', [])
                if term['term'] in included_exclusions:
                    excluded = True
                    break
            
            # Check if this term excludes any already-included terms (remove those)
            if not excluded and current_exclusions:
                filtered_terms = [t for t in filtered_terms if t['term'] not in current_exclusions]
            
            if not excluded:
                filtered_terms.append(term)
        
        return filtered_terms
    
    def get_multi_tag_destinations(self, matching_terms):
        """
        Determine destination folders for images that match multiple terms.
        
        Args:
            matching_terms (list): List of term configurations that matched the image
            
        Returns:
            dict: Contains 'destinations' list and 'strategy' string
                destinations: List of dicts with 'type', 'terms', 'path', 'folder_name'
                strategy: The multi-tag mode used for this operation
        
        Multi-tag modes:
        - single_folder: Choose one folder using conflict resolution (first_match, most_specific, etc.)
        - multi_folder: Copy image to separate folder for each matching term
        - smart_combination: Create combination folders when 2-3 tags match, otherwise individual folders
        - all_combinations: Copy to BOTH individual term folders AND combination folders (maximum coverage)
        """
        if not matching_terms:
            return {'destinations': [], 'strategy': 'none'}
        
        # Apply exclusion rules to filter out conflicting terms
        filtered_terms = self.filter_terms_by_exclusions(matching_terms)
        
        mode = self.get_multi_tag_mode()
        settings = self.get_auto_sort_settings()
        max_folders = settings.get('multi_tag_max_folders', 5)
        
        destinations = []
        strategy = mode
        
        if mode == 'single_folder':
            # Legacy mode: resolve conflicts to choose single destination
            if filtered_terms:
                resolved_term = self._resolve_single_conflict(filtered_terms)
                if resolved_term:
                    destinations.append({
                        'type': 'single_term',
                        'terms': [resolved_term],
                        'path': self.get_term_folder_path(resolved_term['term']),
                        'folder_name': resolved_term.get('folder_name', resolved_term['term'])
                    })
        
        elif mode == 'multi_folder':
            # Copy to separate individual folders for each matching term
            multi_copy_terms = [t for t in filtered_terms if t.get('allow_multi_copy', True)]
            
            for term in multi_copy_terms[:max_folders]:
                destinations.append({
                    'type': 'single_term',
                    'terms': [term],
                    'path': self.get_term_folder_path(term['term']),
                    'folder_name': term.get('folder_name', term['term'])
                })
        
        elif mode == 'smart_combination':
            # Intelligent mode: prefer combination folders for 2-3 tags, fallback to individual
            if self.should_create_combination_folder(filtered_terms):
                combination_path = self.get_combination_folder_path(filtered_terms)
                if combination_path:
                    destinations.append({
                        'type': 'combination',
                        'terms': filtered_terms,
                        'path': combination_path,
                        'folder_name': self.get_combination_folder_name(filtered_terms)
                    })
            else:
                # Fallback: use individual folders when combination criteria not met
                multi_copy_terms = [t for t in filtered_terms if t.get('allow_multi_copy', True)]
                for term in multi_copy_terms[:max_folders]:
                    destinations.append({
                        'type': 'single_term',
                        'terms': [term],
                        'path': self.get_term_folder_path(term['term']),
                        'folder_name': term.get('folder_name', term['term'])
                    })
        
        elif mode == 'all_combinations':
            # Maximum coverage mode: copy to BOTH individual AND combination folders
            # This ensures each tag folder contains ALL images with that tag
            multi_copy_terms = [t for t in filtered_terms if t.get('allow_multi_copy', True)]
            
            # Add individual folders for each matching term
            for term in multi_copy_terms[:max_folders]:
                destinations.append({
                    'type': 'single_term',
                    'terms': [term],
                    'path': self.get_term_folder_path(term['term']),
                    'folder_name': term.get('folder_name', term['term'])
                })
            
            # Also add combination folder if criteria are met
            if self.should_create_combination_folder(filtered_terms):
                combination_path = self.get_combination_folder_path(filtered_terms)
                if combination_path:
                    destinations.append({
                        'type': 'combination',
                        'terms': filtered_terms,
                        'path': combination_path,
                        'folder_name': self.get_combination_folder_name(filtered_terms)
                    })
        
        return {'destinations': destinations, 'strategy': strategy}
    
    def _resolve_single_conflict(self, matches):
        """Resolve conflicts for single-folder mode (existing logic)."""
        if not matches:
            return None
        
        if len(matches) == 1:
            return matches[0]
        
        settings = self.get_auto_sort_settings()
        strategy = settings.get('handle_multiple_matches', 'first_match')
        
        if strategy == 'first_match':
            return matches[0]
        elif strategy == 'most_specific':
            return max(matches, key=lambda x: len(x['term']))
        elif strategy == 'skip':
            return None
        else:
            return matches[0]
    
    def setup_combination_folders(self, term_combinations):
        """Create folders for specific term combinations."""
        auto_sort_base = self.sorted_folders.get('auto_sorted')
        if not auto_sort_base:
            return
        
        for combination in term_combinations:
            folder_path = self.get_combination_folder_path(combination)
            if folder_path:
                os.makedirs(folder_path, exist_ok=True)
    
    def get_basic_settings(self):
        """Get basic settings (for backward compatibility)."""
        return {
            'last_folder': self.config.get('last_folder', ''),
            'num_rows': self.config.get('num_rows', 5),
            'random_order': self.config.get('random_order', False),
            'copy_instead_of_move': self.config.get('copy_instead_of_move', False),
            'include_subfolders': self.config.get('include_subfolders', True)
        }
    
    def update_basic_settings(self, **kwargs):
        """Update basic settings."""
        for key, value in kwargs.items():
            if key in ['last_folder', 'num_rows', 'random_order', 'copy_instead_of_move', 'include_subfolders']:
                self.config[key] = value
        self.save_config()