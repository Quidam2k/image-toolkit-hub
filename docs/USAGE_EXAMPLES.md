# Export Batch Tool - Usage Examples

This document provides practical examples for common workflows with the Export Batch Tool.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Creating Video Batches](#creating-video-batches)
3. [Query Combinations](#query-combinations)
4. [Advanced Workflows](#advanced-workflows)
5. [Troubleshooting](#troubleshooting)

## Quick Start

### First Time Setup

**Step 1: Check available tags**
```bash
python export_batch.py list
```

This shows all 80 tags with frequencies. Browse to understand what's available.

**Step 2: Try a simple query**
```bash
python export_batch.py query --tags blowjob --limit 5
```

This shows a sample without copying anything (dry-run).

**Step 3: Export if satisfied**
```bash
python export_batch.py export --tags blowjob --output ./my_batches
```

This creates a batch folder with all matching images.

---

## Creating Video Batches

These examples show creating different batch types for WAN 2.2 i2v.

### Scenario 1: Single-Tag Batch (Homogeneous)

**Goal:** Create a batch with only one type of content for consistent style

**Query:**
```bash
python export_batch.py export --tags succubus --name succubus_consistent
```

**Result:** 1,632 images all tagged with "succubus"

**Use case:** When you want a video with consistent character appearance

---

### Scenario 2: Character Variety (OR Logic)

**Goal:** Mix multiple characters but exclude a specific type

**Query:**
```bash
python export_batch.py export --tags "succubus|elf|girl" --name fantasy_variety
```

**Result:** 3,872 images (union of all three tags)

**Use case:** Diverse fantasy character content

**Further customize:**
```bash
# Even more variety
python export_batch.py export --tags "succubus|elf|girl|boy|woman|man"

# Fantasy characters only (more focused)
python export_batch.py export --tags "succubus|elf" --name fantasy_only

# Humans only
python export_batch.py export --tags "girl|boy|woman|man,!futanari"
```

---

### Scenario 3: Content Type Specific (AND Logic)

**Goal:** Mix characters but enforce specific content type

**Query:**
```bash
python export_batch.py export --tags "blowjob,girl" --name blowjob_girls
```

**Result:** Images with BOTH "blowjob" AND "girl" tags

**Other combinations:**
```bash
# Blowjob with succubus
python export_batch.py export --tags "blowjob,succubus"

# Sex with multiple characters
python export_batch.py export --tags "sex,succubus|elf"

# Penetration but NOT solo
python export_batch.py export --tags "penetration,!masturbation"
```

---

### Scenario 4: Exclude Specific Content (NOT Logic)

**Goal:** Get a general category but exclude unwanted elements

**Query:**
```bash
python export_batch.py export --tags "blowjob,!futanari,!boy" --name blowjob_female_only
```

**Result:** 2,300+ images with blowjob but excluding futanari and boy tags

**Other examples:**
```bash
# All realistic content except 3D
python export_batch.py export --tags "realistic,!3d"

# All girl content except kneeling
python export_batch.py export --tags "girl,!kneeling"

# All nude content except masturbation
python export_batch.py export --tags "nude,!masturbation"
```

---

### Scenario 5: Complex Multi-Criteria (Advanced)

**Goal:** Sophisticated query combining multiple criteria

**Query 1: Fantasy oral content with variety**
```bash
python export_batch.py export --tags "(blowjob|oral sex),succubus|elf" --name fantasy_oral
```

Result: (blowjob OR oral sex) AND (succubus OR elf)

**Query 2: Realistic content excluding solo**
```bash
python export_batch.py export --tags "realistic,(sex|penetration),!masturbation" --name realistic_group
```

**Query 3: Diverse nude with specific exclusions**
```bash
python export_batch.py export --tags "nude,(girl|woman),!kneeling,!futanari"
```

---

## Query Combinations

### Understanding AND vs OR

**AND (Comma):**
- Requirements: ALL tags must be present
- Fewer results (intersection)
- More specific, filtered results

**OR (Pipe):**
- Requirements: AT LEAST ONE tag must be present
- More results (union)
- Broader, more variety

### Comparison Table

| Query | Results | Use Case |
|-------|---------|----------|
| `blowjob` | 2,847 | Single content type |
| `blowjob,succubus` | 128 | Specific combination |
| `blowjob\|succubus` | 4,319 | Either content type |
| `blowjob,!elf` | 2,716 | Content excluding a tag |
| `(blowjob\|succubus),!futanari` | 3,876 | Complex: (A OR B) AND NOT C |

---

## Advanced Workflows

### Workflow 1: Testing Then Production

**Step 1: Quick test with symlinks**
```bash
# Create test batch with symlinks (2 seconds)
python export_batch.py export --tags "blowjob,succubus" --mode symlink --name test_batch
```

**Step 2: Review test results**
- Check the batch folder
- Verify image quality/appropriateness
- Ensure query returned expected results

**Step 3: Create production batch**
```bash
# Create final batch with real copies (45 seconds)
python export_batch.py export --tags "blowjob,succubus" --mode copy --name production_final
```

---

### Workflow 2: Creating Multiple Variations

**Goal:** Create several different batches for different video clips

```bash
# Batch 1: Action-heavy
python export_batch.py export --tags "sex,penetration" --name clip1_action

# Batch 2: Oral-focused
python export_batch.py export --tags "blowjob|oral sex" --name clip2_oral

# Batch 3: Fantasy variety
python export_batch.py export --tags "succubus|elf,!futanari" --name clip3_fantasy

# Batch 4: Diverse and spicy
python export_batch.py export --tags "futanari|sex|penetration" --name clip4_spicy

# Batch 5: Aesthetic/realistic focus
python export_batch.py export --tags "realistic,detailed" --name clip5_aesthetic
```

Result: 5 different batch folders ready for WAN 2.2

---

### Workflow 3: Iterative Refinement

**Step 1: Start broad**
```bash
python export_batch.py query --tags girl --limit 10
# Found: 1,548 images
```

**Step 2: Check specific sub-tags**
```bash
python export_batch.py query --tags "girl,petite" --limit 5
# Found: 48 images

python export_batch.py query --tags "girl,pink hair" --limit 5
# Found: 28 images
```

**Step 3: Create refined batch**
```bash
python export_batch.py export --tags "girl,petite,!futanari" --name petite_girls_refined
```

---

### Workflow 4: Tag Discovery

**Goal:** Find what tags are available before querying

```bash
# List all tags with frequencies
python export_batch.py list --sort count

# Sort by name to find related tags
python export_batch.py list --sort name | grep -i "hair"

# Then query discovered tags
python export_batch.py export --tags "pink hair,1girl"
```

---

## Troubleshooting

### Common Issues and Solutions

### Issue 1: "Unknown tags: xyz"

**Problem:**
```bash
python export_batch.py query --tags blowjob,fellatio
# ERROR: Unknown tags: fellatio
```

**Solution:**
Check available tags:
```bash
python export_batch.py list | grep -i fellatio
```

Use the exact tag name:
```bash
python export_batch.py query --tags "blowjob|oral sex"  # Not "fellatio"
```

---

### Issue 2: Query Returns No Results

**Problem:**
```bash
python export_batch.py query --tags "blowjob,futanari,woman"
# Found: 0 matching images
```

**Solution:**
The combination might be too specific. Try:

1. Check if each tag exists independently:
```bash
python export_batch.py query --tags blowjob
python export_batch.py query --tags futanari
python export_batch.py query --tags woman
```

2. Try OR instead of AND:
```bash
python export_batch.py query --tags "blowjob|futanari|woman"
```

3. Try with fewer tags:
```bash
python export_batch.py query --tags "blowjob,woman"
```

---

### Issue 3: Batch Folder Is Huge

**Problem:**
Batch folder is 8+ GB after export

**Solution:**
This is normal! 2,900+ images × 2-3MB average = 6-9GB

**Strategies:**

1. For testing: Use `--mode symlink`
```bash
python export_batch.py export --tags blowjob --mode symlink
# Uses minimal disk space for testing
```

2. For production: Accept the size or split into smaller batches
```bash
# Instead of one huge batch, create multiple smaller ones
python export_batch.py export --tags "blowjob,succubus"  # 128 images, ~400MB
python export_batch.py export --tags "blowjob,!succubus,!elf"  # Remaining
```

---

### Issue 4: Export is Too Slow

**Problem:**
Copying 2,847 images takes too long (45+ seconds)

**Solution:**

1. **Use symlink mode for testing:**
```bash
python export_batch.py export --tags blowjob --mode symlink
# 2 seconds instead of 45 seconds
```

2. **Create smaller batches:**
```bash
python export_batch.py export --tags "blowjob,succubus"  # 128 images only
```

3. **Check disk speed:**
The bottleneck is usually disk I/O. SSD vs HDD makes a huge difference.

---

### Issue 5: Manifest File Missing

**Problem:**
Batch folder has images but no manifest.json

**Solution:**
Manifests are always created. Check:
```bash
ls batch_exports/batch_*/manifest.json
```

If missing, the export may have failed. Try again:
```bash
python export_batch.py export --tags blowjob --name retry_batch
```

---

## Real-World Example Workflows

### Example Workflow A: Creating a Varied Video

**Goal:** Create a 5-minute video with diverse content

**Step 1: Plan content mix**
- 30% blowjob content
- 20% succubus characters
- 20% fantasy settings
- 30% diverse poses/angles

**Step 2: Create query**
```bash
# Blowjob with variety
python export_batch.py query --tags "(blowjob),(succubus|elf|girl)"
# Found: ~900 images

# All looks good, export!
python export_batch.py export --tags "(blowjob),(succubus|elf|girl)" --name varied_video_batch
```

**Step 3: Feed to WAN 2.2**
- Point WAN 2.2 to batch folder
- Process with interpolation
- Output: smooth, diverse 5-min clip

---

### Example Workflow B: Character-Focused Series

**Goal:** Create 3 character-specific video clips

**Clip 1: Succubus Focus**
```bash
python export_batch.py export --tags "succubus" --name succubus_series_clip1
```

**Clip 2: Succubus Action**
```bash
python export_batch.py export --tags "succubus,(sex|blowjob)" --name succubus_series_clip2
```

**Clip 3: Succubus Fantasy**
```bash
python export_batch.py export --tags "succubus,elf" --name succubus_series_clip3
```

Result: 3 coordinated clips with character consistency

---

### Example Workflow C: Aesthetic Series

**Goal:** Create clips with consistent visual style

**Clip 1: Realistic**
```bash
python export_batch.py export --tags "realistic,detailed" --name aesthetic_realistic
```

**Clip 2: 3D**
```bash
python export_batch.py export --tags "3d,detailed" --name aesthetic_3d
```

**Clip 3: Fantasy Art**
```bash
python export_batch.py export --tags "elf|succubus,!3d,detailed" --name aesthetic_fantasy_art
```

---

## Performance Tips

### Speed Up Queries
- Single tag queries are instant (<1ms)
- AND queries with 2+ tags: <5ms
- Complex queries with NOT: <10ms

### Speed Up Exports
| Mode | Speed | Disk Space | Best For |
|------|-------|-----------|----------|
| Copy | ~45s for 2,847 imgs | Full copy (8GB) | Final batches |
| Symlink | ~2s for 2,847 imgs | Minimal (links only) | Testing |

### Choose Your Mode Based on Need:
- **Testing new queries:** Use `--mode symlink` (instant)
- **Final production batch:** Use `--mode copy` (safe, independent)
- **Archive:** Use `--mode copy` (no dependencies on source)

---

## Tips & Tricks

### Tip 1: Use Filters in Your Shell

Find tags matching a pattern:
```bash
python export_batch.py list --sort name | grep "hair"
# Output: blue_eyes, pink_hair, red_hair, etc.
```

### Tip 2: Create Batch Scripts

Create a `create_batches.sh` script:
```bash
#!/bin/bash
python export_batch.py export --tags blowjob --name batch_1
python export_batch.py export --tags succubus|elf --name batch_2
python export_batch.py export --tags girl --name batch_3
echo "All batches created!"
```

Run all at once:
```bash
bash create_batches.sh
```

### Tip 3: Estimate Batch Size

Before exporting, check how many images:
```bash
python export_batch.py query --tags "blowjob,succubus"
# Shows: 128 images (roughly 400MB)
```

Then decide on mode:
- < 1,000 images: Doesn't matter
- 1,000-3,000 images: Use symlink for testing
- > 3,000 images: Definitely symlink first!

### Tip 4: Documentation

Save your batch creation workflow:
```bash
# batch_workflow.txt
blowjob → 2847 images (basic action)
succubus → 1632 images (character focused)
blowjob,succubus → 128 images (specific combo)
(blowjob|succubus),!elf → 3876 images (mixed non-fantasy)
```

---

## FAQ

**Q: Can I combine more than 2 tags with OR?**
A: Yes! `blowjob|succubus|elf|girl|woman` works fine.

**Q: Can I have multiple AND conditions?**
A: Yes! `blowjob,succubus,detailed` requires all three.

**Q: What's the largest batch I can create?**
A: All 7,287 images if you query the broadest possible criteria. Limited by disk space.

**Q: Can I delete or modify batches?**
A: Yes, they're just folders. Delete when done. The manifest.json is for reference only.

**Q: How often should I update tag_frequency.json?**
A: Each time you add new images to the collection or want updated frequencies.

**Q: Can I use the tool without WAN 2.2?**
A: Yes! It's useful for any batch image operations, not just i2v.

---

**Last Updated:** October 18, 2025
