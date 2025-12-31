# Configuration System Updates

## Overview
This document specifies the changes needed to the existing configuration system to support metadata-based auto-sorting functionality.

## Current Configuration Structure
The existing `ConfigManager` handles:
```json
{
  "source_folders": [],
  "output_folders": {
    "1": "1",
    "2": "2", 
    "3": "3",
    "removed": "removed"
  },
  "num_rows": 5,
  "random_order": false,
  "active_sources": {}
}
```

## Extended Configuration Schema

### New Configuration Sections
```json
{
  "source_folders": [],
  "output_folders": {
    "1": "1",
    "2": "2",
    "3": "3", 
    "removed": "removed",
    "auto_sorted": "auto_sorted",
    "unmatched": "unmatched"
  },
  "num_rows": 5,
  "random_order": false,
  "active_sources": {},
  
  "auto_sort_terms": [
    {
      "term": "portrait",
      "enabled": true,
      "priority": 1,
      "match_type": "word_boundary",
      "case_sensitive": false,
      "folder_name": "portrait"
    },
    {
      "term": "landscape", 
      "enabled": true,
      "priority": 2,
      "match_type": "contains",
      "case_sensitive": false,
      "folder_name": "landscape"
    }
  ],
  
  "auto_sort_settings": {
    "enabled": true,
    "create_subfolders": true,
    "handle_multiple_matches": "first_match",
    "handle_no_matches": "leave_in_place",
    "backup_before_sort": false,
    "log_operations": true,
    "max_log_entries": 1000
  },
  
  "metadata_cache": {
    "enabled": true,
    "max_entries": 10000,
    "expire_days": 30,
    "cache_file": "metadata_cache.json"
  },
  
  "ui_preferences": {
    "show_auto_sort_toolbar": true,
    "show_metadata_status": true,
    "show_progress_details": true,
    "auto_sort_confirmation": true
  }
}
```

## ConfigManager Enhancements

### Extended Default Configuration
```python
class ConfigManager:
    def __init__(self, config_file='imagesorter_config.json'):
        self.config_file = config_file
        self.default_config = {
            # Existing defaults
            'source_folders': [],
            'output_folders': {
                '1': '1', '2': '2', '3': '3', 
                'removed': 'removed',
                'auto_sorted': 'auto_sorted',
                'unmatched': 'unmatched'
            },
            'num_rows': 5,
            'random_order': False,
            'active_sources': {},
            
            # New auto-sort defaults
            'auto_sort_terms': [],
            'auto_sort_settings': {
                'enabled': True,
                'create_subfolders': True,
                'handle_multiple_matches': 'first_match',
                'handle_no_matches': 'leave_in_place',
                'backup_before_sort': False,
                'log_operations': True,
                'max_log_entries': 1000
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
                'auto_sort_confirmation': True
            }
        }
```

### New Configuration Methods
```python
def get_auto_sort_terms(self):
    """Get list of auto-sort terms with their settings."""
    return self.config.get('auto_sort_terms', [])

def add_auto_sort_term(self, term, **kwargs):
    """Add a new auto-sort term."""
    new_term = {
        'term': term,
        'enabled': kwargs.get('enabled', True),
        'priority': kwargs.get('priority', len(self.config['auto_sort_terms']) + 1),
        'match_type': kwargs.get('match_type', 'word_boundary'),
        'case_sensitive': kwargs.get('case_sensitive', False),
        'folder_name': kwargs.get('folder_name', term.lower().replace(' ', '_'))
    }
    self.config['auto_sort_terms'].append(new_term)
    self.save_config()

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
    self.save_config()

def get_auto_sort_settings(self):
    """Get auto-sort configuration settings."""
    return self.config.get('auto_sort_settings', {})

def update_auto_sort_settings(self, **kwargs):
    """Update auto-sort settings."""
    if 'auto_sort_settings' not in self.config:
        self.config['auto_sort_settings'] = {}
    
    self.config['auto_sort_settings'].update(kwargs)
    self.save_config()
```

## Folder Structure Management

### Extended Folder Setup
```python
def setup_folders(self):
    """Create output folders including auto-sort destinations."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Standard folders
    self.sorted_folders = {
        k: os.path.join(script_dir, v) 
        for k, v in self.config['output_folders'].items()
    }
    
    # Create standard folders
    for folder in self.sorted_folders.values():
        os.makedirs(folder, exist_ok=True)
    
    # Create auto-sort subfolders
    if self.config['auto_sort_settings'].get('create_subfolders', True):
        self.setup_auto_sort_folders()

def setup_auto_sort_folders(self):
    """Create folders for auto-sort terms."""
    auto_sort_base = self.sorted_folders.get('auto_sorted', 'auto_sorted')
    
    for term_config in self.config['auto_sort_terms']:
        if term_config.get('enabled', True):
            folder_name = term_config.get('folder_name', term_config['term'])
            term_folder = os.path.join(auto_sort_base, folder_name)
            os.makedirs(term_folder, exist_ok=True)
    
    # Create unmatched folder if configured
    if self.config['auto_sort_settings'].get('handle_no_matches') == 'move_to_unmatched':
        unmatched_folder = os.path.join(auto_sort_base, 'unmatched')
        os.makedirs(unmatched_folder, exist_ok=True)

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
        return os.path.join(auto_sort_base, folder_name)
    
    return None
```

## Configuration Migration

### Version Management
```python
class ConfigManager:
    CURRENT_VERSION = "2.0"
    
    def load_config(self):
        """Load configuration with version migration."""
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
            
            # Check version and migrate if needed
            config_version = loaded_config.get('config_version', '1.0')
            if config_version != self.CURRENT_VERSION:
                loaded_config = self.migrate_config(loaded_config, config_version)
            
            return {**self.default_config, **loaded_config}
            
        except FileNotFoundError:
            return self.default_config.copy()

    def migrate_config(self, old_config, from_version):
        """Migrate configuration from older versions."""
        if from_version == '1.0':
            # Add new fields with defaults
            old_config['auto_sort_terms'] = []
            old_config['auto_sort_settings'] = self.default_config['auto_sort_settings'].copy()
            old_config['metadata_cache'] = self.default_config['metadata_cache'].copy()
            old_config['ui_preferences'] = self.default_config['ui_preferences'].copy()
            
            # Add new output folders
            if 'auto_sorted' not in old_config['output_folders']:
                old_config['output_folders']['auto_sorted'] = 'auto_sorted'
            if 'unmatched' not in old_config['output_folders']:
                old_config['output_folders']['unmatched'] = 'unmatched'
        
        old_config['config_version'] = self.CURRENT_VERSION
        return old_config
```

## Term Configuration Validation

### Input Validation
```python
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
```

## Import/Export Functionality

### Term List Import/Export
```python
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
```

## Configuration Backup

### Automatic Backup
```python
def backup_config(self):
    """Create a backup of the current configuration."""
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

def save_config(self):
    """Save configuration with automatic backup."""
    # Create backup before saving
    if os.path.exists(self.config_file):
        self.backup_config()
    
    # Add version and timestamp
    self.config['config_version'] = self.CURRENT_VERSION
    self.config['last_saved'] = datetime.now().isoformat()
    
    # Save configuration
    with open(self.config_file, 'w') as f:
        json.dump(self.config, f, indent=2)
```