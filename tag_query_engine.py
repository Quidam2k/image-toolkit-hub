"""
Tag Query Engine - Parse and execute flexible tag queries against the frequency database.

Supports:
  - Single tags: "blowjob"
  - AND queries: "blowjob,succubus" or "blowjob AND succubus"
  - OR queries: "blowjob|succubus" or "blowjob OR succubus"
  - NOT queries: "blowjob,!elf" or "blowjob AND NOT elf"
  - Complex: "(blowjob|succubus),!elf"

Database format (tag_frequency.json):
  {
    "tags": {
      "blowjob": {"count": 2921, "images": [...]},
      "succubus": {"count": 1632, "images": [...]},
      ...
    }
  }
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

logger = logging.getLogger(__name__)


class TagQueryEngine:
    """Query and match tags against the tag frequency database."""

    def __init__(self, db_file: str = 'tag_frequency.json'):
        """Initialize engine with database file path."""
        self.db_file = db_file
        self.database = None
        self.tags_db = {}  # Normalized tag → images mapping
        self.tag_list = []  # All available tags
        self.image_index = {}  # image → tags mapping (for validation)

    def load_database(self) -> bool:
        """Load and index the tag frequency database.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db_path = Path(self.db_file)
            if not db_path.exists():
                logger.error(f"Database file not found: {self.db_file}")
                return False

            with open(db_path, 'r', encoding='utf-8') as f:
                self.database = json.load(f)

            # Build indexes
            if 'tags' not in self.database:
                logger.error("Invalid database format: missing 'tags' key")
                return False

            # Index tags and images
            for tag, tag_data in self.database['tags'].items():
                tag_normalized = tag.lower()
                images = tag_data.get('images', [])
                self.tags_db[tag_normalized] = set(images)
                self.tag_list.append(tag_normalized)

                # Build reverse index
                for image in images:
                    if image not in self.image_index:
                        self.image_index[image] = set()
                    self.image_index[image].add(tag_normalized)

            # Build full path index by scanning auto_sorted folder
            self._build_full_path_index()

            logger.info(f"Loaded database: {len(self.tag_list)} tags, "
                       f"{len(self.image_index)} images")
            return True

        except Exception as e:
            logger.error(f"Failed to load database: {e}")
            return False

    def _build_full_path_index(self) -> None:
        """Build full path index by scanning master_images folder."""
        master_images = Path('master_images')
        if not master_images.exists():
            logger.warning("master_images folder not found, using relative filenames")
            return

        self.full_path_index = {}
        try:
            for image_file in master_images.glob('*'):
                if image_file.is_file() and self._is_image_file(image_file):
                    filename = image_file.name
                    if filename not in self.full_path_index:
                        self.full_path_index[filename] = str(image_file)
            logger.info(f"Built full path index: {len(self.full_path_index)} files")
        except Exception as e:
            logger.warning(f"Failed to build full path index: {e}")

    def _is_image_file(self, path: Path) -> bool:
        """Check if file is a supported image format."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return path.suffix.lower() in image_extensions

    def list_available_tags(self) -> List[Tuple[str, int]]:
        """List all available tags with counts, sorted by frequency.

        Returns:
            List of (tag, count) tuples, sorted by count descending
        """
        if not self.database:
            return []

        tags_with_counts = []
        for tag, tag_data in self.database['tags'].items():
            count = tag_data.get('count', 0)
            tags_with_counts.append((tag, count))

        return sorted(tags_with_counts, key=lambda x: x[1], reverse=True)

    def parse_query(self, query_string: str) -> Optional[Dict]:
        """Parse a query string into a structured format.

        Query formats:
            "blowjob"                    → Single tag
            "blowjob,succubus"          → AND
            "blowjob|succubus"          → OR
            "blowjob,!elf"              → AND with NOT
            "(blowjob|succubus),!elf"   → Complex

        Returns:
            Dict with keys:
                - include_tags: list of tags to match
                - exclude_tags: list of tags to exclude
                - operator: 'AND' or 'OR' for include_tags
            Returns None if parsing fails
        """
        query = query_string.strip()

        if not query:
            logger.error("Empty query string")
            return None

        try:
            # Handle parentheses for grouping
            query = query.replace('(', '').replace(')', '')

            # Split by comma for main AND operations
            and_parts = [p.strip() for p in query.split(',')]

            include_tags = []
            exclude_tags = []
            main_operator = 'AND'

            for part in and_parts:
                if not part:
                    continue

                # Check for exclusion (NOT)
                if part.startswith('!'):
                    tag = part[1:].lower().strip()
                    exclude_tags.append(tag)
                    continue

                # Check for OR within this part
                if '|' in part:
                    or_tags = [t.strip().lower() for t in part.split('|')]
                    include_tags.extend(or_tags)
                    if len(and_parts) == 1:  # This is the only AND part
                        main_operator = 'OR'
                else:
                    # Single tag
                    tag = part.lower().strip()
                    include_tags.append(tag)

            # Determine operator
            if len(include_tags) <= 1:
                operator = 'SINGLE'
            elif '|' in query:
                operator = 'OR'
            else:
                operator = 'AND'

            return {
                'operator': operator,
                'include_tags': include_tags,
                'exclude_tags': exclude_tags,
            }

        except Exception as e:
            logger.error(f"Failed to parse query '{query}': {e}")
            return None

    def validate_query(self, query_string: str) -> Tuple[bool, Optional[str]]:
        """Validate a query string.

        Returns:
            (is_valid, error_message)
        """
        parsed = self.parse_query(query_string)
        if parsed is None:
            return False, "Invalid query syntax"

        if not self.database:
            return False, "Database not loaded"

        all_requested_tags = set(parsed['include_tags'] + parsed['exclude_tags'])
        available_tags = set(self.tag_list)

        invalid_tags = all_requested_tags - available_tags

        if invalid_tags:
            suggestions = self._find_similar_tags(list(invalid_tags)[0])
            msg = f"Unknown tags: {', '.join(invalid_tags)}"
            if suggestions:
                msg += f"\nDid you mean: {', '.join(suggestions[:3])}?"
            return False, msg

        return True, None

    def find_matching_images(self, parsed_query: Dict) -> List[str]:
        """Find images matching the parsed query.

        Returns:
            Sorted list of matching image paths (full paths if available)
        """
        if not self.database or not parsed_query:
            return []

        include_tags = parsed_query.get('include_tags', [])
        exclude_tags = parsed_query.get('exclude_tags', [])
        operator = parsed_query.get('operator', 'AND')

        if not include_tags:
            return []

        # Get image sets for each tag
        tag_image_sets = {}
        for tag in include_tags + exclude_tags:
            tag_normalized = tag.lower()
            if tag_normalized in self.tags_db:
                tag_image_sets[tag_normalized] = self.tags_db[tag_normalized]
            else:
                tag_image_sets[tag_normalized] = set()

        # Apply inclusion logic
        if operator == 'SINGLE':
            result = tag_image_sets.get(include_tags[0].lower(), set())
        elif operator == 'AND':
            # Intersection of all include tags
            result = set(tag_image_sets.get(include_tags[0].lower(), set()))
            for tag in include_tags[1:]:
                result = result.intersection(tag_image_sets.get(tag.lower(), set()))
        else:  # OR
            # Union of all include tags
            result = set()
            for tag in include_tags:
                result = result.union(tag_image_sets.get(tag.lower(), set()))

        # Apply exclusion logic
        for tag in exclude_tags:
            result = result - tag_image_sets.get(tag.lower(), set())

        # Convert to full paths if available
        result_with_paths = []
        if hasattr(self, 'full_path_index'):
            for filename in result:
                full_path = self.full_path_index.get(filename, filename)
                result_with_paths.append(full_path)
        else:
            result_with_paths = list(result)

        return sorted(result_with_paths)

    def query(self, query_string: str) -> Tuple[bool, List[str], Optional[str]]:
        """Execute a query (validate, parse, and match).

        Returns:
            (success, images, error_message)
        """
        # Validate first
        is_valid, error_msg = self.validate_query(query_string)
        if not is_valid:
            return False, [], error_msg

        # Parse
        parsed = self.parse_query(query_string)
        if parsed is None:
            return False, [], "Failed to parse query"

        # Execute
        results = self.find_matching_images(parsed)

        return True, results, None

    def _find_similar_tags(self, tag: str, limit: int = 3) -> List[str]:
        """Find similar tags (for error suggestions)."""
        tag = tag.lower()

        # Simple similarity: tags that share significant substrings
        similar = []
        for available_tag in self.tag_list:
            if tag in available_tag or available_tag in tag:
                similar.append(available_tag)
            elif self._levenshtein_distance(tag, available_tag) <= 2:
                similar.append(available_tag)

        return sorted(similar)[:limit]

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return TagQueryEngine._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    engine = TagQueryEngine()
    if not engine.load_database():
        print("Failed to load database")
        exit(1)

    # Test queries
    test_queries = [
        "blowjob",
        "blowjob,succubus",
        "blowjob|succubus",
        "blowjob,!elf",
    ]

    for query in test_queries:
        success, images, error = engine.query(query)
        if success:
            print(f"Query: {query}")
            print(f"  Found: {len(images)} images")
            if images:
                print(f"  Sample: {images[:3]}")
        else:
            print(f"Query: {query}")
            print(f"  Error: {error}")
        print()
