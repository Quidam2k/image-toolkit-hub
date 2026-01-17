# Image Ranker - Build Specification

## Overview

Build a pairwise image comparison tool for ranking thousands of AI-generated images (Midjourney upscales) using the OpenSkill algorithm (Plackett-Luce model). The goal is to identify cream-of-the-crop images worthy of upscaling, refinement, and printing on products for sale.

This is an ongoing workflow tool, not a one-shot ranking. New images will be added continuously, and rankings will be refined over time through additional comparisons.

## Core Requirements

### Algorithm: OpenSkill (not basic Elo)

Use the `openskill` Python library (`pip install openskill`). OpenSkill is superior to basic Elo because:

1. **Tracks uncertainty (σ)** alongside skill estimate (μ)
2. **Transitive inference**: If A > B and B > C, the system infers A > C without direct comparison
3. **Prioritizes uncertain items**: New images or under-compared images can be surfaced for comparison
4. **Converges faster**: Needs fewer comparisons to establish stable rankings
5. **Open license**: No trademark restrictions (unlike TrueSkill which is Microsoft-owned)
6. **Faster**: 150% faster than TrueSkill with equivalent accuracy

Key API usage:
```python
from openskill.models import PlackettLuce

# Create model instance (do this once, reuse it)
model = PlackettLuce()

# Create ratings (default μ=25, σ=8.333)
r1 = model.rating()
r2 = model.rating()

# After comparison (r1 wins) - note: teams are nested lists
[[r1], [r2]] = model.rate([[r1], [r2]])  # first team wins by default

# For ties/skips:
[[r1], [r2]] = model.rate([[r1], [r2]], ranks=[1, 1])  # same rank = draw

# Sort key for leaderboard (conservative estimate: μ - 3σ):
sorted_images = sorted(images, key=lambda img: img.rating.ordinal(), reverse=True)

# Access mu and sigma:
print(r1.mu, r1.sigma)
```

### Persistence: SQLite

Store everything in a single SQLite database file (e.g., `rankings.db`). This survives sessions and can be backed up easily.

**Schema:**
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    filepath TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    mu REAL DEFAULT 25.0,
    sigma REAL DEFAULT 8.333333,
    comparison_count INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_compared_at TIMESTAMP
);

