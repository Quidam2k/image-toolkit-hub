"""
Visual Classifier for Image Grid Sorter

Provides visual classification for LoRA-specific sorting including:
- Shot composition (portrait, upper_body, cowboy_shot, full_body, wide_shot)
- Person count (solo, duo, group)
- NSFW rating (safe, sensitive, questionable, explicit)

Uses WD14 tagger for visual analysis and optionally YOLO for person detection.

Author: Claude Code Implementation
Version: 1.0
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ShotType(Enum):
    """Shot composition types for LoRA sorting."""
    EXTREME_CLOSEUP = "extreme_closeup"  # close-up tag
    PORTRAIT = "portrait"  # portrait, face close-up
    UPPER_BODY = "upper_body"  # upper body / half portrait
    COWBOY = "cowboy_shot"  # mid-body, thighs up
    FULL_BODY = "full_body"  # full body visible
    WIDE_SHOT = "wide_shot"  # wide angle, person smaller in frame
    UNKNOWN = "unknown"


class PersonCount(Enum):
    """Person count categories."""
    SOLO = "solo"  # single person
    DUO = "duo"  # two people
    GROUP = "group"  # three or more
    NONE = "none"  # no people detected
    UNKNOWN = "unknown"


class NSFWRating(Enum):
    """Content rating from WD14."""
    GENERAL = "general"  # safe for work
    SENSITIVE = "sensitive"  # mild content
    QUESTIONABLE = "questionable"  # suggestive
    EXPLICIT = "explicit"  # adult content
    UNKNOWN = "unknown"


@dataclass
class VisualClassification:
    """Result of visual classification for an image."""
    image_path: str
    shot_type: ShotType
    person_count: PersonCount
    nsfw_rating: NSFWRating
    confidence_scores: Dict[str, float]
    raw_tags: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'image_path': self.image_path,
            'shot_type': self.shot_type.value,
            'person_count': self.person_count.value,
            'nsfw_rating': self.nsfw_rating.value,
            'confidence_scores': self.confidence_scores,
            'raw_tags': self.raw_tags
        }


class VisualClassifier:
    """
    Visual classifier for LoRA-specific image sorting.

    Uses WD14 tagger for visual analysis. The WD14 model includes tags for:
    - Shot composition: portrait, upper_body, cowboy_shot, full_body, wide_shot, close-up
    - Person count: solo, 1girl, 1boy, 2girls, multiple_girls, etc.
    - NSFW rating: general, sensitive, questionable, explicit
    """

    # Shot composition tags mapped to ShotType enum
    SHOT_TYPE_TAGS = {
        'close-up': ShotType.EXTREME_CLOSEUP,
        'portrait': ShotType.PORTRAIT,
        'upper_body': ShotType.UPPER_BODY,
        'cowboy_shot': ShotType.COWBOY,
        'full_body': ShotType.FULL_BODY,
        'wide_shot': ShotType.WIDE_SHOT,
        'very_wide_shot': ShotType.WIDE_SHOT,
    }

    # Person count tags - priority order for detection
    PERSON_COUNT_TAGS = {
        'solo': PersonCount.SOLO,
        'solo_focus': PersonCount.SOLO,
        '1girl': PersonCount.SOLO,
        '1boy': PersonCount.SOLO,
        '2girls': PersonCount.DUO,
        '2boys': PersonCount.DUO,
        '1girl_1boy': PersonCount.DUO,
        'multiple_girls': PersonCount.GROUP,
        'multiple_boys': PersonCount.GROUP,
        '3girls': PersonCount.GROUP,
        '4girls': PersonCount.GROUP,
        '5girls': PersonCount.GROUP,
        '6+girls': PersonCount.GROUP,
        'crowd': PersonCount.GROUP,
    }

    # Rating tags
    RATING_TAGS = {
        'general': NSFWRating.GENERAL,
        'sensitive': NSFWRating.SENSITIVE,
        'questionable': NSFWRating.QUESTIONABLE,
        'explicit': NSFWRating.EXPLICIT,
    }

    def __init__(self, wd14_tagger=None, use_yolo=False, yolo_model_path=None):
        """
        Initialize the visual classifier.

        Args:
            wd14_tagger: Optional pre-loaded WD14Tagger instance
            use_yolo: Whether to use YOLO for more accurate person detection
            yolo_model_path: Path to YOLO model (if use_yolo=True)
        """
        self.logger = logging.getLogger(__name__)
        self.wd14_tagger = wd14_tagger
        self.use_yolo = use_yolo
        self.yolo_model = None

        # Load WD14 if not provided
        if self.wd14_tagger is None:
            self._load_wd14()

        # Load YOLO if requested
        if self.use_yolo:
            self._load_yolo(yolo_model_path)

    def _load_wd14(self):
        """Load WD14 tagger for visual analysis."""
        try:
            from wd14_tagger import WD14Tagger
            self.wd14_tagger = WD14Tagger()
            if self.wd14_tagger.loaded:
                self.logger.info("WD14 tagger loaded for visual classification")
            else:
                self.logger.warning("WD14 tagger failed to load")
        except ImportError as e:
            self.logger.error(f"Failed to import WD14Tagger: {e}")
            self.wd14_tagger = None

    def _load_yolo(self, model_path=None):
        """Load YOLO model for person detection."""
        try:
            from ultralytics import YOLO

            # Use provided path or default to YOLOv8n
            if model_path and os.path.exists(model_path):
                self.yolo_model = YOLO(model_path)
            else:
                # Download YOLOv8n if needed (small, fast model)
                self.yolo_model = YOLO('yolov8n.pt')

            self.logger.info("YOLO model loaded for person detection")
        except ImportError:
            self.logger.warning(
                "ultralytics not installed. Person detection via YOLO disabled.\n"
                "Install with: pip install ultralytics"
            )
            self.yolo_model = None
            self.use_yolo = False
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            self.yolo_model = None
            self.use_yolo = False

    def classify_image(self, image_path: str, threshold: float = 0.35) -> VisualClassification:
        """
        Classify an image for LoRA sorting.

        Args:
            image_path: Path to image file
            threshold: Confidence threshold for WD14 tags

        Returns:
            VisualClassification with shot type, person count, and rating
        """
        if not os.path.exists(image_path):
            return VisualClassification(
                image_path=image_path,
                shot_type=ShotType.UNKNOWN,
                person_count=PersonCount.UNKNOWN,
                nsfw_rating=NSFWRating.UNKNOWN,
                confidence_scores={},
                raw_tags=[]
            )

        # Get WD14 tags
        tags_with_scores = {}
        raw_tags = []

        if self.wd14_tagger and self.wd14_tagger.loaded:
            tag_results = self.wd14_tagger.get_tags(image_path, threshold=threshold)
            tags_with_scores = {tag: float(conf) for tag, conf in tag_results}
            raw_tags = list(tags_with_scores.keys())

        # Classify shot type
        shot_type = self._classify_shot_type(tags_with_scores)

        # Classify person count
        if self.use_yolo and self.yolo_model:
            person_count = self._detect_persons_yolo(image_path)
        else:
            person_count = self._classify_person_count(tags_with_scores)

        # Classify NSFW rating
        nsfw_rating = self._classify_rating(tags_with_scores)

        return VisualClassification(
            image_path=image_path,
            shot_type=shot_type,
            person_count=person_count,
            nsfw_rating=nsfw_rating,
            confidence_scores=tags_with_scores,
            raw_tags=raw_tags
        )

    def _classify_shot_type(self, tags_with_scores: Dict[str, float]) -> ShotType:
        """Determine shot type from WD14 tags."""
        best_shot = ShotType.UNKNOWN
        best_score = 0.0

        for tag, shot_type in self.SHOT_TYPE_TAGS.items():
            if tag in tags_with_scores:
                score = tags_with_scores[tag]
                if score > best_score:
                    best_score = score
                    best_shot = shot_type

        return best_shot

    def _classify_person_count(self, tags_with_scores: Dict[str, float]) -> PersonCount:
        """Determine person count from WD14 tags."""
        # Check for explicit count tags in priority order
        tag_list = list(tags_with_scores.keys())

        # Check for group first (highest priority)
        group_tags = ['multiple_girls', 'multiple_boys', '3girls', '4girls',
                      '5girls', '6+girls', 'crowd']
        for tag in group_tags:
            if tag in tag_list:
                return PersonCount.GROUP

        # Check for duo
        duo_tags = ['2girls', '2boys']
        for tag in duo_tags:
            if tag in tag_list:
                return PersonCount.DUO

        # Check for solo
        solo_tags = ['solo', 'solo_focus', '1girl', '1boy']
        for tag in solo_tags:
            if tag in tag_list:
                return PersonCount.SOLO

        return PersonCount.UNKNOWN

    def _detect_persons_yolo(self, image_path: str) -> PersonCount:
        """Use YOLO to detect and count people in image."""
        if not self.yolo_model:
            return PersonCount.UNKNOWN

        try:
            # Run detection
            results = self.yolo_model(image_path, verbose=False)

            # Count person detections (class 0 in COCO)
            person_count = 0
            for result in results:
                for box in result.boxes:
                    if int(box.cls) == 0:  # person class
                        person_count += 1

            if person_count == 0:
                return PersonCount.NONE
            elif person_count == 1:
                return PersonCount.SOLO
            elif person_count == 2:
                return PersonCount.DUO
            else:
                return PersonCount.GROUP

        except Exception as e:
            self.logger.warning(f"YOLO detection failed: {e}")
            return PersonCount.UNKNOWN

    def _classify_rating(self, tags_with_scores: Dict[str, float]) -> NSFWRating:
        """Determine NSFW rating from WD14 tags."""
        best_rating = NSFWRating.UNKNOWN
        best_score = 0.0

        for tag, rating in self.RATING_TAGS.items():
            if tag in tags_with_scores:
                score = tags_with_scores[tag]
                if score > best_score:
                    best_score = score
                    best_rating = rating

        return best_rating

    def classify_batch(self, image_paths: List[str],
                       threshold: float = 0.35,
                       progress_callback=None) -> List[VisualClassification]:
        """
        Classify multiple images.

        Args:
            image_paths: List of image paths
            threshold: Confidence threshold for WD14 tags
            progress_callback: Optional callback(current, total, filename)

        Returns:
            List of VisualClassification results
        """
        results = []
        total = len(image_paths)

        for i, image_path in enumerate(image_paths):
            result = self.classify_image(image_path, threshold)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, os.path.basename(image_path))

        return results

    def get_sorting_folder(self, classification: VisualClassification,
                           sort_by: str = 'shot_type') -> str:
        """
        Get the folder name for sorting based on classification.

        Args:
            classification: VisualClassification result
            sort_by: What to sort by - 'shot_type', 'person_count', 'nsfw_rating'

        Returns:
            Folder name string
        """
        if sort_by == 'shot_type':
            return classification.shot_type.value
        elif sort_by == 'person_count':
            return classification.person_count.value
        elif sort_by == 'nsfw_rating':
            return classification.nsfw_rating.value
        else:
            return 'unsorted'


class LoRASortingProfile:
    """
    Defines sorting criteria for a specific LoRA.

    Each LoRA may expect different starting compositions (portrait vs full body),
    person counts (solo vs duo), etc. This profile defines what to filter for.
    """

    def __init__(self, name: str,
                 shot_types: Optional[List[ShotType]] = None,
                 person_counts: Optional[List[PersonCount]] = None,
                 nsfw_ratings: Optional[List[NSFWRating]] = None,
                 required_tags: Optional[List[str]] = None,
                 excluded_tags: Optional[List[str]] = None):
        """
        Create a LoRA sorting profile.

        Args:
            name: Profile name (usually the LoRA name)
            shot_types: Acceptable shot types (None = any)
            person_counts: Acceptable person counts (None = any)
            nsfw_ratings: Acceptable ratings (None = any)
            required_tags: Tags that must be present
            excluded_tags: Tags that must not be present
        """
        self.name = name
        self.shot_types = shot_types
        self.person_counts = person_counts
        self.nsfw_ratings = nsfw_ratings
        self.required_tags = required_tags or []
        self.excluded_tags = excluded_tags or []

    def matches(self, classification: VisualClassification) -> bool:
        """
        Check if a classification matches this profile.

        Args:
            classification: VisualClassification to check

        Returns:
            True if image matches profile criteria
        """
        # Check shot type
        if self.shot_types and classification.shot_type not in self.shot_types:
            if classification.shot_type != ShotType.UNKNOWN:
                return False

        # Check person count
        if self.person_counts and classification.person_count not in self.person_counts:
            if classification.person_count != PersonCount.UNKNOWN:
                return False

        # Check NSFW rating
        if self.nsfw_ratings and classification.nsfw_rating not in self.nsfw_ratings:
            if classification.nsfw_rating != NSFWRating.UNKNOWN:
                return False

        # Check required tags
        for tag in self.required_tags:
            if tag not in classification.raw_tags:
                return False

        # Check excluded tags
        for tag in self.excluded_tags:
            if tag in classification.raw_tags:
                return False

        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'shot_types': [st.value for st in self.shot_types] if self.shot_types else None,
            'person_counts': [pc.value for pc in self.person_counts] if self.person_counts else None,
            'nsfw_ratings': [nr.value for nr in self.nsfw_ratings] if self.nsfw_ratings else None,
            'required_tags': self.required_tags,
            'excluded_tags': self.excluded_tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LoRASortingProfile':
        """Create profile from dictionary."""
        shot_types = None
        if data.get('shot_types'):
            shot_types = [ShotType(st) for st in data['shot_types']]

        person_counts = None
        if data.get('person_counts'):
            person_counts = [PersonCount(pc) for pc in data['person_counts']]

        nsfw_ratings = None
        if data.get('nsfw_ratings'):
            nsfw_ratings = [NSFWRating(nr) for nr in data['nsfw_ratings']]

        return cls(
            name=data['name'],
            shot_types=shot_types,
            person_counts=person_counts,
            nsfw_ratings=nsfw_ratings,
            required_tags=data.get('required_tags', []),
            excluded_tags=data.get('excluded_tags', [])
        )


# Example LoRA profiles
EXAMPLE_PROFILES = {
    'portrait_lora': LoRASortingProfile(
        name='portrait_lora',
        shot_types=[ShotType.PORTRAIT, ShotType.EXTREME_CLOSEUP, ShotType.UPPER_BODY],
        person_counts=[PersonCount.SOLO],
        nsfw_ratings=None  # Any rating
    ),
    'action_lora': LoRASortingProfile(
        name='action_lora',
        shot_types=[ShotType.FULL_BODY, ShotType.COWBOY, ShotType.WIDE_SHOT],
        person_counts=None,  # Any count
        nsfw_ratings=None
    ),
    'duo_lora': LoRASortingProfile(
        name='duo_lora',
        shot_types=None,  # Any shot type
        person_counts=[PersonCount.DUO],
        nsfw_ratings=None
    ),
    'sfw_portrait': LoRASortingProfile(
        name='sfw_portrait',
        shot_types=[ShotType.PORTRAIT, ShotType.UPPER_BODY],
        person_counts=[PersonCount.SOLO],
        nsfw_ratings=[NSFWRating.GENERAL, NSFWRating.SENSITIVE]
    )
}


def main():
    """Test the visual classifier."""
    print("="*60)
    print("Visual Classifier for LoRA Sorting")
    print("="*60)
    print("Classifies images by shot type, person count, and NSFW rating")
    print("="*60)

    try:
        # Initialize classifier (WD14 only, no YOLO by default)
        classifier = VisualClassifier(use_yolo=False)

        if classifier.wd14_tagger and classifier.wd14_tagger.loaded:
            print("\nWD14 tagger loaded successfully!")
            print("Ready to classify images")

            print("\nAvailable shot types:")
            for shot_type in ShotType:
                print(f"  - {shot_type.value}")

            print("\nAvailable person counts:")
            for pc in PersonCount:
                print(f"  - {pc.value}")

            print("\nExample LoRA profiles:")
            for name, profile in EXAMPLE_PROFILES.items():
                print(f"  - {name}: {profile.to_dict()}")
        else:
            print("\nWD14 tagger not loaded. Check model files.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
