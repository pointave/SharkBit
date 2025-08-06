# SharkBit

SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features like scene detection and multi-video playback. It provides a modern graphical user interface (GUI) and leverages OpenCV, ffmpeg, and other libraries for fast video processing.  ***EXPORT with shortcut B needs to have you push any number key first before it will export.*** 

---

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
| `Backspace` | Minimize                                                    |

> **Tip:** To have more videos playing at once, **Ctrl+click** on two or more videos in the file list.

---

## 🛠️ Installation

```bash
git clone https://github.com/pointave/SharkBit
cd sharkbit
conda create -n sharkbit python=3.12 -y
conda activate sharkbit
pip install -r requirements.txt
```

> **Optional:** Add `yt-dlp.exe` to the `sharkbit` folder to enable YouTube downloads.
> ALSO if you want you can install pytorch in the environment it will speed up exports.

---

## Features
- **Graphical Video Cropping**: Interactive crop region selection with drag-and-resize controls.
- **Scene Detection & Navigation**: Custom slider and navigation for video scenes.
- **Customizable UI**: Multiple retro and modern themes, icon sets, and layout options.
- **Session Restore**: Remembers your last session, folders, and settings.
- **System Monitoring**: Built-in CPU/GPU monitoring for heavy processing tasks.

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

## Credits
* [PyQt](https://riverbankcomputing.com/software/pyqt/)
* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* OpenCV
* Ffmpeg

---

DISCLAMER  
There is still no audio, should come in near future. The themes are wip as well, saw that new model on the llmarena that makes very modern UI's that I hope will make each pretty and unique.

For more details, see the code comments and individual module docstrings.
