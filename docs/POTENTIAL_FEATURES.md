# Potential Features for Image Toolkit Hub

A living document of feature ideas for future development. Ideas are organized by category and include rough effort estimates.

**Last Updated:** January 17, 2026

---

## AI-Powered Features

These features leverage the existing CLIP/WD14 infrastructure but require computing and storing embeddings for images.

### Semantic Search ("Find me a cat in space")
- **Concept:** Natural language search instead of exact tag matching
- **How it works:** Map user text queries to CLIP embeddings, find nearest images
- **UX:** Simple search bar that accepts sentences like "sad visuals with blue tones"
- **Prerequisites:**
  - Compute CLIP embeddings for all images (one-time batch job)
  - Store embeddings in SQLite or numpy files (~1KB per image)
- **Effort:** Medium-High (embedding pipeline + search UI)

### Find Similar Images (Visual Reverse Search)
- **Concept:** Select an image, click "Show Similar" to find visually related images
- **How it works:** Cosine similarity between selected image's embedding and collection
- **Use case:** Find one perfect reference, see everything else that matches that vibe
- **Prerequisites:** Same as semantic search (stored embeddings)
- **Effort:** Medium (once embeddings exist)

### Galaxy View (t-SNE/UMAP Visualization)
- **Concept:** 2D scatter plot where every dot is an image, similar images cluster together
- **How it works:** Dimensionality reduction on CLIP embeddings
- **UX:** Zoomable/pannable canvas, hover to preview, click to select
- **Use cases:**
  - Discover clusters of similar content
  - Find outliers or low-quality images
  - Bulk-select and tag entire clusters
- **Prerequisites:** Stored embeddings + visualization library (matplotlib or custom canvas)
- **Effort:** High

---

## Workflow & Interaction

### Quick Look Preview (Spacebar)
- **Concept:** macOS-style Quick Look - press Space to see full-size image without leaving context
- **Current state:** Need to open separate dialogs to view details
- **Implementation:** Overlay panel or borderless Toplevel with large image
- **Effort:** Low-Medium

### Global Drag-and-Drop
- **Concept:** Drag folders/images from Explorer onto the app window
- **Actions:** Add to source queue, trigger quick sort, or start tagging
- **Implementation:** Tkinter DnD (tkinterdnd2 library) or native Windows hooks
- **Effort:** Medium (cross-platform DnD can be tricky)

### Context-Aware Right-Click Menus
- **Concept:** Right-click on image thumbnails for power-user shortcuts
- **Options:**
  - Open in external editor (Photoshop, Paint.NET)
  - Open file location in Explorer
  - Quick exclude/delete
  - Copy tags to clipboard
  - Add to ranking session
- **Effort:** Low-Medium

### Keyboard Shortcut Customization
- **Concept:** User-configurable keybindings
- **Current state:** Hardcoded shortcuts
- **Implementation:** Settings panel with keybind editor
- **Effort:** Medium

---

## Visual & Feedback

### Collection Dashboard / Home Tab
- **Concept:** High-level insights about image collection at a glance
- **Stats to show:**
  - Total images across all sources
  - Top 10 tags with percentages
  - Distribution by folder/category
  - Recent activity summary
- **Effort:** Medium (data aggregation + UI)

### Gamified Ranking UI ("Focus Mode")
- **Concept:** Distraction-free ranking experience
- **Features:**
  - Fullscreen interface
  - Smooth transition animations
  - Progress indicator ("Matches per minute")
  - Streak counter for flow state
- **Current state:** Ranker works but could be more immersive
- **Effort:** Low-Medium (UI polish)

### Progress Overlay Instead of Dialogs
- **Concept:** Replace modal progress dialogs with non-modal overlays
- **Benefit:** Can continue browsing while operations run
- **Effort:** Medium (architectural change)

---

## Accessibility & Personalization

### Workspace Profiles
- **Concept:** Save and switch between layout/configuration sets
- **Example profiles:**
  - "Culling" - Large thumbnails, delete shortcuts, minimal UI
  - "Tagging" - Side panel with tag editor, metadata visible
  - "Ranking" - Focus mode, fullscreen comparisons
- **Effort:** Medium

### High-Contrast / Color Blind Modes
- **Concept:** Ensure UI themes support accessibility needs
- **Implementation:** Additional theme presets in ui_theme.py
- **Effort:** Low

### Adjustable Thumbnail Sizes
- **Concept:** Slider or presets for thumbnail size in grid views
- **Current state:** Fixed thumbnail sizes
- **Effort:** Low

---

## Data & Export

### Batch Metadata Editor
- **Concept:** Edit tags/metadata for multiple selected images at once
- **Operations:** Add tag to all, remove tag from all, find/replace
- **Effort:** Medium

### Export Presets
- **Concept:** Save export configurations (format, size, destination)
- **Use case:** "Export for training" vs "Export for web"
- **Effort:** Low

### Sync with External Tag Databases
- **Concept:** Import/export compatibility with Hydrus, Danbooru, etc.
- **Effort:** Medium-High (format research)

---

## Infrastructure Improvements

### Background Operation Queue
- **Concept:** Queue multiple operations to run sequentially
- **Benefit:** Start auto-sort, tag embedding, and export - let them run
- **Current state:** Operations are one-at-a-time
- **Effort:** Medium-High

### Undo/Redo System Enhancement
- **Concept:** More comprehensive undo across all operations
- **Current state:** UndoManager exists but limited scope
- **Effort:** Medium

### Plugin System
- **Concept:** Allow custom scripts/extensions
- **Use cases:** Custom taggers, export formats, sorting rules
- **Effort:** High

---

## Notes

### Embedding Pipeline Prerequisite
Several AI features require stored embeddings. If pursuing these, the first step would be:

1. Create `embedding_generator.py` that runs CLIP on images
2. Store embeddings in SQLite table: `image_path, embedding_blob, timestamp`
3. Create index for fast nearest-neighbor search (or use FAISS library)
4. Batch process existing collection (~1 image/second on CPU)

This is a one-time investment that unlocks: semantic search, find similar, galaxy view, and auto-clustering.

### Priority Suggestions
Based on effort vs. impact:

**Quick wins (low effort, good impact):**
- Context menus
- Adjustable thumbnails
- Gamified ranking polish

**Medium investment, high value:**
- Collection dashboard
- Batch metadata editor
- Workspace profiles

**Large projects (when time permits):**
- Embedding pipeline + AI features
- Plugin system
- Background operation queue
