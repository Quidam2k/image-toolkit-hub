"""
Metadata Parser for Image Grid Sorter

Comprehensive metadata extraction from AI-generated images including:
- PNG metadata (parameters, workflows, etc.)
- EXIF data from JPEG files  
- Companion .txt tag files
- Cached parsing for performance
- Support for various AI image generators

Supported formats: PNG, JPEG, WebP
Version: 2.1
"""

import os
import html
import json
import re
import time
from collections import OrderedDict
from PIL import Image
from PIL.ExifTags import TAGS
import logging


# Default cache configuration
DEFAULT_MAX_CACHE_SIZE = 10000

class MetadataParser:
    """
    Extract and parse metadata from AI-generated images and companion files.
    
    Handles various metadata sources including embedded PNG parameters,
    EXIF data, and companion .txt files. Includes caching for performance
    and comprehensive parsing for multiple AI image generation tools.
    """
    
    def __init__(self, max_cache_size=None):
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.webp']
        self.cache = OrderedDict()  # LRU cache with size limit
        self.max_cache_size = max_cache_size or DEFAULT_MAX_CACHE_SIZE
        self.logger = logging.getLogger(__name__)
        self._compiled_patterns = {}  # Cache compiled regex patterns
    
    def extract_metadata(self, image_path):
        """Extract all available metadata from an image file and companion tag files."""
        if not os.path.exists(image_path):
            return {}
        
        # Check cache first
        file_mtime = os.path.getmtime(image_path)
        
        # Check if companion tag file exists and include its mtime in cache key
        tag_file_path = image_path + '.txt'
        tag_file_mtime = 0
        if os.path.exists(tag_file_path):
            tag_file_mtime = os.path.getmtime(tag_file_path)
        
        cache_key = f"{image_path}|{file_mtime}|{tag_file_mtime}"

        if cache_key in self.cache:
            # Move to end to mark as recently used (LRU)
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        
        metadata = {}
        file_ext = os.path.splitext(image_path)[1].lower()
        
        try:
            if file_ext == '.png':
                metadata = self.extract_png_metadata(image_path)
            elif file_ext in ['.jpg', '.jpeg']:
                metadata = self.extract_jpeg_metadata(image_path)
            elif file_ext == '.webp':
                metadata = self.extract_webp_metadata(image_path)
            
            # Parse Stable Diffusion parameters if found
            if 'parameters' in metadata:
                parsed_params = self.parse_sd_parameters(metadata['parameters'])
                metadata.update(parsed_params)
            
            # Extract tags from companion .txt file if it exists
            tag_content = self.extract_tag_file(image_path)
            if tag_content:
                metadata['tags'] = tag_content
            
            # Debug logging for metadata extraction
            if not metadata:
                self.logger.debug(f"No metadata found for {os.path.basename(image_path)}")
                self.logger.debug(f"  File extension: {file_ext}, exists: {os.path.exists(image_path)}")
                self.logger.debug(f"  Tag file exists: {os.path.exists(tag_file_path)}")
            else:
                self.logger.debug(f"Found {len(metadata)} metadata fields for {os.path.basename(image_path)}")

            # Cache the result with LRU eviction
            self.cache[cache_key] = metadata
            # Evict oldest entries if cache exceeds max size
            while len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)  # Remove oldest (first) item
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {image_path}: {e}")
            metadata = {}
        
        return metadata
    
    def extract_png_metadata(self, image_path):
        """Extract metadata from PNG text chunks (plus EXIF/XMP when present)."""
        metadata = {}

        try:
            with Image.open(image_path) as img:
                if hasattr(img, 'text') and img.text:
                    for key, value in img.text.items():
                        metadata[key] = value
                self._read_exif(img, metadata)
                self._read_xmp(img, metadata)
        except Exception as e:
            self.logger.error(f"Error reading PNG metadata from {image_path}: {e}")

        return metadata

    def extract_jpeg_metadata(self, image_path):
        """Extract metadata from JPEG EXIF and XMP data."""
        metadata = {}

        try:
            with Image.open(image_path) as img:
                self._read_exif(img, metadata)
                self._read_xmp(img, metadata)
        except Exception as e:
            self.logger.error(f"Error reading JPEG EXIF from {image_path}: {e}")

        return metadata

    def extract_webp_metadata(self, image_path):
        """Extract metadata from WebP images (info strings, EXIF, XMP)."""
        metadata = {}

        try:
            with Image.open(image_path) as img:
                if hasattr(img, 'info') and img.info:
                    for key, value in img.info.items():
                        if isinstance(value, str):
                            metadata[key] = value
                self._read_exif(img, metadata)
                self._read_xmp(img, metadata)
        except Exception as e:
            self.logger.error(f"Error reading WebP metadata from {image_path}: {e}")

        return metadata

    def _decode_exif_bytes(self, tag, value):
        """Decode an EXIF bytes value, honouring UserComment/XP* encodings."""
        if tag == 'UserComment' and len(value) >= 8:
            prefix, body = value[:8], value[8:]
            if prefix == b'UNICODE\x00':
                # Byte order is not recorded; pick the decode that looks like text.
                candidates = [body.decode(enc, errors='ignore') for enc in ('utf-16-be', 'utf-16-le')]
                return max(candidates, key=lambda s: sum(1 for c in s if ' ' <= c <= '~')).strip('\x00')
            if prefix == b'ASCII\x00\x00\x00':
                return body.decode('ascii', errors='ignore').strip('\x00')
        if tag.startswith('XP'):
            return value.decode('utf-16-le', errors='ignore').strip('\x00')
        return value.decode('utf-8', errors='ignore').strip('\x00')

    def _read_exif(self, img, metadata):
        """Copy EXIF tags (base IFD + Exif IFD, where UserComment lives) into metadata."""
        try:
            exif_data = img.getexif()
        except Exception:
            return
        if not exif_data:
            return

        items = list(exif_data.items())
        try:
            items += list(exif_data.get_ifd(0x8769).items())
        except Exception:
            pass

        for tag_id, value in items:
            tag = TAGS.get(tag_id, str(tag_id))

            # Convert bytes to string if needed
            if isinstance(value, bytes):
                try:
                    value = self._decode_exif_bytes(tag, value)
                except (UnicodeDecodeError, AttributeError):
                    continue

            metadata[tag] = value
            if not isinstance(value, str):
                continue

            # ComfyUI WebP/JPEG savers stash the graph in EXIF as "prompt:{json}"
            if value.startswith('prompt:'):
                metadata.setdefault('prompt', value[len('prompt:'):])
            elif value.startswith('workflow:'):
                metadata.setdefault('workflow', value[len('workflow:'):])

            # Look for SD parameters in specific fields
            if tag in ['UserComment', 'ImageDescription', 'XPComment']:
                if any(keyword in value.lower() for keyword in ['steps:', 'sampler:', 'cfg scale:']):
                    metadata['parameters'] = value
                # Check for embedded tags
                elif 'TAGS:' in value:
                    self._extract_embedded_tags_from_field(metadata, value)

    def _read_xmp(self, img, metadata):
        """Pull dc:description out of the raw XMP packet (no defusedxml needed)."""
        raw = img.info.get('xmp') or img.info.get('XML:com.adobe.xmp')
        if not raw:
            return
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='ignore')
        match = re.search(r'<dc:description>.*?<rdf:li[^>]*>(.*?)</rdf:li>', raw, re.DOTALL)
        if not match:
            match = re.search(r'dc:description="([^"]*)"', raw)
        if match:
            text = html.unescape(match.group(1)).strip()
            if text:
                metadata['xmp_description'] = text

    # ------------------------------------------------------------------
    # Prompt lookup across generators (A1111, ComfyUI, Midjourney)
    # ------------------------------------------------------------------

    _COMFY_TEXT_KEYS = ('text', 'text_g', 'text_l', 't5xxl', 'clip_l', 'prompt', 'string',
                        'value', 'text_a', 'text_b', 'string_a', 'string_b', 'text1', 'text2')
    _COMFY_COND_KEYS = ('conditioning', 'conditioning_1', 'conditioning_2',
                        'conditioning_to', 'conditioning_from', 'guider')

    def get_prompt_text(self, metadata):
        """Best-effort positive prompt for an image. Returns (text, source).

        Sources tried in order: A1111 positive_prompt, ComfyUI graph, Midjourney/
        description fields, companion tags, raw parameters. ("", "") if none.
        """
        if not metadata:
            return "", ""

        text = metadata.get('positive_prompt')
        if isinstance(text, str) and text.strip():
            return text.strip(), 'a1111'

        text = self._comfy_prompt_text(metadata.get('prompt'), metadata.get('workflow'))
        if text:
            return text, 'comfyui'

        for key in ('Description', 'xmp_description', 'ImageDescription'):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                cleaned = re.sub(r'\s*Job ID:\s*[0-9a-fA-F-]+\s*$', '', value.strip()).strip()
                if cleaned:
                    is_mj = cleaned != value.strip() or ' --' in cleaned
                    return cleaned, ('midjourney' if is_mj else 'description')

        for key, source in (('tags', 'tags'), ('parameters', 'parameters'), ('raw_parameters', 'parameters')):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip(), source

        return "", ""

    @staticmethod
    def _is_comfy_link(value):
        return (isinstance(value, list) and len(value) == 2
                and isinstance(value[0], (str, int)) and isinstance(value[1], int))

    # Display/echo nodes (ShowText|pysssss and friends) mirror the *runtime* value
    # of the link they consume into numbered widget strings. That value is the
    # wildcard-resolved prompt, whereas the upstream template node still holds the
    # unresolved ``||wildcard||`` text.
    _COMFY_ECHO_LINK_KEYS = ('text', 'string', 'anything', 'any', 'value', 'input',
                             'text_input', 'source')
    _COMFY_ECHO_VALUE_RE = re.compile(r'^(?:text|string|value|output|anything)_(\d+)$')

    def _comfy_resolved_texts(self, nodes):
        """Map '<src_node>:<slot>' -> echoed runtime text, from display/echo nodes."""
        resolved = {}
        for node in nodes.values():
            inputs = node.get('inputs')
            if not isinstance(inputs, dict):
                continue
            link = next((inputs[k] for k in self._COMFY_ECHO_LINK_KEYS
                         if self._is_comfy_link(inputs.get(k))), None)
            if link is None:
                continue
            parts = []
            for key, value in inputs.items():
                match = self._COMFY_ECHO_VALUE_RE.match(str(key))
                if match and isinstance(value, str) and value.strip():
                    parts.append((int(match.group(1)), value.strip()))
            if not parts:
                continue
            # Key on node *and* slot: one node can echo several outputs of another
            # (e.g. a dedupe report on slot 1 alongside the prompt on slot 0).
            resolved.setdefault('{}:{}'.format(link[0], link[1]),
                                '\n'.join(v for _, v in sorted(parts)))
        return resolved

    def _comfy_follow(self, graph, link, polarity, visited, texts, resolved=None):
        """Walk upstream from a conditioning/text link, collecting prompt strings."""
        if resolved:
            # Stop at the last node whose output was echoed: that is the populated
            # prompt, after wildcards/expanders have been evaluated.
            echoed = resolved.get('{}:{}'.format(link[0], link[1]))
            if echoed:
                if echoed not in texts:
                    texts.append(echoed)
                return
        node_id = str(link[0])
        if node_id in visited:
            return
        visited.add(node_id)
        node = graph.get(node_id)
        if not isinstance(node, dict):
            return
        inputs = node.get('inputs')
        if not isinstance(inputs, dict):
            return

        found_text = False
        for key in self._COMFY_TEXT_KEYS:
            value = inputs.get(key)
            if isinstance(value, str):
                found_text = True
                if value.strip() and value.strip() not in texts:
                    texts.append(value.strip())
            elif self._is_comfy_link(value):
                found_text = True
                self._comfy_follow(graph, value, polarity, visited, texts, resolved)
        if found_text:
            return

        # Pass-through node (combine/concat/controlnet/guidance/guider): keep walking.
        for key in (polarity,) + self._COMFY_COND_KEYS:
            value = inputs.get(key)
            if self._is_comfy_link(value):
                self._comfy_follow(graph, value, polarity, visited, texts, resolved)

    def _comfy_prompt_text(self, prompt_chunk, workflow_chunk=None):
        """Extract the positive prompt from ComfyUI 'prompt' (API graph) / 'workflow' chunks."""
        graph = self._load_json_chunk(prompt_chunk)
        if isinstance(graph, dict):
            nodes = {str(k): v for k, v in graph.items() if isinstance(v, dict)}
            resolved = self._comfy_resolved_texts(nodes)

            # 1. Follow each sampler's positive (or guider) input.
            texts = []
            for node in nodes.values():
                inputs = node.get('inputs')
                if 'sampler' not in str(node.get('class_type', '')).lower() or not isinstance(inputs, dict):
                    continue
                for key in ('positive', 'guider'):
                    if self._is_comfy_link(inputs.get(key)):
                        self._comfy_follow(nodes, inputs[key], 'positive', set(), texts, resolved)
            if texts:
                return ', '.join(texts)

            # 2. Any CLIPTextEncode text not reachable from a negative input.
            negative_ids = set()
            for node in nodes.values():
                inputs = node.get('inputs')
                if isinstance(inputs, dict) and self._is_comfy_link(inputs.get('negative')):
                    self._comfy_follow(nodes, inputs['negative'], 'negative', negative_ids, [])
            for node_id, node in nodes.items():
                if node_id in negative_ids or 'cliptextencode' not in str(node.get('class_type', '')).lower():
                    continue
                self._comfy_follow(nodes, [node_id, 0], 'positive', set(), texts, resolved)
            if texts:
                return ', '.join(texts)

        # 3. Last resort: widget strings on text-encode nodes in the UI workflow.
        workflow = self._load_json_chunk(workflow_chunk)
        if isinstance(workflow, dict) and isinstance(workflow.get('nodes'), list):
            link_source = {}
            for link in workflow.get('links') or []:
                if isinstance(link, list) and len(link) >= 2:
                    link_source[link[0]] = link[1]
            negative_nodes = set()
            for node in workflow['nodes']:
                for inp in (node.get('inputs') or []) if isinstance(node, dict) else []:
                    if isinstance(inp, dict) and inp.get('name') == 'negative' and inp.get('link') in link_source:
                        negative_nodes.add(link_source[inp['link']])
            texts = []
            for node in workflow['nodes']:
                if not isinstance(node, dict) or 'textencode' not in str(node.get('type', '')).lower():
                    continue
                if node.get('id') in negative_nodes or 'neg' in str(node.get('title', '')).lower():
                    continue
                for value in node.get('widgets_values') or []:
                    if isinstance(value, str) and value.strip() and value.strip() not in texts:
                        texts.append(value.strip())
            if texts:
                return ', '.join(texts)

        return ""

    @staticmethod
    def _load_json_chunk(chunk):
        if not isinstance(chunk, str) or not chunk.strip().startswith('{'):
            return None
        try:
            return json.loads(chunk)
        except (ValueError, RecursionError):
            return None
    
    def extract_tag_file(self, image_path):
        """Extract content from companion .txt tag file."""
        tag_file_path = image_path + '.txt'
        
        if not os.path.exists(tag_file_path):
            return None
        
        try:
            with open(tag_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content if content else None
        except Exception as e:
            self.logger.error(f"Error reading tag file {tag_file_path}: {e}")
            return None
    
    def _extract_embedded_tags_from_field(self, metadata, field_value):
        """Extract embedded tags from EXIF field value."""
        try:
            if 'TAGS:' in field_value:
                # Find the tags part
                tags_start = field_value.find('TAGS:')
                if tags_start != -1:
                    tags_part = field_value[tags_start + 5:]  # Skip 'TAGS:'
                    
                    # If there's a separator, take only the tags part
                    if ' | ' in tags_part:
                        tags_part = tags_part.split(' | ')[0]
                    
                    # Add to metadata
                    if tags_part.strip():
                        metadata['tags'] = tags_part.strip()
                        metadata['tags_source'] = 'embedded'
        except Exception as e:
            self.logger.debug(f"Error extracting embedded tags: {e}")
    
    def parse_sd_parameters(self, param_string):
        """Parse Stable Diffusion parameters into structured data."""
        if not param_string or not isinstance(param_string, str):
            return {}
        
        result = {}
        
        try:
            lines = param_string.strip().split('\n')
            
            # Extract positive prompt (first line or before "Negative prompt:")
            positive_prompt = ""
            negative_prompt = ""
            parameters = {}
            
            # Process lines to separate prompts from parameters
            param_line = ""
            prompt_lines = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('Negative prompt:'):
                    # Extract negative prompt
                    negative_prompt = line.replace('Negative prompt:', '').strip()
                elif any(param in line for param in ['Steps:', 'Sampler:', 'CFG scale:', 'Seed:', 'Size:', 'Model:']):
                    # This looks like a parameters line
                    param_line = line
                    break
                else:
                    # This is part of the positive prompt
                    prompt_lines.append(line)
            
            # Join prompt lines
            positive_prompt = ' '.join(prompt_lines).strip()
            
            # Handle case where negative prompt is on same line as positive
            if 'Negative prompt:' in positive_prompt:
                parts = positive_prompt.split('Negative prompt:', 1)
                positive_prompt = parts[0].strip()
                if len(parts) > 1 and not negative_prompt:
                    negative_prompt = parts[1].strip()
            
            result['positive_prompt'] = positive_prompt
            result['negative_prompt'] = negative_prompt
            
            # Parse technical parameters
            if param_line:
                param_pairs = param_line.split(', ')
                for pair in param_pairs:
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert numeric values
                        if key in ['Steps', 'CFG scale', 'Seed']:
                            try:
                                if '.' in value:
                                    parameters[key] = float(value)
                                else:
                                    parameters[key] = int(value)
                            except ValueError:
                                parameters[key] = value
                        else:
                            parameters[key] = value
            
            result['parameters'] = parameters
            
        except Exception as e:
            self.logger.error(f"Error parsing SD parameters: {e}")
            result = {'raw_parameters': param_string}
        
        return result
    
    def search_terms_in_metadata(self, metadata, search_terms):
        """Search for specific terms in metadata with scope control."""
        if not metadata or not search_terms:
            return []
        
        matches = []

        # Prepare separate text sources
        prompt_text = ""
        tag_text = ""
        other_metadata_text = ""

        # Build prompt text (from positive_prompt only)
        if 'positive_prompt' in metadata:
            prompt_text += metadata['positive_prompt'] + " "

        # Build tag text (ONLY from tags field - .txt files or embedded tags)
        if 'tags' in metadata:
            tag_text += metadata['tags'] + " "

        # Build other metadata text (for legacy 'either' mode fallback)
        for key, value in metadata.items():
            if isinstance(value, str) and key not in ['positive_prompt', 'negative_prompt', 'parameters', 'tags']:
                other_metadata_text += value + " "

        # Search for each term
        for term_config in search_terms:
            if not term_config.get('enabled', True):
                continue
            
            # Get search scope settings
            search_scope = term_config.get('search_scope', 'either')
            include_negative = term_config.get('include_negative_prompt', False)
            
            # Add negative prompt to prompt text if enabled
            current_prompt_text = prompt_text
            if include_negative and 'negative_prompt' in metadata:
                current_prompt_text += metadata['negative_prompt'] + " "
            
            # Determine what text to search based on scope
            if search_scope == 'prompt_only':
                search_texts = [current_prompt_text] if current_prompt_text.strip() else []
            elif search_scope == 'tags_only':
                # ONLY search in actual tags (from .txt files or embedded tags)
                search_texts = [tag_text] if tag_text.strip() else []
            elif search_scope == 'either':
                # OR logic - search in prompts, tags, AND other metadata (legacy behavior)
                search_texts = []
                if current_prompt_text.strip():
                    search_texts.append(current_prompt_text)
                if tag_text.strip():
                    search_texts.append(tag_text)
                if other_metadata_text.strip():
                    search_texts.append(other_metadata_text)
            elif search_scope == 'both':
                # AND logic - must be found in both prompts AND tags
                search_texts = 'both_required'
            
            # Perform the search
            term = term_config['term'].strip()
            match_type = term_config.get('match_type', 'word_boundary')
            case_sensitive = term_config.get('case_sensitive', False)
            
            if search_scope == 'both':
                # Special handling for AND logic
                prompt_match = self._search_term_in_text(current_prompt_text, term, match_type, case_sensitive)
                tag_match = self._search_term_in_text(tag_text, term, match_type, case_sensitive)
                
                if prompt_match and tag_match:
                    matches.append(term_config)
            else:
                # OR logic or single source
                found = False
                for search_text in search_texts:
                    if self._search_term_in_text(search_text, term, match_type, case_sensitive):
                        found = True
                        break
                
                if found:
                    matches.append(term_config)
        
        # Sort matches by priority
        matches.sort(key=lambda x: x.get('priority', 999))
        return matches
    
    def _get_compiled_pattern(self, term, match_type, case_sensitive):
        """Get or compile a regex pattern, caching the result."""
        cache_key = (term, match_type, case_sensitive)

        if cache_key in self._compiled_patterns:
            return self._compiled_patterns[cache_key]

        try:
            search_term = term if case_sensitive else term.lower()
            flags = 0 if case_sensitive else re.IGNORECASE

            if match_type == 'word_boundary':
                pattern = re.compile(r'\b' + re.escape(search_term) + r'\b', flags)
            elif match_type == 'regex':
                pattern = re.compile(search_term, flags)
            else:
                # For 'exact' and 'contains', we don't need to compile
                pattern = None

            self._compiled_patterns[cache_key] = pattern
            return pattern
        except re.error:
            self._compiled_patterns[cache_key] = None
            return None

    def _search_term_in_text(self, text, term, match_type, case_sensitive):
        """Search for a single term in text using specified match type."""
        if not text or not term:
            return False

        search_text = text if case_sensitive else text.lower()
        search_term = term if case_sensitive else term.lower()

        if match_type == 'exact':
            return search_term == search_text.strip()
        elif match_type == 'contains':
            return search_term in search_text
        elif match_type == 'word_boundary':
            pattern = self._get_compiled_pattern(term, match_type, case_sensitive)
            if pattern:
                return bool(pattern.search(search_text))
            return False
        elif match_type == 'regex':
            pattern = self._get_compiled_pattern(term, match_type, case_sensitive)
            if pattern:
                return bool(pattern.search(search_text))
            return False

        return False
    
    def clear_cache(self):
        """Clear the metadata cache."""
        self.cache.clear()
    
    def get_cache_size(self):
        """Get the current cache size."""
        return len(self.cache)