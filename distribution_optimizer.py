"""
Distribution Optimizer for Balanced Multi-Tag Sorting

This module implements a balanced distribution algorithm that:
1. Analyzes current folder sizes
2. Calculates balance scores for each potential destination
3. Selects destinations that improve overall distribution balance
4. Maintains sort quality (no false positives)

The algorithm softens priority-based ordering when folders become
imbalanced, preferring underrepresented folders to improve overall
distribution.
"""

import os
import json
import logging
from collections import defaultdict
from datetime import datetime


class DistributionOptimizer:
    """Optimizes multi-tag sorting for balanced folder distribution."""

    def __init__(self, config_file='imagesorter_config.json', db_file='tag_frequency.json'):
        """
        Initialize optimizer.

        Args:
            config_file: Path to configuration file
            db_file: Path to tag frequency database
        """
        self.config_file = config_file
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)

        # Tuning parameters
        self.balance_threshold = 0.80  # Consider underrepresented if < 80% of target
        self.overrepresentation_threshold = 1.20  # Start penalizing at 120% of target
        self.severe_overrepresentation_threshold = 1.50  # Exclude if > 150% of target

        # Scoring parameters
        self.base_priority_score = 100
        self.secondary_priority_score = 50
        self.tertiary_priority_score = 25

    def load_folder_sizes(self, terms):
        """
        Load current folder sizes for all terms.

        Args:
            terms: List of term configurations

        Returns:
            dict: Mapping of term name to current folder size
        """
        folder_sizes = {}

        for term in terms:
            term_name = term.get('term', term.get('folder_name', 'unknown'))
            folder_path = term.get('folder_path')

            if folder_path and os.path.isdir(folder_path):
                # Count images in folder
                image_count = len([
                    f for f in os.listdir(folder_path)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'))
                ])
                folder_sizes[term_name] = image_count
            else:
                folder_sizes[term_name] = 0

        return folder_sizes

    def calculate_target_size(self, terms):
        """
        Calculate target folder size for balanced distribution.

        Args:
            terms: List of term configurations

        Returns:
            float: Target average size per folder
        """
        total_images = sum(self.load_folder_sizes(terms).values())
        num_terms = len(terms)

        if num_terms == 0:
            return 0

        return total_images / num_terms

    def calculate_balance_score(self, term_name, current_size, target_size):
        """
        Calculate balance score for a term.

        Score indicates how much this term should be preferred:
        - Positive score: good choice (underrepresented)
        - Zero score: neutral (at target)
        - Negative score: bad choice (overrepresented)

        Args:
            term_name: Name of the term
            current_size: Current folder size
            target_size: Target folder size

        Returns:
            float: Balance score
        """
        if target_size == 0:
            return 0

        # Calculate how far from target
        ratio = current_size / target_size

        # Assign balance bonus/penalty based on ratio
        if ratio < self.balance_threshold:
            # Significantly underrepresented - strong bonus
            bonus = 50 * (self.balance_threshold - ratio) / self.balance_threshold
        elif ratio < 1.0:
            # Slightly underrepresented - mild bonus
            bonus = 20 * (1.0 - ratio)
        elif ratio < self.overrepresentation_threshold:
            # At or slightly above target - neutral
            bonus = 0
        elif ratio < self.severe_overrepresentation_threshold:
            # Overrepresented - penalty
            bonus = -30 * (ratio - self.overrepresentation_threshold) / (
                self.severe_overrepresentation_threshold - self.overrepresentation_threshold
            )
        else:
            # Severely overrepresented - strong penalty
            bonus = -50

        return bonus

    def score_matching_terms(self, matching_terms, current_sizes, target_size):
        """
        Score each matching term based on both priority and balance.

        Args:
            matching_terms: List of matching term configurations
            current_sizes: dict of term name to current folder size
            target_size: Target average folder size

        Returns:
            list: Terms sorted by score (highest first)
        """
        scored_terms = []

        for i, term in enumerate(matching_terms):
            term_name = term.get('term', term.get('folder_name', 'unknown'))
            current_size = current_sizes.get(term_name, 0)

            # Base priority score (first match gets highest score)
            if i == 0:
                base_score = self.base_priority_score
            elif i == 1:
                base_score = self.secondary_priority_score
            else:
                base_score = self.tertiary_priority_score

            # Calculate balance score
            balance_bonus = self.calculate_balance_score(term_name, current_size, target_size)

            # Only apply priority bonus if balance is acceptable
            # For overrepresented folders, ignore priority
            current_ratio = current_size / target_size if target_size > 0 else 0
            if current_ratio > self.overrepresentation_threshold:
                # Overrepresented - only balance matters
                total_score = balance_bonus
            else:
                # Acceptable balance - use both priority and balance
                total_score = base_score + balance_bonus

            scored_terms.append({
                'term_config': term,
                'term_name': term_name,
                'priority': i,
                'current_size': current_size,
                'base_score': base_score,
                'balance_bonus': balance_bonus,
                'total_score': total_score,
                'ratio': current_ratio,
            })

        # Sort by score (highest first)
        scored_terms.sort(key=lambda x: x['total_score'], reverse=True)

        return scored_terms

    def select_balanced_destinations(self, matching_terms, current_sizes, target_size, max_folders=5):
        """
        Select best destination folders for balanced distribution.

        Args:
            matching_terms: List of matching term configurations
            current_sizes: dict of term name to current folder size
            target_size: Target average folder size
            max_folders: Maximum number of folders to select

        Returns:
            list: Selected term configurations (top N by balance score)
        """
        if not matching_terms:
            return []

        # Score all matching terms
        scored_terms = self.score_matching_terms(matching_terms, current_sizes, target_size)

        # Filter out severely overrepresented folders
        filtered_terms = [
            t for t in scored_terms
            if t['ratio'] < self.severe_overrepresentation_threshold
        ]

        # If all terms are severely overrepresented, use the least bad one
        if not filtered_terms and scored_terms:
            filtered_terms = scored_terms[:1]

        # Select top N terms by score
        selected = filtered_terms[:max_folders]

        return [t['term_config'] for t in selected]

    def create_balanced_destinations(self, matching_terms, config_manager, max_folders=5):
        """
        Create destination list for balanced distribution.

        Args:
            matching_terms: List of matching term configurations
            config_manager: ConfigManager instance (for getting term paths)
            max_folders: Maximum number of destination folders

        Returns:
            list: Destination dicts ready for sorting
        """
        if not matching_terms:
            return []

        # Get current folder sizes
        current_sizes = self.load_folder_sizes(matching_terms)

        # Calculate target size
        total_size = sum(current_sizes.values())
        target_size = total_size / len(matching_terms) if len(matching_terms) > 0 else 0

        # Select best destinations
        selected_terms = self.select_balanced_destinations(
            matching_terms, current_sizes, target_size, max_folders
        )

        # Build destination list
        destinations = []
        for term in selected_terms:
            term_name = term.get('term', term.get('folder_name', 'unknown'))
            folder_path = config_manager.get_term_folder_path(term_name)

            destinations.append({
                'type': 'single_term',
                'terms': [term],
                'path': folder_path,
                'folder_name': term_name,
            })

        return destinations

    def generate_balance_report(self, terms, output_file='balance_report.json'):
        """
        Generate report on current distribution balance.

        Args:
            terms: List of term configurations
            output_file: Where to save the report

        Returns:
            dict: Balance analysis data
        """
        current_sizes = self.load_folder_sizes(terms)
        target_size = self.calculate_target_size(terms)

        report = {
            'generated': datetime.now().isoformat(),
            'total_images': sum(current_sizes.values()),
            'total_terms': len(terms),
            'target_size': target_size,
            'distribution': [],
        }

        # Calculate statistics for each term
        for term in terms:
            term_name = term.get('term', term.get('folder_name', 'unknown'))
            size = current_sizes.get(term_name, 0)
            ratio = size / target_size if target_size > 0 else 0
            percentage = (size / report['total_images'] * 100) if report['total_images'] > 0 else 0

            report['distribution'].append({
                'term': term_name,
                'size': size,
                'target': target_size,
                'ratio': round(ratio, 2),
                'percentage': round(percentage, 1),
                'status': self._get_balance_status(ratio),
            })

        # Sort by size (descending)
        report['distribution'].sort(key=lambda x: x['size'], reverse=True)

        # Calculate imbalance metrics
        if report['distribution']:
            sizes = [d['size'] for d in report['distribution']]
            max_size = max(sizes)
            min_size = min(sizes)
            report['imbalance_ratio'] = round(max_size / min_size if min_size > 0 else 0, 2)
            report['max_folder_size'] = max_size
            report['min_folder_size'] = min_size
        else:
            report['imbalance_ratio'] = 0

        # Save report
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)

        return report

    def _get_balance_status(self, ratio):
        """Get status description for balance ratio."""
        if ratio < self.balance_threshold:
            return 'underrepresented'
        elif ratio < self.overrepresentation_threshold:
            return 'balanced'
        elif ratio < self.severe_overrepresentation_threshold:
            return 'overrepresented'
        else:
            return 'severely_overrepresented'

    def print_balance_report(self, report):
        """Print balance report to console."""
        print("\n" + "=" * 80)
        print("DISTRIBUTION BALANCE REPORT")
        print("=" * 80)
        print(f"\nGenerated: {report['generated']}")
        print(f"Total images: {report['total_images']}")
        print(f"Total terms: {report['total_terms']}")
        print(f"Target size per folder: {report['target_size']:.0f}")
        print(f"Imbalance ratio: {report['imbalance_ratio']:.1f}:1")
        print(f"  (Largest {report['max_folder_size']} / Smallest {report['min_folder_size']})")

        print(f"\n[DISTRIBUTION]")
        print(f"  Rank  Term                    Size  Target  Ratio  Status")
        print(f"  {'-' * 70}")

        for i, dist in enumerate(report['distribution'], 1):
            status = dist['status']
            ratio_str = f"{dist['ratio']}x"
            print(
                f"  {i:3d}. {dist['term']:20s} {dist['size']:5d} "
                f"{dist['target']:7.0f} {ratio_str:>6} {status}"
            )

        print("\n" + "=" * 80)


def main():
    """Test the distribution optimizer."""
    print("\n[INFO] Distribution Optimizer Module")
    print("[INFO] This module is used by config_manager.py for balanced sorting")
    print("[INFO] See PHASE_4_PLAN.md for implementation details")


if __name__ == '__main__':
    main()
