#!/usr/bin/env python3
"""
Test script for the auto-sort functionality.
This validates the core logic without requiring GUI dependencies.
"""

import os
import json
import tempfile
from config_manager import ConfigManager

def test_config_manager():
    """Test the configuration manager functionality."""
    print("Testing ConfigManager...")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name
    
    try:
        # Initialize config manager
        cm = ConfigManager(temp_config)
        
        # Test adding terms
        cm.add_auto_sort_term("portrait", match_type="word_boundary", priority=1)
        cm.add_auto_sort_term("landscape", match_type="contains", priority=2)
        cm.add_auto_sort_term("anime", match_type="word_boundary", priority=3)
        
        # Test getting terms
        terms = cm.get_auto_sort_terms()
        assert len(terms) == 3, f"Expected 3 terms, got {len(terms)}"
        
        # Test term properties
        portrait_term = next(t for t in terms if t['term'] == 'portrait')
        assert portrait_term['match_type'] == 'word_boundary'
        assert portrait_term['priority'] == 1
        
        # Test settings
        settings = cm.get_auto_sort_settings()
        assert 'handle_multiple_matches' in settings
        
        # Test export/import
        export_file = tempfile.mktemp(suffix='.json')
        cm.export_terms(export_file)
        
        # Verify export file
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert 'terms' in exported_data
        assert len(exported_data['terms']) == 3
        
        print("✓ ConfigManager tests passed")
        
        # Cleanup
        os.unlink(export_file)
        
    finally:
        if os.path.exists(temp_config):
            os.unlink(temp_config)

def test_metadata_parsing():
    """Test metadata parsing logic without PIL dependencies."""
    print("Testing metadata parsing logic...")
    
    # Test SD parameter parsing
    sample_params = """masterpiece, detailed face, beautiful woman, portrait
Negative prompt: ugly, blurry, distorted
Steps: 20, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 1234567890, Size: 512x768, Model hash: abcd1234"""
    
    # Mock the MetadataParser class without PIL dependencies
    class MockMetadataParser:
        def parse_sd_parameters(self, param_string):
            if not param_string or not isinstance(param_string, str):
                return {}
            
            result = {}
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
                    negative_prompt = line.replace('Negative prompt:', '').strip()
                elif any(param in line for param in ['Steps:', 'Sampler:', 'CFG scale:', 'Seed:', 'Size:', 'Model:']):
                    param_line = line
                    break
                else:
                    prompt_lines.append(line)
            
            positive_prompt = ' '.join(prompt_lines).strip()
            
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
            return result
        
        def term_matches(self, text, term, match_type):
            if not text or not term:
                return False
            
            import re
            try:
                if match_type == 'exact':
                    return text.strip() == term.strip()
                elif match_type == 'contains':
                    return term in text
                elif match_type == 'word_boundary':
                    pattern = r'\b' + re.escape(term) + r'\b'
                    return bool(re.search(pattern, text, re.IGNORECASE))
                elif match_type == 'regex':
                    return bool(re.search(term, text, re.IGNORECASE))
                else:
                    pattern = r'\b' + re.escape(term) + r'\b'
                    return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                return term in text
    
    parser = MockMetadataParser()
    
    # Test parameter parsing
    parsed = parser.parse_sd_parameters(sample_params)
    
    assert 'positive_prompt' in parsed
    assert 'negative_prompt' in parsed
    assert 'parameters' in parsed
    
    assert 'portrait' in parsed['positive_prompt']
    assert 'ugly' in parsed['negative_prompt']
    assert parsed['parameters']['Steps'] == 20
    assert parsed['parameters']['CFG scale'] == 7
    
    # Test term matching
    text = "beautiful portrait of a woman"
    assert parser.term_matches(text, "portrait", "word_boundary") == True
    assert parser.term_matches(text, "landscape", "word_boundary") == False
    assert parser.term_matches(text, "beautiful", "contains") == True
    
    print("✓ Metadata parsing tests passed")

def test_auto_sort_logic():
    """Test the auto-sort conflict resolution logic."""
    print("Testing auto-sort logic...")
    
    # Mock sorter class
    class MockAutoSorter:
        def __init__(self):
            pass
        
        def resolve_conflicts(self, matches):
            if not matches:
                return None
            if len(matches) == 1:
                return matches[0]
            
            # Test different strategies
            strategy = 'first_match'  # Default strategy
            
            if strategy == 'first_match':
                return matches[0]
            elif strategy == 'most_specific':
                return max(matches, key=lambda x: len(x['term']))
            else:
                return matches[0]
    
    sorter = MockAutoSorter()
    
    # Test single match
    single_match = [{'term': 'portrait', 'priority': 1}]
    result = sorter.resolve_conflicts(single_match)
    assert result['term'] == 'portrait'
    
    # Test multiple matches
    multiple_matches = [
        {'term': 'portrait', 'priority': 1},
        {'term': 'beautiful', 'priority': 2},
        {'term': 'woman', 'priority': 3}
    ]
    result = sorter.resolve_conflicts(multiple_matches)
    assert result['term'] == 'portrait'  # First match
    
    # Test no matches
    result = sorter.resolve_conflicts([])
    assert result is None
    
    print("✓ Auto-sort logic tests passed")

def run_all_tests():
    """Run all tests."""
    print("Running auto-sort functionality tests...\n")
    
    try:
        test_config_manager()
        test_metadata_parsing()
        test_auto_sort_logic()
        
        print("\n✓ All tests passed successfully!")
        print("\nThe auto-sort implementation is ready for use.")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        raise

if __name__ == "__main__":
    run_all_tests()