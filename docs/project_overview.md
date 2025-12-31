# Image Sorter - Project Overview

## Current Architecture

The Image Sorter is a tkinter-based Python application for visually sorting images into categorized folders. The application follows a modular architecture:

### Core Components

- **`app.py`** - Main application class (`ImageSorter`) that coordinates all components
- **`config_manager.py`** - Handles configuration loading/saving and folder setup
- **`image_loader.py`** - Manages image loading, threading, and preprocessing
- **`ui_manager.py`** - Handles UI creation, event binding, and user interactions
- **`image_preview.py`** - Creates hover preview windows for images
- **`config_dialog.py`** - Settings dialog for user preferences
- **`utils.py`** - Utility functions for file operations

### Current Features

1. **Visual Sorting**: Display images in a grid layout for manual categorization
2. **Multiple Source Folders**: Support for multiple input directories
3. **Configurable Categories**: User-defined output folders (1, 2, 3, removed)
4. **Undo Functionality**: Reverse recent sorting operations
5. **Preview on Hover**: Quick image preview without opening
6. **Batch Processing**: Efficient loading and display of image batches
7. **Threading**: Background image loading for responsive UI

### Data Flow

1. Images loaded from source folders → ImageLoader
2. Images preprocessed and cached → displayed in UI
3. User interactions (clicks/keys) → sorting actions
4. Files moved/copied to destination folders
5. Undo operations tracked in history deque

## New Feature: Metadata Auto-Sort

### Objective
Add automatic sorting based on image metadata (specifically Stable Diffusion Forge generation data) to complement the existing visual sorting workflow.

### Key Requirements
- Parse image metadata for search terms
- Automatically sort images into term-based subfolders
- Maintain compatibility with existing manual sorting
- Provide UI for term management
- Support batch metadata processing
- Handle various image formats and metadata storage methods

### Integration Points
- Extend ConfigManager for metadata terms storage
- Add new UI components for term management
- Create metadata parsing utilities
- Integrate auto-sort with existing batch processing
- Update progress tracking for metadata operations