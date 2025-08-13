# SharkBit

SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features like scene detection and multi-video playback. Streamlined dataset generation by making all the shortcuts on one hand. This project will continue to evolve. Updated to now have audio trimming like Audacity. I will repair code soon currently next track button doesnt work and pause is accomplished by pushing the Audio Button. I'll have separate memory for audio amd video so you can switch much faster.

I'm sorry I lost the most perfect version of this app, I'll try to rebuild what once was. 

## 🔑 Shortcuts

| Key         | Action                                                      |
| ----------- | ----------------------------------------------------------- |
| `Q`         | Close program                                               |
| `W`         | Open current folder                                         |
| `E / R`     | Previous / Next file in list                                |
| `T`         | Theme toggle                                                |
| `Y`         | Pull-out window (Shift pulls out multi-vid)                 |
| `A / S`     | Step down / up one frame                                    |
| `D / F`     | Jump 113 frames (Shift/Ctrl doubles/quadruples jump amount) |
| `G`         | Toggle random sorting                                       |
| `H`         | Remove crop selection                                       |
| `Z`         | Toggle trim preview                                         |
| `X`         | Auto-advance toggle                                         |
| `C`         | Screenshot                                                  |
| `V / Enter` | Play / Pause                                                |
| `B`         | Save clip (cropped or uncropped)                            |
| `I`         | Show info (if you use show_text comfynode you'll get prompt)|
| `/`         | Search                                                      |
| `\`         | Refresh                                                     |
| `Backspace` | Minimize                                                    |
| `Random`     | Ctrl+shft+c copies file path, Ctrl+z will undo deletetion  |

> **Tip:** To have more videos playing at once, **Ctrl+click** on two or more videos in the file list.

---

## 🛠️ Installation

```bash
git clone https://github.com/pointave/SharkBit
cd sharkbit
conda create -n sharkbit python=3.12 -y
conda activate sharkbit
OPTIONAL pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

> **Optional:** Add `yt-dlp.exe` to the `sharkbit` folder to enable YouTube downloads.
> ALSO if you want you can install pytorch in the environment it will speed up exports and give you monitorning VRAM and gpu usage.
> Update with git pull in sharkbit directory
=======
SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features for YouTube video handling, scene detection, and multi-video workflows. It provides a modern graphical user interface (GUI) and leverages OpenCV, ffmpeg, and other libraries for fast, flexible video processing.

>>>>>>> 4bfdca0 (Beautify the themes, half-way there)
---

## Features
- **Graphical Video Cropping**: Interactive crop region selection with drag-and-resize controls.
<<<<<<< HEAD
=======
- **Batch/Multi-Video Mode**: Efficiently process and export multiple videos at once.
- **YouTube Integration**: Download and crop YouTube videos directly (using bundled yt-dlp).
>>>>>>> 4bfdca0 (Beautify the themes, half-way there)
- **Scene Detection & Navigation**: Custom slider and navigation for video scenes.
- **Customizable UI**: Multiple retro and modern themes, icon sets, and layout options.
- **Session Restore**: Remembers your last session, folders, and settings.
- **System Monitoring**: Built-in CPU/GPU monitoring for heavy processing tasks.

---

<<<<<<< HEAD
=======
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

>>>>>>> 4bfdca0 (Beautify the themes, half-way there)
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
<<<<<<< HEAD
2. **Load Videos**: Select folders or paste YouTube URLs to add videos. Change line 509 in the cropper to set your own favorite folder.
3. **Preview & Crop**: Use the UI to set crop regions, navigate frames/scenes.
4. **Export**: Save cropped or uncropped videos.
=======
2. **Load Videos**: Select folders or paste YouTube URLs to add videos.
3. **Preview & Crop**: Use the UI to set crop regions, navigate frames/scenes.
4. **Export**: Save cropped or uncropped videos/images.
>>>>>>> 4bfdca0 (Beautify the themes, half-way there)
5. **Session Restore**: Previous state is auto-loaded from `session_data.json`.

---

<<<<<<< HEAD
## Credits
* [PyQt](https://riverbankcomputing.com/software/pyqt/)
* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* OpenCV
* Ffmpeg

---

DISCLAMER  
=======
## License
See `LICENSE` for details.

---

## Credits
- Developed by PointAve
- Uses open-source libraries (see requirements.txt)

---
>>>>>>> 4bfdca0 (Beautify the themes, half-way there)

For more details, see the code comments and individual module docstrings.
