# Metadata Handling Specification

## Overview
This document specifies how to extract and parse metadata from AI-generated images, particularly those created with Stable Diffusion WebUI Forge.

## Metadata Storage Formats

### PNG Images
Stable Diffusion WebUI typically stores metadata in PNG text chunks:
- **`parameters`** - Contains generation parameters, prompt, negative prompt, etc.
- **`workflow`** - ComfyUI workflow data (if applicable)
- **`prompt`** - Raw prompt text

### JPEG Images
JPEG images store metadata in EXIF data:
- **`UserComment`** - Often contains generation parameters
- **`ImageDescription`** - May contain prompt information
- **`Software`** - Identifies the generating software

## Required Dependencies
```python
from PIL import Image
from PIL.ExifTags import TAGS
import json
import re
```

## Metadata Extraction Implementation

### Core Metadata Parser Class
```python
class MetadataParser:
    def __init__(self):
        self.supported_formats = ['.png', '.jpg', '.jpeg']
    
    def extract_metadata(self, image_path):
        """Extract all available metadata from an image file."""
        pass
    
    def parse_parameters(self, parameters_text):
        """Parse Stable Diffusion parameters string."""
        pass
    
    def search_terms_in_metadata(self, metadata, search_terms):
        """Search for specific terms in metadata."""
        pass
```

### PNG Metadata Extraction
```python
def extract_png_metadata(self, image_path):
    """Extract metadata from PNG text chunks."""
    try:
        with Image.open(image_path) as img:
            metadata = {}
            if hasattr(img, 'text'):
                for key, value in img.text.items():
                    metadata[key] = value
            return metadata
    except Exception as e:
        return {}
```

### JPEG EXIF Extraction
```python
def extract_jpeg_metadata(self, image_path):
    """Extract metadata from JPEG EXIF data."""
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            metadata = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                metadata[tag] = value
            return metadata
    except Exception as e:
        return {}
```

## Stable Diffusion Parameter Parsing

### Parameter String Format
Typical Stable Diffusion parameters string:
```
masterpiece, detailed face, beautiful woman
Negative prompt: ugly, blurry, distorted
Steps: 20, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 1234567890, Size: 512x768, Model hash: abcd1234, Model: mymodel_v1.safetensors
```

### Parsing Logic
```python
def parse_sd_parameters(self, param_string):
    """Parse Stable Diffusion parameters into structured data."""
    if not param_string:
        return {}
    
    lines = param_string.strip().split('\n')
    result = {}
    
    # Extract positive prompt (first line before "Negative prompt:")
    positive_prompt = lines[0]
    if 'Negative prompt:' in positive_prompt:
        positive_prompt = positive_prompt.split('Negative prompt:')[0].strip()
    result['positive_prompt'] = positive_prompt
    
    # Extract negative prompt
    negative_prompt = ""
    for line in lines:
        if line.startswith('Negative prompt:'):
            negative_prompt = line.replace('Negative prompt:', '').strip()
            break
    result['negative_prompt'] = negative_prompt
    
    # Extract technical parameters
    param_line = lines[-1] if lines else ""
    params = {}
    param_pairs = param_line.split(', ')
    for pair in param_pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)
            params[key.strip()] = value.strip()
    result['parameters'] = params
    
    return result
```

## Term Matching Strategy

### Search Methods
1. **Exact Match**: Direct string matching in prompts
2. **Partial Match**: Substring matching with word boundaries
3. **Regex Match**: Pattern-based matching for complex terms
4. **Tag-based**: Matching specific prompt tags/tokens

### Implementation
```python
def find_matching_terms(self, metadata, search_terms):
    """Find which search terms match the image metadata."""
    matches = []
    
    # Combine all searchable text
    searchable_text = ""
    if 'positive_prompt' in metadata:
        searchable_text += metadata['positive_prompt'].lower() + " "
    if 'negative_prompt' in metadata:
        searchable_text += metadata['negative_prompt'].lower() + " "
    
    # Check each search term
    for term in search_terms:
        term_lower = term.lower().strip()
        
        # Word boundary matching to avoid partial word matches
        pattern = r'\b' + re.escape(term_lower) + r'\b'
        if re.search(pattern, searchable_text):
            matches.append(term)
    
    return matches
```

## Performance Considerations

### Caching Strategy
- Cache parsed metadata to avoid re-parsing
- Store metadata in lightweight format (JSON)
- Implement LRU cache for frequently accessed images

### Batch Processing
- Process metadata in background threads
- Update progress indicators for long operations
- Allow cancellation of metadata scanning

### Error Handling
- Gracefully handle corrupted metadata
- Log parsing errors for debugging
- Continue processing even if individual files fail

## File Structure Updates

### New Files to Create
- `metadata_parser.py` - Core metadata extraction and parsing
- `auto_sorter.py` - Automatic sorting logic based on metadata
- `term_manager.py` - UI and logic for managing search terms

### Integration Points
- Extend `ConfigManager` to store search terms
- Add metadata operations to `ImageLoader`
- Update `UIManager` for new controls
- Integrate with existing undo/history system