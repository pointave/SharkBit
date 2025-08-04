# SharkBit

SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features like scene detection and multi-video playback. It provides a modern graphical user interface (GUI) and leverages OpenCV, ffmpeg, and other libraries for fast video processing.

---

## Features
- **Graphical Video Cropping**: Interactive crop region selection with drag-and-resize controls.
- **Scene Detection & Navigation**: Custom slider and navigation for video scenes.
- **Customizable UI**: Multiple retro and modern themes, icon sets, and layout options.
- **Session Restore**: Remembers your last session, folders, and settings.
- **System Monitoring**: Built-in CPU/GPU monitoring for heavy processing tasks.

---

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
2. **Load Videos**: Select folders or paste YouTube URLs to add videos. Change line 509 in the cropper to set your own favorite folder.
3. **Preview & Crop**: Use the UI to set crop regions, navigate frames/scenes.
4. **Export**: Save cropped or uncropped videos.
5. **Session Restore**: Previous state is auto-loaded from `session_data.json`.

---

## License
See `LICENSE` for details.

---

## Credits
- Developed by PointAve

---

For more details, see the code comments and individual module docstrings.