CREATE TABLE comparisons (
    id INTEGER PRIMARY KEY,
    winner_id INTEGER REFERENCES images(id),
    loser_id INTEGER REFERENCES images(id),
    was_draw BOOLEAN DEFAULT FALSE,
    compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_images_exposure ON images((mu - 3 * sigma) DESC);
CREATE INDEX idx_images_uncertainty ON images(sigma DESC);
CREATE INDEX idx_images_filepath ON images(filepath);
```

### Interface: Flask Web UI

Local web interface at `http://localhost:5000`. Key features:

1. **Side-by-side image display** - Show two images at reasonable size
2. **Keyboard shortcuts**:
   - Left arrow or `1` → Left image wins
   - Right arrow or `2` → Right image wins
   - `S` → Skip (treat as draw, or just pick new pair)
   - `U` → Undo last comparison
   - `R` → Refresh/rescan for new images
3. **Progress indicator** - Show comparison count, estimated ranking stability
4. **Quick stats** - Total images, comparisons done, top-rated preview

### Smart Pairing Strategy

Don't just pick random pairs. Prioritize comparisons that reduce uncertainty fastest:

1. **New images first**: Images with σ close to default (8.333) and low comparison_count
2. **High uncertainty**: Prioritize images with high σ values
3. **Similar ratings**: Compare images with similar μ values to disambiguate rankings
4. **Avoid repetition**: Don't show the same pair twice in a session

Suggested algorithm:
```python
def pick_pair(images):
    # Weight by uncertainty (sigma) - higher sigma = more likely to be picked
    # Also factor in comparison_count to ensure coverage
    weights = [img.sigma * (1 + 1/(img.comparison_count + 1)) for img in images]
    
    # Pick first image weighted by uncertainty
    img1 = random.choices(images, weights=weights)[0]
    
    # Pick second image: prefer similar mu, high sigma, not recently compared against img1
    candidates = [img for img in images if img.id != img1.id]
    # Weight by: sigma * closeness_to_img1_mu
    weights2 = [
        c.sigma * (1 / (abs(c.mu - img1.mu) + 1))
        for c in candidates
    ]
    img2 = random.choices(candidates, weights=weights2)[0]
    
    return img1, img2
```

### Auto-Detect New Images

On startup and when user presses `R`:

1. Scan configured image directory (recursively optional)
2. Find all .jpg, .jpeg, .png, .webp files
3. Add any files not already in database with default ratings
4. Optionally mark removed files (don't delete from DB - they may come back)

```python
def scan_for_new_images(directory, recursive=True):
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    existing = {row['filepath'] for row in db.execute('SELECT filepath FROM images')}
    
    for path in Path(directory).rglob('*') if recursive else Path(directory).glob('*'):
        if path.suffix.lower() in extensions and str(path) not in existing:
            db.execute(
                'INSERT INTO images (filepath, filename) VALUES (?, ?)',
                (str(path), path.name)
            )
```

### Export & Top-N Extraction

Key feature for the workflow - extract the best images:

1. **View rankings**: Show sortable table of all images by exposure score
2. **Export top N**: Copy/symlink top N images to an output directory
3. **Export to CSV**: Full rankings data for analysis
4. **Threshold export**: Export all images above a certain exposure score

```python
def export_top_n(n, output_dir):
    top = db.execute('''
        SELECT filepath, mu, sigma, (mu - 3 * sigma) as exposure
        FROM images
        ORDER BY exposure DESC
        LIMIT ?
    ''', (n,)).fetchall()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    for i, row in enumerate(top, 1):
        src = Path(row['filepath'])
        # Prefix with rank for easy sorting in file browser
        dst = output_dir / f"{i:04d}_{src.name}"
        shutil.copy2(src, dst)  # or os.symlink for space savings
```

## File Structure

```
image-ranker/
├── app.py              # Flask application, routes
├── database.py         # SQLite operations, schema init
├── ranking.py          # OpenSkill integration, pairing logic
├── scanner.py          # Image directory scanning
├── exporter.py         # Export/extraction functions
├── templates/
│   ├── base.html       # Base template with nav
│   ├── compare.html    # Main comparison interface
│   ├── rankings.html   # Full rankings table view
│   └── export.html     # Export configuration
├── static/
│   ├── style.css       # Minimal styling
│   └── app.js          # Keyboard handlers, AJAX
├── rankings.db         # SQLite database (created on first run)
└── config.py           # Configuration (image dirs, etc.)
```

## Configuration

Support both CLI args and a config file:

```python
# config.py or via CLI
IMAGE_DIRECTORIES = ['/path/to/mj/upscales']  # Can be multiple
RECURSIVE_SCAN = True
DATABASE_PATH = './rankings.db'
HOST = '127.0.0.1'
PORT = 5000
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
```

## UI Wireframe

### Compare View (main screen)
```
┌─────────────────────────────────────────────────────────────┐
│  Image Ranker    [Rankings] [Export] [Rescan]    #1847 done │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐       ┌─────────────────┐            │
│   │                 │       │                 │            │
│   │                 │       │                 │            │
│   │    Image A      │       │    Image B      │            │
│   │                 │       │                 │            │
│   │                 │       │                 │            │
│   └─────────────────┘       └─────────────────┘            │
│   μ=27.3 σ=4.1 #12          μ=24.8 σ=6.2 #5               │
│                                                             │
│         [← or 1: Left wins]   [→ or 2: Right wins]         │
│                    [S: Skip]  [U: Undo]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Rankings View
```
┌─────────────────────────────────────────────────────────────┐
│  Rankings                              [Export Top 100]     │
├─────────────────────────────────────────────────────────────┤
│  Rank │ Thumbnail │ Filename        │ μ     │ σ    │ Score │
│  ─────┼───────────┼─────────────────┼───────┼──────┼───────│
│  1    │ [thumb]   │ epic_dragon.png │ 38.2  │ 2.1  │ 31.9  │
│  2    │ [thumb]   │ sunset_cat.jpg  │ 36.8  │ 2.4  │ 29.6  │
│  3    │ [thumb]   │ neon_city.png   │ 35.1  │ 2.8  │ 26.7  │
│  ...  │           │                 │       │      │       │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Notes

### Performance Considerations

- **Lazy image loading**: Don't load all images into memory. Serve from disk.
- **Thumbnail generation**: Consider generating thumbnails for rankings view
- **Database indices**: Ensure proper indices for common queries
- **Batch operations**: When scanning thousands of files, batch INSERT operations

### Edge Cases to Handle

1. **Missing files**: Image was deleted from disk but exists in DB
2. **Duplicate filenames**: Different paths, same filename - use full path as key
3. **Very large images**: Consider max dimensions for display
4. **Corrupt images**: Gracefully skip images that can't be loaded
5. **Empty directory**: Handle case of no images found

### Future Enhancements (not MVP)

- Tags/categories for filtering
- Multi-user support with separate rankings
- Batch comparison mode (show 4+ images, pick best)
- Auto-backup database
- Image zoom on hover/click
- Keyboard shortcut for "flag for review"
- Integration with upscaling pipeline

## Getting Started Commands

```bash
# Install dependencies
pip install flask openskill pillow

# Initialize and run
python app.py --directory /path/to/images

# Or with config file
python app.py --config config.yaml
```

## Success Criteria

1. Can rank 5000+ images without performance issues
2. Rankings persist across sessions
3. New images are automatically detected and integrated
4. Can export top N images with one click
5. Keyboard-only operation is smooth and fast
6. Comparison count needed for stable top-100 is reasonable (~2000-3000 comparisons for 5000 images)
