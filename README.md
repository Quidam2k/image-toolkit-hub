# Enhanced Image Grid Sorter

A comprehensive Python/Tkinter toolkit for visually sorting and organizing large image collections with AI-powered classification and auto-sorting capabilities.

## Quick Start

### Windows Users
Simply double-click `start.bat` to launch the application.

### Using the Hub (Recommended)
```bash
python app_hub.py
```
The Image Toolkit Hub provides a modern interface to access all tools:
- **Manual Grid Sorter** - Visual grid for keyboard/mouse sorting
- **Auto-Sort by Tags** - Sort by metadata and prompt content
- **Visual Classification** - AI-powered sorting by shot type, person count
- **T-Shirt Ready Finder** - Find images with simple/removable backgrounds

### Direct Grid Sorter
```bash
python image_sorter_enhanced.py
```

## Requirements

- Python 3.7 or higher
- Required packages:
  - tkinter (usually included with Python)
  - Pillow (PIL) - `pip install Pillow`

## Features

### Visual Grid Sorting
- Display images in a customizable grid layout
- Sort images with mouse clicks or keyboard shortcuts
- Supports multiple source folders with organized destination folders

### Multi-Source Management
- Add multiple source folders containing images
- Enable/disable specific sources with checkboxes
- Automatically creates organized destination folders for each source:
  ```
  sorted_SourceFolderName/
  ├── 1/           # Category 1 images
  ├── 2/           # Category 2 images  
  ├── 3/           # Category 3 images
  ├── removed/     # Removed/skipped images
  ├── auto_sorted/ # Auto-sorted images
  └── unmatched/   # Images that don't match any terms
  ```

### Auto-Sort Capabilities
- Automatically sort images based on metadata/prompt content
- Configure custom search terms with different matching modes
- Multi-tag support with various sorting strategies
- Smart combination folders for images matching multiple terms
- Progress tracking with pause/resume/cancel options

### Advanced Features
- Metadata caching for improved performance
- Tag file embedding into image metadata
- Configuration backup and migration
- Extensive statistics and operation logging
- Import/export term configurations
- Re-sort existing collections with updated rules

## Controls

### Mouse Controls
- **Left Click**: Sort to folder 1
- **Right Click**: Next page
- **Middle Click**: Open configuration
- **Mouse Button 4**: Sort to folder 2
- **Mouse Button 5**: Sort to folder 3

### Keyboard Controls
- **1, 2, 3**: Sort to respective folders
- **Space**: Next page
- **R**: Reload images
- **C**: Open configuration
- **Escape**: Exit application
- **Ctrl+A**: Auto-sort all images
- **Ctrl+T**: Open term manager

### Menu Options
- **File > Settings**: Configure application
- **File > Auto-Sort Images**: Batch auto-sort
- **File > Term Manager**: Manage auto-sort terms
- **Tools > Scan Metadata**: Check metadata in current batch
- **Tools > Embed Tag Files**: Embed .txt files into image metadata

## Getting Started

1. **First Launch**: Run `start.bat` or the Python script
2. **Configuration**: Set up your source folders and display preferences
3. **Add Sources**: Use "Add Source Folder..." to add folders containing images
4. **Start Sorting**: Use mouse/keyboard to sort images into categories
5. **Auto-Sort**: Configure terms in Term Manager for automatic sorting

## Supported Formats

- PNG, JPG/JPEG, BMP, GIF, WebP image formats
- Handles large images (up to ~300MP) with automatic optimization
- Supports companion .txt tag files

## Tips

- **Copy Mode**: Enable to keep original images in source folders
- **Random Order**: Randomize image display for unbiased sorting
- **Auto-Sort Terms**: Great for AI-generated images with embedded prompts
- **Multi-Tag Modes**: Choose how to handle images matching multiple terms
- **Backup**: Configuration is automatically backed up before changes

## Troubleshooting

### Python Not Found
- Install Python from https://python.org
- Make sure "Add Python to PATH" is checked during installation
- Restart your command prompt/terminal after installation

### Missing Pillow
```bash
pip install Pillow
```

### Large Image Warnings
The application automatically handles large images and suppresses decompression bomb warnings for legitimate large images.

## File Structure

```
image_grid_sorter/
├── start.bat                    # Easy launcher (Windows)
├── image_sorter_enhanced.py     # Main application
├── config_manager.py            # Configuration management
├── setup_dialog.py              # Setup/configuration dialog
├── metadata_parser.py           # Image metadata extraction
├── auto_sorter.py               # Automatic sorting logic
├── term_manager.py              # Term management dialog
└── [other modules...]           # Additional components
```

## Version History

- **v2.1**: Added multi-source support, organized destination folders, improved large image handling
- **v2.0**: Enhanced auto-sorting, multi-tag support, metadata embedding
- **v1.x**: Original grid-based sorting functionality