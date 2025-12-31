# Enhanced Image Grid Sorter - Complete User Guide

A comprehensive image management and sorting application designed for handling large collections of AI-generated images with intelligent auto-sorting capabilities.

## 🎯 What This Application Does

**Primary Purpose:** Efficiently sort and organize thousands of images using both manual grid-based sorting and intelligent automatic categorization based on metadata content.

**Perfect For:**
- AI-generated image collections from Stable Diffusion, DALL-E, etc.
- Large photo libraries that need categorization
- Content creators managing visual assets
- Anyone with thousands of images to organize

---

## 🚀 Major Features (Version 2.1)

### 🤖 Intelligent Auto-Sorting
- **Metadata-Based Categorization**: Automatically reads prompts, tags, and generation parameters
- **Multi-Tag Support**: Images can be placed in multiple folders simultaneously
- **4 Sorting Modes**: Choose how to handle images that match multiple categories
- **Smart Re-Sorting**: Update existing collections when you add new terms

### 🎛️ Advanced Multi-Tag Modes

#### **All-Combinations Mode** (Recommended)
- Images appear in **BOTH** individual tag folders **AND** combination folders
- Example: Image with "portrait" + "fantasy" appears in:
  - `portrait/` folder
  - `fantasy/` folder  
  - `portrait_fantasy/` combination folder
- **Perfect for:** Complete tag coverage - every folder contains ALL images with that tag

#### **Smart-Combination Mode**
- Creates combination folders for 2-3 matching tags, otherwise uses individual folders
- Intelligent fallback system based on your preferences

#### **Multi-Folder Mode**
- Places copies in separate individual folders for each matching tag
- No combination folders created

#### **Single-Folder Mode** (Legacy)
- Places image in only one folder using conflict resolution rules

### 📁 Complete Workflow Management
- **Source Scanning**: Automatically process entire folder hierarchies
- **Re-Sort Existing**: Update previously sorted images with new rules
- **Unmatched Handling**: *(Coming Soon)* Move unprocessed images to review folder
- **Progress Tracking**: Real-time feedback with pause/resume/cancel support

### 🎨 Grid-Based Manual Sorting
- **Full-Screen Interface**: Optimized for efficient image review
- **Keyboard Controls**: Sort images using number keys (1, 2, 3) or removal
- **Mouse Support**: Click-based sorting for preferred workflow
- **Batch Processing**: Handle multiple images simultaneously

---

## 🎮 Quick Start Guide

### 1. Launch the Application
```bash
python3 image_sorter_enhanced.py
```

### 2. Initial Setup
- **First Run**: Setup dialog will guide you through initial configuration
- **Source Folder**: Choose the folder containing your images to sort
- **Output Folders**: Configure destination folders (1, 2, 3, removed, auto_sorted, unmatched)

### 3. Configure Auto-Sort Terms
1. Go to **File → Term Manager** or click **"Manage Terms"** in the toolbar
2. Click **"Add Term"** to create your first search term
3. Configure each term:
   - **Term**: The word or phrase to search for (e.g., "portrait", "landscape", "anime")
   - **Priority**: Lower numbers = higher priority (1 = highest)
   - **Match Type**: How to find the term (word boundary recommended)
   - **Search Scope**: Where to look (prompt, tags, or both)

### 4. Set Multi-Tag Mode
1. In the Term Manager dialog, find **"Multi-Tag Mode"** dropdown
2. Select **"all_combinations"** for maximum coverage (recommended)
3. Configure combination folder settings:
   - ✅ **Create combination folders**
   - **Separator**: `_` (underscore)
   - **Min tags**: 2, **Max tags**: 3

### 5. Run Auto-Sort
1. Click **"Auto-Sort All"** in toolbar or **File → Auto-Sort Images**
2. Review the confirmation dialog showing your settings
3. Monitor progress with the real-time progress dialog
4. Review results summary when complete

---

## 📋 Menu Reference

### File Menu
- **Settings**: Change source folder and basic configuration
- **Auto-Sort Images...**: Sort all images in source folder
- **Re-sort Auto-Sorted Images...**: *(NEW)* Update existing sorted images with current rules
- **Term Manager...**: Configure search terms and multi-tag settings

### Tools Menu
- **Scan Metadata**: Analyze current batch for metadata content
- **Clear Metadata Cache**: Reset cached metadata for fresh analysis
- **Embed Tag Files in Images**: Merge .txt tag files into image metadata
- **Export/Import Terms**: Share term configurations

### Help Menu
- **Keyboard Shortcuts**: View all available hotkeys
- **Auto-Sort Guide**: Detailed help for auto-sort features
- **About**: Version and system information

---

## 🔧 Advanced Configuration

### Multi-Tag Settings Explained

**Max Folders**: Maximum number of individual folders an image can be copied to (default: 5)

**Combination Folders**:
- **Min tags for combination**: Minimum matching terms to create combination folder (default: 2)
- **Max tags for combination**: Maximum terms before falling back to individual folders (default: 3)
- **Separator**: Character used between terms in combination folder names (default: `_`)

