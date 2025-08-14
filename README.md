# SharkBit

SharkBit is a desktop application for video cropping, editing, and exporting, with advanced features like scene detection and multi-video playback. Streamlined dataset generation by making all the shortcuts on one hand. There is a second tab accessible through the Shark Portal. Audio trimming easily with A and S key to set markers and B to export. To view video while editing audio files you need to click on audio file list first. App is not optimized yet but fully functional.

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

=======
- **Batch/Multi-Video Mode**: Efficiently process and export multiple videos at once.
- **YouTube Integration**: Download and crop YouTube videos directly (using bundled yt-dlp).
>>>>>>> 4bfdca0 (Beautify the themes, half-way there)
- **Scene Detection & Navigation**: Custom slider and navigation for video scenes.
- **Customizable UI**: Multiple retro and modern themes, icon sets, and layout options.
- **Session Restore**: Remembers your last session, folders, and settings.
- **System Monitoring**: Built-in CPU/GPU monitoring for heavy processing tasks.

---

## Typical Workflow
1. **Launch**: Run `main.py` to start the app.
2. **Cycle** Course through huge lists with the R and E shortcuts.
3. **Preview** If its clip worthy, click on the seekbar or press number key. Preview the trim with Z key.
4. **Tune** Fine tune with the A and S key to pick the best first frame of the clip, which by default is 113 frames.
5.  **Export** Use B key to export either a cropped or uncropped video file.
6.  **Report** Click on the folder you are currently in to refresh the folder and click into the uncropped folder.
7.  **Recycle** The delete button will send it to a  trash/backup folder so you can use it as a favorites or a dump bin.

1. **Prepare**  Choose a long video.
2. **Alternate** Click on Shark Portal.
3. **Reverberate** Click on audio file in the folder you have selected.
4. **Edit** Now you can edit with A and D keys to place markers.
5. **Map** Pinch, Scroll, Drag...The waveform allows you to pixel peek sounds.
6. **Export** Export with the B key. 

---

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
