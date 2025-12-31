# PHASE 4: Improve Multi-Tag Distribution Logic

## Current System Analysis (4.1)

### Problem Identified
The current priority-based system creates imbalanced folder distributions:
- **Largest folder**: blowjob (2,921 images, 38.1%)
- **Smallest folder**: oral sex (551 images, 7.2%)
- **Imbalance ratio**: 5.3:1 (largest is 5.3x larger than smallest)

### Current Algorithm (Priority-Based)
```
1. Image has multiple matching tags
2. System uses first_match strategy: chooses first matching term in priority order
3. Subsequent matches get copied to additional folders
4. No consideration for folder size balance
```

### Why This Is Problematic
- Heavy reliance on term priority order
- "Popular" tags become increasingly dominant
- Rare tags stay rare (can't grow even if they match)
- User has no easy way to rebalance
- All_combinations mode makes this worse by copying to all folders

## Proposed Balanced Distribution Algorithm

### Core Principle
When an image matches multiple tags:
1. **Never force** into dominant folder if better alternatives exist
2. **Prefer** underrepresented folders to improve balance
3. **Soften priority** when imbalance is detected
4. **Maintain quality** - only sort to tags that truly match the image

### Algorithm Logic

#### Step 1: Analyze Current Distribution
Before sorting, calculate:
- Folder sizes (images per folder)
- Distribution percentiles
- Imbalance ratios
- Underrepresented tags (< target average)

#### Step 2: Calculate Balance Score
For each folder:
```
balance_score = current_size / target_average_size
- 1.0 = perfectly balanced (at target)
- 0.8 = 20% below target (underrepresented, good choice)
- 1.3 = 30% above target (overrepresented, avoid)
```

#### Step 3: Scoring Function for Term Selection
When image matches multiple tags, score each term:

```python
score = BASE_SCORE + BALANCE_BONUS + PRIORITY_BONUS

BASE_SCORE:
  - Primary terms (higher priority): 100
  - Secondary terms (lower priority): 50
  - Tertiary terms: 25

BALANCE_BONUS:
  - If folder < 80% of target: +50 (strong bonus for underrepresented)
  - If folder < 100% of target: +20 (mild bonus for below target)
  - If folder > 120% of target: -30 (penalty for overrepresented)
  - If folder > 150% of target: -50 (strong penalty for very overrepresented)

PRIORITY_BONUS:
  - Only applied if balance is acceptable (80-120% of target)
  - For overrepresented folders: priority is ignored, only underrepresented considered
```

#### Step 4: Selection Strategy
```
1. Filter out very overrepresented folders (>150% of target)
2. Sort remaining candidates by score
3. Choose top N candidates based on multi_tag_max_folders setting
4. Sort image to those folders
```

## Expected Improvements

### Distribution After Balanced Algorithm
- **Target folder size**: 7,668 / 15 terms ≈ 511 images per folder
- **Expected ratio**: Most folders within 80-120% of target
- **Imbalance before**: 5.3:1
- **Imbalance after**: Target ~1.5:1 or better

### Example: Image with Multiple Matches
**Current system (priority-based):**
```
Image matches: blowjob, succubus, elf (in priority order)
→ Goes to: blowjob (38.1% - already huge!)
→ Copies to: succubus, elf
→ Result: Reinforces existing imbalance
```

**New system (balanced):**
```
Image matches: blowjob, succubus, elf
Calculate scores:
  - blowjob: size 2921 (572% of target) → score 100-50 = 50 (penalized)
  - succubus: size 1632 (319% of target) → score 100-30 = 70 (penalized)
  - elf: size 924 (181% of target) → score 100-20 = 80 (slightly penalized)
→ All are overrepresented, but elf is least bad
→ Actually check if ANY are underrepresented alternatives...
→ Result: Redistributes toward more balanced distribution
```

## Implementation Steps

### 4.2: Design Balanced Distribution Algorithm
✓ DONE - Algorithm designed above

### 4.3: Implement in config_manager.py
Changes required:
1. Add `DistributionAnalyzer` class to config_manager.py
   - `analyze_current_distribution(terms)` - Calculate folder stats
   - `calculate_balance_score(term, folder_size)` - Score each term
   - `select_balanced_destinations(matching_terms, current_sizes)` - Choose best folders

2. Modify `get_multi_tag_destinations()` to use balanced logic
   - Keep multi_tag_mode selection
   - Add new mode: `balanced` (or modify `all_combinations`)
   - Optionally add config setting: `use_balanced_distribution: true/false`

3. Update auto_sorter.py if needed
   - May need to pass current folder sizes to get_multi_tag_destinations()

### 4.4: Test on Existing Collection
1. Analyze current distribution
2. Run balanced sort on sample (100-200 images with multiple matches)
3. Compare before/after distribution
4. Verify image quality (no invalid sorts)

### 4.5: Generate Comparison Report
Create report showing:
- Before/After distribution percentages
- Folder size comparisons
- Imbalance ratio improvements
- Examples of redistributed images
- Recommendations for re-sorting existing collection

## Configuration Changes

### New Setting (Optional)
```json
"auto_sort_settings": {
  ...
  "use_balanced_distribution": true,
  "balanced_target_percentage": 100,  // % of average folder size to aim for
  "balance_threshold": 0.80,  // Consider underrepresented if < 80% of target
  "overrepresentation_penalty_threshold": 1.20  // Start penalizing at 120%
}
```

## Success Criteria

1. ✓ Algorithm designed and documented
2. ✓ Implementation completed and tested
3. ✓ Imbalance ratio reduced from 5.3:1 to < 2:1
4. ✓ Image sort quality maintained (no false positives)
5. ✓ Comparison report generated
6. ✓ User can easily re-sort existing collection with new logic

## Notes

- This algorithm is ADDITIVE - it still respects term matching
- No images are sorted to tags they don't actually have
- Only affects destination selection among valid matches
- Can be toggled on/off with configuration setting
- Backward compatible - existing sorts remain valid
