# SharkBit

An efficient video tool for cycling through videos and making precise trims or captures, with intuitive keyboard shortcuts.

---

## 🔑 Shortcuts

| Key         | Action                                                      |
| ----------- | ----------------------------------------------------------- |
| `Q`         | Close program                                               |
| `W`         | Open current folder                                         |
| `E / R`     | Previous / Next file in list                                |
| `T`         | Fullscreen toggle                                           |
| `Y`         | Pull-out window                                             |
| `A / S`     | Step down / up one frame                                    |
| `D / F`     | Jump 113 frames (Shift/Ctrl doubles/quadruples jump amount) |
| `G`         | Jump to random frame                                        |
| `H`         | Remove crop selection                                       |
| `Z`         | Toggle trim preview                                         |
| `X`         | Auto-advance toggle                                         |
| `C`         | Screenshot                                                  |
| `V`         | Play / Pause                                                |
| `B`         | Save clip (cropped or uncropped)                            |
| `/`         | Search                                                      |
| `Backspace` | Minimize                                                    |

> **Tip:** To have more videos playing at once, **Ctrl+click** on two or more videos in the file list.

---

## 🖼️ UI Preview

![Screenshot 2025-07-04 115641](https://github.com/user-attachments/assets/07fc67da-8e1d-4623-9879-4fc1a0ced63a)

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

---

## 📁 Default Folder

By default, SharkBit opens to your **Videos** folder.
To change the default location:

1. Open `scripts/video_cropper.py`
2. Go to **line 216**
3. **Uncomment** the line for your custom path and **comment out** the one above it.

---

## 🙌 Credits

* [PyQt](https://riverbankcomputing.com/software/pyqt/)
* [yt-dlp](https://github.com/yt-dlp/yt-dlp)

---

Let me know if you want this saved as a `.md` file or edited further.