**Examples**:
- 1 matching term → Individual folder: `portrait/`
- 2 matching terms → Individual + combination: `portrait/`, `fantasy/`, `portrait_fantasy/`
- 4+ matching terms → Individual folders only (too many for combination)

### Term Configuration Best Practices

**Priority System**: 
- Use priorities to handle overlapping terms
- Example: "person" (priority 10) vs "portrait" (priority 5) - portrait wins for conflicting images

**Exclusion Rules**:
- Set terms to exclude others (e.g., "landscape" excludes "portrait")
- Helps avoid inappropriate combinations

**Search Scopes**:
- **Prompt Only**: Search only in generation prompts
- **Tags Only**: Search only in tag files/metadata tags
- **Either**: Search both prompt and tags (recommended)
- **Both**: Must appear in both prompt AND tags

---

## 📊 Understanding Results

### Auto-Sort Summary
After sorting, you'll see a detailed summary:
- **Processed**: Total images analyzed
- **Sorted**: Images successfully categorized
- **Errors**: Problems encountered (with details)
- **Term Counts**: How many images matched each term
- **Unmatched**: Images that didn't match any terms

### File Operations
- **Move Mode**: Original images are moved to destination folders
- **Copy Mode**: Original images remain, copies placed in destination folders
- **Undo Tracking**: All file operations are logged for potential reversal

---

## 🔍 Troubleshooting

### Common Issues

**"No metadata found"**
- Ensure images are PNG format with embedded parameters, or have companion .txt files
- Use **Tools → Scan Metadata** to check current batch

**"Terms not matching expected images"**
- Check **Match Type** - try "contains" instead of "word boundary"
- Verify **Search Scope** includes the right metadata sources
- Use **Term Manager → Test Terms** to debug matching

**"Images appearing in wrong folders"**
- Review **Priority** settings - lower numbers win conflicts
- Check **Exclusion Rules** for unintended exclusions
- Consider adjusting **Multi-Tag Mode** for different behavior

**Performance Issues**
- **Clear Metadata Cache** if seeing stale results
- Reduce **Max Folders** if operations are slow
- Use **Copy Mode** if you want to preserve originals

### Getting Help

**Built-In Help**:
- **Help → Auto-Sort Guide**: Comprehensive feature documentation
- **Help → Keyboard Shortcuts**: All available hotkeys
- Term Manager includes tooltips and help text

**Debugging Tools**:
- **Tools → Scan Metadata**: Check what metadata is found
- Term Manager **Test Terms** button: Debug term matching
- Progress dialogs show detailed operation status

---

## 🎯 Workflow Examples

### Example 1: Basic Character Sorting
```
Terms:
- "girl" (priority 1, word boundary, either)
- "boy" (priority 1, word boundary, either)
- "couple" (priority 2, word boundary, either)

Mode: all_combinations
Result: Images sorted by character type with combination folders for multiple characters
```

### Example 2: Style + Subject Organization
```
Terms:
- "anime" (priority 5, word boundary, either)
- "realistic" (priority 5, word boundary, either) 
- "portrait" (priority 10, word boundary, either)
- "landscape" (priority 10, word boundary, either)

Mode: all_combinations
Result: Complete cross-categorization by both style and subject
```

### Example 3: Adding New Categories
```
1. Start with basic terms, run auto-sort
2. Add new detailed terms (clothing, poses, etc.)
3. Use "Re-sort Auto-Sorted Images" to apply new terms to existing collection
4. All images now categorized with both old and new terms
```

---

## 🚀 What's Coming Next

### Unmatched Image Handling *(In Development)*
- **Automatic Collection**: Move unmatched images to review folder
- **Metadata Inspection**: Browse unmatched images with full metadata display
- **Smart Suggestions**: AI-assisted term suggestions based on unmatched content
- **Direct Integration**: Add new terms directly from unmatched viewer

### Future Enhancements
- **Batch Term Creation**: Generate multiple terms from common patterns
- **Advanced Filtering**: Date ranges, file sizes, metadata completeness
- **Export Options**: Generate categorization reports and statistics
- **Plugin System**: Extensible architecture for custom metadata sources

---

## 📝 Version History

**Version 2.1** *(Current)*
- ✅ All-Combinations multi-tag mode for complete tag coverage
- ✅ Re-sort functionality for existing collections
- ✅ Enhanced progress tracking and error handling
- ✅ Comprehensive documentation and user guides

**Version 2.0**
- ✅ Multi-tag sorting with smart combination folders
- ✅ Advanced term configuration with exclusions and priorities
- ✅ JSON-based configuration with automatic migration
- ✅ Enhanced UI with comprehensive menu system

**Version 1.x**
- ✅ Basic auto-sorting with metadata extraction
- ✅ Grid-based manual sorting interface
- ✅ PNG parameter parsing for AI-generated images

---

*For technical implementation details, see the developer documentation in FUTURE_CLAUDE_NOTES.md*