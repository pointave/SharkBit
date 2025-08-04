# SharkBit

SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features for YouTube video handling, scene detection, and multi-video workflows. It provides a modern graphical user interface (GUI) and leverages OpenCV, ffmpeg, and other libraries for fast, flexible video processing.

---

## Features
- **Graphical Video Cropping**: Interactive crop region selection with drag-and-resize controls.
- **Batch/Multi-Video Mode**: Efficiently process and export multiple videos at once.
- **YouTube Integration**: Download and crop YouTube videos directly (using bundled yt-dlp).
- **Scene Detection & Navigation**: Custom slider and navigation for video scenes.
- **Customizable UI**: Multiple retro and modern themes, icon sets, and layout options.
- **Session Restore**: Remembers your last session, folders, and settings.
- **System Monitoring**: Built-in CPU/GPU monitoring for heavy processing tasks.

---

## Directory Structure

- `main.py` — Application entry point. Launches the PyQt6 GUI and loads the main window.
- `scripts/` — Core logic and UI modules:
  - `video_cropper.py` — Main window and app logic (video cropping, multi-video, YouTube, etc.)
  - `video_loader.py` — Video/folder loading, session management
  - `video_editor.py` — Video playback, frame navigation, crop selection
  - `video_exporter.py` — Export cropped/uncropped videos and screenshots
  - `ui_elements.py` — UI components and layout
  - `theme_selector.py` — Theme switching dialog
  - `custom_graphics_scene.py`, `custom_graphics_view.py` — Advanced graphics for cropping
  - `interactive_crop_region.py` — Drag-resize crop rectangles
  - `scene_slider.py` — Custom slider for scenes
- `styles/` — CSS stylesheets for theming
- `icons/` — SVG/PNG icons for UI
- `Monitoring/` — System monitoring utilities
- `yt-dlp.exe` — Bundled YouTube video downloader
- `session_data.json` — Persistent session state

---

## Dependencies
See `requirements.txt` for full list. Key packages:
- `PyQt6` — GUI framework
- `opencv-python`, `ffmpeg-python`, `numpy` — Video processing
- `Pillow`, `piexif` — Image and EXIF handling
- `py-cpuinfo`, `psutil`, `pynvml` — System monitoring
- `deepdiff` — Data comparison

---

## Typical Workflow
1. **Launch**: Run `main.py` to start the app.
2. **Load Videos**: Select folders or paste YouTube URLs to add videos.
3. **Preview & Crop**: Use the UI to set crop regions, navigate frames/scenes.
4. **Export**: Save cropped or uncropped videos/images.
5. **Session Restore**: Previous state is auto-loaded from `session_data.json`.

---

## License
See `LICENSE` for details.

---

## Credits
- Developed by PointAve
- Uses open-source libraries (see requirements.txt)

---

For more details, see the code comments and individual module docstrings.
