"""
Image Ranker - Core ranking logic using OpenSkill algorithm

This module provides pairwise image ranking using the OpenSkill library
(Plackett-Luce model) with SQLite persistence.

Key features:
- OpenSkill-based rating with uncertainty tracking (mu, sigma)
- Smart pairing strategy that prioritizes uncertain images
- SQLite database for persistent rankings
- Undo support via comparison history
- Export functionality for top-N images

Author: Claude Code Implementation
"""

import sqlite3
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from openskill.models import PlackettLuce
import shutil
import re

logger = logging.getLogger(__name__)

# Project management constants
PROJECTS_DIR = Path("data")
PROJECT_PREFIX = "rankings_"
PROJECT_SUFFIX = ".db"
LEGACY_DB = "rankings.db"


def get_projects_dir() -> Path:
    """Get the projects directory, creating if needed."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def list_projects() -> List[Dict[str, Any]]:
    """
    List all available ranking projects.

    Returns:
        List of dicts with 'name', 'path', 'image_count', 'comparison_count'
    """
    projects = []
    projects_dir = get_projects_dir()

    # Check for legacy database first
    legacy_path = projects_dir / LEGACY_DB
    if legacy_path.exists():
        projects.append({
            'name': '(Unsaved Project)',
            'path': str(legacy_path),
            'is_legacy': True
        })

    # Find all project databases
    for db_file in projects_dir.glob(f"{PROJECT_PREFIX}*{PROJECT_SUFFIX}"):
        name = db_file.stem[len(PROJECT_PREFIX):]  # Remove prefix
        projects.append({
            'name': name,
            'path': str(db_file),
            'is_legacy': False
        })

    # Add stats to each project
    for proj in projects:
        try:
            with sqlite3.connect(proj['path']) as conn:
                proj['image_count'] = conn.execute(
                    "SELECT COUNT(*) FROM images"
                ).fetchone()[0]
                proj['comparison_count'] = conn.execute(
                    "SELECT COUNT(*) FROM comparisons"
                ).fetchone()[0]
        except:
            proj['image_count'] = 0
            proj['comparison_count'] = 0

    return projects


def create_project(name: str) -> str:
    """
    Create a new ranking project.

    Args:
        name: Project name (will be sanitized)

    Returns:
        Path to the new database file
    """
    # Sanitize name
    safe_name = re.sub(r'[^\w\-\s]', '', name).strip().replace(' ', '_')
    if not safe_name:
        safe_name = "untitled"

    db_path = get_projects_dir() / f"{PROJECT_PREFIX}{safe_name}{PROJECT_SUFFIX}"

    # Ensure unique name
    counter = 1
    while db_path.exists():
        db_path = get_projects_dir() / f"{PROJECT_PREFIX}{safe_name}_{counter}{PROJECT_SUFFIX}"
        counter += 1

    # Create empty database (ImageRanker will init schema)
    return str(db_path)


def rename_legacy_project(new_name: str) -> str:
    """
    Rename the legacy rankings.db to a proper project name.

    Args:
        new_name: New project name

    Returns:
        Path to the renamed database
    """
    legacy_path = get_projects_dir() / LEGACY_DB
    if not legacy_path.exists():
        raise FileNotFoundError("No legacy database to rename")

    # Sanitize name
    safe_name = re.sub(r'[^\w\-\s]', '', new_name).strip().replace(' ', '_')
    if not safe_name:
        safe_name = "untitled"

    new_path = get_projects_dir() / f"{PROJECT_PREFIX}{safe_name}{PROJECT_SUFFIX}"

    # Ensure unique name
    counter = 1
    while new_path.exists():
        new_path = get_projects_dir() / f"{PROJECT_PREFIX}{safe_name}_{counter}{PROJECT_SUFFIX}"
        counter += 1

    shutil.move(legacy_path, new_path)
    logger.info(f"Renamed legacy database to {new_path}")
    return str(new_path)


def get_project_path(name: str) -> str:
    """Get the database path for a project by name."""
    if name == '(Unsaved Project)':
        return str(get_projects_dir() / LEGACY_DB)
    return str(get_projects_dir() / f"{PROJECT_PREFIX}{name}{PROJECT_SUFFIX}")


@dataclass
class RankedImage:
    """Represents an image with its ranking data."""
    id: int
    filepath: str
    filename: str
    mu: float
    sigma: float
    comparison_count: int
    added_at: datetime
    last_compared_at: Optional[datetime]

    @property
    def ordinal(self) -> float:
        """Conservative skill estimate (mu - 3*sigma)."""
        return self.mu - 3 * self.sigma

    @property
    def exists(self) -> bool:
        """Check if the image file still exists on disk."""
        return Path(self.filepath).exists()


class ImageRanker:
    """
    Core ranking engine using OpenSkill algorithm.

    Manages image ratings, pairwise comparisons, and persistence.
    """

    # Default OpenSkill parameters
    DEFAULT_MU = 25.0
    DEFAULT_SIGMA = 25.0 / 3  # ~8.333

    # Supported image extensions
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}

    def __init__(self, db_path: str = "data/rankings.db"):
        """
        Initialize the ranker with a database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.model = PlackettLuce()
        self._session_pairs: set = set()  # Track pairs shown this session

        self._init_database()

    def _init_database(self):
        """Initialize database schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    mu REAL DEFAULT 25.0,
                    sigma REAL DEFAULT 8.333333,
                    comparison_count INTEGER DEFAULT 0,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_compared_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS comparisons (
                    id INTEGER PRIMARY KEY,
                    winner_id INTEGER REFERENCES images(id),
                    loser_id INTEGER REFERENCES images(id),
                    was_draw BOOLEAN DEFAULT FALSE,
                    compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_images_ordinal
                    ON images((mu - 3 * sigma) DESC);
                CREATE INDEX IF NOT EXISTS idx_images_uncertainty
                    ON images(sigma DESC);
                CREATE INDEX IF NOT EXISTS idx_images_filepath
                    ON images(filepath);
                CREATE INDEX IF NOT EXISTS idx_comparisons_winner
                    ON comparisons(winner_id);
                CREATE INDEX IF NOT EXISTS idx_comparisons_loser
                    ON comparisons(loser_id);
            """)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def scan_folder(self, folder: str, recursive: bool = True) -> Dict[str, int]:
        """
        Scan a folder for images and add new ones to the database.

        Args:
            folder: Path to scan
            recursive: Whether to scan subdirectories

        Returns:
            Dict with 'added', 'existing', 'total' counts
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder}")

        # Get existing filepaths
        with self._get_connection() as conn:
            existing = {row['filepath'] for row in
                       conn.execute("SELECT filepath FROM images").fetchall()}

        # Find image files
        pattern = '**/*' if recursive else '*'
        new_images = []

        for path in folder_path.glob(pattern):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                filepath = str(path.resolve())
                if filepath not in existing:
                    new_images.append((filepath, path.name))

        # Batch insert new images
        if new_images:
            with self._get_connection() as conn:
                conn.executemany(
                    "INSERT INTO images (filepath, filename, mu, sigma) VALUES (?, ?, ?, ?)",
                    [(fp, fn, self.DEFAULT_MU, self.DEFAULT_SIGMA) for fp, fn in new_images]
                )
                conn.commit()

        logger.info(f"Scanned {folder}: {len(new_images)} new, {len(existing)} existing")

        return {
            'added': len(new_images),
            'existing': len(existing),
            'total': len(new_images) + len(existing)
        }

    def get_image_count(self) -> int:
        """Get total number of images in database."""
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM images").fetchone()
            return result[0] if result else 0

    def get_comparison_count(self) -> int:
        """Get total number of comparisons made."""
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM comparisons").fetchone()
            return result[0] if result else 0

    def get_image(self, image_id: int) -> Optional[RankedImage]:
        """Get a single image by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM images WHERE id = ?", (image_id,)
            ).fetchone()

            if row:
                return self._row_to_image(row)
        return None

    def get_all_images(self, order_by: str = 'ordinal') -> List[RankedImage]:
        """
        Get all images, optionally sorted.

        Args:
            order_by: 'ordinal' (default), 'mu', 'sigma', 'comparison_count', 'added_at'
        """
        order_clause = {
            'ordinal': '(mu - 3 * sigma) DESC',
            'mu': 'mu DESC',
            'sigma': 'sigma DESC',
            'comparison_count': 'comparison_count DESC',
            'added_at': 'added_at DESC'
        }.get(order_by, '(mu - 3 * sigma) DESC')

        with self._get_connection() as conn:
            rows = conn.execute(f"SELECT * FROM images ORDER BY {order_clause}").fetchall()
            return [self._row_to_image(row) for row in rows]

    def get_top_images(self, n: int = 100) -> List[RankedImage]:
        """Get top N images by ordinal score."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM images ORDER BY (mu - 3 * sigma) DESC LIMIT ?",
                (n,)
            ).fetchall()
            return [self._row_to_image(row) for row in rows]

    def _row_to_image(self, row: sqlite3.Row) -> RankedImage:
        """Convert database row to RankedImage object."""
        return RankedImage(
            id=row['id'],
            filepath=row['filepath'],
            filename=row['filename'],
            mu=row['mu'],
            sigma=row['sigma'],
            comparison_count=row['comparison_count'],
            added_at=datetime.fromisoformat(row['added_at']) if row['added_at'] else datetime.now(),
            last_compared_at=datetime.fromisoformat(row['last_compared_at']) if row['last_compared_at'] else None
        )

    def pick_pair(self) -> Optional[Tuple[RankedImage, RankedImage]]:
        """
        Select a pair of images for comparison using smart pairing.

        Strategy:
        1. Weight by uncertainty (sigma) - higher sigma = more likely
        2. Factor in comparison count for coverage
        3. Prefer similar mu values to disambiguate rankings
        4. Avoid pairs already shown this session

        Returns:
            Tuple of two RankedImage objects, or None if not enough images
        """
        # Get a limited sample of high-uncertainty images for performance
        # With 26k+ images, we don't need to consider all of them
        images = self._get_candidate_images(limit=500)

        if len(images) < 2:
            return None

        # Calculate weights for first image selection
        # Higher sigma + lower comparison count = higher weight
        weights = [
            img.sigma * (1 + 1 / (img.comparison_count + 1))
            for img in images
        ]

        # Try to find a valid pair not shown this session
        max_attempts = 20
        for _ in range(max_attempts):
            # Pick first image weighted by uncertainty
            img1 = random.choices(images, weights=weights)[0]

            # Pick second image: prefer similar mu, high sigma
            candidates = [img for img in images if img.id != img1.id]
            if not candidates:
                return None

            weights2 = [
                c.sigma * (1 / (abs(c.mu - img1.mu) + 1))
                for c in candidates
            ]
            img2 = random.choices(candidates, weights=weights2)[0]

            # Check if this pair was already shown
            pair_key = tuple(sorted([img1.id, img2.id]))
            if pair_key not in self._session_pairs:
                # Verify files exist before returning (only check 2 files, not all)
                if img1.exists and img2.exists:
                    self._session_pairs.add(pair_key)
                    return (img1, img2)
                # If files missing, mark for removal and try again
                if not img1.exists:
                    images = [img for img in images if img.id != img1.id]
                    weights = [w for i, w in enumerate(weights) if images[i].id != img1.id] if len(images) == len(weights) - 1 else weights
                if not img2.exists:
                    images = [img for img in images if img.id != img2.id]

        # Fallback: return any valid pair
        if len(images) >= 2:
            for img1, img2 in [random.sample(images, 2) for _ in range(10)]:
                if img1.exists and img2.exists:
                    return (img1, img2)

        return None

    def _get_candidate_images(self, limit: int = 500) -> List[RankedImage]:
        """
        Get a sample of candidate images for pair selection.

        Prioritizes high-uncertainty (high sigma) and under-compared images.
        Uses SQL for efficiency instead of loading all images.
        """
        with self._get_connection() as conn:
            # Get images ordered by sigma (highest uncertainty first)
            # Mix in some randomness to avoid always comparing the same images
            rows = conn.execute("""
                SELECT id, filepath, filename, mu, sigma, comparison_count,
                       added_at, last_compared_at
                FROM images
                ORDER BY sigma DESC, comparison_count ASC, RANDOM()
                LIMIT ?
            """, (limit,)).fetchall()

        return [
            RankedImage(
                id=row['id'],
                filepath=row['filepath'],
                filename=row['filename'],
                mu=row['mu'],
                sigma=row['sigma'],
                comparison_count=row['comparison_count'],
                added_at=datetime.fromisoformat(row['added_at']) if row['added_at'] else datetime.now(),
                last_compared_at=datetime.fromisoformat(row['last_compared_at']) if row['last_compared_at'] else None
            )
            for row in rows
        ]

    def record_comparison(self, winner_id: int, loser_id: int, is_draw: bool = False) -> bool:
        """
        Record a comparison result and update ratings.

        Args:
            winner_id: ID of winning image (ignored if is_draw)
            loser_id: ID of losing image (ignored if is_draw)
            is_draw: Whether the comparison was a draw/skip

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            # Get current ratings
            winner_row = conn.execute(
                "SELECT mu, sigma FROM images WHERE id = ?", (winner_id,)
            ).fetchone()
            loser_row = conn.execute(
                "SELECT mu, sigma FROM images WHERE id = ?", (loser_id,)
            ).fetchone()

            if not winner_row or not loser_row:
                logger.error(f"Image not found: winner={winner_id}, loser={loser_id}")
                return False

            # Create OpenSkill rating objects
            r1 = self.model.rating(mu=winner_row['mu'], sigma=winner_row['sigma'])
            r2 = self.model.rating(mu=loser_row['mu'], sigma=loser_row['sigma'])

            # Update ratings
            if is_draw:
                [[r1], [r2]] = self.model.rate([[r1], [r2]], ranks=[1, 1])
            else:
                [[r1], [r2]] = self.model.rate([[r1], [r2]])  # First team wins

            now = datetime.now().isoformat()

            # Update database
            conn.execute(
                """UPDATE images
                   SET mu = ?, sigma = ?, comparison_count = comparison_count + 1,
                       last_compared_at = ?
                   WHERE id = ?""",
                (r1.mu, r1.sigma, now, winner_id)
            )
            conn.execute(
                """UPDATE images
                   SET mu = ?, sigma = ?, comparison_count = comparison_count + 1,
                       last_compared_at = ?
                   WHERE id = ?""",
                (r2.mu, r2.sigma, now, loser_id)
            )

            # Record comparison history
            conn.execute(
                """INSERT INTO comparisons (winner_id, loser_id, was_draw)
                   VALUES (?, ?, ?)""",
                (winner_id, loser_id, is_draw)
            )

            conn.commit()

        logger.debug(f"Recorded comparison: {winner_id} vs {loser_id}, draw={is_draw}")
        return True

    def undo_last_comparison(self) -> Optional[Dict[str, Any]]:
        """
        Undo the most recent comparison.

        This recalculates ratings by replaying all comparisons except the last.

        Returns:
            Dict with undo details, or None if nothing to undo
        """
        with self._get_connection() as conn:
            # Get last comparison
            last = conn.execute(
                "SELECT * FROM comparisons ORDER BY id DESC LIMIT 1"
            ).fetchone()

            if not last:
                return None

            # Get the images involved
            winner_id = last['winner_id']
            loser_id = last['loser_id']

            # Delete the comparison
            conn.execute("DELETE FROM comparisons WHERE id = ?", (last['id'],))

            # Reset ratings for both images and recalculate from history
            self._recalculate_ratings(conn, [winner_id, loser_id])

            conn.commit()

        # Remove from session pairs
        pair_key = tuple(sorted([winner_id, loser_id]))
        self._session_pairs.discard(pair_key)

        return {
            'winner_id': winner_id,
            'loser_id': loser_id,
            'was_draw': last['was_draw']
        }

    def _recalculate_ratings(self, conn: sqlite3.Connection, image_ids: List[int]):
        """
        Recalculate ratings for specific images based on their comparison history.

        This is called after undo to ensure consistency.
        """
        for image_id in image_ids:
            # Reset to default
            conn.execute(
                "UPDATE images SET mu = ?, sigma = ?, comparison_count = 0 WHERE id = ?",
                (self.DEFAULT_MU, self.DEFAULT_SIGMA, image_id)
            )

        # Get all comparisons involving these images
        placeholders = ','.join('?' * len(image_ids))
        comparisons = conn.execute(
            f"""SELECT * FROM comparisons
                WHERE winner_id IN ({placeholders}) OR loser_id IN ({placeholders})
                ORDER BY id""",
            image_ids + image_ids
        ).fetchall()

        # Replay comparisons
        for comp in comparisons:
            winner_row = conn.execute(
                "SELECT mu, sigma FROM images WHERE id = ?", (comp['winner_id'],)
            ).fetchone()
            loser_row = conn.execute(
                "SELECT mu, sigma FROM images WHERE id = ?", (comp['loser_id'],)
            ).fetchone()

            r1 = self.model.rating(mu=winner_row['mu'], sigma=winner_row['sigma'])
            r2 = self.model.rating(mu=loser_row['mu'], sigma=loser_row['sigma'])

            if comp['was_draw']:
                [[r1], [r2]] = self.model.rate([[r1], [r2]], ranks=[1, 1])
            else:
                [[r1], [r2]] = self.model.rate([[r1], [r2]])

            conn.execute(
                "UPDATE images SET mu = ?, sigma = ?, comparison_count = comparison_count + 1 WHERE id = ?",
                (r1.mu, r1.sigma, comp['winner_id'])
            )
            conn.execute(
                "UPDATE images SET mu = ?, sigma = ?, comparison_count = comparison_count + 1 WHERE id = ?",
                (r2.mu, r2.sigma, comp['loser_id'])
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive ranking statistics.

        Returns:
            Dict with detailed stats about the ranking state
        """
        with self._get_connection() as conn:
            # Basic counts
            total = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            compared = conn.execute(
                "SELECT COUNT(*) FROM images WHERE comparison_count > 0"
            ).fetchone()[0]
            comparisons = conn.execute("SELECT COUNT(*) FROM comparisons").fetchone()[0]

            # Comparison distribution
            avg_comparisons_per_image = comparisons * 2 / total if total > 0 else 0

            # Images by comparison count buckets
            zero_comparisons = conn.execute(
                "SELECT COUNT(*) FROM images WHERE comparison_count = 0"
            ).fetchone()[0]
            one_to_three = conn.execute(
                "SELECT COUNT(*) FROM images WHERE comparison_count BETWEEN 1 AND 3"
            ).fetchone()[0]
            four_to_ten = conn.execute(
                "SELECT COUNT(*) FROM images WHERE comparison_count BETWEEN 4 AND 10"
            ).fetchone()[0]
            over_ten = conn.execute(
                "SELECT COUNT(*) FROM images WHERE comparison_count > 10"
            ).fetchone()[0]

            # Sigma statistics (uncertainty)
            sigma_stats = conn.execute(
                """SELECT AVG(sigma), MIN(sigma), MAX(sigma)
                   FROM images WHERE comparison_count > 0"""
            ).fetchone()
            avg_sigma = sigma_stats[0] or self.DEFAULT_SIGMA
            min_sigma = sigma_stats[1] or self.DEFAULT_SIGMA
            max_sigma = sigma_stats[2] or self.DEFAULT_SIGMA

            # Mu statistics (skill estimate)
            mu_stats = conn.execute(
                """SELECT AVG(mu), MIN(mu), MAX(mu)
                   FROM images WHERE comparison_count > 0"""
            ).fetchone()
            avg_mu = mu_stats[0] or self.DEFAULT_MU
            min_mu = mu_stats[1] or self.DEFAULT_MU
            max_mu = mu_stats[2] or self.DEFAULT_MU

            # Top image score
            top_ordinal = conn.execute(
                "SELECT MAX(mu - 3 * sigma) FROM images WHERE comparison_count > 0"
            ).fetchone()[0] or 0

            # Rankings stability indicator
            # Low average sigma among compared images = more stable
            stability = max(0, min(100, 100 * (1 - avg_sigma / self.DEFAULT_SIGMA)))

            # Estimated comparisons needed
            # Basic ranking: 0.5x images, Confident: 2x images, High confidence: 3x images
            basic_needed = max(0, int(total * 0.5) - comparisons)
            confident_needed = max(0, int(total * 2) - comparisons)
            high_conf_needed = max(0, int(total * 3) - comparisons)

            # Progress percentages
            basic_progress = min(100, (comparisons / (total * 0.5) * 100)) if total > 0 else 0
            confident_progress = min(100, (comparisons / (total * 2) * 100)) if total > 0 else 0

        return {
            # Basic counts
            'total_images': total,
            'compared_images': compared,
            'uncompared_images': total - compared,
            'total_comparisons': comparisons,

            # Per-image stats
            'avg_comparisons_per_image': round(avg_comparisons_per_image, 2),

            # Distribution buckets
            'images_zero_comparisons': zero_comparisons,
            'images_1_to_3_comparisons': one_to_three,
            'images_4_to_10_comparisons': four_to_ten,
            'images_over_10_comparisons': over_ten,

            # Sigma (uncertainty) stats
            'average_sigma': round(avg_sigma, 3),
            'min_sigma': round(min_sigma, 3),
            'max_sigma': round(max_sigma, 3),

            # Mu (skill) stats
            'average_mu': round(avg_mu, 2),
            'min_mu': round(min_mu, 2),
            'max_mu': round(max_mu, 2),
            'top_ordinal_score': round(top_ordinal, 2),

            # Stability and progress
            'stability_percent': round(stability, 1),
            'basic_progress_percent': round(basic_progress, 1),
            'confident_progress_percent': round(confident_progress, 1),

            # Comparisons needed
            'comparisons_for_basic': basic_needed,
            'comparisons_for_confident': confident_needed,
            'comparisons_for_high_confidence': high_conf_needed,

            # Session
            'session_pairs_shown': len(self._session_pairs)
        }

    def clear_session(self):
        """Clear session state (allows pairs to be shown again)."""
        self._session_pairs.clear()

    def clear_database(self):
        """Clear all images and comparisons from database. Starts fresh."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM comparisons")
            conn.execute("DELETE FROM images")
            conn.commit()
        self._session_pairs.clear()
        logger.info("Database cleared - all images and comparisons removed")

    def export_rankings_csv(self, output_path: str) -> int:
        """
        Export rankings to CSV file.

        Returns:
            Number of images exported
        """
        import csv

        images = self.get_all_images(order_by='ordinal')

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['rank', 'filename', 'filepath', 'mu', 'sigma', 'ordinal', 'comparisons'])

            for rank, img in enumerate(images, 1):
                writer.writerow([
                    rank,
                    img.filename,
                    img.filepath,
                    round(img.mu, 3),
                    round(img.sigma, 3),
                    round(img.ordinal, 3),
                    img.comparison_count
                ])

        logger.info(f"Exported {len(images)} rankings to {output_path}")
        return len(images)

    def export_top_images(self, n: int, output_dir: str, copy: bool = True) -> List[str]:
        """
        Export top N images to a directory.

        Args:
            n: Number of images to export
            output_dir: Destination directory
            copy: If True, copy files. If False, create symlinks.

        Returns:
            List of exported file paths
        """
        import shutil

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        top_images = self.get_top_images(n)
        exported = []

        for rank, img in enumerate(top_images, 1):
            if not img.exists:
                logger.warning(f"Skipping missing file: {img.filepath}")
                continue

            src = Path(img.filepath)
            # Prefix with rank for easy sorting
            dst = output_path / f"{rank:04d}_{src.name}"

            try:
                if copy:
                    shutil.copy2(src, dst)
                else:
                    dst.symlink_to(src)
                exported.append(str(dst))
            except Exception as e:
                logger.error(f"Failed to export {src}: {e}")

        logger.info(f"Exported {len(exported)} images to {output_dir}")
        return exported

    def remove_missing_images(self) -> int:
        """
        Remove images from database that no longer exist on disk.

        Returns:
            Number of images removed
        """
        images = self.get_all_images()
        missing = [img for img in images if not img.exists]

        if missing:
            with self._get_connection() as conn:
                for img in missing:
                    # Remove comparisons involving this image
                    conn.execute(
                        "DELETE FROM comparisons WHERE winner_id = ? OR loser_id = ?",
                        (img.id, img.id)
                    )
                    conn.execute("DELETE FROM images WHERE id = ?", (img.id,))
                conn.commit()

        if missing:
            logger.info(f"Removed {len(missing)} missing images from database")

        return len(missing)

    def get_folders(self) -> List[str]:
        """Get unique folders that contain ranked images."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT filepath FROM images").fetchall()

        folders = set()
        for row in rows:
            folder = str(Path(row['filepath']).parent)
            folders.add(folder)

        return sorted(folders)
