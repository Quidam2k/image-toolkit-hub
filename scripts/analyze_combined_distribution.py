"""
PHASE 3: Analyze Combined Distribution

Comprehensive analysis of tag frequency across combined image collection:
1. Load and analyze tag_frequency.json database
2. Generate distribution statistics and insights
3. Identify underrepresented tags (problematic for auto-sort)
4. Create recommendations for auto-sort configuration
5. Analyze potential folder balance with proposed terms
"""

import json
import os
from collections import defaultdict
from datetime import datetime


class DistributionAnalyzer:
    """Analyze tag frequency distribution and provide recommendations."""

    def __init__(self, db_file='tag_frequency.json'):
        """Initialize analyzer with frequency database."""
        self.db_file = db_file
        self.database = None
        self.load_database()

    def load_database(self):
        """Load frequency database from JSON file."""
        if not os.path.exists(self.db_file):
            print(f"[ERROR] Database file not found: {self.db_file}")
            return False

        with open(self.db_file, 'r') as f:
            self.database = json.load(f)
        return True

    def get_statistics(self):
        """Get overall database statistics."""
        if not self.database:
            return None

        tags = self.database.get('tags', {})
        return {
            'total_unique_tags': len(tags),
            'total_images': self.database['statistics']['total_images'],
            'average_tags_per_image': self.database['statistics'].get('total_images', 0) / max(len(tags), 1),
        }

    def get_tag_distribution_percentiles(self):
        """Get distribution percentiles (top 25%, 50%, 75%, etc)."""
        if not self.database:
            return None

        tags = self.database.get('tags', {})
        counts = sorted([tag['count'] for tag in tags.values()], reverse=True)

        if not counts:
            return None

        total = len(counts)
        return {
            'top_10_percent': counts[int(total * 0.1)] if total > 10 else counts[-1],
            'top_25_percent': counts[int(total * 0.25)] if total > 4 else counts[-1],
            'median': counts[total // 2],
            'bottom_25_percent': counts[int(total * 0.75)] if total > 4 else counts[-1],
            'bottom_10_percent': counts[-1],
        }

    def identify_problematic_tags(self, thresholds=None):
        """Identify tags with problematic distributions."""
        if thresholds is None:
            thresholds = {
                'very_rare': 3,      # 3 or fewer images
                'rare': 10,           # 10 or fewer images
                'uncommon': 50,       # 50 or fewer images
                'moderate': 100,      # 100 or fewer images
            }

        if not self.database:
            return None

        tags = self.database.get('tags', {})
        results = defaultdict(list)

        for tag_name, tag_data in tags.items():
            count = tag_data['count']
            for level, threshold in thresholds.items():
                if count <= threshold:
                    results[level].append({
                        'tag': tag_name,
                        'count': count,
                        'percent': (count / tag_data.get('images_total', 1)) * 100 if tag_data.get('images_total') else 0
                    })

        # Sort each level by count descending
        for level in results:
            results[level].sort(key=lambda x: x['count'], reverse=True)

        return results

    def get_top_tags(self, limit=40):
        """Get top N tags by frequency."""
        if not self.database:
            return None

        tags = self.database.get('tags', {})
        sorted_tags = sorted(
            tags.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        return [
            {
                'rank': i + 1,
                'tag': tag_name,
                'count': tag_data['count'],
                'images_total': len(tag_data.get('images', [])),
                'percent': (tag_data['count'] / self.database['statistics']['total_images'] * 100) if self.database['statistics'].get('total_images') else 0,
            }
            for i, (tag_name, tag_data) in enumerate(sorted_tags[:limit])
        ]

    def analyze_multi_tag_scenarios(self, term_sets):
        """Analyze how different multi-tag configurations would distribute images."""
        if not self.database:
            return None

        tags = self.database.get('tags', {})
        images_by_tag = {}

        for tag_name, tag_data in tags.items():
            images_by_tag[tag_name.lower()] = set(tag_data.get('images', []))

        results = []

        for scenario in term_sets:
            scenario_analysis = {
                'name': scenario['name'],
                'terms': scenario['terms'],
                'distribution': {}
            }

            for term in scenario['terms']:
                term_lower = term.lower()
                if term_lower in images_by_tag:
                    scenario_analysis['distribution'][term] = len(images_by_tag[term_lower])

            results.append(scenario_analysis)

        return results

    def generate_recommendations(self, top_n=15):
        """Generate recommendations for auto-sort configuration."""
        if not self.database:
            return None

        top_tags = self.get_top_tags(limit=top_n)
        stats = self.get_statistics()
        percentiles = self.get_tag_distribution_percentiles()

        recommendations = {
            'summary': {
                'total_images': stats['total_images'],
                'total_unique_tags': stats['total_unique_tags'],
                'recommended_sort_terms_count': min(top_n, 15),
            },
            'recommended_terms': [tag['tag'] for tag in top_tags[:top_n]],
            'rationale': [
                f"Top {top_n} tags are recommended because they represent {sum(tag['percent'] for tag in top_tags[:top_n]):.1f}% of tag usage",
                f"This ensures the majority of images can be properly sorted",
                f"Median tag frequency: {percentiles['median']} images",
                f"Avoids underrepresented tags (<5 images each) which create nearly-empty folders",
            ],
            'expected_folder_distribution': {},
            'warnings': []
        }

        # Calculate expected distribution
        avg_per_folder = stats['total_images'] / top_n
        for tag in top_tags[:top_n]:
            recommendations['expected_folder_distribution'][tag['tag']] = {
                'images': tag['count'],
                'percent': tag['percent'],
                'balance_vs_average': (tag['count'] / avg_per_folder - 1) * 100
            }

        # Check for imbalance
        counts = [tag['count'] for tag in top_tags[:top_n]]
        min_count = min(counts)
        max_count = max(counts)
        imbalance_ratio = max_count / min_count if min_count > 0 else 0

        if imbalance_ratio > 5:
            recommendations['warnings'].append(
                f"High imbalance detected: largest folder ({max_count}) is {imbalance_ratio:.1f}x larger than smallest ({min_count})"
            )

        # Check for problematic tags
        problematic = self.identify_problematic_tags()
        if problematic['very_rare']:
            recommendations['warnings'].append(
                f"Found {len(problematic['very_rare'])} very rare tags (<3 images each) - these should NOT be used for auto-sort"
            )

        return recommendations

    def print_full_analysis(self):
        """Print comprehensive analysis to console."""
        if not self.database:
            print("[ERROR] Database not loaded")
            return

        print("\n" + "=" * 80)
        print("PHASE 3: COMBINED DISTRIBUTION ANALYSIS")
        print("=" * 80)

        # Basic statistics
        stats = self.get_statistics()
        print(f"\n[STATISTICS]")
        print(f"  Total images in collection: {stats['total_images']:,}")
        print(f"  Total unique tags: {stats['total_unique_tags']}")
        print(f"  Average tags per image: {stats['average_tags_per_image']:.1f}")

        # Distribution percentiles
        percentiles = self.get_tag_distribution_percentiles()
        print(f"\n[DISTRIBUTION PERCENTILES]")
        print(f"  Top 10% threshold: {percentiles['top_10_percent']} images")
        print(f"  Top 25% threshold: {percentiles['top_25_percent']} images")
        print(f"  Median: {percentiles['median']} images")
        print(f"  Bottom 25% threshold: {percentiles['bottom_25_percent']} images")
        print(f"  Rarest: {percentiles['bottom_10_percent']} images")

        # Top tags
        print(f"\n[TOP 40 TAGS]")
        top_tags = self.get_top_tags(limit=40)
        for tag in top_tags:
            print(
                f"  {tag['rank']:2d}. {tag['tag']:20s} {tag['count']:5d} images ({tag['percent']:5.1f}%)"
            )

        # Problematic tags
        problematic = self.identify_problematic_tags()
        print(f"\n[PROBLEMATIC TAGS - UNDERREPRESENTED]")
        print(f"  Very rare (<3 images): {len(problematic['very_rare'])} tags")
        if problematic['very_rare'][:5]:
            for tag in problematic['very_rare'][:5]:
                print(f"    - {tag['tag']}: {tag['count']} images")
            if len(problematic['very_rare']) > 5:
                print(f"    ... and {len(problematic['very_rare']) - 5} more")

        print(f"  Rare (<10 images): {len(problematic['rare'])} tags")
        print(f"  Uncommon (<50 images): {len(problematic['uncommon'])} tags")

        # Recommendations
        print(f"\n[RECOMMENDATIONS FOR AUTO-SORT]")
        recommendations = self.generate_recommendations(top_n=15)
        print(f"  Recommended terms ({len(recommendations['recommended_terms'])}): {', '.join(recommendations['recommended_terms'][:8])}")
        if len(recommendations['recommended_terms']) > 8:
            print(f"                              {', '.join(recommendations['recommended_terms'][8:])}")

        print(f"\n[EXPECTED FOLDER DISTRIBUTION]")
        dist = recommendations['expected_folder_distribution']
        avg = sum(d['images'] for d in dist.values()) / len(dist)
        print(f"  Average folder size: {avg:.0f} images")
        print(f"  Range: {min(d['images'] for d in dist.values())} - {max(d['images'] for d in dist.values())} images")

        for term in recommendations['recommended_terms'][:8]:
            if term in dist:
                info = dist[term]
                print(f"  - {term:20s}: {info['images']:5d} images ({info['percent']:5.1f}%)")

        if recommendations['warnings']:
            print(f"\n[WARNINGS]")
            for warning in recommendations['warnings']:
                print(f"  [WARNING] {warning}")

        print("\n" + "=" * 80)

    def save_analysis_report(self, output_file='phase3_analysis_report.json'):
        """Save analysis report to JSON file."""
        if not self.database:
            print("[ERROR] Database not loaded")
            return False

        report = {
            'generated': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'distribution_percentiles': self.get_tag_distribution_percentiles(),
            'top_40_tags': self.get_top_tags(limit=40),
            'problematic_tags': self.identify_problematic_tags(),
            'recommendations': self.generate_recommendations(top_n=15),
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n[OK] Analysis report saved to: {output_file}")
        return True


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("PHASE 3: ANALYZE COMBINED DISTRIBUTION")
    print("=" * 80)

    try:
        analyzer = DistributionAnalyzer('tag_frequency.json')

        if not analyzer.database:
            print("[ERROR] Failed to load frequency database")
            return 1

        # Print full analysis to console
        analyzer.print_full_analysis()

        # Save detailed report
        analyzer.save_analysis_report('phase3_analysis_report.json')

        print("\n[SUCCESS] Phase 3 analysis complete")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
